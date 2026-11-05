# Data Validation and Synchronization Report

## Scope
This report records the validation results completed for the Credential Management System staging environment. The checks were read-only with respect to database contents during validation and comparison.

## Recorded result summary

| Validation area | Result | Evidence recorded |
|---|---|---|
| CSV-to-MySQL row counts | PASS | All 10 tables matched |
| Primary-key comparison | PASS | All 10 tables matched |
| Full column-value comparison | PASS | All compared values matched after JSON normalization |
| JSON comparison | PASS | JSON values compared structurally, not by key order/whitespace |
| Foreign-key orphan checks | PASS | All 10 relationship checks passed |
| Business-rule validation | PASS | 24 checks passed; zero reported issues |
| Staging credential counts | PASS | 10,000 total; 9,500 active; 500 revoked |
| Revocation records | PASS | 500 |
| Verification requests | PASS | 5,000 |
| Audit events | PASS | 15,500 |

## Table row counts

| Table | CSV/MySQL rows |
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

## Validation interpretation
- The full comparator checked row counts, primary keys, every comparable column value, and foreign-key relationships.
- JSON columns were normalized before comparison, so object key ordering and insignificant whitespace did not create false differences.
- `revocation.created_at` is database-generated and is not present in the source CSV; the comparator treats this as an expected database-managed field.
- The staging validator reported 24 PASS checks and zero data-quality findings.
- These results apply to the staging database snapshot used during the recorded run. The production database was not rebuilt as part of this validation.

## Important environment note
The verified database for these results is `credential_management_staging_db`. Do not switch `.env` to `credential_management_db` when rerunning the staging checks unless you deliberately intend to validate that separate database.

## Reproduction commands
From the project root:

```powershell
python -m src.database.validate_data_quality
python -m src.database.compare_csv_mysql_full
```

Both scripts should be run with the intended staging database selected in the local environment configuration. The full comparator uses read-only SELECT queries. Do not rerun schema creation or bulk import simply to reproduce these reports.

## Limitations
This report documents the successful checks that were run. It does not establish production security, load/performance capacity, legal validity of credentials, or cryptographic signature assurance. The generator's signing material is simulated.
