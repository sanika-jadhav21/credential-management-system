import unittest

from src.data_generation.evaluate import (
    independent_rule_engine,
    make_normal_control,
)


class EvaluationRuleTests(unittest.TestCase):
    def test_all_four_anomaly_types_and_controls(self):
        cases = [
            ("CREDENTIAL_ISSUED_BEFORE_COMPLETION", {
                "issue_date": "2026-01-01",
                "completion_date": "2026-01-02",
            }),
            ("DUPLICATE_CREDENTIAL_ID", {
                "credential_id_first_record": "CRD-1",
                "credential_id_duplicate_record": "CRD-1",
            }),
            ("REVOKED_CREDENTIAL_VERIFIED_AS_ACTIVE", {
                "credential_status": "REVOKED",
                "simulated_system_result": "VALID",
            }),
            ("ALTERED_PAYLOAD_HASH_NOT_DETECTED", {
                "checked_payload_hash": "a" * 64,
                "provided_payload_hash": "b" * 64,
                "simulated_system_result": "VALID",
            }),
        ]

        for issue_type, details in cases:
            with self.subTest(issue_type=issue_type):
                prediction, _ = independent_rule_engine(details)
                self.assertEqual(prediction, "ANOMALY")

                normal_control = make_normal_control(issue_type, details)
                control_prediction, _ = independent_rule_engine(normal_control)
                self.assertEqual(control_prediction, "NORMAL")


if __name__ == "__main__":
    unittest.main()
