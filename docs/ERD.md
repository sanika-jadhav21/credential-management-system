# Entity Relationship Diagram

The diagram reflects the ten tables defined in `database/schema.sql`. `issuer_key` is the additional supporting entity.

```mermaid
erDiagram
    LEARNER ||--o{ COMPLETION_RECORD : has
    COURSE ||--o{ COMPLETION_RECORD : contains
    COURSE ||--o{ CREDENTIAL_RULE : defines
    ISSUER ||--o{ ISSUER_KEY : owns
    COMPLETION_RECORD ||--o{ CREDENTIAL : qualifies_for
    CREDENTIAL_RULE ||--o{ CREDENTIAL : governs
    ISSUER ||--o{ CREDENTIAL : issues
    ISSUER_KEY ||--o{ CREDENTIAL : signs_with
    CREDENTIAL ||--o{ VERIFICATION_REQUEST : receives
    CREDENTIAL ||--o{ REVOCATION : may_have
    LEARNER o|--o{ AUDIT_EVENT : referenced_by
    COURSE o|--o{ AUDIT_EVENT : referenced_by
    CREDENTIAL_RULE o|--o{ AUDIT_EVENT : referenced_by
    COMPLETION_RECORD o|--o{ AUDIT_EVENT : referenced_by
    CREDENTIAL o|--o{ AUDIT_EVENT : referenced_by
    ISSUER o|--o{ AUDIT_EVENT : referenced_by
    VERIFICATION_REQUEST o|--o{ AUDIT_EVENT : referenced_by
    REVOCATION o|--o{ AUDIT_EVENT : referenced_by

    LEARNER {
        varchar learner_id PK
        varchar email UK
        enum learner_status
    }
    COURSE {
        varchar course_id PK
        varchar course_code UK
        enum course_status
        date effective_from
        date effective_to
    }
    CREDENTIAL_RULE {
        varchar rule_id PK
        varchar course_id FK
        int rule_version
        decimal min_assessment_score
        decimal min_attendance_pct
        decimal min_completion_pct
    }
    COMPLETION_RECORD {
        varchar completion_id PK
        varchar learner_id FK
        varchar course_id FK
        datetime completion_date
        enum completion_status
    }
    ISSUER {
        varchar issuer_id PK
        varchar issuer_email UK
        enum issuer_status
    }
    ISSUER_KEY {
        varchar issuer_key_id PK
        varchar issuer_id FK
        int key_version
        varchar signing_key_id UK
    }
    CREDENTIAL {
        varchar credential_id PK
        varchar completion_id FK
        varchar rule_id FK
        varchar issuer_key_id FK
        char payload_hash
        enum credential_status
    }
    VERIFICATION_REQUEST {
        varchar verification_id PK
        varchar credential_id FK
        enum verification_result
        int response_time_ms
    }
    REVOCATION {
        varchar revocation_id PK
        varchar credential_id FK
        datetime revoked_at
        enum reason_code
    }
    AUDIT_EVENT {
        varchar audit_event_id PK
        varchar event_type
        datetime event_timestamp
        json previous_state
        json new_state
        json event_metadata
    }
```

## Relationship notes
- Credential-to-completion, credential-to-rule/course, and credential-to-issuer-key/issuer use composite foreign keys to prevent mismatched parent identities.
- The schema restricts deletes and updates on referenced parent keys.
- `audit_event` uses nullable foreign keys because one event targets a subset of the entities.
- Credential issuance history is sequenced with `issuance_number`; the pair `(completion_id, issuance_number)` is unique.
