import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.fakes import FakeActivity, FakeMaterials, FakeReports
from backend.workspace.main import app
from backend.workspace.security import issue_token

ACTIVITY = "backend.workspace.routers.activity.activity_collection"


class DamageReportApiTests(unittest.TestCase):
    def test_member_and_admin_can_report_without_double_counting(self):
        reports = FakeReports()
        material_id = "a" * 24
        materials = FakeMaterials([{"_id": material_id, "name": "Kabeltrumma 25m"}])

        module = "backend.workspace.routers.damage_reports"
        with (
            patch(f"{module}.reports_collection", return_value=reports),
            patch(f"{module}.materials_collection", return_value=materials),
            patch(ACTIVITY, return_value=FakeActivity()),
        ):
            with TestClient(app) as client:
                member_token = issue_token("member@example.com", "Medlem")
                admin_token = issue_token("admin@example.com", "Admin")
                member_headers = {"Authorization": f"Bearer {member_token}"}
                admin_headers = {"Authorization": f"Bearer {admin_token}"}
                payload = {"material_id": material_id, "serial_number": "abc-123"}

                self.assertEqual(client.post("/damage-reports", json=payload).status_code, 401)
                created = client.post("/damage-reports", headers=member_headers, json=payload)
                self.assertEqual(created.status_code, 201)
                self.assertEqual(created.json()["serial_number"], "ABC-123")

                for unknown_id in ("b" * 24, "MAT-9999"):
                    unknown = {"material_id": unknown_id, "serial_number": "XYZ-1"}
                    rejected = client.post("/damage-reports", headers=member_headers, json=unknown)
                    self.assertEqual(rejected.status_code, 422)

                duplicate = client.post("/damage-reports", headers=admin_headers, json=payload)
                self.assertEqual(duplicate.status_code, 409)
                self.assertEqual(len(reports), 1)

                listed = client.get("/damage-reports", headers=admin_headers)
                self.assertEqual(listed.status_code, 200)
                self.assertEqual(len(listed.json()), 1)
                self.assertEqual(listed.json()[0]["material_id"], material_id)


if __name__ == "__main__":
    unittest.main()
