"""
Read-only data-quality and business-rule validation for Credential Management System.

Run from project root:
    python -m src.database.validate_data_quality

This script only executes SELECT queries. It never changes database records.
"""

from __future__ import annotations

import os
import sys

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
    load_dotenv(override=True)
except ImportError:
    pass


DATABASE_NAME = os.getenv("DB_NAME", "credential_management_db")


def run_count(cursor, label: str, sql: str) -> int:
    cursor.execute(sql)
    result = cursor.fetchone()
    count = int(result[0]) if result else 0
    status = "PASS" if count == 0 else f"REVIEW ({count})"
    print(f"{label:<58} {status}")
    return count


def main() -> int:
    if not os.getenv("DB_USER"):
        print("DB_USER is missing from your .env file.")
        return 1

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

        print("CREDENTIAL MANAGEMENT SYSTEM")
        print("READ-ONLY DATA QUALITY & BUSINESS RULE VALIDATION")
        print("=" * 78)
        print(f"Database: {DATABASE_NAME}")
        print("Database changes: NONE (SELECT queries only)")
        print()

        checks = [
            (
                "Duplicate credential issuance sequence",
                """
                SELECT COUNT(*) FROM (
                    SELECT completion_id, issuance_number
                    FROM credential
                    GROUP BY completion_id, issuance_number
                    HAVING COUNT(*) > 1
                ) duplicates_found
                """,
            ),
            (
                "Credential with missing or mismatched learner/course completion",
                """
                SELECT COUNT(*)
                FROM credential c
                LEFT JOIN completion_record cr
                  ON cr.completion_id = c.completion_id
                 AND cr.learner_id = c.learner_id
                 AND cr.course_id = c.course_id
                WHERE cr.completion_id IS NULL
                """,
            ),
            (
                "Credential issued without completed completion record",
                """
                SELECT COUNT(*)
                FROM credential c
                JOIN completion_record cr
                  ON cr.completion_id = c.completion_id
                 AND cr.learner_id = c.learner_id
                 AND cr.course_id = c.course_id
                WHERE cr.completion_status <> 'COMPLETED'
                   OR cr.completion_pct < 100
                   OR cr.completion_date IS NULL
                   OR cr.completion_date > c.issue_date
                """,
            ),
            (
                "Credential issued before credential rule effective date",
                """
                SELECT COUNT(*)
                FROM credential c
                JOIN credential_rule r
                  ON r.rule_id = c.rule_id AND r.course_id = c.course_id
                WHERE c.issue_date < r.effective_from
                   OR (r.effective_to IS NOT NULL
                       AND c.issue_date >= r.effective_to)
                """,
            ),
            (
                "Credential issued outside course effective dates",
                """
                SELECT COUNT(*)
                FROM credential c
                JOIN course co ON co.course_id = c.course_id
                WHERE c.issue_date < co.effective_from
                   OR (co.effective_to IS NOT NULL
                       AND c.issue_date >= co.effective_to)
                """,
            ),
            (
                "Credential failing attendance requirement",
                """
                SELECT COUNT(*)
                FROM credential c
                JOIN completion_record cr
                  ON cr.completion_id = c.completion_id
                 AND cr.learner_id = c.learner_id
                 AND cr.course_id = c.course_id
                JOIN credential_rule r
                  ON r.rule_id = c.rule_id AND r.course_id = c.course_id
                WHERE cr.attendance_pct < r.min_attendance_pct
                """,
            ),
            (
                "Credential failing completion percentage requirement",
                """
                SELECT COUNT(*)
                FROM credential c
                JOIN completion_record cr
                  ON cr.completion_id = c.completion_id
                 AND cr.learner_id = c.learner_id
                 AND cr.course_id = c.course_id
                JOIN credential_rule r
                  ON r.rule_id = c.rule_id AND r.course_id = c.course_id
                WHERE cr.completion_pct < r.min_completion_pct
                """,
            ),
            (
                "Credential failing required assessment pass",
                """
                SELECT COUNT(*)
                FROM credential c
                JOIN completion_record cr
                  ON cr.completion_id = c.completion_id
                 AND cr.learner_id = c.learner_id
                 AND cr.course_id = c.course_id
                JOIN credential_rule r
                  ON r.rule_id = c.rule_id AND r.course_id = c.course_id
                WHERE r.require_assessment_pass = 1
                  AND (
                    cr.assessment_status <> 'PASSED'
                    OR cr.assessment_score IS NULL
                    OR cr.assessment_score < r.min_assessment_score
                  )
                """,
            ),
            (
                "Credential failing required all-modules condition",
                """
                SELECT COUNT(*)
                FROM credential c
                JOIN completion_record cr
                  ON cr.completion_id = c.completion_id
                 AND cr.learner_id = c.learner_id
                 AND cr.course_id = c.course_id
                JOIN credential_rule r
                  ON r.rule_id = c.rule_id AND r.course_id = c.course_id
                JOIN course co ON co.course_id = c.course_id
                WHERE r.require_all_modules = 1
                  AND cr.modules_completed < co.total_modules
                """,
            ),
            (
                "Credential uses inactive learner",
                """
                SELECT COUNT(*)
                FROM credential c
                JOIN learner l ON l.learner_id = c.learner_id
                WHERE l.learner_status <> 'ACTIVE'
                """,
            ),
            (
                "Credential uses inactive/retired course",
                """
                SELECT COUNT(*)
                FROM credential c
                JOIN course co ON co.course_id = c.course_id
                WHERE co.course_status <> 'ACTIVE'
                """,
            ),
            (
                "Credential uses inactive/retired rule",
                """
                SELECT COUNT(*)
                FROM credential c
                JOIN credential_rule r
                  ON r.rule_id = c.rule_id AND r.course_id = c.course_id
                WHERE r.rule_status <> 'ACTIVE'
                """,
            ),
            (
                "Revocation record whose credential is not REVOKED",
                """
                SELECT COUNT(*)
                FROM revocation r
                JOIN credential c ON c.credential_id = r.credential_id
                WHERE c.credential_status <> 'REVOKED'
                """,
            ),
            (
                "REVOKED credential without revocation record",
                """
                SELECT COUNT(*)
                FROM credential c
                LEFT JOIN revocation r ON r.credential_id = c.credential_id
                WHERE c.credential_status = 'REVOKED'
                  AND r.revocation_id IS NULL
                """,
            ),
            (
                "Revocation effective date earlier than revocation creation",
                """
                SELECT COUNT(*)
                FROM revocation
                WHERE effective_at < revoked_at
                """,
            ),
            (
                "VALID verification linked to non-ACTIVE credential",
                """
                SELECT COUNT(*)
                FROM verification_request v
                JOIN credential c ON c.credential_id = v.credential_id
                WHERE v.verification_result = 'VALID'
                  AND c.credential_status <> 'ACTIVE'
                """,
            ),
            (
                "REVOKED verification linked to non-REVOKED credential",
                """
                SELECT COUNT(*)
                FROM verification_request v
                JOIN credential c ON c.credential_id = v.credential_id
                WHERE v.verification_result = 'REVOKED'
                  AND c.credential_status <> 'REVOKED'
                """,
            ),
            (
                "HASH_MISMATCH verification with equal supplied and stored hashes",
                """
                SELECT COUNT(*)
                FROM verification_request
                WHERE verification_result = 'HASH_MISMATCH'
                  AND checked_payload_hash = provided_payload_hash
                """,
            ),
            (
                "NOT_FOUND verification incorrectly linked to a credential",
                """
                SELECT COUNT(*)
                FROM verification_request
                WHERE verification_result = 'NOT_FOUND'
                  AND credential_id IS NOT NULL
                """,
            ),
            (
                "NOT_FOUND verification submitted ID exists in credential table",
                """
                SELECT COUNT(*)
                FROM verification_request v
                JOIN credential c
                  ON c.credential_id = v.submitted_credential_id
                WHERE v.verification_result = 'NOT_FOUND'
                """,
            ),
            (
                "Audit event missing event type or timestamp",
                """
                SELECT COUNT(*)
                FROM audit_event
                WHERE event_type IS NULL OR event_timestamp IS NULL
                """,
            ),
            (
                "Credential issuance audit events not matching credential count",
                """
                SELECT ABS(
                    (SELECT COUNT(*) FROM credential)
                    -
                    (SELECT COUNT(*) FROM audit_event
                     WHERE event_type = 'CREDENTIAL_ISSUED')
                )
                """,
            ),
            (
                "Credential revocation audit events not matching revocation count",
                """
                SELECT ABS(
                    (SELECT COUNT(*) FROM revocation)
                    -
                    (SELECT COUNT(*) FROM audit_event
                     WHERE event_type = 'CREDENTIAL_REVOKED')
                )
                """,
            ),
            (
                "Verification audit events not matching verification request count",
                """
                SELECT ABS(
                    (SELECT COUNT(*) FROM verification_request)
                    -
                    (SELECT COUNT(*) FROM audit_event
                     WHERE event_type = 'CREDENTIAL_VERIFIED')
                )
                """,
            ),
        ]

        print("BUSINESS RULE AND DATA QUALITY CHECKS")
        print("-" * 78)
        total_issues = 0
        for label, sql in checks:
            total_issues += run_count(cursor, label, sql)

        print()
        print("SUMMARY COUNTS")
        print("-" * 78)
        summary_queries = [
            ("Total credentials", "SELECT COUNT(*) FROM credential"),
            ("Active credentials", "SELECT COUNT(*) FROM credential WHERE credential_status='ACTIVE'"),
            ("Revoked credentials", "SELECT COUNT(*) FROM credential WHERE credential_status='REVOKED'"),
            ("Revocation records", "SELECT COUNT(*) FROM revocation"),
            ("Verification requests", "SELECT COUNT(*) FROM verification_request"),
            ("Audit events", "SELECT COUNT(*) FROM audit_event"),
        ]
        for label, sql in summary_queries:
            cursor.execute(sql)
            print(f"{label:<58} {int(cursor.fetchone()[0]):,}")

        print()
        print("FINAL RESULT")
        print("-" * 78)
        print(f"Validation checks executed: {len(checks):,}")
        print(f"Total issue counts across checks: {total_issues:,}")
        if total_issues == 0:
            print("DATA QUALITY AND BUSINESS RULE VALIDATION: PASS")
        else:
            print("DATA QUALITY AND BUSINESS RULE VALIDATION: REVIEW REQUIRED")
        print("No database records were modified.")

        cursor.close()
        return 0 if total_issues == 0 else 2

    except mysql.connector.Error as exc:
        print(f"MySQL error: {exc}")
        return 1
    finally:
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
