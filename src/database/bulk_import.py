"""Import all ten generated CSV files into the staging database.

Run from the project root:
    python -m src.database.bulk_import

This importer deliberately targets credential_management_staging_db and never
uses DB_NAME from .env, so the original database is not modified.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterator

try:
    import mysql.connector
except ImportError:
    print("Missing dependency: mysql-connector-python. Install with: pip install mysql-connector-python", file=sys.stderr)
    raise SystemExit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_NAME = "credential_management_staging_db"
BATCH_SIZE = 1000

# Parent tables first, then dependent tables. Column names must match CSV headers
# and database schema exactly.
IMPORT_PLAN: list[tuple[str, str, list[str]]] = [
    ("learners.csv", "learner", [
        "learner_id", "first_name", "last_name", "email", "phone",
        "date_of_birth", "registration_date", "learner_status",
        "created_at", "updated_at",
    ]),
    ("courses.csv", "course", [
        "course_id", "course_code", "course_name", "description", "category",
        "duration_hours", "total_modules", "course_status", "effective_from",
        "effective_to", "created_at", "updated_at",
    ]),
    ("credential_rules.csv", "credential_rule", [
        "rule_id", "course_id", "rule_version", "min_assessment_score",
        "min_attendance_pct", "min_completion_pct", "require_all_modules",
        "require_assessment_pass", "effective_from", "effective_to",
        "rule_status", "created_at",
    ]),
    ("issuers.csv", "issuer", [
        "issuer_id", "issuer_name", "organization_name", "issuer_email",
        "issuer_status", "created_at", "updated_at",
    ]),
    ("issuer_keys.csv", "issuer_key", [
        "issuer_key_id", "issuer_id", "key_version", "signing_key_id",
        "public_key", "key_algorithm", "key_status", "valid_from", "valid_to",
        "created_at",
    ]),
    ("completion_records.csv", "completion_record", [
        "completion_id", "learner_id", "course_id", "enrollment_date",
        "completion_date", "completion_pct", "attendance_pct",
        "assessment_score", "assessment_attempts", "modules_completed",
        "completion_status", "assessment_status", "instructor_reference",
        "created_at", "updated_at",
    ]),
    ("credentials.csv", "credential", [
        "credential_id", "learner_id", "course_id", "completion_id", "rule_id",
        "issuer_id", "issuer_key_id", "issuance_number", "issue_date",
        "valid_from", "expires_at", "credential_status", "payload_hash",
        "hash_algorithm", "signature_value", "signature_algorithm", "created_at",
    ]),
    ("revocations.csv", "revocation", [
        "revocation_id", "credential_id", "revocation_sequence", "revoked_at",
        "effective_at", "reason_code", "reason_description", "revoked_by_role",
        "revoked_by_reference",
    ]),
    ("verification_requests.csv", "verification_request", [
        "verification_id", "submitted_credential_id", "credential_id",
        "verifier_organization", "verifier_reference", "request_timestamp",
        "response_timestamp", "verification_result", "verification_reason",
        "checked_payload_hash", "provided_payload_hash", "response_time_ms",
        "request_channel",
    ]),
    ("audit_events.csv", "audit_event", [
        "audit_event_id", "event_type", "event_timestamp", "actor_role",
        "actor_reference", "target_entity_type", "learner_id", "course_id",
        "rule_id", "completion_id", "credential_id", "issuer_id",
        "verification_id", "revocation_id", "previous_state", "new_state",
        "event_metadata", "correlation_id", "created_at",
    ]),
]

JSON_COLUMNS = {"audit_event": {"previous_state", "new_state", "event_metadata"}}
BOOLEAN_COLUMNS = {"credential_rule": {"require_all_modules", "require_assessment_pass"}}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize_value(table: str, column: str, value: str | None) -> Any:
    if value is None or value == "":
        return None
    if column in BOOLEAN_COLUMNS.get(table, set()):
        v = value.strip().lower()
        if v in {"true", "1", "yes"}:
            return 1
        if v in {"false", "0", "no"}:
            return 0
        raise ValueError(f"Invalid boolean at {table}.{column}: {value!r}")
    if column in JSON_COLUMNS.get(table, set()):
        json.loads(value)
    return value


def read_csv_rows(path: Path, expected_columns: list[str], table: str) -> Iterator[tuple[Any, ...]]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing CSV: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        actual = reader.fieldnames or []
        if actual != expected_columns:
            raise ValueError(
                f"CSV header mismatch for {path.name}.\n"
                f"Expected: {expected_columns}\nActual:   {actual}"
            )
        for line_no, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"Extra CSV values in {path.name}, line {line_no}")
            yield tuple(normalize_value(table, col, row[col]) for col in expected_columns)


def table_count(cursor, table: str) -> int:
    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
    return int(cursor.fetchone()[0])


def validate_all_files(raw_dir: Path) -> None:
    for filename, table, columns in IMPORT_PLAN:
        path = raw_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Required file missing: {path}")
        # Read and validate headers before opening the DB transaction.
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            header = next(csv.reader(f), [])
        if header != columns:
            raise ValueError(
                f"CSV header mismatch for {filename}.\nExpected: {columns}\nActual:   {header}"
            )


def insert_table(cursor, raw_dir: Path, filename: str, table: str, columns: list[str]) -> int:
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(f"`{c}`" for c in columns)
    sql = f"INSERT INTO `{table}` ({column_sql}) VALUES ({placeholders})"
    batch: list[tuple[Any, ...]] = []
    inserted = 0
    for row in read_csv_rows(raw_dir / filename, columns, table):
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            cursor.executemany(sql, batch)
            inserted += len(batch)
            batch.clear()
    if batch:
        cursor.executemany(sql, batch)
        inserted += len(batch)
    return inserted


def main() -> int:
    root = project_root()
    raw_dir = root / "data" / "raw"
    print("CREDENTIAL MANAGEMENT SYSTEM | STAGING CSV IMPORT")
    print(f"Project root : {root}")
    print(f"Target DB    : {DATABASE_NAME}")
    print(f"CSV folder   : {raw_dir}")

    missing_env = [k for k in ("DB_USER",) if not os.getenv(k)]
    if missing_env:
        print("Missing .env setting(s): " + ", ".join(missing_env))
        return 1

    connection = None
    cursor = None
    try:
        validate_all_files(raw_dir)
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD", ""),
            database=DATABASE_NAME,
            charset="utf8mb4",
            use_unicode=True,
            autocommit=False,
        )
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        selected_db = cursor.fetchone()[0]
        if selected_db != DATABASE_NAME:
            raise RuntimeError(f"Safety check failed: connected to {selected_db!r}")

        # Refuse to mix with any earlier/partial import. No rows are deleted.
        populated = []
        for _, table, _ in IMPORT_PLAN:
            count = table_count(cursor, table)
            if count:
                populated.append(f"{table}={count:,}")
        if populated:
            raise RuntimeError(
                "Import stopped: staging tables are not empty: " + ", ".join(populated)
                + ". No data was inserted. Do not truncate; inspect the staging DB first."
            )

        print("\nImport started. All 10 tables will be inserted in FK-safe order.")
        total = 0
        for filename, table, columns in IMPORT_PLAN:
            count = insert_table(cursor, raw_dir, filename, table, columns)
            print(f"{table:<24} {count:>10,} rows inserted")
            total += count

        connection.commit()
        print("\nIMPORT COMMITTED SUCCESSFULLY")
        print(f"Total rows inserted: {total:,}")
        print("\nFINAL TABLE COUNTS")
        for _, table, _ in IMPORT_PLAN:
            print(f"{table:<24} {table_count(cursor, table):>10,}")
        return 0

    except Exception as exc:
        if connection is not None:
            connection.rollback()
        print("\nIMPORT FAILED; transaction rolled back.")
        print(f"Reason: {exc}")
        return 1
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
