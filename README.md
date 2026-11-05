# Credential Management System

## Project overview
The Credential Management System is a rule-driven synthetic credential lifecycle project. It models learners, courses, completion evidence, credential eligibility, issuance, issuer/key metadata, third-party verification, revocation, and audit history.

The project demonstrates:
- Eligibility checks before credential issuance.
- Stable identifiers and relational integrity.
- SHA-256 payload hash metadata for integrity demonstrations.
- Verification outcomes, including `VALID`, `REVOKED`, `HASH_MISMATCH`, `EXPIRED`, and `NOT_FOUND`.
- Revocation and append-only audit-event records.
- Separate synthetic anomaly fixtures and rule-based evaluation.

> **Security scope:** The generated key and signature values are explicitly simulated. They are not production cryptographic signing keys or legally trusted digital signatures. A production deployment needs managed private keys, real asymmetric signatures, access control, secure key rotation, and operational monitoring.

## Database
- MySQL 8.0
- Database: `credential_management_db`
- Staging database used for the verified import and validation: `credential_management_staging_db`
- Schema: `database/schema.sql`
- Ten relational tables are present. `issuer_key` is an additional supporting entity alongside the nine core business entities.

## Data volume (verified generator output)
| Entity/table | Rows |
|---|---:|
| learner | 20,000 |
| course | 1,000 |
| credential_rule | 1,000 |
| completion_record | 20,000 |
| issuer | 5 |
| issuer_key | 5 |
| credential | 10,000 |
| revocation | 500 |
| verification_request | 5,000 |
| audit_event | 15,500 |
| **Total** | **77,010** |

Synthetic generation uses fixed seed `20261022`. The generator uses a fixed reference date to support repeatability.

## Project layout
```text
credential_management_system/
├── .env                       # local DB credentials; never commit
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── config/
├── database/
│   ├── schema.sql
│   └── schema_staging.sql
├── data/
│   ├── raw/                   # generated source CSVs
│   ├── processed/             # ground truth and evaluation outputs
│   └── exports/
├── src/
│   ├── data_generation/
│   │   ├── generator.py
│   │   ├── ground_truth.py
│   │   └── evaluate.py
│   └── database/
│       ├── bulk_import.py
│       ├── bulk_import_staging.py
│       ├── compare_csv_mysql.py
│       ├── compare_csv_mysql_full.py
│       └── validate_data_quality.py
└── tests/
```

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Configure `.env` using `.env.example`. Keep `.env` out of Git.
4. Create the database schema using the appropriate SQL file for the target database. Do not rerun schema creation or imports against an already populated database unless you intentionally want to rebuild it.

## Reproducible workflow
Run commands from the project root (`E:\credential_management_system`):

```powershell
# Generate source datasets (only when a regeneration is intended)
python -m src.data_generation.generator

# Generate the separate anomaly ground-truth fixtures
python -m src.data_generation.ground_truth

# Run the rule-engine evaluation
python -m src.data_generation.evaluate

# Validate source CSV data against documented business rules
python -m src.database.validate_data_quality

# Compare CSV rows and every column with MySQL (read-only)
python -m src.database.compare_csv_mysql_full
```

The evaluation script reads source CSVs and `ground_truth.csv`. It writes:
- `data/processed/evaluation_dataset.csv`
- `data/processed/evaluation_metrics.json`
- `data/processed/evaluation_report.txt`

The evaluator scores four labelled anomaly fixtures and four paired normal controls. It reports source-data findings separately. Metrics are controlled synthetic rule-engine test metrics, not ML model performance.

## Verified checks recorded during project work
- CSV-to-MySQL full comparison: all ten tables matched row counts, primary keys, and column values after JSON normalization; zero differing cells.
- Foreign-key relationship checks: all passed.
- Staging database business-rule validation: 24 checks passed with zero reported issues.
- Staging data counts: 10,000 credentials, 9,500 active credentials, 500 revoked credentials, 500 revocation records, 5,000 verification requests, and 15,500 audit events.

These are recorded results from the completed validation run, not claims that every possible production scenario has been tested.

## Limitations and future improvements
- Replace simulated signing metadata with a proper asymmetric signing system and managed key store.
- Add authenticated role-based access and approval workflows.
- Add API/UI integration and end-to-end automated tests if required by the deployment scope.
- Add independent larger test suites, property-based tests, and security testing.
- Define retention, privacy, and legal requirements before using real learner data.
