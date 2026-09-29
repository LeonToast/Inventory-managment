import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError

from backend.workspace.main import app
from backend.workspace.security import issue_token


class FakeReports(list):
    def create_index(self, *_args, **_kwargs):
        return "serial_number"

    def find(self, query, _projection=None):
        return FakeReports(report for report in self if report["kind"] == query["kind"])

    def sort(self, key, direction):
        return sorted(self, key=lambda report: report[key], reverse=direction == -1)

    def insert_one(self, document):
        if any(report["serial_number"] == document["serial_number"] for report in self):
            raise DuplicateKeyError("duplicate serial number")
        document = {**document, "_id": str(len(self) + 1)}
        self.append(document)
        return type("InsertResult", (), {"inserted_id": document["_id"]})()


class DamageReportApiTests(unittest.TestCase):
    def test_member_and_admin_can_report_without_double_counting(self):
        reports = FakeReports()

        target = "backend.workspace.routers.damage_reports.reports_collection"
        with patch(target, return_value=reports):
            with TestClient(app) as client:
                member_token = issue_token("member@example.com", "Medlem")
                admin_token = issue_token("admin@example.com", "Admin")
                member_headers = {"Authorization": f"Bearer {member_token}"}
                admin_headers = {"Authorization": f"Bearer {admin_token}"}
                payload = {"material_id": "MAT-1024", "serial_number": "abc-123"}

                self.assertEqual(client.post("/damage-reports", json=payload).status_code, 401)
                created = client.post("/damage-reports", headers=member_headers, json=payload)
                self.assertEqual(created.status_code, 201)
                self.assertEqual(created.json()["serial_number"], "ABC-123")

                duplicate = client.post("/damage-reports", headers=admin_headers, json=payload)
                self.assertEqual(duplicate.status_code, 409)
                self.assertEqual(len(reports), 1)

                listed = client.get("/damage-reports", headers=admin_headers)
                self.assertEqual(listed.status_code, 200)
                self.assertEqual(len(listed.json()), 1)


if __name__ == "__main__":
    unittest.main()
