import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.fakes import FakeActivity, FakeMaterials, FakeReports
from backend.workspace.main import app
from backend.workspace.security import issue_token

MODULE = "backend.workspace.routers.materials"
ACTIVITY = "backend.workspace.routers.activity.activity_collection"
NO_SUCH_ID = "0" * 24
NEW_MATERIAL = {
    "name": "Kabeltrumma 25m",
    "category": "Elektronik",
    "warehouse": "Lager A",
    "quantity": 12,
    "unit": "st",
}


def headers(role):
    return {"Authorization": f"Bearer {issue_token(f'{role}@example.com', role)}"}


def fake_database(materials=None, reports=None):
    # An empty fake is falsy, so test against None rather than using `or`.
    materials = FakeMaterials() if materials is None else materials
    reports = FakeReports() if reports is None else reports
    return (
        patch(f"{MODULE}.materials_collection", return_value=materials),
        patch(f"{MODULE}.reports_collection", return_value=reports),
    )


class MaterialApiTests(unittest.TestCase):
    def setUp(self):
        # Adding a material also writes to the activity feed; keep that off the real database.
        patcher = patch(ACTIVITY, return_value=FakeActivity())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_admin_adds_material_and_everyone_can_list_it(self):
        materials, reports = fake_database()
        with materials, reports, TestClient(app) as client:
            self.assertEqual(client.get("/materials").status_code, 401)
            self.assertEqual(client.get("/materials", headers=headers("Medlem")).json(), [])

            created = client.post("/materials", headers=headers("Admin"), json=NEW_MATERIAL)
            self.assertEqual(created.status_code, 201)
            self.assertEqual(created.json()["quantity"], 12)

            listed = client.get("/materials", headers=headers("Medlem")).json()
            self.assertEqual([item["name"] for item in listed], ["Kabeltrumma 25m"])
            self.assertEqual(listed[0]["id"], created.json()["id"])

    def test_only_the_form_values_are_stored(self):
        stored = FakeMaterials()
        materials, reports = fake_database(stored)
        with materials, reports, TestClient(app) as client:
            sent = {**NEW_MATERIAL, "article_number": "MAT-9999", "section": "Sektion 3"}
            created = client.post("/materials", headers=headers("Admin"), json=sent)
            self.assertEqual(created.status_code, 201)

            self.assertEqual(len(stored), 1)
            self.assertEqual({k: v for k, v in stored[0].items() if k != "_id"}, NEW_MATERIAL)
            self.assertEqual(
                sorted(created.json()), ["category", "id", "name", "quantity", "unit", "warehouse"]
            )

    def test_materials_are_listed_in_the_order_they_were_added(self):
        materials, reports = fake_database()
        with materials, reports, TestClient(app) as client:
            for name in ("Först", "Andra", "Tredje"):
                client.post("/materials", headers=headers("Admin"), json={**NEW_MATERIAL, "name": name})
            listed = client.get("/materials", headers=headers("Medlem")).json()
            self.assertEqual([item["name"] for item in listed], ["Först", "Andra", "Tredje"])

    def test_location_is_optional(self):
        required_only = {key: NEW_MATERIAL[key] for key in ("name", "category", "quantity", "unit")}
        materials, reports = fake_database()
        with materials, reports, TestClient(app) as client:
            created = client.post("/materials", headers=headers("Admin"), json=required_only)
            self.assertEqual(created.status_code, 201)
            self.assertEqual(created.json()["warehouse"], "")

    def test_only_admins_can_add_materials(self):
        materials, reports = fake_database()
        with materials, reports, TestClient(app) as client:
            self.assertEqual(client.post("/materials", json=NEW_MATERIAL).status_code, 401)
            member = client.post("/materials", headers=headers("Medlem"), json=NEW_MATERIAL)
            self.assertEqual(member.status_code, 403)

    def test_rejects_invalid_input(self):
        materials, reports = fake_database()
        with materials, reports, TestClient(app) as client:
            for bad in (
                {**NEW_MATERIAL, "quantity": -1},
                {**NEW_MATERIAL, "name": "   "},
                {**NEW_MATERIAL, "category": "Annat"},
                {**NEW_MATERIAL, "unit": ""},
            ):
                response = client.post("/materials", headers=headers("Admin"), json=bad)
                self.assertEqual(response.status_code, 422)

    def test_admin_edits_a_material(self):
        materials, reports = fake_database()
        with materials, reports, TestClient(app) as client:
            admin = headers("Admin")
            created = client.post("/materials", headers=admin, json=NEW_MATERIAL).json()
            edit = {
                "name": "Kabeltrumma 50m",
                "category": "Utrustning",
                "warehouse": "Lager B",
                "quantity": 3,
                "unit": "m",
            }

            updated = client.patch(f"/materials/{created['id']}", headers=admin, json=edit)
            self.assertEqual(updated.status_code, 200)
            self.assertEqual(updated.json(), {"id": created["id"], **edit})

            listed = client.get("/materials", headers=headers("Medlem")).json()
            self.assertEqual([(m["name"], m["unit"]) for m in listed], [("Kabeltrumma 50m", "m")])

    def test_editing_checks_permissions_input_and_ids(self):
        materials, reports = fake_database()
        with materials, reports, TestClient(app) as client:
            admin = headers("Admin")
            material = client.post("/materials", headers=admin, json=NEW_MATERIAL).json()
            url = f"/materials/{material['id']}"

            self.assertEqual(client.patch(url, json=NEW_MATERIAL).status_code, 401)
            member = client.patch(url, headers=headers("Medlem"), json=NEW_MATERIAL)
            self.assertEqual(member.status_code, 403)

            negative = client.patch(url, headers=admin, json={**NEW_MATERIAL, "quantity": -1})
            self.assertEqual(negative.status_code, 422)
            blank = client.patch(url, headers=admin, json={**NEW_MATERIAL, "name": " "})
            self.assertEqual(blank.status_code, 422)

            missing = client.patch(f"/materials/{NO_SUCH_ID}", headers=admin, json=NEW_MATERIAL)
            self.assertEqual(missing.status_code, 404)
            self.assertEqual(missing.json()["detail"], "Materialet hittades inte")
            bad_id = client.patch("/materials/inte-ett-id", headers=admin, json=NEW_MATERIAL)
            self.assertEqual(bad_id.status_code, 400)

    def test_admin_deletes_a_material(self):
        materials, reports = fake_database()
        with materials, reports, TestClient(app) as client:
            admin = headers("Admin")
            first = client.post("/materials", headers=admin, json=NEW_MATERIAL).json()
            second = client.post("/materials", headers=admin, json=NEW_MATERIAL).json()
            url = f"/materials/{second['id']}"

            self.assertEqual(client.delete(url).status_code, 401)
            self.assertEqual(client.delete(url, headers=headers("Medlem")).status_code, 403)

            self.assertEqual(client.delete(url, headers=admin).status_code, 200)
            self.assertEqual(client.delete(url, headers=admin).status_code, 404)
            self.assertEqual(
                client.delete("/materials/inte-ett-id", headers=admin).status_code, 400
            )

            listed = client.get("/materials", headers=admin).json()
            self.assertEqual([m["id"] for m in listed], [first["id"]])

    def test_a_material_with_damage_reports_cannot_be_deleted(self):
        damage = FakeReports()
        materials, reports = fake_database(reports=damage)
        with materials, reports, TestClient(app) as client:
            admin = headers("Admin")
            damaged = client.post("/materials", headers=admin, json=NEW_MATERIAL).json()
            clean = client.post("/materials", headers=admin, json=NEW_MATERIAL).json()
            damage.insert_one(
                {"kind": "damage", "material_id": damaged["id"], "serial_number": "S1"}
            )

            blocked = client.delete(f"/materials/{damaged['id']}", headers=admin)
            self.assertEqual(blocked.status_code, 409)
            self.assertEqual(
                blocked.json()["detail"],
                "Materialet har rapporterade skador och kan inte tas bort.",
            )
            self.assertEqual(len(client.get("/materials", headers=admin).json()), 2)

            self.assertEqual(
                client.delete(f"/materials/{clean['id']}", headers=admin).status_code, 200
            )
            self.assertEqual(len(client.get("/materials", headers=admin).json()), 1)


if __name__ == "__main__":
    unittest.main()
