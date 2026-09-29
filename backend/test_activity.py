import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

from backend.fakes import FakeActivity, FakeAnnouncements, FakeMaterials, FakeReports
from backend.workspace.main import app
from backend.workspace.security import issue_token

ROUTERS = "backend.workspace.routers"
MATERIAL = {
    "name": "Kabeltrumma 25m",
    "category": "Elektronik",
    "warehouse": "Lager A",
    "quantity": 12,
    "unit": "st",
}
ANNOUNCEMENT = {"title": "Nya rutiner", "text": "Läs igenom checklistan.", "category": "Viktigt"}


def headers(role):
    return {"Authorization": f"Bearer {issue_token(f'{role}@example.com', role)}"}


class ActivityApiTests(unittest.TestCase):
    def setUp(self):
        self.activity = FakeActivity()
        self.materials = FakeMaterials()
        self.reports = FakeReports()
        for target, fake in (
            (f"{ROUTERS}.activity.activity_collection", self.activity),
            (f"{ROUTERS}.announcements.announcements_collection", FakeAnnouncements()),
            (f"{ROUTERS}.materials.materials_collection", self.materials),
            (f"{ROUTERS}.materials.reports_collection", self.reports),
            (f"{ROUTERS}.damage_reports.materials_collection", self.materials),
            (f"{ROUTERS}.damage_reports.reports_collection", self.reports),
        ):
            patcher = patch(target, return_value=fake)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def feed(self):
        return self.client.get("/activity", headers=headers("Medlem")).json()

    def test_feed_requires_login_and_starts_empty(self):
        self.assertEqual(self.client.get("/activity").status_code, 401)
        self.assertEqual(self.feed(), [])

    def test_creating_a_material_is_logged(self):
        created = self.client.post("/materials", headers=headers("Admin"), json=MATERIAL)
        self.assertEqual(created.status_code, 201)

        [entry] = self.feed()
        self.assertEqual(entry["kind"], "material")
        self.assertEqual(entry["title"], "Nytt material skapat")
        self.assertEqual(entry["description"], "Kabeltrumma 25m · 12 st · Lager A")
        self.assertTrue(entry["created_at"].endswith("+00:00"))

    def test_a_material_without_a_warehouse_has_no_empty_part_in_its_description(self):
        without = {**MATERIAL, "warehouse": ""}
        self.client.post("/materials", headers=headers("Admin"), json=without)
        self.assertEqual(self.feed()[0]["description"], "Kabeltrumma 25m · 12 st")

    def test_publishing_a_report_is_logged(self):
        created = self.client.post("/announcements", headers=headers("Admin"), json=ANNOUNCEMENT)
        self.assertEqual(created.status_code, 201)

        [entry] = self.feed()
        self.assertEqual(entry["kind"], "report")
        self.assertEqual(entry["title"], "Ny rapport publicerad")
        self.assertEqual(entry["description"], "Nya rutiner")

    def test_reporting_damage_is_logged_with_material_name_and_serial_number(self):
        material = self.client.post("/materials", headers=headers("Admin"), json=MATERIAL).json()
        payload = {"material_id": material["id"], "serial_number": "abc-123"}
        created = self.client.post("/damage-reports", headers=headers("Medlem"), json=payload)
        self.assertEqual(created.status_code, 201)

        damage = self.feed()[0]
        self.assertEqual(damage["kind"], "damage")
        self.assertEqual(damage["title"], "Skada rapporterad")
        self.assertEqual(damage["description"], "Kabeltrumma 25m · ABC-123")

    def test_only_the_five_latest_are_kept_and_the_oldest_is_deleted(self):
        for number in range(7):
            name = {**MATERIAL, "name": f"Material {number}"}
            self.client.post("/materials", headers=headers("Admin"), json=name)
            self.assertLessEqual(len(self.activity), 5)

        descriptions = [entry["description"] for entry in self.feed()]
        self.assertEqual(len(descriptions), 5)
        self.assertTrue(descriptions[0].startswith("Material 6 "))
        self.assertTrue(descriptions[-1].startswith("Material 2 "))
        # The two oldest are gone from the collection itself, not just hidden.
        stored = [entry["description"] for entry in self.activity]
        self.assertFalse(any(text.startswith(("Material 0 ", "Material 1 ")) for text in stored))

    def test_the_feed_trims_a_collection_that_is_already_too_long(self):
        for number in range(8):
            self.activity.insert_one(
                {
                    "kind": "material",
                    "title": "Nytt material skapat",
                    "description": f"Gammal {number}",
                    "created_by": "Admin@example.com",
                    "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                }
            )
        self.client.post("/materials", headers=headers("Admin"), json=MATERIAL)

        self.assertEqual(len(self.activity), 5)
        descriptions = [entry["description"] for entry in self.feed()]
        self.assertEqual(descriptions[0], "Kabeltrumma 25m · 12 st · Lager A")
        self.assertEqual(descriptions[-1], "Gammal 4")

    def test_entries_from_all_three_kinds_are_mixed_in_order(self):
        material = self.client.post("/materials", headers=headers("Admin"), json=MATERIAL).json()
        self.client.post("/announcements", headers=headers("Admin"), json=ANNOUNCEMENT)
        payload = {"material_id": material["id"], "serial_number": "S1"}
        self.client.post("/damage-reports", headers=headers("Admin"), json=payload)

        self.assertEqual([entry["kind"] for entry in self.feed()], ["damage", "report", "material"])

    def test_the_response_does_not_reveal_who_did_it(self):
        self.client.post("/materials", headers=headers("Admin"), json=MATERIAL)
        self.assertEqual(
            sorted(self.feed()[0]), ["created_at", "description", "id", "kind", "title"]
        )
        self.assertEqual(self.activity[0]["created_by"], "Admin@example.com")

    def test_actions_that_fail_are_not_logged(self):
        admin, member = headers("Admin"), headers("Medlem")
        invalid = {**MATERIAL, "quantity": -1}
        self.assertEqual(self.client.post("/materials", headers=admin, json=invalid).status_code, 422)
        self.assertEqual(self.client.post("/materials", headers=member, json=MATERIAL).status_code, 403)
        self.assertEqual(
            self.client.post("/announcements", headers=member, json=ANNOUNCEMENT).status_code, 403
        )
        unknown = {"material_id": "b" * 24, "serial_number": "S1"}
        self.assertEqual(
            self.client.post("/damage-reports", headers=member, json=unknown).status_code, 422
        )

        material = self.client.post("/materials", headers=admin, json=MATERIAL).json()
        payload = {"material_id": material["id"], "serial_number": "S1"}
        self.client.post("/damage-reports", headers=member, json=payload)
        duplicate = self.client.post("/damage-reports", headers=member, json=payload)
        self.assertEqual(duplicate.status_code, 409)

        self.assertEqual([entry["kind"] for entry in self.feed()], ["damage", "material"])

    def test_editing_and_deleting_are_not_logged(self):
        admin = headers("Admin")
        material = self.client.post("/materials", headers=admin, json=MATERIAL).json()
        edit = {**MATERIAL, "quantity": 1}
        self.client.patch(f"/materials/{material['id']}", headers=admin, json=edit)
        self.client.delete(f"/materials/{material['id']}", headers=admin)
        self.assertEqual(len(self.feed()), 1)

    def test_a_failure_to_log_does_not_fail_the_action(self):
        broken = patch(f"{ROUTERS}.activity.activity_collection", side_effect=PyMongoError("down"))
        with broken, self.assertLogs(f"{ROUTERS}.activity", level="ERROR"):
            created = self.client.post("/materials", headers=headers("Admin"), json=MATERIAL)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(len(self.materials), 1)


if __name__ == "__main__":
    unittest.main()
