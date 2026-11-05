# Credential Management System

## Project overview
A rule-driven synthetic credential lifecycle project. It demonstrates learner/course master data, completion evidence, credential eligibility and issuance, issuer/key metadata, third-party verification, revocation, audit events, data validation, and controlled anomaly evaluation.

> **Security scope:** Issuer key and signature values are simulated metadata. SHA-256 payload hashes demonstrate integrity checking, but this project does not implement production-grade asymmetric digital signatures, managed private keys, authenticated roles, or legally trusted credentials.

## Verified data volume
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

Fixed seed: `20261022`. Generator reference date: `2026-11-04`.

## Project layout
```text
credential_management_system/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── AI_PROMPT_HISTORY.md
├── SOURCE_MANIFEST.json
├── config/
├── database/
│   ├── schema.sql
│   └── schema_staging.sql
├── data/
│   ├── raw/
│   ├── processed/
│   └── exports/
├── docs/
│   ├── DATA_DICTIONARY.md
│   ├── ERD.md
│   ├── ERD_RELATIONSHIPS.txt
│   ├── VALIDATION_REPORT.md
│   └── REQUIREMENTS_TRACEABILITY.md
├── src/
│   ├── data_generation/
│   └── database/
└── tests/
```

## Setup
Run commands from the project root in PowerShell.

```powershell
python -m venv .credential_management
.\.credential_management\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and configure the local MySQL connection. Never commit `.env` or share its contents.

## Reproducible workflow
```powershell
# Generate source datasets only when regeneration is intended
python -m src.data_generation.generator

# Generate separate anomaly ground-truth fixtures
python -m src.data_generation.ground_truth

# Run controlled rule-engine evaluation
python -m src.data_generation.evaluate

# Run unit tests
python -m unittest tests.test_evaluation_rules -v

# Validate source CSV data against business rules
python -m src.database.validate_data_quality

# Compare source CSV data with the configured MySQL database (read-only)
python -m src.database.compare_csv_mysql_full
```

**Database caution:** The previously validated database was `credential_management_staging_db`. Confirm the database selected in local `.env` before running database validation. Do not rerun schema creation or bulk import against an already populated database unless intentionally rebuilding it.

## Evaluation interpretation
The evaluator uses four labelled anomaly fixtures and four normal controls. The recorded confusion matrix was TP=4, TN=4, FP=0, FN=0. These are controlled synthetic rule-engine test results, not trained-ML performance and not evidence of real-world generalization.

Ground-truth labels are stored separately from ordinary operational source tables. Do not use ground-truth labels as prediction features.

## Recorded validation evidence
- Ten source CSV tables were compared with the staging MySQL database; row counts, primary keys, and comparable column values matched after JSON normalization.
- The recorded staging validation reported 24 passing business-rule checks and zero findings.
- Two independent generator runs with seed `20261022` produced identical SHA-256 checksums for all ten `data/raw` CSV files.
- See `docs/VALIDATION_REPORT.md` for the recorded procedure and scope.

These are recorded results from the tested project snapshot. They do not imply production security, load capacity, or testing of every possible lifecycle transition.

## Known limitations and future work
- Dataset sizes are currently configured as constants in `src/data_generation/generator.py`; starter/full scale configuration is not exposed as a command-line option.
- Each synthetic issuer currently has one active key version. Historical key rotation and issuer change scenarios should be added for broader lifecycle coverage.
- Audit events are generated and retained as event records, but database-level prevention of UPDATE/DELETE has not been demonstrated.
- Simulated signing metadata is not production cryptography.
- Add authenticated role-based access, API/UI integration, larger independent test suites, property-based tests, and security testing if deployment scope requires them.
