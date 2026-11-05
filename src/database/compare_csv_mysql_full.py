"""
Full read-only CSV vs MySQL comparison.

Compares:
- Row counts
- Primary-key sets
- Every CSV column against the corresponding MySQL column
- JSON values semantically (ignores key order and whitespace)
- Important foreign-key relationships

Run from project root:
    python -m src.database.compare_csv_mysql_full

The script performs SELECT queries only.
It never modifies database records.
"""

from __future__ import annotations

import csv
import json
import os
import sys

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import mysql.connector

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)

except ImportError:
    pass


# ============================================================
# CONFIGURATION
# ============================================================

DATABASE_NAME = os.getenv(
    "DB_NAME",
    "credential_management_staging_db"
)

RAW_DIR_NAME = "raw"

MAX_EXAMPLES_PER_COLUMN = 5


# These columns are generated automatically by MySQL.
# They are intentionally absent from the CSV files.

DATABASE_GENERATED_COLUMNS = {
    ("revocation", "created_at"),
    ("verification_request", "created_at"),
}


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
    (
        "verification_requests.csv",
        "verification_request",
        "verification_id"
    ),
    ("audit_events.csv", "audit_event", "audit_event_id"),
]


# ============================================================
# FOREIGN KEY CHECKS
# ============================================================

ORPHAN_CHECKS = [

    (
        "completion_record -> learner",
        """
        SELECT COUNT(*)
        FROM completion_record cr
        LEFT JOIN learner l
            ON l.learner_id = cr.learner_id
        WHERE l.learner_id IS NULL
        """
    ),

    (
        "completion_record -> course",
        """
        SELECT COUNT(*)
        FROM completion_record cr
        LEFT JOIN course c
            ON c.course_id = cr.course_id
        WHERE c.course_id IS NULL
        """
    ),

    (
        "credential -> learner",
        """
        SELECT COUNT(*)
        FROM credential x
        LEFT JOIN learner l
            ON l.learner_id = x.learner_id
        WHERE l.learner_id IS NULL
        """
    ),

    (
        "credential -> course",
        """
        SELECT COUNT(*)
        FROM credential x
        LEFT JOIN course c
            ON c.course_id = x.course_id
        WHERE c.course_id IS NULL
        """
    ),

    (
        "credential -> completion (composite)",
        """
        SELECT COUNT(*)
        FROM credential x
        LEFT JOIN completion_record cr
            ON cr.completion_id = x.completion_id
            AND cr.learner_id = x.learner_id
            AND cr.course_id = x.course_id
        WHERE cr.completion_id IS NULL
        """
    ),

    (
        "credential -> rule and course",
        """
        SELECT COUNT(*)
        FROM credential x
        LEFT JOIN credential_rule r
            ON r.rule_id = x.rule_id
            AND r.course_id = x.course_id
        WHERE r.rule_id IS NULL
        """
    ),

    (
        "credential -> issuer",
        """
        SELECT COUNT(*)
        FROM credential x
        LEFT JOIN issuer i
            ON i.issuer_id = x.issuer_id
        WHERE i.issuer_id IS NULL
        """
    ),

    (
        "credential -> issuer key and issuer",
        """
        SELECT COUNT(*)
        FROM credential x
        LEFT JOIN issuer_key k
            ON k.issuer_key_id = x.issuer_key_id
            AND k.issuer_id = x.issuer_id
        WHERE k.issuer_key_id IS NULL
        """
    ),

    (
        "revocation -> credential",
        """
        SELECT COUNT(*)
        FROM revocation r
        LEFT JOIN credential c
            ON c.credential_id = r.credential_id
        WHERE c.credential_id IS NULL
        """
    ),

    (
        "verification_request -> credential (nullable)",
        """
        SELECT COUNT(*)
        FROM verification_request v
        LEFT JOIN credential c
            ON c.credential_id = v.credential_id
        WHERE v.credential_id IS NOT NULL
            AND c.credential_id IS NULL
        """
    ),

]


# ============================================================
# PROJECT PATH
# ============================================================

def project_root() -> Path:
    """
    Return project root directory.

    Expected structure:
        project/
            src/
                database/
                    compare_csv_mysql_full.py
    """

    return Path(__file__).resolve().parents[2]


# ============================================================
# CSV VALUE PARSING
# ============================================================

def parse_csv_value(
    raw: str | None,
    column: dict[str, Any]
) -> Any:

    """
    Convert CSV text according to MySQL column metadata.
    """

    if raw is None:
        return None

    data_type = str(column["DATA_TYPE"]).lower()

    nullable = column["IS_NULLABLE"] == "YES"

    value = raw.strip()

    # CSV empty values represent SQL NULL for nullable columns.

    if value == "" and nullable:
        return None

    # Integer types

    if data_type in {
        "tinyint",
        "smallint",
        "mediumint",
        "int",
        "bigint"
    }:

        return int(value) if value != "" else value

    # Decimal and floating-point types

    if data_type in {
        "decimal",
        "numeric",
        "float",
        "double",
        "real"
    }:

        return Decimal(value) if value != "" else value

    # DATE

    if data_type == "date":

        return date.fromisoformat(value) if value else value

    # DATETIME and TIMESTAMP

    if data_type in {"datetime", "timestamp"}:

        if not value:
            return value

        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    # TIME

    if data_type == "time":

        return time.fromisoformat(value) if value else value

    # YEAR

    if data_type == "year":

        return int(value) if value else value

    # ENUM and SET

    if data_type in {"enum", "set"}:

        return value

    # Binary types

    if data_type in {
        "binary",
        "varbinary",
        "blob",
        "tinyblob",
        "mediumblob",
        "longblob"
    }:

        return value.encode("utf-8")

    # JSON and text columns remain strings here.
    # JSON normalization is handled separately.

    return value


# ============================================================
# MYSQL VALUE NORMALIZATION
# ============================================================

def normalize_db_value(value: Any) -> Any:

    """
    Normalize MySQL values before comparison.
    """

    if value is None:
        return None

    if isinstance(value, Decimal):

        return value.normalize()

    if isinstance(value, datetime):

        if value.tzinfo is None:
            return value

        return value.isoformat()

    if isinstance(value, date):

        return value

    if isinstance(value, time):

        return value

    if isinstance(value, bytearray):

        return bytes(value)

    return value


# ============================================================
# JSON NORMALIZATION
# ============================================================

def normalize_json_value(value: Any) -> Any:

    """
    Canonicalize JSON values.

    JSON object key order and insignificant whitespace
    do not change the underlying JSON value.

    Example:

    CSV:
        {"name":"ABC","status":"ACTIVE"}

    MySQL:
        {"status": "ACTIVE", "name": "ABC"}

    Both values will be treated as equal.
    """

    if value is None:
        return None

    parsed = value

    # MySQL connector may return JSON as a string.

    if isinstance(value, str):

        text = value.strip()

        if not text:
            return value

        if text.startswith("{") or text.startswith("["):

            try:

                parsed = json.loads(text)

            except json.JSONDecodeError:

                return value

        else:

            return value

    # Normalize JSON objects and arrays.

    if isinstance(parsed, (dict, list)):

        return json.dumps(
            parsed,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False
        )

    return parsed


# ============================================================
# VALUE COMPARISON
# ============================================================

def values_equal(
    csv_value: Any,
    db_value: Any
) -> bool:

    """
    Compare CSV and MySQL values safely.
    """

    left = csv_value

    right = normalize_db_value(db_value)

    # JSON semantic comparison.

    left_json = normalize_json_value(left)

    right_json = normalize_json_value(right)

    if left_json != left or right_json != right:

        return left_json == right_json

    # Decimal comparison.

    if isinstance(left, Decimal) and isinstance(
        right,
        (int, float, Decimal)
    ):

        try:

            return left == Decimal(str(right))

        except InvalidOperation:

            return False

    # Datetime comparison.

    if isinstance(left, datetime) and isinstance(
        right,
        datetime
    ):

        return left == right

    return left == right


# ============================================================
# FETCH TABLE METADATA
# ============================================================

def fetch_table_metadata(
    cursor,
    table: str
) -> tuple[
    list[str],
    dict[str, dict[str, Any]],
    list[str]
]:

    """
    Fetch column information from information_schema.
    """

    cursor.execute(
        """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            COLUMN_TYPE,
            IS_NULLABLE,
            ORDINAL_POSITION

        FROM information_schema.COLUMNS

        WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = %s

        ORDER BY ORDINAL_POSITION
        """,

        (DATABASE_NAME, table)
    )

    rows = cursor.fetchall()

    if not rows:

        raise RuntimeError(
            f"Table '{table}' was not found "
            f"in database '{DATABASE_NAME}'."
        )

    columns = [
        row["COLUMN_NAME"]
        for row in rows
    ]

    metadata = {
        row["COLUMN_NAME"]: row
        for row in rows
    }

    return columns, metadata, columns


# ============================================================
# COMPARE ONE TABLE
# ============================================================

def compare_one_table(
    cursor,
    root: Path,
    filename: str,
    table: str,
    pk: str
) -> tuple[bool, int]:

    """
    Compare one CSV file with its MySQL table.

    Checks:
    - Column structure
    - Primary keys
    - Row counts
    - Every available CSV column value
    """

    csv_path = (
        root
        / "data"
        / RAW_DIR_NAME
        / filename
    )

    if not csv_path.is_file():

        raise FileNotFoundError(
            f"CSV not found: {csv_path}"
        )

    sql_columns, metadata, _ = fetch_table_metadata(
        cursor,
        table
    )

    # --------------------------------------------------------
    # READ CSV
    # --------------------------------------------------------

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as handle:

        reader = csv.DictReader(handle)

        csv_columns = reader.fieldnames or []

        if not csv_columns:

            raise ValueError(
                f"No CSV header found in {filename}."
            )

        # Check missing columns.

        missing_in_csv = [

            column

            for column in sql_columns

            if column not in csv_columns

            and (
                table,
                column
            ) not in DATABASE_GENERATED_COLUMNS

        ]

        # Check extra columns.

        extra_in_csv = [

            column

            for column in csv_columns

            if column not in sql_columns

        ]

        if missing_in_csv or extra_in_csv:

            raise ValueError(
                f"Column mismatch for {table}. "
                f"Missing in CSV: {missing_in_csv}; "
                f"extra in CSV: {extra_in_csv}"
            )

        # Compare columns available in both CSV and MySQL.

        compare_columns = [

            column

            for column in csv_columns

            if column in metadata

        ]

        if pk not in compare_columns:

            raise ValueError(
                f"Primary key '{pk}' missing from {filename}."
            )

        csv_rows: dict[str, dict[str, Any]] = {}

        # Read and parse all CSV rows.

        for line_no, raw_row in enumerate(
            reader,
            start=2
        ):

            key = (
                raw_row.get(pk) or ""
            ).strip()

            if not key:

                raise ValueError(
                    f"Blank primary key in {filename}, "
                    f"line {line_no}."
                )

            if key in csv_rows:

                raise ValueError(
                    f"Duplicate CSV primary key '{key}' "
                    f"in {filename}."
                )

            parsed = {

                column: parse_csv_value(
                    raw_row.get(column),
                    metadata[column]
                )

                for column in compare_columns

            }

            csv_rows[key] = parsed

    # --------------------------------------------------------
    # READ MYSQL TABLE
    # --------------------------------------------------------

    quoted_columns = ", ".join(

        f"`{column}`"

        for column in compare_columns

    )

    cursor.execute(
        f"SELECT {quoted_columns} FROM `{table}`"
    )

    db_rows = cursor.fetchall()

    db_by_key: dict[str, dict[str, Any]] = {}

    for row in db_rows:

        key = str(row[pk])

        if key in db_by_key:

            raise RuntimeError(
                f"Duplicate primary key '{key}' "
                f"returned by MySQL table {table}."
            )

        db_by_key[key] = dict(row)

    # --------------------------------------------------------
    # PRIMARY KEY COMPARISON
    # --------------------------------------------------------

    csv_keys = set(csv_rows)

    db_keys = set(db_by_key)

    missing = sorted(
        csv_keys - db_keys
    )

    extra = sorted(
        db_keys - csv_keys
    )

    print(

        f"{table:<22} "
        f"CSV={len(csv_rows):>7,}  "
        f"MySQL={len(db_rows):>7,}  "

        f"{'PK PASS' if not missing and not extra else 'PK DIFFERENT'}"

    )

    if missing:

        print(
            f"  CSV rows missing in MySQL "
            f"({len(missing)}): "
            f"{', '.join(missing[:5])}"
        )

    if extra:

        print(
            f"  MySQL rows absent from CSV "
            f"({len(extra)}): "
            f"{', '.join(extra[:5])}"
        )

    # --------------------------------------------------------
    # COLUMN VALUE COMPARISON
    # --------------------------------------------------------

    differing_columns: dict[
        str,
        list[str]
    ] = {}

    total_cell_differences = 0

    common_keys = sorted(
        csv_keys & db_keys
    )

    for key in common_keys:

        expected = csv_rows[key]

        actual = db_by_key[key]

        for column in compare_columns:

            if not values_equal(
                expected[column],
                actual[column]
            ):

                total_cell_differences += 1

                differing_columns.setdefault(
                    column,
                    []
                )

                if (
                    len(differing_columns[column])
                    < MAX_EXAMPLES_PER_COLUMN
                ):

                    differing_columns[column].append(

                        f"{pk}={key}: "
                        f"CSV={expected[column]!r}, "
                        f"MySQL={actual[column]!r}"

                    )

    # --------------------------------------------------------
    # DISPLAY DIFFERENCES
    # --------------------------------------------------------

    if differing_columns:

        print(

            f"  VALUE DIFFERENCES: "
            f"{total_cell_differences:,} cell(s) "
            f"across {len(differing_columns)} column(s)"

        )

        for column, examples in differing_columns.items():

            print(
                f"    Column '{column}':"
            )

            for example in examples:

                print(
                    f"      {example}"
                )

    else:

        print(
            "  ALL COLUMN VALUES: PASS"
        )

    table_pass = (

        not missing

        and not extra

        and total_cell_differences == 0

    )

    return table_pass, total_cell_differences


# ============================================================
# MAIN FUNCTION
# ============================================================

def main() -> int:

    root = project_root()

    # Check environment variables.

    required_env = [
        "DB_USER"
    ]

    missing_env = [

        name

        for name in required_env

        if not os.getenv(name)

    ]

    if missing_env:

        print(
            "Missing .env setting(s): "
            + ", ".join(missing_env)
        )

        return 1

    print(
        "CREDENTIAL MANAGEMENT SYSTEM"
    )

    print(
        "FULL READ-ONLY CSV / MYSQL COMPARISON"
    )

    print(
        "=" * 76
    )

    print(
        f"Project root: {root}"
    )

    print(
        f"Database: {DATABASE_NAME}"
    )

    print(
        f"CSV folder: {root / 'data' / RAW_DIR_NAME}"
    )

    print(
        "Comparison: row counts, primary keys, "
        "every column value, and FK relationships"
    )

    print(
        "Database changes: NONE (SELECT queries only)"
    )

    print()

    connection = None

    cursor = None

    try:

        # ----------------------------------------------------
        # CONNECT TO MYSQL
        # ----------------------------------------------------

        connection = mysql.connector.connect(

            host=os.getenv(
                "DB_HOST",
                "localhost"
            ),

            port=int(
                os.getenv(
                    "DB_PORT",
                    "3306"
                )
            ),

            user=os.getenv(
                "DB_USER"
            ),

            password=os.getenv(
                "DB_PASSWORD",
                ""
            ),

            database=DATABASE_NAME

        )

        cursor = connection.cursor(
            dictionary=True
        )

        # ----------------------------------------------------
        # TABLE COMPARISON
        # ----------------------------------------------------

        print(
            "TABLE-BY-TABLE FULL VALUE COMPARISON"
        )

        print(
            "-" * 76
        )

        all_tables_match = True

        total_differences = 0

        for filename, table, pk in TABLES:

            passed, differences = compare_one_table(

                cursor,
                root,
                filename,
                table,
                pk

            )

            all_tables_match = (
                all_tables_match and passed
            )

            total_differences += differences

        # ----------------------------------------------------
        # FOREIGN KEY CHECKS
        # ----------------------------------------------------

        print()

        print(
            "FOREIGN-KEY RELATIONSHIP CHECKS"
        )

        print(
            "-" * 76
        )

        relationships_match = True

        for label, sql in ORPHAN_CHECKS:

            cursor.execute(sql)

            result = cursor.fetchone()

            orphan_count = int(
                result["COUNT(*)"]
            )

            passed = orphan_count == 0

            relationships_match = (
                relationships_match and passed
            )

            status = (
                "PASS"
                if passed
                else f"FAIL ({orphan_count:,})"
            )

            print(
                f"{label:<55} {status}"
            )

        # ----------------------------------------------------
        # FINAL RESULT
        # ----------------------------------------------------

        print()

        print(
            "FINAL RESULT"
        )

        print(
            "-" * 76
        )

        print(

            "All 10 tables fully match CSV: "

            + (
                "PASS"
                if all_tables_match
                else "REVIEW REQUIRED"
            )

        )

        print(
            f"Total differing cells:         "
            f"{total_differences:,}"
        )

        print(

            "Foreign-key checks:             "

            + (
                "PASS"
                if relationships_match
                else "REVIEW REQUIRED"
            )

        )

        print(
            "No database records were modified."
        )

        if all_tables_match and relationships_match:

            print()

            print(
                "CSV / MYSQL SYNCHRONIZATION: SUCCESS"
            )

            return 0

        else:

            print()

            print(
                "CSV / MYSQL SYNCHRONIZATION: REVIEW REQUIRED"
            )

            return 2

    # --------------------------------------------------------
    # ERROR HANDLING
    # --------------------------------------------------------

    except (
        mysql.connector.Error,
        OSError,
        ValueError,
        RuntimeError
    ) as exc:

        print()

        print(
            f"Comparison failed: {exc}"
        )

        return 1

    finally:

        if cursor is not None:

            cursor.close()

        if (
            connection is not None
            and connection.is_connected()
        ):

            connection.close()


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )