# Data Validation, Synchronization, and Reproducibility Report

## 1. Scope

This report records the validation and synchronization checks completed for the Credential Management System, together with the fixed-seed reproducibility test performed on the generated CSV datasets.

The database validation and CSV-to-MySQL comparison were performed against the staging environment. Those checks were read-only with respect to database contents. The reproducibility test generated the CSV datasets twice using the same configured random seed and compared the SHA-256 checksums of the resulting files.

## 2. Recorded result summary

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
| Fixed-seed CSV reproducibility | PASS | Two generation runs used seed `20261022`; all 10 CSV files had matching SHA-256 checksums |

## 3. Table row counts

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

## 4. Database validation interpretation

- The full comparator checked row counts, primary keys, every comparable column value, and foreign-key relationships.
- JSON columns were normalized before comparison, so object key ordering and insignificant whitespace did not create false differences.
- `revocation.created_at` is database-generated and is not present in the source CSV; the comparator treats this as an expected database-managed field.
- The staging validator reported 24 PASS checks and zero data-quality findings.
- These results apply to the staging database snapshot used during the recorded run. The production database was not rebuilt as part of this validation.

## 5. Fixed-seed reproducibility test

### Test configuration

| Item | Recorded value |
|---|---|
| Random seed | `20261022` |
| Reference date printed by generator | `2026-11-04` |
| Independent generation runs | 2 |
| Output directory compared | `data/raw` |
| CSV files in each run | 10 |
| Hash algorithm | SHA-256 |
| Comparison method | PowerShell `Get-FileHash` and `Compare-Object` |

### Procedure performed

1. Ran `python -m src.data_generation.generator` for the first generation run.
2. Copied the ten CSV files from `data/raw` into a temporary backup directory named `credential_run1`.
3. Ran `python -m src.data_generation.generator` again with the same configured seed, `20261022`.
4. Copied the ten regenerated CSV files from `data/raw` into a second temporary backup directory named `credential_run2`.
5. Calculated SHA-256 hashes for each file in both directories, matched files by filename, and compared the filename/hash pairs using `Compare-Object`.

### Result

**PASS.** The two backup directories each contained the same ten expected CSV filenames. The PowerShell `Compare-Object` command returned no differences when comparing the filename and SHA-256 hash pairs. Therefore, the ten generated CSV files in `data/raw` were byte-for-byte identical between the two recorded runs.

This result demonstrates deterministic CSV generation for the tested seed, generator version, configuration, and reference date. It does not by itself prove that every environment or future generator version will produce identical output.

### Reproduction commands

Run from the project root in PowerShell. These commands make temporary copies of the generated CSVs; they do not import data into MySQL.

```powershell
# Run 1
python -m src.data_generation.generator
$run1 = "$env:TEMP\credential_run1"
New-Item -ItemType Directory -Force -Path $run1 | Out-Null
Copy-Item .\data\raw\*.csv $run1

# Run 2
python -m src.data_generation.generator
$run2 = "$env:TEMP\credential_run2"
New-Item -ItemType Directory -Force -Path $run2 | Out-Null
Copy-Item .\data\raw\*.csv $run2

# Calculate and compare SHA-256 hashes
$hash1 = Get-ChildItem $run1 -File | Sort-Object Name | ForEach-Object {
    [PSCustomObject]@{
        File = $_.Name
        Hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    }
}

$hash2 = Get-ChildItem $run2 -File | Sort-Object Name | ForEach-Object {
    [PSCustomObject]@{
        File = $_.Name
        Hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    }
}

Compare-Object $hash1 $hash2 -Property File, Hash
```

An empty `Compare-Object` result means that all compared filenames and hashes match. Any output indicates one or more differences that should be investigated.

## 6. Important environment note

The verified database for the database-validation results is `credential_management_staging_db`. Do not switch `.env` to `credential_management_db` when rerunning the staging checks unless you deliberately intend to validate that separate database.

## 7. Database reproduction commands

From the project root, with the intended staging database selected in the local environment configuration:

```powershell
python -m src.database.validate_data_quality
python -m src.database.compare_csv_mysql_full
```

Both scripts should be run with the intended staging database selected in the local environment configuration. The full comparator uses read-only SELECT queries. Do not rerun schema creation or bulk import simply to reproduce these reports.

## 8. Limitations

- This report documents the successful checks that were run. It does not establish production security, load/performance capacity, or the legal validity of credentials.
- The generator's signing material is simulated. The hash and signature-related metadata should not be described as a production-grade digital-signature or key-management infrastructure.
- The anomaly evaluation metrics reported elsewhere in the project apply to the controlled synthetic fixtures and normal controls used by that evaluation; they do not establish real-world generalization or trained machine-learning model performance.
- The reproducibility result applies to the two runs performed with the recorded seed, generator version, configuration, and reference date. Changes to code, dependencies, configuration, or date handling may change generated outputs.
