"""
Controlled, reproducible evaluation for the Credential Management System.

Run from the project root:
    python -m src.data_generation.evaluate

Read-only inputs:
    data/raw/credentials.csv
    data/raw/completion_records.csv
    data/raw/verification_requests.csv
    data/raw/revocations.csv
    data/processed/ground_truth.csv

Outputs:
    data/processed/evaluation_dataset.csv
    data/processed/evaluation_metrics.json
    data/processed/evaluation_report.txt

The anomaly detector does NOT use issue_type to decide its prediction.
It applies all independent business checks to each observed condition.
The four injected anomalies and four matching normal controls are scored
separately from source-data quality checks.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEED = 20261022
SUPPORTED_ANOMALIES = {
    "CREDENTIAL_ISSUED_BEFORE_COMPLETION",
    "DUPLICATE_CREDENTIAL_ID",
    "REVOKED_CREDENTIAL_VERIFIED_AS_ACTIVE",
    "ALTERED_PAYLOAD_HASH_NOT_DETECTED",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required input file not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "case_id", "case_group", "issue_type", "entity_id",
        "ground_truth_label", "predicted_label", "test_passed",
        "detection_reason", "expected_outcome",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_datetime(value: str) -> datetime:
    value = str(value).strip()
    if not value:
        raise ValueError("Required date/time value is blank.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def safe_json(value: str) -> dict[str, Any]:
    try:
        obj = json.loads(value)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Invalid observed_condition JSON: {value}") from exc
    if not isinstance(obj, dict):
        raise ValueError("observed_condition must be a JSON object.")
    return obj


def independent_rule_engine(details: dict[str, Any]) -> tuple[str, str]:
    """
    Apply every relevant check from observed values.
    No issue_type, ground-truth label, or expected outcome is read here.
    """
    violations: list[str] = []

    issue_date = details.get("issue_date")
    completion_date = details.get("completion_date")
    if issue_date and completion_date:
        if parse_datetime(issue_date) < parse_datetime(completion_date):
            violations.append("credential issue date is earlier than completion date")

    # Check uniqueness using the two attempted record IDs as an actual set test.
    attempted_ids = details.get("credential_ids")
    if attempted_ids is None:
        first_id = details.get("credential_id_first_record")
        second_id = details.get("credential_id_duplicate_record")
        attempted_ids = [first_id, second_id] if first_id or second_id else []
    attempted_ids = [str(x) for x in attempted_ids if x not in (None, "")]
    if len(attempted_ids) != len(set(attempted_ids)):
        violations.append("credential ID uniqueness constraint was violated")

    if (
        details.get("credential_status") == "REVOKED"
        and details.get("simulated_system_result") == "VALID"
    ):
        violations.append("revoked credential was incorrectly accepted as VALID")

    checked_hash = details.get("checked_payload_hash", "")
    provided_hash = details.get("provided_payload_hash", "")
    if (
        checked_hash and provided_hash
        and checked_hash.lower() != provided_hash.lower()
        and details.get("simulated_system_result") == "VALID"
    ):
        violations.append("payload hash mismatch was incorrectly accepted as VALID")

    if violations:
        return "ANOMALY", "; ".join(violations)
    return "NORMAL", "all applicable business-rule checks passed"


def make_normal_control(issue_type: str, source_details: dict[str, Any]) -> dict[str, Any]:
    """Create a paired valid control by correcting only the target condition."""
    details = dict(source_details)

    if issue_type == "CREDENTIAL_ISSUED_BEFORE_COMPLETION":
        details["issue_date"] = details["completion_date"]
    elif issue_type == "DUPLICATE_CREDENTIAL_ID":
        first = details.get("credential_id_first_record", "CRD-TEST-000001")
        details["credential_id_first_record"] = first
        details["credential_id_duplicate_record"] = f"{first}-UNIQUE"
        details["credential_ids"] = [first, f"{first}-UNIQUE"]
    elif issue_type == "REVOKED_CREDENTIAL_VERIFIED_AS_ACTIVE":
        details["simulated_system_result"] = "REVOKED"
    elif issue_type == "ALTERED_PAYLOAD_HASH_NOT_DETECTED":
        details["simulated_system_result"] = "HASH_MISMATCH"
    else:
        raise ValueError(f"Unsupported anomaly type: {issue_type}")

    return details


def validate_ground_truth(rows: list[dict[str, str]]) -> None:
    required = {
        "anomaly_id", "issue_type", "entity_type", "entity_id",
        "related_entity_id", "observed_condition", "ground_truth_label",
        "expected_outcome",
    }
    if not rows:
        raise ValueError("ground_truth.csv has no records.")
    missing = required - set(rows[0])
    if missing:
        raise ValueError("ground_truth.csv missing columns: " + ", ".join(sorted(missing)))

    seen: set[str] = set()
    types: set[str] = set()
    for row in rows:
        case_id = row["anomaly_id"].strip()
        if not case_id or case_id in seen:
            raise ValueError(f"Blank or duplicate anomaly_id: {case_id!r}")
        seen.add(case_id)
        if row["issue_type"] not in SUPPORTED_ANOMALIES:
            raise ValueError(f"Unsupported issue_type: {row['issue_type']}")
        if row["ground_truth_label"] != "INVALID":
            raise ValueError(
                f"{case_id}: expected ground_truth_label INVALID from ground_truth generator."
            )
        if not row["expected_outcome"].strip():
            raise ValueError(f"{case_id}: expected_outcome is blank.")
        safe_json(row["observed_condition"])
        types.add(row["issue_type"])

    missing_types = SUPPORTED_ANOMALIES - types
    if missing_types:
        raise ValueError("Missing anomaly type(s): " + ", ".join(sorted(missing_types)))
    if len(rows) != len(SUPPORTED_ANOMALIES):
        raise ValueError(
            "Expected exactly one independently generated case per supported anomaly type; "
            f"found {len(rows)}."
        )


def binary_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(r["ground_truth_label"] == "ANOMALY" and r["predicted_label"] == "ANOMALY" for r in rows)
    tn = sum(r["ground_truth_label"] == "NORMAL" and r["predicted_label"] == "NORMAL" for r in rows)
    fp = sum(r["ground_truth_label"] == "NORMAL" and r["predicted_label"] == "ANOMALY" for r in rows)
    fn = sum(r["ground_truth_label"] == "ANOMALY" and r["predicted_label"] == "NORMAL" for r in rows)
    total = len(rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "total_cases": total,
        "confusion_matrix": {
            "true_positive": tp, "true_negative": tn,
            "false_positive": fp, "false_negative": fn,
        },
        "accuracy": round((tp + tn) / total, 4) if total else 0.0,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
    }


def main() -> None:
    root = project_root()
    raw = root / "data" / "raw"
    processed = root / "data" / "processed"

    credentials = read_csv(raw / "credentials.csv")
    completions = read_csv(raw / "completion_records.csv")
    verifications = read_csv(raw / "verification_requests.csv")
    revocations = read_csv(raw / "revocations.csv")
    ground_truth = read_csv(processed / "ground_truth.csv")
    validate_ground_truth(ground_truth)

    # Source integrity checks are reported separately and never injected into MySQL.
    credential_ids = [r["credential_id"] for r in credentials]
    completion_ids = [r["completion_id"] for r in completions]
    if len(credential_ids) != len(set(credential_ids)):
        raise ValueError("Duplicate credential_id found in operational source CSV.")
    if len(completion_ids) != len(set(completion_ids)):
        raise ValueError("Duplicate completion_id found in operational source CSV.")

    completion_by_id = {r["completion_id"]: r for r in completions}
    source_findings: list[dict[str, str]] = []
    for credential in credentials:
        completion = completion_by_id.get(credential["completion_id"])
        if completion is None:
            source_findings.append({
                "entity_id": credential["credential_id"],
                "finding": "missing completion parent",
            })
            continue
        if completion.get("completion_status") != "COMPLETED" or not completion.get("completion_date"):
            source_findings.append({
                "entity_id": credential["credential_id"],
                "finding": "credential linked to non-completed completion",
            })
            continue
        if parse_datetime(credential["issue_date"]) < parse_datetime(completion["completion_date"]):
            source_findings.append({
                "entity_id": credential["credential_id"],
                "finding": "issue date precedes completion date",
            })
        payload_hash = credential.get("payload_hash", "")
        try:
            valid_hash = len(payload_hash) == 64 and int(payload_hash, 16) >= 0
        except ValueError:
            valid_hash = False
        if credential.get("hash_algorithm") != "SHA256" or not valid_hash:
            source_findings.append({
                "entity_id": credential["credential_id"],
                "finding": "invalid SHA256 hash metadata",
            })

    scored: list[dict[str, Any]] = []
    for gt in ground_truth:
        details = safe_json(gt["observed_condition"])
        prediction, reason = independent_rule_engine(details)
        scored.append({
            "case_id": gt["anomaly_id"],
            "case_group": "ANOMALY",
            "issue_type": gt["issue_type"],
            "entity_id": gt["entity_id"],
            "ground_truth_label": "ANOMALY",
            "predicted_label": prediction,
            "test_passed": prediction == "ANOMALY",
            "detection_reason": reason,
            "expected_outcome": gt["expected_outcome"],
        })

        # Paired normal control: same observed structure, only target defect corrected.
        normal_details = make_normal_control(gt["issue_type"], details)
        normal_prediction, normal_reason = independent_rule_engine(normal_details)
        scored.append({
            "case_id": f"CTRL-{gt['anomaly_id']}",
            "case_group": "NORMAL_CONTROL",
            "issue_type": gt["issue_type"],
            "entity_id": gt["entity_id"],
            "ground_truth_label": "NORMAL",
            "predicted_label": normal_prediction,
            "test_passed": normal_prediction == "NORMAL",
            "detection_reason": normal_reason,
            "expected_outcome": "ACCEPT_OR_CORRECT_STATUS",
        })

    anomaly_rows = [r for r in scored if r["case_group"] == "ANOMALY"]
    normal_rows = [r for r in scored if r["case_group"] == "NORMAL_CONTROL"]
    if len(anomaly_rows) != 4 or len(normal_rows) != 4:
        raise AssertionError("Evaluation suite must contain four anomaly and four normal controls.")

    metrics = {
        "evaluation_type": "controlled_synthetic_rule_engine_test",
        "seed": SEED,
        "scoring_scope": "4 independently labelled anomaly fixtures plus 4 paired normal controls",
        "overall": binary_metrics(scored),
        "normal_controls": binary_metrics(normal_rows),
        "anomaly_cases": binary_metrics(anomaly_rows),
        "per_anomaly_type": {},
        "coverage": {
            "supported_anomaly_types": sorted(SUPPORTED_ANOMALIES),
            "anomaly_cases": len(anomaly_rows),
            "normal_control_cases": len(normal_rows),
            "all_anomaly_types_covered": {k: any(r["issue_type"] == k for r in anomaly_rows) for k in sorted(SUPPORTED_ANOMALIES)},
        },
        "source_data_quality": {
            "credentials_read": len(credentials),
            "completion_records_read": len(completions),
            "source_rule_findings": len(source_findings),
            "findings": source_findings,
        },
        "operational_counts": {
            "verification_requests": len(verifications),
            "revocation_records": len(revocations),
            "valid_verification_responses": sum(r.get("verification_result") == "VALID" for r in verifications),
            "revoked_verification_responses": sum(r.get("verification_result") == "REVOKED" for r in verifications),
        },
        "limitations": [
            "These are controlled synthetic rule-engine test metrics, not machine-learning metrics.",
            "The test suite contains four anomaly fixtures and four paired normal controls; it does not establish real-world generalization.",
            "Source data-quality findings are reported separately and are not mixed into the fixture confusion matrix.",
            "The hash scenario compares the observed checked and provided hashes; it does not constitute a production digital-signature implementation.",
        ],
    }

    for issue_type in sorted(SUPPORTED_ANOMALIES):
        group = [r for r in scored if r["issue_type"] == issue_type]
        metrics["per_anomaly_type"][issue_type] = {
            "cases": len(group),
            "passed": sum(bool(r["test_passed"]) for r in group),
            "failed": sum(not bool(r["test_passed"]) for r in group),
            "details": [
                {"case_id": r["case_id"], "expected": r["ground_truth_label"],
                 "predicted": r["predicted_label"], "passed": r["test_passed"]}
                for r in group
            ],
        }

    # Deterministic row order and checksum.
    scored.sort(key=lambda r: r["case_id"])
    write_csv(processed / "evaluation_dataset.csv", scored)
    serialized = json.dumps(scored, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    checksum = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    metrics["reproducibility"] = {
        "evaluation_dataset_sha256": checksum,
        "fixed_seed": SEED,
        "source_files_modified": False,
        "mysql_modified": False,
    }

    metrics_path = processed / "evaluation_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    report_lines = [
        "CREDENTIAL MANAGEMENT SYSTEM",
        "CONTROLLED RULE-ENGINE EVALUATION REPORT",
        "=" * 60,
        f"Anomaly fixtures: {len(anomaly_rows)}",
        f"Normal controls: {len(normal_rows)}",
        f"Total scored cases: {len(scored)}",
        f"Passed test cases: {sum(bool(r['test_passed']) for r in scored)}",
        f"Failed test cases: {sum(not bool(r['test_passed']) for r in scored)}",
        "",
        "OVERALL METRICS",
        json.dumps(metrics["overall"], indent=2),
        "",
        "PER-ANOMALY COVERAGE",
        json.dumps(metrics["per_anomaly_type"], indent=2),
        "",
        f"Source data-quality findings: {len(source_findings)}",
        f"Verification requests: {len(verifications)}",
        f"Revocation records: {len(revocations)}",
        f"Evaluation SHA-256: {checksum}",
        "",
        "Metrics describe controlled synthetic rule-engine tests, not ML performance.",
        "Operational CSV files and MySQL tables were not modified.",
    ]
    (processed / "evaluation_report.txt").write_text("\n".join(report_lines), encoding="utf-8")

    print("\n".join(report_lines))


if __name__ == "__main__":
    main()
