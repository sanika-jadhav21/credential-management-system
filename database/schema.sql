
-- Step 3.1: Create project database

CREATE DATABASE IF NOT EXISTS credential_management_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_0900_ai_ci;

-- Select the project database
USE credential_management_db;

-- Verify the selected database
SELECT DATABASE() AS selected_database;



-- Step 3.2: Verify database configuration

SELECT
    SCHEMA_NAME AS database_name,
    DEFAULT_CHARACTER_SET_NAME AS character_set,
    DEFAULT_COLLATION_NAME AS collation
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME = 'credential_management_db';




-- Step 3.3: Create learner table

USE credential_management_db;

CREATE TABLE learner (
    learner_id VARCHAR(20) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NULL,
    date_of_birth DATE NULL,
    registration_date DATETIME(6) NOT NULL,
    learner_status ENUM(
        'ACTIVE',
        'INACTIVE',
        'SUSPENDED'
    ) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_learner
        PRIMARY KEY (learner_id),

    CONSTRAINT uq_learner_email
        UNIQUE (email),

    CONSTRAINT chk_learner_first_name
        CHECK (CHAR_LENGTH(TRIM(first_name)) > 0),

    CONSTRAINT chk_learner_last_name
        CHECK (CHAR_LENGTH(TRIM(last_name)) > 0)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;



-- Verify learner table structure
DESCRIBE learner;



-- Step 3.4: Create course table
USE credential_management_db;

CREATE TABLE course (
    course_id VARCHAR(20) NOT NULL,
    course_code VARCHAR(30) NOT NULL,
    course_name VARCHAR(200) NOT NULL,
    description TEXT NULL,
    category VARCHAR(100) NOT NULL,
    duration_hours DECIMAL(7,2) NOT NULL,
    total_modules INT UNSIGNED NOT NULL,
    course_status ENUM(
        'ACTIVE',
        'INACTIVE',
        'RETIRED'
    ) NOT NULL DEFAULT 'ACTIVE',
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_course
        PRIMARY KEY (course_id),

    CONSTRAINT uq_course_code
        UNIQUE (course_code),

    CONSTRAINT chk_course_duration
        CHECK (duration_hours > 0),

    CONSTRAINT chk_course_total_modules
        CHECK (total_modules > 0),

    CONSTRAINT chk_course_effective_dates
        CHECK (
            effective_to IS NULL
            OR effective_to > effective_from
        ),

    CONSTRAINT chk_course_name
        CHECK (CHAR_LENGTH(TRIM(course_name)) > 0)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;


-- Verify course table structure
DESCRIBE course;


-- Verify CHECK constraints on course table
SELECT
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'credential_management_db'
  AND TABLE_NAME = 'course'
  AND CONSTRAINT_TYPE = 'CHECK'
ORDER BY CONSTRAINT_NAME;



-- Step 3.5: Create credential_rule table
USE credential_management_db;

CREATE TABLE credential_rule (
    rule_id VARCHAR(25) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    rule_version INT UNSIGNED NOT NULL,
    min_assessment_score DECIMAL(5,2) NOT NULL,
    min_attendance_pct DECIMAL(5,2) NOT NULL,
    min_completion_pct DECIMAL(5,2) NOT NULL,
    require_all_modules BOOLEAN NOT NULL DEFAULT TRUE,
    require_assessment_pass BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    rule_status ENUM(
        'ACTIVE',
        'INACTIVE',
        'RETIRED'
    ) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_credential_rule
        PRIMARY KEY (rule_id),

    CONSTRAINT uq_course_rule_version
        UNIQUE (course_id, rule_version),

    -- Required later for composite foreign key
    CONSTRAINT uq_rule_course
        UNIQUE (rule_id, course_id),

    CONSTRAINT fk_rule_course
        FOREIGN KEY (course_id)
        REFERENCES course(course_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT chk_rule_version
        CHECK (rule_version > 0),

    CONSTRAINT chk_rule_assessment_score
        CHECK (
            min_assessment_score BETWEEN 0 AND 100
        ),

    CONSTRAINT chk_rule_attendance
        CHECK (
            min_attendance_pct BETWEEN 0 AND 100
        ),

    CONSTRAINT chk_rule_completion
        CHECK (
            min_completion_pct BETWEEN 0 AND 100
        ),

    CONSTRAINT chk_rule_effective_dates
        CHECK (
            effective_to IS NULL
            OR effective_to > effective_from
        )
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
  
  
-- Verify credential_rule table structure
DESCRIBE credential_rule;


-- Verify credential_rule constraints
SELECT
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'credential_management_db'
  AND TABLE_NAME = 'credential_rule'
ORDER BY CONSTRAINT_TYPE, CONSTRAINT_NAME;




-- Step 3.6: Create completion_record table

USE credential_management_db;

CREATE TABLE completion_record (
    completion_id VARCHAR(60) NOT NULL,
    learner_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    enrollment_date DATETIME(6) NOT NULL,
    completion_date DATETIME(6) NULL,
    completion_pct DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    attendance_pct DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    assessment_score DECIMAL(5,2) NULL,
    assessment_attempts INT UNSIGNED NOT NULL DEFAULT 0,
    modules_completed INT UNSIGNED NOT NULL DEFAULT 0,
    completion_status ENUM(
        'ENROLLED',
        'IN_PROGRESS',
        'COMPLETED',
        'FAILED',
        'WITHDRAWN'
    ) NOT NULL DEFAULT 'ENROLLED',
    assessment_status ENUM(
        'NOT_ATTEMPTED',
        'PASSED',
        'FAILED'
    ) NOT NULL DEFAULT 'NOT_ATTEMPTED',
    instructor_reference VARCHAR(100) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_completion_record
        PRIMARY KEY (completion_id),

    -- One completion record per learner per course
    CONSTRAINT uq_learner_course
        UNIQUE (learner_id, course_id),

    -- Required later for credential composite foreign key
    CONSTRAINT uq_completion_learner_course
        UNIQUE (completion_id, learner_id, course_id),

    CONSTRAINT fk_completion_learner
        FOREIGN KEY (learner_id)
        REFERENCES learner(learner_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_completion_course
        FOREIGN KEY (course_id)
        REFERENCES course(course_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT chk_completion_percentage
        CHECK (completion_pct BETWEEN 0 AND 100),

    CONSTRAINT chk_completion_attendance
        CHECK (attendance_pct BETWEEN 0 AND 100),

    CONSTRAINT chk_completion_assessment_score
        CHECK (
            assessment_score IS NULL
            OR assessment_score BETWEEN 0 AND 100
        ),

    CONSTRAINT chk_completion_dates
        CHECK (
            completion_date IS NULL
            OR completion_date >= enrollment_date
        ),

    CONSTRAINT chk_completed_record
        CHECK (
            completion_status <> 'COMPLETED'
            OR (
                completion_pct = 100
                AND completion_date IS NOT NULL
            )
        ),

    CONSTRAINT chk_assessment_status
        CHECK (
            assessment_status <> 'PASSED'
            OR assessment_score IS NOT NULL
        )
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
  
  
  
-- Verify completion_record table structure
DESCRIBE completion_record;

SELECT
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'credential_management_db'
  AND TABLE_NAME = 'completion_record'
ORDER BY CONSTRAINT_TYPE, CONSTRAINT_NAME;



-- Step 3.7: Create issuer table

USE credential_management_db;

CREATE TABLE issuer (
    issuer_id VARCHAR(20) NOT NULL,
    issuer_name VARCHAR(150) NOT NULL,
    organization_name VARCHAR(200) NOT NULL,
    issuer_email VARCHAR(255) NOT NULL,
    issuer_status ENUM(
        'ACTIVE',
        'INACTIVE',
        'SUSPENDED'
    ) NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_issuer
        PRIMARY KEY (issuer_id),

    CONSTRAINT uq_issuer_email
        UNIQUE (issuer_email),

    CONSTRAINT chk_issuer_name
        CHECK (CHAR_LENGTH(TRIM(issuer_name)) > 0),

    CONSTRAINT chk_issuer_organization
        CHECK (CHAR_LENGTH(TRIM(organization_name)) > 0)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;


-- Verify issuer table structure
DESCRIBE issuer;


-- Verify issuer table constraints
SELECT
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'credential_management_db'
  AND TABLE_NAME = 'issuer'
ORDER BY CONSTRAINT_TYPE, CONSTRAINT_NAME;






-- Step 3.8: Create issuer_key table
USE credential_management_db;

CREATE TABLE issuer_key (
    issuer_key_id VARCHAR(30) NOT NULL,
    issuer_id VARCHAR(20) NOT NULL,
    key_version INT UNSIGNED NOT NULL,
    signing_key_id VARCHAR(100) NOT NULL,
    public_key TEXT NOT NULL,
    key_algorithm VARCHAR(40) NOT NULL,
    key_status ENUM(
        'ACTIVE',
        'RETIRED',
        'REVOKED'
    ) NOT NULL DEFAULT 'ACTIVE',
    valid_from DATETIME(6) NOT NULL,
    valid_to DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_issuer_key
        PRIMARY KEY (issuer_key_id),

    CONSTRAINT uq_issuer_key_version
        UNIQUE (issuer_id, key_version),

    CONSTRAINT uq_signing_key_id
        UNIQUE (signing_key_id),

    -- Required later for credential composite foreign key
    CONSTRAINT uq_issuer_key_pair
        UNIQUE (issuer_key_id, issuer_id),

    CONSTRAINT fk_issuer_key_issuer
        FOREIGN KEY (issuer_id)
        REFERENCES issuer(issuer_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT chk_issuer_key_version
        CHECK (key_version > 0),

    CONSTRAINT chk_issuer_key_dates
        CHECK (
            valid_to IS NULL
            OR valid_to > valid_from
        ),

    CONSTRAINT chk_issuer_public_key
        CHECK (CHAR_LENGTH(TRIM(public_key)) > 0)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;


-- Verify issuer_key table structure
DESCRIBE issuer_key;


-- Verify issuer_key constraints
SELECT
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'credential_management_db'
  AND TABLE_NAME = 'issuer_key'
ORDER BY CONSTRAINT_TYPE, CONSTRAINT_NAME;






-- Step 3.9: Create credential table

USE credential_management_db;

CREATE TABLE credential (
    credential_id VARCHAR(25) NOT NULL,
    learner_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    completion_id VARCHAR(60) NOT NULL,
    rule_id VARCHAR(25) NOT NULL,
    issuer_id VARCHAR(20) NOT NULL,
    issuer_key_id VARCHAR(30) NOT NULL,
    issuance_number INT UNSIGNED NOT NULL DEFAULT 1,
    issue_date DATETIME(6) NOT NULL,
    valid_from DATETIME(6) NOT NULL,
    expires_at DATETIME(6) NULL,
    credential_status ENUM(
        'ACTIVE',
        'REVOKED',
        'EXPIRED'
    ) NOT NULL DEFAULT 'ACTIVE',
    payload_hash CHAR(64) NOT NULL,
    hash_algorithm VARCHAR(20) NOT NULL DEFAULT 'SHA256',
    signature_value TEXT NOT NULL,
    signature_algorithm VARCHAR(40) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_credential
        PRIMARY KEY (credential_id),

    -- Prevent duplicate issuance sequence for one completion
    CONSTRAINT uq_completion_issuance
        UNIQUE (completion_id, issuance_number),

    -- Ensure learner and course match completion record
    CONSTRAINT fk_credential_completion
        FOREIGN KEY (completion_id, learner_id, course_id)
        REFERENCES completion_record(
            completion_id,
            learner_id,
            course_id
        )
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    -- Ensure rule belongs to the same course
    CONSTRAINT fk_credential_rule_course
        FOREIGN KEY (rule_id, course_id)
        REFERENCES credential_rule(rule_id, course_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    -- Ensure signing key belongs to the specified issuer
    CONSTRAINT fk_credential_issuer_key
        FOREIGN KEY (issuer_key_id, issuer_id)
        REFERENCES issuer_key(issuer_key_id, issuer_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT chk_credential_issuance_number
        CHECK (issuance_number > 0),

    CONSTRAINT chk_credential_dates
        CHECK (
            expires_at IS NULL
            OR expires_at > valid_from
        ),

    CONSTRAINT chk_credential_issue_date
        CHECK (valid_from >= issue_date),

    CONSTRAINT chk_credential_hash
        CHECK (
            CHAR_LENGTH(payload_hash) = 64
            AND payload_hash REGEXP '^[0-9a-fA-F]{64}$'
        ),

    CONSTRAINT chk_credential_hash_algorithm
        CHECK (hash_algorithm = 'SHA256'),

    CONSTRAINT chk_credential_signature
        CHECK (CHAR_LENGTH(TRIM(signature_value)) > 0)
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;


-- Verify credential table structure
DESCRIBE credential;



-- Verify credential table constraints
SELECT
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'credential_management_db'
  AND TABLE_NAME = 'credential'
ORDER BY CONSTRAINT_TYPE, CONSTRAINT_NAME;



-- Verify all CHECK constraints on credential

SELECT
    CONSTRAINT_NAME,
    CHECK_CLAUSE
FROM information_schema.CHECK_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'credential_management_db'
  AND CONSTRAINT_NAME IN (
      SELECT CONSTRAINT_NAME
      FROM information_schema.TABLE_CONSTRAINTS
      WHERE TABLE_SCHEMA = 'credential_management_db'
        AND TABLE_NAME = 'credential'
        AND CONSTRAINT_TYPE = 'CHECK'
  )
ORDER BY CONSTRAINT_NAME;






-- Step 3.10: Create verification_request table

USE credential_management_db;

CREATE TABLE verification_request (
    verification_id VARCHAR(25) NOT NULL,
    submitted_credential_id VARCHAR(25) NOT NULL,
    credential_id VARCHAR(25) NULL,
    verifier_organization VARCHAR(200) NULL,
    verifier_reference VARCHAR(100) NULL,
    request_timestamp DATETIME(6) NOT NULL,
    response_timestamp DATETIME(6) NULL,

    verification_result ENUM(
        'VALID',
        'REVOKED',
        'NOT_FOUND',
        'HASH_MISMATCH',
        'INVALID_SIGNATURE',
        'NOT_YET_VALID',
        'EXPIRED',
        'INELIGIBLE'
    ) NOT NULL,

    verification_reason VARCHAR(500) NULL,
    checked_payload_hash CHAR(64) NULL,
    provided_payload_hash CHAR(64) NULL,
    response_time_ms INT UNSIGNED NULL,

    request_channel ENUM(
        'API',
        'WEB',
        'MANUAL'
    ) NOT NULL DEFAULT 'API',

    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_verification_request
        PRIMARY KEY (verification_id),

    CONSTRAINT fk_verification_credential
        FOREIGN KEY (credential_id)
        REFERENCES credential(credential_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT chk_verification_timestamps
        CHECK (
            response_timestamp IS NULL
            OR response_timestamp >= request_timestamp
        ),

    CONSTRAINT chk_verification_checked_hash
        CHECK (
            checked_payload_hash IS NULL
            OR (
                CHAR_LENGTH(checked_payload_hash) = 64
                AND checked_payload_hash REGEXP '^[0-9a-fA-F]{64}$'
            )
        ),

    CONSTRAINT chk_verification_provided_hash
        CHECK (
            provided_payload_hash IS NULL
            OR (
                CHAR_LENGTH(provided_payload_hash) = 64
                AND provided_payload_hash REGEXP '^[0-9a-fA-F]{64}$'
            )
        ),

    CONSTRAINT chk_verification_not_found
        CHECK (
            verification_result <> 'NOT_FOUND'
            OR credential_id IS NULL
        )

) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;


DESCRIBE verification_request;

SELECT
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'credential_management_db'
  AND TABLE_NAME = 'verification_request'
ORDER BY CONSTRAINT_TYPE, CONSTRAINT_NAME;





-- Step 3.11: Create revocation table

USE credential_management_db;

CREATE TABLE revocation (
    revocation_id VARCHAR(60) NOT NULL,
    credential_id VARCHAR(25) NOT NULL,
    revocation_sequence INT UNSIGNED NOT NULL DEFAULT 1,

    revoked_at DATETIME(6) NOT NULL,
    effective_at DATETIME(6) NOT NULL,

    reason_code ENUM(
        'FRAUD',
        'ISSUED_IN_ERROR',
        'ACADEMIC_MISCONDUCT',
        'IDENTITY_MISMATCH',
        'ADMINISTRATIVE_ERROR',
        'OTHER'
    ) NOT NULL,

    reason_description VARCHAR(500) NULL,

    revoked_by_role VARCHAR(50) NOT NULL,
    revoked_by_reference VARCHAR(100) NULL,

    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_revocation
        PRIMARY KEY (revocation_id),

    -- One permanent revocation record per credential
    CONSTRAINT uq_revocation_credential
        UNIQUE (credential_id),

    CONSTRAINT fk_revocation_credential
        FOREIGN KEY (credential_id)
        REFERENCES credential(credential_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT chk_revocation_sequence
        CHECK (revocation_sequence > 0),

    CONSTRAINT chk_revocation_other_reason
        CHECK (
            reason_code <> 'OTHER'
            OR (
                reason_description IS NOT NULL
                AND CHAR_LENGTH(TRIM(reason_description)) > 0
            )
        )

) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

DESCRIBE revocation;

SELECT
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'credential_management_db'
  AND TABLE_NAME = 'revocation'
ORDER BY CONSTRAINT_TYPE, CONSTRAINT_NAME;






-- Step 3.12: Create audit_event table
USE credential_management_db;

CREATE TABLE audit_event (
    audit_event_id VARCHAR(25) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_timestamp DATETIME(6) NOT NULL,

    actor_role VARCHAR(50) NOT NULL,
    actor_reference VARCHAR(100) NULL,

    target_entity_type ENUM(
        'LEARNER',
        'COURSE',
        'CREDENTIAL_RULE',
        'COMPLETION_RECORD',
        'CREDENTIAL',
        'ISSUER',
        'VERIFICATION_REQUEST',
        'REVOCATION'
    ) NOT NULL,

    learner_id VARCHAR(20) NULL,
    course_id VARCHAR(20) NULL,
    rule_id VARCHAR(25) NULL,
    completion_id VARCHAR(60) NULL,
    credential_id VARCHAR(25) NULL,
    issuer_id VARCHAR(20) NULL,
    verification_id VARCHAR(25) NULL,
    revocation_id VARCHAR(60) NULL,

    previous_state JSON NULL,
    new_state JSON NULL,
    event_metadata JSON NULL,

    correlation_id VARCHAR(100) NULL,

    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CONSTRAINT pk_audit_event
        PRIMARY KEY (audit_event_id),

    CONSTRAINT fk_audit_learner
        FOREIGN KEY (learner_id)
        REFERENCES learner(learner_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_audit_course
        FOREIGN KEY (course_id)
        REFERENCES course(course_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_audit_rule
        FOREIGN KEY (rule_id)
        REFERENCES credential_rule(rule_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_audit_completion
        FOREIGN KEY (completion_id)
        REFERENCES completion_record(completion_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_audit_credential
        FOREIGN KEY (credential_id)
        REFERENCES credential(credential_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_audit_issuer
        FOREIGN KEY (issuer_id)
        REFERENCES issuer(issuer_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_audit_verification
        FOREIGN KEY (verification_id)
        REFERENCES verification_request(verification_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    CONSTRAINT fk_audit_revocation
        FOREIGN KEY (revocation_id)
        REFERENCES revocation(revocation_id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,

    -- Exactly one target reference must be provided
    CONSTRAINT chk_audit_exactly_one_target
        CHECK (
            (learner_id IS NOT NULL) +
            (course_id IS NOT NULL) +
            (rule_id IS NOT NULL) +
            (completion_id IS NOT NULL) +
            (credential_id IS NOT NULL) +
            (issuer_id IS NOT NULL) +
            (verification_id IS NOT NULL) +
            (revocation_id IS NOT NULL) = 1
        ),

    -- Target type must match the populated reference
    CONSTRAINT chk_audit_target_type
        CHECK (
            (target_entity_type = 'LEARNER'
                AND learner_id IS NOT NULL)
            OR
            (target_entity_type = 'COURSE'
                AND course_id IS NOT NULL)
            OR
            (target_entity_type = 'CREDENTIAL_RULE'
                AND rule_id IS NOT NULL)
            OR
            (target_entity_type = 'COMPLETION_RECORD'
                AND completion_id IS NOT NULL)
            OR
            (target_entity_type = 'CREDENTIAL'
                AND credential_id IS NOT NULL)
            OR
            (target_entity_type = 'ISSUER'
                AND issuer_id IS NOT NULL)
            OR
            (target_entity_type = 'VERIFICATION_REQUEST'
                AND verification_id IS NOT NULL)
            OR
            (target_entity_type = 'REVOCATION'
                AND revocation_id IS NOT NULL)
        )

) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

DESCRIBE audit_event;

SELECT
    CONSTRAINT_NAME,
    CONSTRAINT_TYPE
FROM information_schema.TABLE_CONSTRAINTS
WHERE TABLE_SCHEMA = 'credential_management_db'
  AND TABLE_NAME = 'audit_event'
ORDER BY CONSTRAINT_TYPE, CONSTRAINT_NAME;

-- Verify AuditEvent CHECK constraint definitions
SELECT
    CONSTRAINT_NAME,
    CHECK_CLAUSE
FROM information_schema.CHECK_CONSTRAINTS
WHERE CONSTRAINT_SCHEMA = 'credential_management_db'
  AND CONSTRAINT_NAME IN (
      'chk_audit_exactly_one_target',
      'chk_audit_target_type'
  );

SHOW CREATE TABLE audit_event;





USE credential_management_db;

-- Verify all tables in the database

SELECT
    TABLE_NAME,
    ENGINE,
    TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'credential_management_db'
  AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;





































































































































































































































































































































































































































































































