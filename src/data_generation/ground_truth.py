"""
Create a separate, deterministic anomaly evaluation set.

Run from the project root:
    python -m src.data_generation.ground_truth

This script DOES NOT modify valid source CSVs or MySQL tables.
It creates:
    data/processed/ground_truth.csv
    data/processed/anomaly_cases.csv

The anomaly cases are controlled evaluation examples. They represent faulty
observations alongside rule-derived expected labels; they are not inserted
into the operational credential tables.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SEED = 20261022


def root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required source file not found: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = root_dir()
    raw = root / "data" / "raw"
    output = root / "data" / "processed"

    completions = read_csv(raw / "completion_records.csv")
    credentials = read_csv(raw / "credentials.csv")
    revocations = read_csv(raw / "revocations.csv")
    verifications = read_csv(raw / "verification_requests.csv")

    if not credentials or not completions:
        raise ValueError("Completion and credential source files must not be empty.")

    rng = random.Random(SEED)
    credential_by_id = {r["credential_id"]: r for r in credentials}
    revoked_ids = {r["credential_id"] for r in revocations}
    completion_by_id = {r["completion_id"]: r for r in completions}

    cases: list[dict[str, Any]] = []

    # 1. Credential issued before its completion date.
    credential_completion_ids = {x.get("completion_id") for x in credentials}
    completed_with_credentials = [
        c for c in completions
        if c.get("completion_status") == "COMPLETED"
        and c.get("completion_date")
        and c.get("completion_id") in credential_completion_ids
    ]
    if not completed_with_credentials:
        raise ValueError("No completed record linked to a credential was found.")
    c1 = completed_with_credentials[0]
    cred1 = next(x for x in credentials if x["completion_id"] == c1["completion_id"])
    completion_dt = datetime.fromisoformat(c1["completion_date"].replace("Z", "+00:00"))
    simulated_issue_date = (completion_dt - timedelta(days=1)).date().isoformat()
    cases.append({
        "anomaly_id": "ANM-0001",
        "issue_type": "CREDENTIAL_ISSUED_BEFORE_COMPLETION",
        "entity_type": "CREDENTIAL",
        "entity_id": cred1["credential_id"],
        "related_entity_id": c1["completion_id"],
        "observed_condition": json.dumps({
            "issue_date": simulated_issue_date,
            "completion_date": c1["completion_date"],
            "scenario": "Simulated issue date precedes completion date"
        }, sort_keys=True),
        "observed_result": "ISSUED",
        "ground_truth_label": "INVALID",
        "expected_outcome": "REJECT_ISSUANCE",
        "rule_basis": "Credential issue date must not precede successful completion date."
    })

    # 2. Duplicate credential ID. Duplicate exists only in this evaluation case,
    # not in credentials.csv or the production credential table.
    cred2 = credentials[1] if len(credentials) > 1 else credentials[0]
    cases.append({
        "anomaly_id": "ANM-0002",
        "issue_type": "DUPLICATE_CREDENTIAL_ID",
        "entity_type": "CREDENTIAL",
        "entity_id": cred2["credential_id"],
        "related_entity_id": cred2["completion_id"],
        "observed_condition": json.dumps({
            "credential_id_first_record": cred2["credential_id"],
            "credential_id_duplicate_record": cred2["credential_id"],
            "scenario": "A second record attempts to reuse the same credential ID"
        }, sort_keys=True),
        "observed_result": "DUPLICATE_INSERT_ATTEMPT",
        "ground_truth_label": "INVALID",
        "expected_outcome": "REJECT_DUPLICATE",
        "rule_basis": "credential_id is a primary key and must be unique."
    })

    # 3. Revoked credential incorrectly reported as VALID.
    revoked_verification = next(
        (v for v in verifications
         if v.get("credential_id") in revoked_ids
         and v.get("verification_result") == "REVOKED"),
        None
    )
    if revoked_verification is None:
        raise ValueError("Could not find a correct REVOKED verification to base the case on.")
    revoked_id = revoked_verification["credential_id"]
    cases.append({
        "anomaly_id": "ANM-0003",
        "issue_type": "REVOKED_CREDENTIAL_VERIFIED_AS_ACTIVE",
        "entity_type": "VERIFICATION_REQUEST",
        "entity_id": revoked_verification["verification_id"],
        "related_entity_id": revoked_id,
        "observed_condition": json.dumps({
            "credential_status": credential_by_id[revoked_id]["credential_status"],
            "simulated_system_result": "VALID",
            "scenario": "Incorrect verification response for a revoked credential"
        }, sort_keys=True),
        "observed_result": "VALID",
        "ground_truth_label": "INVALID",
        "expected_outcome": "REVOKED",
        "rule_basis": "A revoked credential must never be reported as valid."
    })

    # 4. Altered payload hash incorrectly accepted.
    hash_verification = next(
        (v for v in verifications
         if v.get("verification_result") == "HASH_MISMATCH"
         and v.get("checked_payload_hash")
         and v.get("provided_payload_hash")),
        None
    )
    if hash_verification is None:
        raise ValueError("Could not find a HASH_MISMATCH verification case.")
    cases.append({
        "anomaly_id": "ANM-0004",
        "issue_type": "ALTERED_PAYLOAD_HASH_NOT_DETECTED",
        "entity_type": "VERIFICATION_REQUEST",
        "entity_id": hash_verification["verification_id"],
        "related_entity_id": hash_verification["credential_id"],
        "observed_condition": json.dumps({
            "checked_payload_hash": hash_verification["checked_payload_hash"],
            "provided_payload_hash": hash_verification["provided_payload_hash"],
            "simulated_system_result": "VALID",
            "scenario": "Altered payload hash is incorrectly accepted"
        }, sort_keys=True),
        "observed_result": "VALID",
        "ground_truth_label": "INVALID",
        "expected_outcome": "HASH_MISMATCH",
        "rule_basis": "Provided payload hash must match the stored credential payload hash."
    })

    # Shuffle deterministically so row order does not encode the label.
    rng.shuffle(cases)

    fields = [
        "anomaly_id", "issue_type", "entity_type", "entity_id",
        "related_entity_id", "observed_condition", "observed_result",
        "ground_truth_label", "expected_outcome", "rule_basis"
    ]
    write_csv(output / "ground_truth.csv", cases, fields)

    # A separate, readable anomaly case file for review/demo purposes.
    write_csv(output / "anomaly_cases.csv", cases, fields)

    # Reproducibility checksum of the exact ground-truth output.
    serialized = json.dumps(cases, sort_keys=True, ensure_ascii=False).encode("utf-8")
    checksum = hashlib.sha256(serialized).hexdigest()

    print("GROUND-TRUTH DATASET CREATED")
    print("=" * 48)
    print(f"Anomaly cases: {len(cases)}")
    for row in sorted(cases, key=lambda x: x["anomaly_id"]):
        print(f'{row["anomaly_id"]}: {row["issue_type"]} -> {row["expected_outcome"]}')
    print(f"Ground truth: {output / 'ground_truth.csv'}")
    print(f"Anomaly cases: {output / 'anomaly_cases.csv'}")
    print(f"SHA-256 checksum: {checksum}")
    print("Operational CSV files and MySQL tables were not modified.")


if __name__ == "__main__":
    main()
