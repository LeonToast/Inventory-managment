import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.workspace.main import app
from backend.workspace.security import issue_token, password_hash


class FakeMembers:
    def __init__(self, *documents):
        self.documents = list(documents)

    def _matches(self, document, query):
        return all(document.get(key) == value for key, value in query.items() if not isinstance(value, dict))

    def find_one(self, query, _projection=None):
        # The login query uses a case-insensitive regex on email; the fake matches on the pattern's text.
        if isinstance(query.get("email"), dict):
            pattern = query["email"]["$regex"].strip("^$").replace("\\", "")
            return next((d for d in self.documents if d["email"].lower() == pattern.lower()), None)
        return next((d for d in self.documents if self._matches(d, query)), None)

    def find(self, _query, _projection=None):
        return self

    def sort(self, *_args):
        return list(self.documents)

    def update_one(self, query, update):
        for document in self.documents:
            if self._matches(document, query):
                document.update(update["$set"])


class SessionTimestampTests(unittest.TestCase):
    def setUp(self):
        self.member = {
            "_id": "1", "name": "Mia", "email": "mia@example.com", "role": "Medlem",
            "password_hash": password_hash.hash("hemligt123"),
        }
        self.members = FakeMembers(self.member)

    def test_login_and_logout_are_recorded_and_listed(self):
        with (
            patch("backend.workspace.routers.auth.members_collection", return_value=self.members),
            patch("backend.workspace.routers.members.members_collection", return_value=self.members),
            TestClient(app) as client,
        ):
            listed = client.get("/members").json()[0]
            self.assertIsNone(listed["last_login_at"])
            self.assertIsNone(listed["last_logout_at"])

            login = client.post("/login", json={"email": "mia@example.com", "password": "hemligt123"})
            self.assertEqual(login.status_code, 200)
            self.assertIsInstance(self.member["last_login_at"], datetime)

            self.assertEqual(client.post("/logout").status_code, 401)
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            self.assertEqual(client.post("/logout", headers=headers).status_code, 200)

            listed = client.get("/members").json()[0]
            self.assertTrue(listed["last_login_at"].endswith("+00:00"))
            self.assertTrue(listed["last_logout_at"].endswith("+00:00"))

    def test_naive_mongo_datetimes_are_returned_as_utc(self):
        self.member["last_login_at"] = datetime(2026, 9, 29, 9, 58)
        with patch("backend.workspace.routers.members.members_collection", return_value=self.members):
            with TestClient(app) as client:
                listed = client.get("/members").json()[0]
                self.assertEqual(listed["last_login_at"], "2026-09-29T09:58:00+00:00")

    def test_online_status_follows_login_heartbeat_and_logout(self):
        with (
            patch("backend.workspace.routers.auth.members_collection", return_value=self.members),
            patch("backend.workspace.routers.members.members_collection", return_value=self.members),
            TestClient(app) as client,
        ):
            self.assertFalse(client.get("/members").json()[0]["online"])

            credentials = {"email": "mia@example.com", "password": "hemligt123"}
            token = client.post("/login", json=credentials).json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            self.assertTrue(client.get("/members").json()[0]["online"])

            # Browser closed without logging out: no heartbeat for a few minutes means offline.
            self.member["last_seen_at"] = datetime.now(timezone.utc) - timedelta(minutes=5)
            self.assertFalse(client.get("/members").json()[0]["online"])

            self.assertEqual(client.post("/heartbeat").status_code, 401)
            self.assertEqual(client.post("/heartbeat", headers=headers).status_code, 200)
            self.assertTrue(client.get("/members").json()[0]["online"])

            client.post("/logout", headers=headers)
            self.assertFalse(client.get("/members").json()[0]["online"])

    def test_dev_admin_logout_does_not_fail(self):
        with patch("backend.workspace.routers.auth.members_collection", return_value=FakeMembers()):
            with TestClient(app) as client:
                headers = {"Authorization": f"Bearer {issue_token('admin@dev.local', 'Admin')}"}
                self.assertEqual(client.post("/logout", headers=headers).status_code, 200)


if __name__ == "__main__":
    unittest.main()
