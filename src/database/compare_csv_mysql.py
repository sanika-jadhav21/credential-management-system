"""
Read-only comparison of generated CSV files against MySQL tables.

Run from the project root:
    python -m src.database.compare_csv_mysql

This script does NOT insert, update, delete, truncate, or alter database data.
It compares row counts and primary-key sets, then checks key relationships.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

try:
    import mysql.connector
except ImportError:
    print(
        "Missing dependency: mysql-connector-python\n"
        "Install with: pip install mysql-connector-python",
        file=sys.stderr,
    )
    raise SystemExit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_NAME = os.getenv("DB_NAME", "credential_management_db")

# CSV file, SQL table, primary-key column
TABLES = [
    ("learners.csv", "learner", "learner_id"),
    ("courses.csv", "course", "course_id"),
    ("credential_rules.csv", "credential_rule", "rule_id"),
    ("completion_records.csv", "completion_record", "completion_id"),
    ("issuers.csv", "issuer", "issuer_id"),
    ("issuer_keys.csv", "issuer_key", "issuer_key_id"),
    ("credentials.csv", "credential", "credential_id"),
    ("revocations.csv", "revocation", "revocation_id"),
    ("verification_requests.csv", "verification_request", "verification_id"),
    ("audit_events.csv", "audit_event", "audit_event_id"),
]

# Read-only orphan checks for important foreign-key relationships.
ORPHAN_CHECKS = [
    (
        "completion_record -> learner",
        """SELECT COUNT(*) FROM completion_record cr
           LEFT JOIN learner l ON l.learner_id = cr.learner_id
           WHERE l.learner_id IS NULL""",
    ),
    (
        "completion_record -> course",
        """SELECT COUNT(*) FROM completion_record cr
           LEFT JOIN course c ON c.course_id = cr.course_id
           WHERE c.course_id IS NULL""",
    ),
    (
        "credential -> learner",
        """SELECT COUNT(*) FROM credential x
           LEFT JOIN learner l ON l.learner_id = x.learner_id
           WHERE l.learner_id IS NULL""",
    ),
    (
        "credential -> course",
        """SELECT COUNT(*) FROM credential x
           LEFT JOIN course c ON c.course_id = x.course_id
           WHERE c.course_id IS NULL""",
    ),
    (
        "credential -> completion (composite relationship)",
        """SELECT COUNT(*) FROM credential x
           LEFT JOIN completion_record cr
             ON cr.completion_id = x.completion_id
            AND cr.learner_id = x.learner_id
            AND cr.course_id = x.course_id
           WHERE cr.completion_id IS NULL""",
    ),
    (
        "credential -> rule and course",
        """SELECT COUNT(*) FROM credential x
           LEFT JOIN credential_rule r
             ON r.rule_id = x.rule_id AND r.course_id = x.course_id
           WHERE r.rule_id IS NULL""",
    ),
    (
        "credential -> issuer",
        """SELECT COUNT(*) FROM credential x
           LEFT JOIN issuer i ON i.issuer_id = x.issuer_id
           WHERE i.issuer_id IS NULL""",
    ),
    (
        "credential -> issuer key and issuer",
        """SELECT COUNT(*) FROM credential x
           LEFT JOIN issuer_key k
             ON k.issuer_key_id = x.issuer_key_id
            AND k.issuer_id = x.issuer_id
           WHERE k.issuer_key_id IS NULL""",
    ),
    (
        "revocation -> credential",
        """SELECT COUNT(*) FROM revocation r
           LEFT JOIN credential c ON c.credential_id = r.credential_id
           WHERE c.credential_id IS NULL""",
    ),
    (
        "verification_request -> credential (nullable)",
        """SELECT COUNT(*) FROM verification_request v
           LEFT JOIN credential c ON c.credential_id = v.credential_id
           WHERE v.credential_id IS NOT NULL AND c.credential_id IS NULL""",
    ),
]


def project_root() -> Path:
    # Expected location: <project>/src/database/compare_csv_mysql.py
    return Path(__file__).resolve().parents[2]


def read_csv_primary_keys(path: Path, pk_column: str) -> set[str]:
    if not path.is_file():
        raise FileNotFoundError(f"CSV not found: {path}")

    keys: set[str] = set()
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or pk_column not in reader.fieldnames:
            raise ValueError(
                f"Column '{pk_column}' not found in {path.name}. "
                f"Headers: {reader.fieldnames}"
            )

        for line_no, row in enumerate(reader, start=2):
            value = (row.get(pk_column) or "").strip()
            if not value:
                raise ValueError(
                    f"Blank primary key '{pk_column}' in {path.name}, "
                    f"line {line_no}."
                )
            if value in keys:
                raise ValueError(
                    f"Duplicate CSV primary key '{value}' in {path.name}."
                )
            keys.add(value)

    return keys


def main() -> int:
    root = project_root()
    raw_dir = root / "data" / "raw"

    required_env = ["DB_USER"]
    missing = [name for name in required_env if not os.getenv(name)]
    if missing:
        print("Missing .env setting(s): " + ", ".join(missing))
        print("Set DB_USER in your project .env file. DB_PASSWORD may be blank.")
        return 1

    print("CREDENTIAL MANAGEMENT SYSTEM")
    print("READ-ONLY CSV / MYSQL SYNCHRONIZATION CHECK")
    print("=" * 64)
    print(f"Project root: {root}")
    print(f"Database: {DATABASE_NAME}")
    print(f"CSV folder: {raw_dir}")
    print("Database changes: NONE (read-only)")
    print()

    connection = None
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD", ""),
            database=DATABASE_NAME,
        )
        cursor = connection.cursor()

        print("PRIMARY-KEY AND ROW-COUNT COMPARISON")
        print("-" * 64)
        all_match = True

        for filename, table, pk in TABLES:
            csv_keys = read_csv_primary_keys(raw_dir / filename, pk)
            cursor.execute(f"SELECT `{pk}` FROM `{table}`")
            db_keys = {str(row[0]) for row in cursor.fetchall()}

            count_match = len(csv_keys) == len(db_keys)
            ids_match = csv_keys == db_keys
            status = "PASS" if count_match and ids_match else "DIFFERENT"
            all_match = all_match and count_match and ids_match

            print(
                f"{table:<22} CSV={len(csv_keys):>7,}  "
                f"MySQL={len(db_keys):>7,}  {status}"
            )

            if not ids_match:
                missing_in_db = sorted(csv_keys - db_keys)
                extra_in_db = sorted(db_keys - csv_keys)
                if missing_in_db:
                    print(
                        f"  CSV IDs missing in MySQL ({len(missing_in_db)}): "
                        f"{', '.join(missing_in_db[:5])}"
                    )
                if extra_in_db:
                    print(
                        f"  MySQL IDs absent from CSV ({len(extra_in_db)}): "
                        f"{', '.join(extra_in_db[:5])}"
                    )

        print()
        print("FOREIGN-KEY RELATIONSHIP CHECKS")
        print("-" * 64)
        relationships_match = True

        for label, sql in ORPHAN_CHECKS:
            cursor.execute(sql)
            orphan_count = int(cursor.fetchone()[0])
            passed = orphan_count == 0
            relationships_match = relationships_match and passed
            print(f"{label:<52} {'PASS' if passed else f'FAIL ({orphan_count})'}")

        print()
        print("FINAL RESULT")
        print("-" * 64)
        print(f"CSV / MySQL primary-key synchronization: {'PASS' if all_match else 'REVIEW REQUIRED'}")
        print(f"Foreign-key relationship checks:         {'PASS' if relationships_match else 'REVIEW REQUIRED'}")
        print("No database records were modified.")

        cursor.close()
        return 0 if all_match and relationships_match else 2

    except mysql.connector.Error as exc:
        print(f"MySQL connection/query error: {exc}")
        return 1
    except Exception as exc:
        print(f"Comparison failed: {exc}")
        return 1
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
