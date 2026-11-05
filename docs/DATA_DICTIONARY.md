# Data Dictionary

This document follows the MySQL 8 schema in `database/schema.sql`. `PK` means primary key, `FK` means foreign key, `UQ` means unique constraint. `DATETIME(6)` stores date and time with microsecond precision. Nullable means the column may contain `NULL`.

## Entity summary

| Table | Primary key | Main purpose | Key relationships |
|---|---|---|---|
| `learner` | `learner_id` | Learner identity and status | One learner can have many completion records; audit events may reference a learner |
| `course` | `course_id` | Course catalogue and effective dates | One course can have many rules and completion records |
| `credential_rule` | `rule_id` | Versioned eligibility requirements for a course | Many rules belong to one course; credentials reference the matching rule and course |
| `completion_record` | `completion_id` | Learner progress, attendance, assessment, and completion outcome | Each record belongs to one learner and one course |
| `issuer` | `issuer_id` | Credential issuing organization | One issuer can have many issuer keys and credentials |
| `issuer_key` | `issuer_key_id` | Issuer key version metadata | Each key belongs to one issuer; credentials reference the key and issuer pair |
| `credential` | `credential_id` | Issued credential and integrity metadata | References completion, rule, issuer, and issuer key |
| `verification_request` | `verification_id` | Third-party credential verification request and response | May reference one credential; a credential can have many requests |
| `revocation` | `revocation_id` | Revocation event and reason | Each revocation belongs to one credential |
| `audit_event` | `audit_event_id` | Historical event and state-change trace | Optional references to affected business entities |

## Column-level dictionary

### `learner`
| Column | MySQL type | Required | Rule / meaning |
|---|---|---:|---|
| learner_id | VARCHAR(20) | Yes | PK; stable learner identifier |
| first_name | VARCHAR(100) | Yes | Nonblank |
| last_name | VARCHAR(100) | Yes | Nonblank |
| email | VARCHAR(255) | Yes | Unique email |
| phone | VARCHAR(20) | No | Contact number |
| date_of_birth | DATE | No | Date of birth |
| registration_date | DATETIME(6) | Yes | Registration timestamp |
| learner_status | ENUM | Yes | ACTIVE, INACTIVE, SUSPENDED |
| created_at | DATETIME(6) | Yes | Creation timestamp |
| updated_at | DATETIME(6) | Yes | Last update timestamp |

### `course`
| Column | MySQL type | Required | Rule / meaning |
|---|---|---:|---|
| course_id | VARCHAR(20) | Yes | PK |
| course_code | VARCHAR(30) | Yes | Unique course code |
| course_name | VARCHAR(200) | Yes | Nonblank title |
| description | TEXT | No | Course description |
| category | VARCHAR(100) | Yes | Course category |
| duration_hours | DECIMAL(7,2) | Yes | Must be greater than zero |
| total_modules | INT UNSIGNED | Yes | Must be greater than zero |
| course_status | ENUM | Yes | ACTIVE, INACTIVE, RETIRED |
| effective_from | DATE | Yes | Start of course validity |
| effective_to | DATE | No | NULL for active/open-ended course; otherwise later than effective_from |
| created_at | DATETIME(6) | Yes | Creation timestamp |
| updated_at | DATETIME(6) | Yes | Last update timestamp |

### `credential_rule`
| Column | MySQL type | Required | Rule / meaning |
|---|---|---:|---|
| rule_id | VARCHAR(25) | Yes | PK |
| course_id | VARCHAR(20) | Yes | FK to course |
| rule_version | INT UNSIGNED | Yes | Positive version; unique with course_id |
| min_assessment_score | DECIMAL(5,2) | Yes | 0 to 100 |
| min_attendance_pct | DECIMAL(5,2) | Yes | 0 to 100 |
| min_completion_pct | DECIMAL(5,2) | Yes | 0 to 100 |
| require_all_modules | BOOLEAN | Yes | Whether all modules are mandatory |
| require_assessment_pass | BOOLEAN | Yes | Whether assessment pass is mandatory |
| effective_from | DATE | Yes | Rule validity start |
| effective_to | DATE | No | NULL or later than effective_from |
| rule_status | ENUM | Yes | ACTIVE, INACTIVE, RETIRED |
| created_at | DATETIME(6) | Yes | Creation timestamp |

### `completion_record`
| Column | MySQL type | Required | Rule / meaning |
|---|---|---:|---|
| completion_id | VARCHAR(60) | Yes | PK; generated as CMP-learner-course |
| learner_id | VARCHAR(20) | Yes | FK to learner |
| course_id | VARCHAR(20) | Yes | FK to course |
| enrollment_date | DATETIME(6) | Yes | Enrollment timestamp |
| completion_date | DATETIME(6) | No | Required when status is COMPLETED |
| completion_pct | DECIMAL(5,2) | Yes | 0 to 100; completed requires 100 |
| attendance_pct | DECIMAL(5,2) | Yes | 0 to 100 |
| assessment_score | DECIMAL(5,2) | No | NULL or 0 to 100 |
| assessment_attempts | INT UNSIGNED | Yes | Number of attempts |
| modules_completed | INT UNSIGNED | Yes | Completed module count |
| completion_status | ENUM | Yes | ENROLLED, IN_PROGRESS, COMPLETED, FAILED, WITHDRAWN |
| assessment_status | ENUM | Yes | NOT_ATTEMPTED, PASSED, FAILED |
| instructor_reference | VARCHAR(100) | No | Instructor reference |
| created_at | DATETIME(6) | Yes | Creation timestamp |
| updated_at | DATETIME(6) | Yes | Last update timestamp |

### `issuer`
| Column | MySQL type | Required | Rule / meaning |
|---|---|---:|---|
| issuer_id | VARCHAR(20) | Yes | PK |
| issuer_name | VARCHAR(150) | Yes | Issuer display name |
| organization_name | VARCHAR(200) | Yes | Issuer organization |
| issuer_email | VARCHAR(255) | Yes | Unique issuer email |
| issuer_status | ENUM | Yes | ACTIVE, INACTIVE, SUSPENDED |
| created_at | DATETIME(6) | Yes | Creation timestamp |
| updated_at | DATETIME(6) | Yes | Last update timestamp |

### `issuer_key`
| Column | MySQL type | Required | Rule / meaning |
|---|---|---:|---|
| issuer_key_id | VARCHAR(30) | Yes | PK |
| issuer_id | VARCHAR(20) | Yes | FK to issuer |
| key_version | INT UNSIGNED | Yes | Positive; unique with issuer_id |
| signing_key_id | VARCHAR(100) | Yes | Unique key reference |
| public_key | TEXT | Yes | Simulated public-key metadata in this dataset |
| key_algorithm | VARCHAR(40) | Yes | Algorithm label |
| key_status | ENUM | Yes | ACTIVE, RETIRED, REVOKED |
| valid_from | DATETIME(6) | Yes | Key validity start |
| valid_to | DATETIME(6) | No | NULL or later than valid_from |
| created_at | DATETIME(6) | Yes | Creation timestamp |

### `credential`
| Column | MySQL type | Required | Rule / meaning |
|---|---|---:|---|
| credential_id | VARCHAR(25) | Yes | PK; format CRD-2026-000001 |
| learner_id | VARCHAR(20) | Yes | Learner identity associated with completion |
| course_id | VARCHAR(20) | Yes | Course associated with completion |
| completion_id | VARCHAR(60) | Yes | Composite FK ensures learner/course match completion |
| rule_id | VARCHAR(25) | Yes | Composite FK ensures rule belongs to course |
| issuer_id | VARCHAR(20) | Yes | Issuer associated with signing key |
| issuer_key_id | VARCHAR(30) | Yes | Composite FK ensures key belongs to issuer |
| issuance_number | INT UNSIGNED | Yes | Positive; unique per completion |
| issue_date | DATETIME(6) | Yes | Issuance timestamp |
| valid_from | DATETIME(6) | Yes | Must be on/after issue_date |
| expires_at | DATETIME(6) | No | NULL or later than valid_from |
| credential_status | ENUM | Yes | ACTIVE, REVOKED, EXPIRED |
| payload_hash | CHAR(64) | Yes | 64 hexadecimal characters |
| hash_algorithm | VARCHAR(20) | Yes | SHA256 |
| signature_value | TEXT | Yes | Simulated signature value |
| signature_algorithm | VARCHAR(40) | Yes | Signature algorithm label |
| created_at | DATETIME(6) | Yes | Creation timestamp |

### `verification_request`
| Column | MySQL type | Required | Rule / meaning |
|---|---|---:|---|
| verification_id | VARCHAR(25) | Yes | PK; format VER-2026-000001 |
| submitted_credential_id | VARCHAR(25) | Yes | Credential identifier submitted by verifier |
| credential_id | VARCHAR(25) | No | FK to credential; NULL for NOT_FOUND |
| verifier_organization | VARCHAR(200) | No | Requesting organization |
| verifier_reference | VARCHAR(100) | No | External reference |
| request_timestamp | DATETIME(6) | Yes | Request timestamp |
| response_timestamp | DATETIME(6) | No | NULL until response; otherwise >= request timestamp |
| verification_result | ENUM | Yes | VALID, REVOKED, NOT_FOUND, HASH_MISMATCH, INVALID_SIGNATURE, NOT_YET_VALID, EXPIRED, INELIGIBLE |
| verification_reason | VARCHAR(500) | No | Human-readable result explanation |
| checked_payload_hash | CHAR(64) | No | Stored/checked hash |
| provided_payload_hash | CHAR(64) | No | Hash supplied for verification |
| response_time_ms | INT UNSIGNED | No | Response latency in milliseconds |
| request_channel | ENUM | Yes | API, WEB, MANUAL |
| created_at | DATETIME(6) | Yes | Creation timestamp |

### `revocation`
| Column | MySQL type | Required | Rule / meaning |
|---|---|---:|---|
| revocation_id | VARCHAR(60) | Yes | PK; generated from credential and sequence |
| credential_id | VARCHAR(25) | Yes | FK to credential |
| revocation_sequence | INT UNSIGNED | Yes | Positive sequence |
| revoked_at | DATETIME(6) | Yes | Event timestamp |
| effective_at | DATETIME(6) | Yes | Time revocation becomes effective |
| reason_code | ENUM | Yes | FRAUD, ISSUED_IN_ERROR, ACADEMIC_MISCONDUCT, IDENTITY_MISMATCH, ADMINISTRATIVE_ERROR, OTHER |
| reason_description | VARCHAR(500) | No | Description; required when reason_code is OTHER |
| revoked_by_role | VARCHAR(50) | Yes | Actor role |
| revoked_by_reference | VARCHAR(100) | No | Actor reference |
| created_at | DATETIME(6) | Yes | Creation timestamp |

### `audit_event`
| Column | MySQL type | Required | Rule / meaning |
|---|---|---:|---|
| audit_event_id | VARCHAR(25) | Yes | PK |
| event_type | VARCHAR(50) | Yes | Event name |
| event_timestamp | DATETIME(6) | Yes | Event time |
| actor_role | VARCHAR(50) | Yes | Role that initiated the event |
| actor_reference | VARCHAR(100) | No | Actor identifier/reference |
| target_entity_type | ENUM | Yes | Target entity category |
| learner_id | VARCHAR(20) | No | Optional FK to learner |
| course_id | VARCHAR(20) | No | Optional FK to course |
| rule_id | VARCHAR(25) | No | Optional FK to credential_rule |
| completion_id | VARCHAR(60) | No | Optional FK to completion_record |
| credential_id | VARCHAR(25) | No | Optional FK to credential |
| issuer_id | VARCHAR(20) | No | Optional FK to issuer |
| verification_id | VARCHAR(25) | No | Optional FK to verification_request |
| revocation_id | VARCHAR(60) | No | Optional FK to revocation |
| previous_state | JSON | No | State before event |
| new_state | JSON | No | State after event |
| event_metadata | JSON | No | Additional event context |
| correlation_id | VARCHAR(100) | No | Links related events |
| created_at | DATETIME(6) | Yes | Record creation timestamp |

## Cardinality and integrity
- `learner` 1 to many `completion_record`.
- `course` 1 to many `completion_record`.
- `course` 1 to many `credential_rule` versions.
- `issuer` 1 to many `issuer_key` versions.
- `completion_record` 1 to many `credential` issuance sequences, constrained by unique `(completion_id, issuance_number)`.
- `credential_rule` 1 to many `credential` rows over time, with a composite course match.
- `issuer_key` 1 to many `credential` rows, with a composite issuer match.
- `credential` 1 to many `verification_request`.
- `credential` 1 to many `revocation` history records where allowed by schema constraints.
- Each `audit_event` may refer to zero or one row in each supported target entity through nullable FKs. Audit events preserve history rather than replacing the event trail.

The schema uses foreign keys with restrictive delete/update behavior to protect referenced records. It uses unique constraints and CHECK constraints for key domain rules. The exact enforced rules are defined in `database/schema.sql`.
