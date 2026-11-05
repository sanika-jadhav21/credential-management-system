"""
Synthetic Data Generator
Credential Management System

Current scope:
1. Generate Learner dataset.
2. Generate Course dataset.
3. Generate Credential Rule dataset.
4. Generate Completion Record dataset.
5. Validate generated datasets before using them in later project steps.

Run from the project root:
    python -m src.data_generation.generator
"""

import csv
import hashlib
import json
import random
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path

from faker import Faker


# --------------------------------------------------
# 1. Project configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXPORT_DIR = DATA_DIR / "exports"


# --------------------------------------------------
# 2. Reproducibility configuration
# --------------------------------------------------

RANDOM_SEED = 20261022

random.seed(RANDOM_SEED)

fake = Faker("en_IN")
fake.seed_instance(RANDOM_SEED)

# Fixed reference date keeps generated data reproducible.
REFERENCE_DATE = date(2026, 11, 4)


# --------------------------------------------------
# 3. Dataset record counts
# --------------------------------------------------

LEARNER_COUNT = 20_000
COURSE_COUNT = 1_000

# These counts will be used in later generation steps.
CREDENTIAL_COUNT = 10_000
VERIFICATION_COUNT = 5_000


# --------------------------------------------------
# 4. Create required directories
# --------------------------------------------------

for directory in (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    EXPORT_DIR,
):
    directory.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 5. Helper functions
# --------------------------------------------------

def random_datetime(start_date, end_date):
    """Generate a deterministic random datetime between two dates."""

    start = datetime.combine(start_date, time.min)
    end = datetime.combine(end_date, time.max)

    total_seconds = int((end - start).total_seconds())
    random_seconds = random.randint(0, total_seconds)

    return start + timedelta(seconds=random_seconds)


def format_datetime(value):
    """Format a datetime for MySQL-compatible CSV output."""

    return value.strftime("%Y-%m-%d %H:%M:%S")


def write_csv(file_path, fieldnames, records):
    """Write records to a UTF-8 CSV file."""

    with open(
        file_path,
        mode="w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="raise",
        )

        writer.writeheader()
        writer.writerows(records)


# --------------------------------------------------
# 6. Generate Learner dataset
# --------------------------------------------------

def generate_learners():
    learners = []

    for number in range(1, LEARNER_COUNT + 1):
        learner_id = f"LRN-{number:06d}"

        first_name = fake.first_name()
        last_name = fake.last_name()

        # The numeric suffix guarantees unique email addresses.
        clean_first = re.sub(
            r"[^a-z0-9]",
            "",
            first_name.lower(),
        )

        clean_last = re.sub(
            r"[^a-z0-9]",
            "",
            last_name.lower(),
        )

        email = (
            f"{clean_first}.{clean_last}."
            f"{number:06d}@example.com"
        )

        phone = (
            random.choice("6789")
            + "".join(random.choices("0123456789", k=9))
        )

        date_of_birth = fake.date_between(
            start_date=date(1970, 1, 1),
            end_date=date(2008, 12, 31),
        )

        registration_datetime = random_datetime(
            date(2020, 1, 1),
            REFERENCE_DATE,
        )

        learner_status = random.choices(
            ["ACTIVE", "INACTIVE", "SUSPENDED"],
            weights=[85, 10, 5],
            k=1,
        )[0]

        learners.append({
            "learner_id": learner_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "date_of_birth": date_of_birth.isoformat(),
            "registration_date": format_datetime(
                registration_datetime
            ),
            "learner_status": learner_status,
            "created_at": format_datetime(
                registration_datetime
            ),
            "updated_at": format_datetime(
                registration_datetime
            ),
        })

    fieldnames = [
        "learner_id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "date_of_birth",
        "registration_date",
        "learner_status",
        "created_at",
        "updated_at",
    ]

    output_file = RAW_DATA_DIR / "learners.csv"
    write_csv(output_file, fieldnames, learners)

    return learners


# --------------------------------------------------
# 7. Generate Course dataset
# --------------------------------------------------

def generate_courses():
    courses = []

    categories = [
        "Artificial Intelligence",
        "Data Science",
        "Python Programming",
        "Web Development",
        "Database Management",
        "Cloud Computing",
        "Cyber Security",
        "Machine Learning",
        "Software Engineering",
        "Business Analytics",
    ]

    for number in range(1, COURSE_COUNT + 1):
        course_id = f"CRS-{number:06d}"
        course_code = f"COURSE-{number:04d}"

        effective_from = fake.date_between(
            start_date=date(2020, 1, 1),
            end_date=date(2025, 12, 31),
        )

        course_status = random.choices(
            ["ACTIVE", "INACTIVE", "RETIRED"],
            weights=[75, 15, 10],
            k=1,
        )[0]

        effective_to = None

        if course_status != "ACTIVE":
            # MySQL schema requires effective_to > effective_from.
            earliest_end_date = effective_from + timedelta(days=1)

            effective_to = fake.date_between(
                start_date=earliest_end_date,
                end_date=REFERENCE_DATE,
            )

        created_datetime = datetime.combine(
            effective_from,
            time(hour=9),
        )

        updated_datetime = (
            created_datetime
            if effective_to is None
            else datetime.combine(
                effective_to,
                time(hour=9),
            )
        )

        courses.append({
            "course_id": course_id,
            "course_code": course_code,
            "course_name": fake.catch_phrase(),
            "description": fake.sentence(nb_words=15),
            "category": random.choice(categories),
            "duration_hours": f"{random.uniform(5, 200):.2f}",
            "total_modules": random.randint(3, 30),
            "course_status": course_status,
            "effective_from": effective_from.isoformat(),
            "effective_to": (
                effective_to.isoformat()
                if effective_to is not None
                else ""
            ),
            "created_at": format_datetime(created_datetime),
            "updated_at": format_datetime(updated_datetime),
        })

    fieldnames = [
        "course_id",
        "course_code",
        "course_name",
        "description",
        "category",
        "duration_hours",
        "total_modules",
        "course_status",
        "effective_from",
        "effective_to",
        "created_at",
        "updated_at",
    ]

    output_file = RAW_DATA_DIR / "courses.csv"
    write_csv(output_file, fieldnames, courses)

    return courses


# --------------------------------------------------
# 8. Generate Credential Rule dataset
# --------------------------------------------------

def generate_credential_rules(courses):
    rules = []

    for index, course in enumerate(courses, start=1):
        effective_from = date.fromisoformat(
            course["effective_from"]
        )

        effective_to = (
            date.fromisoformat(course["effective_to"])
            if course["effective_to"]
            else None
        )

        # Keep the rule lifecycle aligned with its course lifecycle.
        rule_status = course["course_status"]

        created_datetime = datetime.combine(
            effective_from,
            time.min,
        )

        rules.append({
            "rule_id": f"RULE-{index:06d}",
            "course_id": course["course_id"],
            "rule_version": 1,
            "min_assessment_score": f"{random.uniform(40, 75):.2f}",
            "min_attendance_pct": f"{random.uniform(70, 90):.2f}",
            "min_completion_pct": "100.00",
            "require_all_modules": 1,
            "require_assessment_pass": 1,
            "effective_from": effective_from.isoformat(),
            "effective_to": (
                effective_to.isoformat()
                if effective_to is not None
                else ""
            ),
            "rule_status": rule_status,
            "created_at": format_datetime(created_datetime),
        })

    fieldnames = [
        "rule_id",
        "course_id",
        "rule_version",
        "min_assessment_score",
        "min_attendance_pct",
        "min_completion_pct",
        "require_all_modules",
        "require_assessment_pass",
        "effective_from",
        "effective_to",
        "rule_status",
        "created_at",
    ]

    output_file = RAW_DATA_DIR / "credential_rules.csv"
    write_csv(output_file, fieldnames, rules)

    return rules




# --------------------------------------------------
# 9. Generate Completion Record dataset
# --------------------------------------------------

COMPLETION_COUNT = 20_000
ELIGIBLE_COMPLETION_COUNT = 12_000


def parse_date(value):
    return date.fromisoformat(str(value)[:10])


def generate_completion_records(learners, courses, credential_rules):
    """
    Generate one completion record per learner-course pair.

    The first 12,000 records are deliberately eligible under the active
    credential rules. Remaining records represent incomplete or failed
    learning journeys and are not eligible for credential issuance.
    """

    rng = random.Random(RANDOM_SEED + 1)

    active_learners = [
        learner for learner in learners
        if learner["learner_status"] == "ACTIVE"
    ]
    active_courses = [
        course for course in courses
        if course["course_status"] == "ACTIVE"
    ]

    rule_by_course = {
        rule["course_id"]: rule
        for rule in credential_rules
    }

    if len(active_learners) < ELIGIBLE_COMPLETION_COUNT:
        raise ValueError("Not enough active learners for eligible completions.")

    if len(active_courses) == 0:
        raise ValueError("No active courses available.")

    records = []
    used_pairs = set()

    # Eligible baseline records: guarantee enough valid candidates
    # for the requested 10,000 credential records in a later step.
    learner_order = active_learners.copy()
    rng.shuffle(learner_order)
    course_order = active_courses.copy()
    rng.shuffle(course_order)

    for index in range(ELIGIBLE_COMPLETION_COUNT):
        learner = learner_order[index]
        course = course_order[index % len(course_order)]
        rule = rule_by_course[course["course_id"]]

        pair = (learner["learner_id"], course["course_id"])
        if pair in used_pairs:
            raise AssertionError("Duplicate learner-course pair encountered.")
        used_pairs.add(pair)

        course_start = parse_date(course["effective_from"])
        rule_start = parse_date(rule["effective_from"])
        registration_date = parse_date(learner["registration_date"])
        earliest = max(course_start, rule_start, registration_date)
        if earliest > REFERENCE_DATE:
            raise ValueError("No valid enrollment date range for eligible record.")

        enrollment_date = rng_date(rng, earliest, REFERENCE_DATE)
        completion_date = rng_date(rng, enrollment_date, REFERENCE_DATE)

        min_score = float(rule["min_assessment_score"])
        min_attendance = float(rule["min_attendance_pct"])
        total_modules = int(course["total_modules"])

        score = min(100.0, min_score + rng.uniform(5.0, 25.0))
        attendance = min(100.0, min_attendance + rng.uniform(3.0, 15.0))

        records.append({
            "completion_id": f"CMP-{learner['learner_id']}-{course['course_id']}",
            "learner_id": learner["learner_id"],
            "course_id": course["course_id"],
            "enrollment_date": format_datetime(datetime.combine(enrollment_date, time(9, 0))),
            "completion_date": format_datetime(datetime.combine(completion_date, time(17, 0))),
            "completion_pct": "100.00",
            "attendance_pct": f"{attendance:.2f}",
            "assessment_score": f"{score:.2f}",
            "assessment_attempts": rng.randint(1, 3),
            "modules_completed": total_modules,
            "completion_status": "COMPLETED",
            "assessment_status": "PASSED",
            "instructor_reference": f"INS-{rng.randint(1, 250):04d}",
            "created_at": format_datetime(datetime.combine(enrollment_date, time(9, 0))),
            "updated_at": format_datetime(datetime.combine(completion_date, time(17, 0))),
        })

    # Non-eligible records: incomplete, withdrawn, or failed attempts.
    all_learners = learners.copy()
    all_courses = courses.copy()
    attempts = 0

    while len(records) < COMPLETION_COUNT:
        attempts += 1
        if attempts > COMPLETION_COUNT * 100:
            raise RuntimeError("Could not generate enough unique completion records.")

        learner = rng.choice(all_learners)
        course = rng.choice(all_courses)
        pair = (learner["learner_id"], course["course_id"])

        if pair in used_pairs:
            continue
        used_pairs.add(pair)

        rule = rule_by_course[course["course_id"]]
        course_start = parse_date(course["effective_from"])
        registration_date = parse_date(learner["registration_date"])
        earliest = max(course_start, registration_date)

        course_end = (
            parse_date(course["effective_to"])
            if course.get("effective_to")
            else REFERENCE_DATE
        )
        latest = min(course_end, REFERENCE_DATE)

        if earliest > latest:
            # Use a historically plausible date range for a record
            # that cannot qualify under the current course lifecycle.
            earliest = course_start
            latest = max(course_start, min(REFERENCE_DATE, course_end))

        enrollment_date = rng_date(rng, earliest, latest)
        status = rng.choices(
            ["IN_PROGRESS", "ENROLLED", "FAILED", "WITHDRAWN"],
            weights=[45, 20, 25, 10],
            k=1,
        )[0]

        total_modules = int(course["total_modules"])
        if status == "ENROLLED":
            completion_pct = rng.uniform(0, 10)
            modules_completed = 0
            attendance = rng.uniform(0, 30)
            assessment_attempts = 0
            score = ""
            assessment_status = "NOT_ATTEMPTED"
        elif status == "IN_PROGRESS":
            completion_pct = rng.uniform(10, 95)
            modules_completed = rng.randint(1, max(1, total_modules - 1))
            attendance = rng.uniform(20, 95)
            assessment_attempts = rng.randint(0, 1)
            score = (
                f"{rng.uniform(0, 100):.2f}"
                if assessment_attempts else ""
            )
            assessment_status = (
                "FAILED" if assessment_attempts else "NOT_ATTEMPTED"
            )
        elif status == "FAILED":
            completion_pct = 100.0
            modules_completed = total_modules
            attendance = rng.uniform(30, 100)
            assessment_attempts = rng.randint(1, 3)
            score = f"{rng.uniform(0, 60):.2f}"
            assessment_status = "FAILED"
        else:
            completion_pct = rng.uniform(0, 90)
            modules_completed = rng.randint(0, max(0, total_modules - 1))
            attendance = rng.uniform(0, 80)
            assessment_attempts = 0
            score = ""
            assessment_status = "NOT_ATTEMPTED"

        updated_date = min(REFERENCE_DATE, max(enrollment_date, latest))
        records.append({
            "completion_id": f"CMP-{learner['learner_id']}-{course['course_id']}",
            "learner_id": learner["learner_id"],
            "course_id": course["course_id"],
            "enrollment_date": format_datetime(datetime.combine(enrollment_date, time(9, 0))),
            "completion_date": "",
            "completion_pct": f"{completion_pct:.2f}",
            "attendance_pct": f"{attendance:.2f}",
            "assessment_score": score,
            "assessment_attempts": assessment_attempts,
            "modules_completed": modules_completed,
            "completion_status": status,
            "assessment_status": assessment_status,
            "instructor_reference": f"INS-{rng.randint(1, 250):04d}",
            "created_at": format_datetime(datetime.combine(enrollment_date, time(9, 0))),
            "updated_at": format_datetime(datetime.combine(updated_date, time(17, 0))),
        })

    fieldnames = [
        "completion_id",
        "learner_id",
        "course_id",
        "enrollment_date",
        "completion_date",
        "completion_pct",
        "attendance_pct",
        "assessment_score",
        "assessment_attempts",
        "modules_completed",
        "completion_status",
        "assessment_status",
        "instructor_reference",
        "created_at",
        "updated_at",
    ]

    write_csv(RAW_DATA_DIR / "completion_records.csv", fieldnames, records)
    return records


def rng_date(rng, start_date, end_date):
    """Return a deterministic date between inclusive bounds."""
    if start_date > end_date:
        raise ValueError(f"Invalid date range: {start_date} > {end_date}")
    days = (end_date - start_date).days
    return start_date + timedelta(days=rng.randint(0, days))


def validate_completion_records(records, learners, courses, credential_rules):
    learner_by_id = {row["learner_id"]: row for row in learners}
    learner_ids = set(learner_by_id)
    course_by_id = {row["course_id"]: row for row in courses}
    rule_by_course = {row["course_id"]: row for row in credential_rules}

    assert len(records) == COMPLETION_COUNT
    assert len({row["completion_id"] for row in records}) == len(records)
    assert len({(row["learner_id"], row["course_id"]) for row in records}) == len(records)

    eligible_count = 0
    valid_statuses = {"ENROLLED", "IN_PROGRESS", "COMPLETED", "FAILED", "WITHDRAWN"}
    valid_assessment_statuses = {"NOT_ATTEMPTED", "PASSED", "FAILED"}

    for row in records:
        assert row["learner_id"] in learner_ids
        assert row["course_id"] in course_by_id
        assert row["completion_status"] in valid_statuses
        assert row["assessment_status"] in valid_assessment_statuses

        completion_pct = float(row["completion_pct"])
        attendance_pct = float(row["attendance_pct"])
        assert 0 <= completion_pct <= 100
        assert 0 <= attendance_pct <= 100
        assert int(row["modules_completed"]) <= int(course_by_id[row["course_id"]]["total_modules"])

        if row["completion_status"] == "COMPLETED":
            assert completion_pct == 100.0
            assert row["completion_date"]
        else:
            assert row["completion_date"] == ""

        if row["assessment_status"] == "PASSED":
            assert row["assessment_score"] != ""
        if row["assessment_status"] == "NOT_ATTEMPTED":
            assert int(row["assessment_attempts"]) == 0
            assert row["assessment_score"] == ""

        learner = learner_by_id[row["learner_id"]]
        course = course_by_id[row["course_id"]]
        rule = rule_by_course[row["course_id"]]

        if (
            learner["learner_status"] == "ACTIVE"
            and course["course_status"] == "ACTIVE"
            and rule["rule_status"] == "ACTIVE"
            and row["completion_status"] == "COMPLETED"
            and completion_pct >= float(rule["min_completion_pct"])
            and attendance_pct >= float(rule["min_attendance_pct"])
            and row["assessment_status"] == "PASSED"
            and float(row["assessment_score"]) >= float(rule["min_assessment_score"])
            and (
                not int(rule["require_all_modules"])
                or int(row["modules_completed"]) == int(course["total_modules"])
            )
        ):
            eligible_count += 1

    assert eligible_count >= ELIGIBLE_COMPLETION_COUNT
    print(f"Completion records: {len(records):,} PASS")
    print(f"Eligible completion records: {eligible_count:,} PASS")
    print("Completion PK/FK, uniqueness, status and rule checks: PASS")


# --------------------------------------------------
# 10. Validate generated datasets
# --------------------------------------------------

def validate_datasets(learners, courses, credential_rules):
    # Record count validation
    assert len(learners) == LEARNER_COUNT
    assert len(courses) == COURSE_COUNT
    assert len(credential_rules) == COURSE_COUNT

    # Learner uniqueness validation
    learner_ids = [
        record["learner_id"]
        for record in learners
    ]

    learner_emails = [
        record["email"]
        for record in learners
    ]

    assert len(set(learner_ids)) == LEARNER_COUNT
    assert len(set(learner_emails)) == LEARNER_COUNT

    # Course uniqueness validation
    course_ids = [
        record["course_id"]
        for record in courses
    ]

    course_codes = [
        record["course_code"]
        for record in courses
    ]

    assert len(set(course_ids)) == COURSE_COUNT
    assert len(set(course_codes)) == COURSE_COUNT

    # Learner status validation
    valid_learner_statuses = {
        "ACTIVE",
        "INACTIVE",
        "SUSPENDED",
    }

    for learner in learners:
        assert learner["learner_status"] in valid_learner_statuses
        assert learner["first_name"].strip()
        assert learner["last_name"].strip()

    # Course validation
    valid_course_statuses = {
        "ACTIVE",
        "INACTIVE",
        "RETIRED",
    }

    for course in courses:
        assert float(course["duration_hours"]) > 0
        assert int(course["total_modules"]) > 0
        assert course["course_status"] in valid_course_statuses
        assert course["course_name"].strip()

        effective_from = date.fromisoformat(
            course["effective_from"]
        )

        if course["effective_to"]:
            effective_to = date.fromisoformat(
                course["effective_to"]
            )
            assert effective_to > effective_from

        if course["course_status"] == "ACTIVE":
            assert course["effective_to"] == ""
        else:
            assert course["effective_to"] != ""

    # Credential rule uniqueness and relationship validation
    rule_ids = [
        rule["rule_id"]
        for rule in credential_rules
    ]

    rule_course_ids = [
        rule["course_id"]
        for rule in credential_rules
    ]

    assert len(set(rule_ids)) == COURSE_COUNT
    assert len(set(rule_course_ids)) == COURSE_COUNT

    course_lookup = {
        course["course_id"]: course
        for course in courses
    }

    valid_rule_statuses = {
        "ACTIVE",
        "INACTIVE",
        "RETIRED",
    }

    for rule in credential_rules:
        assert rule["course_id"] in course_lookup
        assert int(rule["rule_version"]) > 0

        assert 0 <= float(rule["min_assessment_score"]) <= 100
        assert 0 <= float(rule["min_attendance_pct"]) <= 100
        assert 0 <= float(rule["min_completion_pct"]) <= 100

        assert rule["require_all_modules"] in (0, 1)
        assert rule["require_assessment_pass"] in (0, 1)
        assert rule["rule_status"] in valid_rule_statuses

        rule_start = date.fromisoformat(rule["effective_from"])
        course = course_lookup[rule["course_id"]]

        assert rule_start == date.fromisoformat(
            course["effective_from"]
        )

        assert rule["rule_status"] == course["course_status"]
        assert rule["effective_to"] == course["effective_to"]

        if rule["effective_to"]:
            rule_end = date.fromisoformat(rule["effective_to"])
            assert rule_end > rule_start

    # Validation summary
    print("\nDATA VALIDATION")
    print("-" * 40)
    print("Learner count: PASS")
    print("Learner ID uniqueness: PASS")
    print("Learner email uniqueness: PASS")
    print("Learner status validation: PASS")
    print("Course count: PASS")
    print("Course ID uniqueness: PASS")
    print("Course code uniqueness: PASS")
    print("Course attributes and status: PASS")
    print("Course date validation: PASS")
    print("Credential rule count: PASS")
    print("Credential rule ID uniqueness: PASS")
    print("Credential rule course relationship: PASS")
    print("Credential rule values and dates: PASS")


# --------------------------------------------------
# 10. Main execution
# --------------------------------------------------

# --------------------------------------------------
# 11. Generate Issuer and Issuer Key master data
# --------------------------------------------------

ISSUER_COUNT = 5
ISSUE_DATE = datetime(2026, 1, 1, 12, 0, 0)
# Verification scenarios are generated after the synthetic revocation window.
REFERENCE_DATETIME = ISSUE_DATE + timedelta(days=60)


def generate_issuers_and_keys():
    issuers = []
    issuer_keys = []

    issuer_names = [
        ("National Skills Certification Board", "National Skills Council"),
        ("Institute of Technology Credentials", "Institute of Technology"),
        ("Digital Learning Accreditation Authority", "Digital Learning Authority"),
        ("Professional Education Certification Board", "Professional Education Group"),
        ("Advanced Training Credential Office", "Advanced Training Institute"),
    ]

    for number, (issuer_name, organization_name) in enumerate(issuer_names, start=1):
        issuer_id = f"ISS-{number:04d}"
        issuer_email = f"issuer{number:02d}@credential.example.com"

        issuers.append({
            "issuer_id": issuer_id,
            "issuer_name": issuer_name,
            "organization_name": organization_name,
            "issuer_email": issuer_email,
            "issuer_status": "ACTIVE",
            "created_at": format_datetime(ISSUE_DATE),
            "updated_at": format_datetime(ISSUE_DATE),
        })

        issuer_keys.append({
            "issuer_key_id": f"KEY-{number:04d}-V01",
            "issuer_id": issuer_id,
            "key_version": 1,
            "signing_key_id": f"SIM-KEY-{number:04d}-V01",
            # This is explicitly simulated metadata, not a production public key.
            "public_key": f"SIMULATED-PUBLIC-KEY-FOR-{issuer_id}-VERSION-1",
            "key_algorithm": "SIMULATED-SHA256",
            "key_status": "ACTIVE",
            "valid_from": format_datetime(datetime(2025, 1, 1, 0, 0, 0)),
            "valid_to": "",
            "created_at": format_datetime(ISSUE_DATE),
        })

    write_csv(
        RAW_DATA_DIR / "issuers.csv",
        ["issuer_id", "issuer_name", "organization_name", "issuer_email",
         "issuer_status", "created_at", "updated_at"],
        issuers,
    )
    write_csv(
        RAW_DATA_DIR / "issuer_keys.csv",
        ["issuer_key_id", "issuer_id", "key_version", "signing_key_id",
         "public_key", "key_algorithm", "key_status", "valid_from",
         "valid_to", "created_at"],
        issuer_keys,
    )
    return issuers, issuer_keys


# --------------------------------------------------
# 12. Credential eligibility and issuance
# --------------------------------------------------

def is_completion_eligible(completion, learner_by_id, course_by_id, rule_by_course):
    learner = learner_by_id[completion["learner_id"]]
    course = course_by_id[completion["course_id"]]
    rule = rule_by_course[completion["course_id"]]

    if learner["learner_status"] != "ACTIVE":
        return False
    if course["course_status"] != "ACTIVE" or rule["rule_status"] != "ACTIVE":
        return False
    if completion["completion_status"] != "COMPLETED":
        return False
    if float(completion["completion_pct"]) < float(rule["min_completion_pct"]):
        return False
    if float(completion["attendance_pct"]) < float(rule["min_attendance_pct"]):
        return False
    if int(rule["require_assessment_pass"]) and completion["assessment_status"] != "PASSED":
        return False
    if completion["assessment_score"] == "":
        if int(rule["require_assessment_pass"]) or float(rule["min_assessment_score"]) > 0:
            return False
    elif float(completion["assessment_score"]) < float(rule["min_assessment_score"]):
        return False
    if int(rule["require_all_modules"]) and int(completion["modules_completed"]) != int(course["total_modules"]):
        return False

    completion_date = date.fromisoformat(completion["completion_date"][:10])
    if completion_date < date.fromisoformat(rule["effective_from"]):
        return False
    if rule["effective_to"]:
        if completion_date > date.fromisoformat(rule["effective_to"]):
            return False
    return True


def generate_credentials(completions, learners, courses, rules, issuers, issuer_keys):
    learner_by_id = {row["learner_id"]: row for row in learners}
    course_by_id = {row["course_id"]: row for row in courses}
    rule_by_course = {row["course_id"]: row for row in rules}
    issuer_by_id = {row["issuer_id"]: row for row in issuers}
    key_by_issuer = {row["issuer_id"]: row for row in issuer_keys}

    eligible = [
        row for row in completions
        if is_completion_eligible(row, learner_by_id, course_by_id, rule_by_course)
    ]

    if len(eligible) < CREDENTIAL_COUNT:
        raise ValueError(
            f"Only {len(eligible):,} eligible completions found; "
            f"{CREDENTIAL_COUNT:,} are required for credential issuance."
        )

    # Exactly the target volume is issued. The ordering is stable under the fixed seed.
    selected = eligible[:CREDENTIAL_COUNT]
    credentials = []
    audit_events = []

    for number, completion in enumerate(selected, start=1):
        learner_id = completion["learner_id"]
        course_id = completion["course_id"]
        rule = rule_by_course[course_id]

        issuer = issuers[(number - 1) % len(issuers)]
        issuer_key = key_by_issuer[issuer["issuer_id"]]

        credential_id = f"CRD-2026-{number:06d}"

        # Issue only after the learner's recorded course completion.
        completion_timestamp = datetime.fromisoformat(completion["completion_date"])
        proposed_issue_timestamp = ISSUE_DATE + timedelta(seconds=number)
        issue_timestamp = max(
            proposed_issue_timestamp,
            completion_timestamp + timedelta(minutes=1),
        )
        valid_from = issue_timestamp
        expires_at = issue_timestamp + timedelta(days=365 * 3)

        # Canonical payload: stable key order and normalized values.
        payload = {
            "credential_id": credential_id,
            "learner_id": learner_id,
            "course_id": course_id,
            "completion_id": completion["completion_id"],
            "rule_id": rule["rule_id"],
            "issuer_id": issuer["issuer_id"],
            "issuer_key_id": issuer_key["issuer_key_id"],
            "issue_date": format_datetime(issue_timestamp),
            "valid_from": format_datetime(valid_from),
            "expires_at": format_datetime(expires_at),
        }
        canonical_payload = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        payload_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

        # Demonstration-only integrity token. This is NOT a production digital signature.
        signature_material = (
            payload_hash + "|" + issuer_key["signing_key_id"] + "|SIMULATION"
        )
        signature_value = hashlib.sha256(
            signature_material.encode("utf-8")
        ).hexdigest()

        credentials.append({
            "credential_id": credential_id,
            "learner_id": learner_id,
            "course_id": course_id,
            "completion_id": completion["completion_id"],
            "rule_id": rule["rule_id"],
            "issuer_id": issuer["issuer_id"],
            "issuer_key_id": issuer_key["issuer_key_id"],
            "issuance_number": 1,
            "issue_date": format_datetime(issue_timestamp),
            "valid_from": format_datetime(valid_from),
            "expires_at": format_datetime(expires_at),
            "credential_status": "ACTIVE",
            "payload_hash": payload_hash,
            "hash_algorithm": "SHA256",
            "signature_value": signature_value,
            "signature_algorithm": "SIMULATED-SHA256",
            "created_at": format_datetime(issue_timestamp),
        })

        audit_id = f"AUD-2026-{number:06d}"
        audit_events.append({
            "audit_event_id": audit_id,
            "event_type": "CREDENTIAL_ISSUED",
            "event_timestamp": format_datetime(issue_timestamp),
            "actor_role": "ACADEMIC_ADMINISTRATOR",
            "actor_reference": "SYSTEM-BATCH-ISSUANCE-001",
            "target_entity_type": "CREDENTIAL",
            "learner_id": "",
            "course_id": "",
            "rule_id": "",
            "completion_id": "",
            "credential_id": credential_id,
            "issuer_id": "",
            "verification_id": "",
            "revocation_id": "",
            "previous_state": "",
            "new_state": json.dumps(
                {"credential_status": "ACTIVE", "payload_hash": payload_hash},
                sort_keys=True, separators=(",", ":")
            ),
            "event_metadata": json.dumps(
                {"completion_id": completion["completion_id"],
                 "rule_id": rule["rule_id"],
                 "issuer_id": issuer["issuer_id"],
                 "issuer_key_id": issuer_key["issuer_key_id"],
                 "signature_mode": "SIMULATED"},
                sort_keys=True, separators=(",", ":")
            ),
            "correlation_id": f"ISSUANCE-BATCH-2026-{number:06d}",
            "created_at": format_datetime(issue_timestamp),
        })

    credential_fields = [
        "credential_id", "learner_id", "course_id", "completion_id", "rule_id",
        "issuer_id", "issuer_key_id", "issuance_number", "issue_date", "valid_from",
        "expires_at", "credential_status", "payload_hash", "hash_algorithm",
        "signature_value", "signature_algorithm", "created_at",
    ]
    audit_fields = [
        "audit_event_id", "event_type", "event_timestamp", "actor_role",
        "actor_reference", "target_entity_type", "learner_id", "course_id",
        "rule_id", "completion_id", "credential_id", "issuer_id",
        "verification_id", "revocation_id", "previous_state", "new_state",
        "event_metadata", "correlation_id", "created_at",
    ]

    write_csv(RAW_DATA_DIR / "credentials.csv", credential_fields, credentials)
    write_csv(RAW_DATA_DIR / "audit_events.csv", audit_fields, audit_events)

    validate_credential_issuance(
        credentials, audit_events, eligible, learner_by_id,
        course_by_id, rule_by_course, issuer_by_id, key_by_issuer
    )
    return credentials, audit_events


def validate_credential_issuance(
    credentials, audit_events, eligible, learner_by_id,
    course_by_id, rule_by_course, issuer_by_id, key_by_issuer
):
    assert len(credentials) == CREDENTIAL_COUNT
    assert len(audit_events) == CREDENTIAL_COUNT
    assert len({row["credential_id"] for row in credentials}) == len(credentials)
    assert len({row["completion_id"] for row in credentials}) == len(credentials)

    completion_ids = {row["completion_id"] for row in eligible}
    for row in credentials:
        assert row["completion_id"] in completion_ids
        assert row["learner_id"] in learner_by_id
        assert row["course_id"] in course_by_id
        assert row["rule_id"] == rule_by_course[row["course_id"]]["rule_id"]
        assert row["issuer_id"] in issuer_by_id
        assert row["issuer_key_id"] == key_by_issuer[row["issuer_id"]]["issuer_key_id"]
        assert re.fullmatch(r"[0-9a-f]{64}", row["payload_hash"])
        assert re.fullmatch(r"[0-9a-f]{64}", row["signature_value"])
        assert row["hash_algorithm"] == "SHA256"
        assert row["signature_algorithm"] == "SIMULATED-SHA256"

    credential_ids = {row["credential_id"] for row in credentials}
    for event in audit_events:
        assert event["target_entity_type"] == "CREDENTIAL"
        assert event["credential_id"] in credential_ids
        assert event["event_type"] == "CREDENTIAL_ISSUED"
        populated_targets = [
            event[field] for field in (
                "learner_id", "course_id", "rule_id", "completion_id",
                "credential_id", "issuer_id", "verification_id", "revocation_id"
            ) if event[field]
        ]
        assert len(populated_targets) == 1

    print(f"Eligible completions available: {len(eligible):,} PASS")
    print(f"Credentials issued: {len(credentials):,} PASS")
    print("Credential ID uniqueness: PASS")
    print("Credential eligibility and FK references: PASS")
    print("SHA-256 payload hash format: PASS")
    print("Issuer and signing-key relationships: PASS")
    print("Issuance audit-event traceability: PASS")



# --------------------------------------------------
# 13. Verification and Revocation workflow
# --------------------------------------------------

def generate_verification_and_revocation(credentials, audit_events):
    """
    Simulate credential revocation and third-party verification.
    Historical issuance events are retained; new events are appended.
    """

    # Reproducible independent RNG prevents changing earlier generated datasets.
    workflow_rng = random.Random(RANDOM_SEED + 303)

    credential_by_id = {
        row["credential_id"]: row for row in credentials
    }

    # Revoke 5% of issued credentials (500 of 10,000).
    revocation_count = 500
    revocation_candidates = sorted(credentials, key=lambda row: row["credential_id"])
    workflow_rng.shuffle(revocation_candidates)
    revoked_credentials = revocation_candidates[:revocation_count]

    revocations = []
    revocation_by_credential = {}

    latest_issue_timestamp = max(
        datetime.fromisoformat(row["issue_date"])
        for row in credentials
    )

    for number, credential in enumerate(revoked_credentials, start=1):
        revoked_at = latest_issue_timestamp + timedelta(days=30, minutes=number)
        revocation_id = f"REV-{credential['credential_id']}-01"

        revocation = {
            "revocation_id": revocation_id,
            "credential_id": credential["credential_id"],
            "revocation_sequence": 1,
            "revoked_at": format_datetime(revoked_at),
            "effective_at": format_datetime(revoked_at),
            "reason_code": workflow_rng.choice([
                "FRAUD", "ISSUED_IN_ERROR", "ACADEMIC_MISCONDUCT",
                "IDENTITY_MISMATCH", "ADMINISTRATIVE_ERROR", "OTHER"
            ]),
            "reason_description": "Synthetic scenario: credential revoked for testing.",
            "revoked_by_role": "ACADEMIC_ADMINISTRATOR",
            "revoked_by_reference": "ADMIN-REVOCATION-BATCH-001",
        }
        revocations.append(revocation)
        revocation_by_credential[credential["credential_id"]] = revocation

        # Current status is updated in the credential snapshot. The previous
        # state remains preserved in the immutable audit event.
        credential["credential_status"] = "REVOKED"

    # Append one audit event for each revocation.
    audit_fields = [
        "audit_event_id", "event_type", "event_timestamp", "actor_role",
        "actor_reference", "target_entity_type", "learner_id", "course_id",
        "rule_id", "completion_id", "credential_id", "issuer_id",
        "verification_id", "revocation_id", "previous_state", "new_state",
        "event_metadata", "correlation_id", "created_at",
    ]

    next_audit_number = len(audit_events) + 1
    for number, revocation in enumerate(revocations, start=next_audit_number):
        event_time = revocation["revoked_at"]
        audit_events.append({
            "audit_event_id": f"AUD-2026-{number:06d}",
            "event_type": "CREDENTIAL_REVOKED",
            "event_timestamp": event_time,
            "actor_role": "ACADEMIC_ADMINISTRATOR",
            "actor_reference": revocation["revoked_by_reference"],
            "target_entity_type": "REVOCATION",
            "learner_id": "",
            "course_id": "",
            "rule_id": "",
            "completion_id": "",
            "credential_id": "",
            "issuer_id": "",
            "verification_id": "",
            "revocation_id": revocation["revocation_id"],
            "previous_state": json.dumps(
                {"credential_status": "ACTIVE"},
                sort_keys=True, separators=(",", ":")
            ),
            "new_state": json.dumps(
                {"credential_status": "REVOKED"},
                sort_keys=True, separators=(",", ":")
            ),
            "event_metadata": json.dumps(
                {"credential_id": revocation["credential_id"],
                 "reason_code": revocation["reason_code"]},
                sort_keys=True, separators=(",", ":")
            ),
            "correlation_id": f"REVOCATION-{revocation['revocation_id']}",
            "created_at": event_time,
        })

    # Verification mix: 4,000 valid, 500 revoked, 250 not found,
    # and 250 altered-payload requests.
    verification_specs = []
    active_credentials = [
        row for row in credentials if row["credential_status"] == "ACTIVE"
    ]
    revoked_list = [
        row for row in credentials if row["credential_status"] == "REVOKED"
    ]
    workflow_rng.shuffle(active_credentials)
    workflow_rng.shuffle(revoked_list)

    verification_specs.extend(
        ("VALID", row) for row in active_credentials[:4000]
    )
    verification_specs.extend(
        ("REVOKED", row) for row in revoked_list[:500]
    )
    verification_specs.extend(
        ("NOT_FOUND", None) for _ in range(250)
    )
    verification_specs.extend(
        ("HASH_MISMATCH", row) for row in active_credentials[4000:4250]
    )
    workflow_rng.shuffle(verification_specs)

    # Calculate the latest lifecycle timestamp ONCE, not once per verification.
    # Recomputing this inside the 5,000-row loop caused millions of redundant
    # datetime conversions and made the generator appear to hang.
    latest_lifecycle_time = max(
        datetime.fromisoformat(row["issue_date"])
        for row in credentials
    )
    if revocations:
        latest_lifecycle_time = max(
            latest_lifecycle_time,
            max(
                datetime.fromisoformat(row["revoked_at"])
                for row in revocations
            ),
        )

    verifications = []
    for number, (scenario, credential) in enumerate(verification_specs, start=1):
        verification_id = f"VER-2026-{number:06d}"
        request_time = latest_lifecycle_time + timedelta(days=1, minutes=number)
        response_time = request_time + timedelta(milliseconds=workflow_rng.randint(35, 450))

        if scenario == "NOT_FOUND":
            submitted_id = f"CRD-2099-{number:06d}"
            linked_credential_id = ""
            result = "NOT_FOUND"
            reason = "Credential ID was not found."
            checked_hash = ""
            provided_hash = ""
        else:
            submitted_id = credential["credential_id"]
            linked_credential_id = credential["credential_id"]
            checked_hash = credential["payload_hash"]
            provided_hash = checked_hash

            if scenario == "REVOKED":
                result = "REVOKED"
                reason = "Credential has an effective revocation record."
            elif scenario == "HASH_MISMATCH":
                result = "HASH_MISMATCH"
                reason = "Submitted payload hash does not match the stored hash."
                provided_hash = hashlib.sha256(
                    (checked_hash + "|ALTERED").encode("utf-8")
                ).hexdigest()
            else:
                result = "VALID"
                reason = "Credential exists, is active, and payload hash matches."

        verifications.append({
            "verification_id": verification_id,
            "submitted_credential_id": submitted_id,
            "credential_id": linked_credential_id,
            "verifier_organization": workflow_rng.choice([
                "Example Employer Ltd.", "University Verification Desk",
                "Background Check Services"
            ]),
            "verifier_reference": f"VERIFIER-{number:06d}",
            "request_timestamp": format_datetime(request_time),
            "response_timestamp": format_datetime(response_time),
            "verification_result": result,
            "verification_reason": reason,
            "checked_payload_hash": checked_hash,
            "provided_payload_hash": provided_hash,
            "response_time_ms": int((response_time - request_time).total_seconds() * 1000),
            "request_channel": workflow_rng.choice(["API", "WEB", "MANUAL"]),
        })

    # Append one audit event for every verification request.
    next_audit_number = len(audit_events) + 1
    for number, verification in enumerate(verifications, start=next_audit_number):
        event_time = verification["response_timestamp"]
        audit_events.append({
            "audit_event_id": f"AUD-2026-{number:06d}",
            "event_type": "CREDENTIAL_VERIFIED",
            "event_timestamp": event_time,
            "actor_role": "SUPPORT_STAFF",
            "actor_reference": verification["verifier_reference"],
            "target_entity_type": "VERIFICATION_REQUEST",
            "learner_id": "",
            "course_id": "",
            "rule_id": "",
            "completion_id": "",
            "credential_id": "",
            "issuer_id": "",
            "verification_id": verification["verification_id"],
            "revocation_id": "",
            "previous_state": "",
            "new_state": json.dumps(
                {"verification_result": verification["verification_result"]},
                sort_keys=True, separators=(",", ":")
            ),
            "event_metadata": json.dumps(
                {"submitted_credential_id": verification["submitted_credential_id"],
                 "response_time_ms": verification["response_time_ms"]},
                sort_keys=True, separators=(",", ":")
            ),
            "correlation_id": f"VERIFICATION-{verification['verification_id']}",
            "created_at": event_time,
        })

    # Persist final current-state credential snapshot and event history.
    credential_fields = [
        "credential_id", "learner_id", "course_id", "completion_id", "rule_id",
        "issuer_id", "issuer_key_id", "issuance_number", "issue_date", "valid_from",
        "expires_at", "credential_status", "payload_hash", "hash_algorithm",
        "signature_value", "signature_algorithm", "created_at",
    ]
    revocation_fields = [
        "revocation_id", "credential_id", "revocation_sequence", "revoked_at",
        "effective_at", "reason_code", "reason_description", "revoked_by_role",
        "revoked_by_reference",
    ]
    verification_fields = [
        "verification_id", "submitted_credential_id", "credential_id",
        "verifier_organization", "verifier_reference", "request_timestamp",
        "response_timestamp", "verification_result", "verification_reason",
        "checked_payload_hash", "provided_payload_hash", "response_time_ms",
        "request_channel",
    ]

    write_csv(RAW_DATA_DIR / "credentials.csv", credential_fields, credentials)
    write_csv(RAW_DATA_DIR / "revocations.csv", revocation_fields, revocations)
    write_csv(RAW_DATA_DIR / "verification_requests.csv", verification_fields, verifications)
    write_csv(RAW_DATA_DIR / "audit_events.csv", audit_fields, audit_events)

    # Validation: IDs, FK links, allowed outcomes, hashes, and event targets.
    assert len(revocations) == revocation_count
    assert len(verifications) == VERIFICATION_COUNT
    assert len({r["revocation_id"] for r in revocations}) == len(revocations)
    assert len({v["verification_id"] for v in verifications}) == len(verifications)
    assert len({e["audit_event_id"] for e in audit_events}) == len(audit_events)

    revoked_ids = {r["credential_id"] for r in revocations}
    assert revoked_ids == {
        c["credential_id"] for c in credentials
        if c["credential_status"] == "REVOKED"
    }
    assert all(r["credential_id"] in credential_by_id for r in revocations)

    credential_ids = set(credential_by_id)
    for verification in verifications:
        assert verification["verification_result"] in {
            "VALID", "REVOKED", "NOT_FOUND", "HASH_MISMATCH"
        }
        if verification["verification_result"] == "NOT_FOUND":
            assert verification["credential_id"] == ""
        else:
            assert verification["credential_id"] in credential_ids
        if verification["verification_result"] == "HASH_MISMATCH":
            assert verification["checked_payload_hash"] != verification["provided_payload_hash"]

    for event in audit_events:
        if event["target_entity_type"] == "REVOCATION":
            assert event["revocation_id"] in {r["revocation_id"] for r in revocations}
        elif event["target_entity_type"] == "VERIFICATION_REQUEST":
            assert event["verification_id"] in {v["verification_id"] for v in verifications}

    print(f"Revocations created: {len(revocations):,} PASS")
    print(f"Verification requests: {len(verifications):,} PASS")
    print("Verification outcomes and credential references: PASS")
    print("Revocation state and history validation: PASS")
    print(f"Audit events (issuance + revocation + verification): {len(audit_events):,} PASS")

    return verifications, revocations, audit_events



def main():
    print("CREDENTIAL MANAGEMENT SYSTEM")
    print("=" * 40)
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Reference date: {REFERENCE_DATE.isoformat()}")

    learners = generate_learners()
    courses = generate_courses()
    credential_rules = generate_credential_rules(courses)
    completion_records = generate_completion_records(
        learners, courses, credential_rules
    )
    issuers, issuer_keys = generate_issuers_and_keys()
    credentials, audit_events = generate_credentials(
        completion_records, learners, courses, credential_rules,
        issuers, issuer_keys
    )
    verifications, revocations, audit_events = generate_verification_and_revocation(
        credentials, audit_events
    )

    print("\nDATA GENERATION")
    print("-" * 40)
    print(f"Learners: {len(learners):,}")
    print(f"Courses: {len(courses):,}")
    print(f"Credential rules: {len(credential_rules):,}")
    print(f"Completion records: {len(completion_records):,}")
    print(f"Issuers: {len(issuers):,}")
    print(f"Issuer keys: {len(issuer_keys):,}")
    print(f"Credentials issued: {len(credentials):,}")
    print(f"Revocations: {len(revocations):,}")
    print(f"Verification requests: {len(verifications):,}")
    print(f"Audit events: {len(audit_events):,}")

    validate_datasets(learners, courses, credential_rules)
    validate_completion_records(
        completion_records, learners, courses, credential_rules
    )
    print("\nCredential issuance workflow completed successfully.")


if __name__ == "__main__":
    main()
