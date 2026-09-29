import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.fakes import FakeActivity, FakeAnnouncements
from backend.workspace.main import app
from backend.workspace.security import issue_token

COLLECTION = "backend.workspace.routers.announcements.announcements_collection"
ACTIVITY = "backend.workspace.routers.activity.activity_collection"
NEW = {"title": "Nya rutiner", "text": "Läs igenom checklistan.", "category": "Viktigt"}
NO_SUCH_ID = "0" * 24


def headers(role):
    return {"Authorization": f"Bearer {issue_token(f'{role}@example.com', role)}"}


class AnnouncementApiTests(unittest.TestCase):
    def setUp(self):
        # Creating an announcement also writes to the activity feed; keep that off the real database.
        patcher = patch(ACTIVITY, return_value=FakeActivity())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_admin_creates_and_everyone_lists_newest_first(self):
        with patch(COLLECTION, return_value=FakeAnnouncements()), TestClient(app) as client:
            self.assertEqual(client.get("/announcements").status_code, 401)
            self.assertEqual(client.get("/announcements", headers=headers("Medlem")).json(), [])

            for title in ("Första", "Andra", "Tredje"):
                created = client.post(
                    "/announcements", headers=headers("Admin"), json={**NEW, "title": title}
                )
                self.assertEqual(created.status_code, 201)
            body = created.json()
            self.assertEqual(sorted(body), ["category", "created_at", "id", "text", "title"])
            self.assertTrue(body["created_at"].endswith("+00:00"))

            listed = client.get("/announcements", headers=headers("Medlem")).json()
            self.assertEqual([item["title"] for item in listed], ["Tredje", "Andra", "Första"])

    def test_naive_mongo_timestamps_are_returned_as_utc(self):
        stored = FakeAnnouncements(
            [{"_id": "a" * 24, **NEW, "created_at": datetime(2026, 9, 29, 9, 58)}]
        )
        with patch(COLLECTION, return_value=stored), TestClient(app) as client:
            listed = client.get("/announcements", headers=headers("Medlem")).json()
            self.assertEqual(listed[0]["created_at"], "2026-09-29T09:58:00+00:00")

    def test_members_can_list_but_not_create_or_delete(self):
        with patch(COLLECTION, return_value=FakeAnnouncements()), TestClient(app) as client:
            created = client.post("/announcements", headers=headers("Admin"), json=NEW).json()
            member = headers("Medlem")
            url = f"/announcements/{created['id']}"

            self.assertEqual(client.get("/announcements", headers=member).status_code, 200)
            self.assertEqual(
                client.post("/announcements", headers=member, json=NEW).status_code, 403
            )
            self.assertEqual(client.post("/announcements", json=NEW).status_code, 401)
            self.assertEqual(client.delete(url, headers=member).status_code, 403)
            self.assertEqual(client.delete(url).status_code, 401)
            self.assertEqual(len(client.get("/announcements", headers=member).json()), 1)

    def test_admin_deletes_an_announcement(self):
        with patch(COLLECTION, return_value=FakeAnnouncements()), TestClient(app) as client:
            admin = headers("Admin")
            keep = client.post("/announcements", headers=admin, json=NEW).json()
            drop = client.post("/announcements", headers=admin, json=NEW).json()
            url = f"/announcements/{drop['id']}"

            self.assertEqual(client.delete(url, headers=admin).status_code, 200)
            missing = client.delete(url, headers=admin)
            self.assertEqual(missing.status_code, 404)
            self.assertEqual(missing.json()["detail"], "Meddelandet hittades inte")
            unknown = client.delete(f"/announcements/{NO_SUCH_ID}", headers=admin)
            self.assertEqual(unknown.status_code, 404)
            bad_id = client.delete("/announcements/inte-ett-id", headers=admin)
            self.assertEqual(bad_id.status_code, 400)

            listed = client.get("/announcements", headers=admin).json()
            self.assertEqual([item["id"] for item in listed], [keep["id"]])

    def test_validation(self):
        with patch(COLLECTION, return_value=FakeAnnouncements()), TestClient(app) as client:
            admin = headers("Admin")
            for bad in (
                {**NEW, "title": "   "},
                {**NEW, "title": "x" * 121},
                {**NEW, "text": ""},
                {**NEW, "text": "x" * 2001},
                {**NEW, "category": "Annat"},
                {"title": "Bara rubrik"},
            ):
                response = client.post("/announcements", headers=admin, json=bad)
                self.assertEqual(response.status_code, 422)

            longest = {**NEW, "title": "x" * 120, "text": "y" * 2000}
            self.assertEqual(
                client.post("/announcements", headers=admin, json=longest).status_code, 201
            )

    def test_fields_the_server_sets_cannot_be_chosen_by_the_client(self):
        stored = FakeAnnouncements()
        with patch(COLLECTION, return_value=stored), TestClient(app) as client:
            sent = {**NEW, "created_by": "någon@annan.se", "created_at": "2001-01-01T00:00:00Z"}
            created = client.post("/announcements", headers=headers("Admin"), json=sent).json()
            self.assertEqual(stored[0]["created_by"], "Admin@example.com")
            posted = datetime.fromisoformat(created["created_at"])
            self.assertGreater(posted, datetime(2020, 1, 1, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
