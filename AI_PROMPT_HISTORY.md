# AI Prompt History and Usage Disclosure

**Project:** Credential Management System  
**Candidate:** Sanika Jadhav  
**GitHub repository:** https://github.com/sanika-jadhav21/credential-management-system  
**Prepared on:** 5 November 2026

> **Important note about completeness:** This document is a reconstructed summary of the AI-assisted development activities based on the available project conversation. It is not a verbatim export of every prompt sent to every AI tool. Before submission, add any missing prompts and identify any other AI tools you used. Do not describe these summaries as exact historical quotations.

## 1. Purpose of this document

This document explains how AI assistance was used during development of the Credential Management System, the activities it supported, and the work reviewed and validated by the candidate.

AI was used as a support tool for understanding requirements, planning implementation, troubleshooting, preparing documentation, and interpreting test results. The candidate is responsible for understanding the submitted project, verifying its behavior, and explaining its design decisions and limitations.

## 2. AI tools used

| AI tool | How it was used |
|---------|-----------------|
| ChatGPT | Requirement analysis, implementation guidance, troubleshooting, validation planning, documentation drafting, and Git workflow guidance |

**Add other tools here if applicable:** Include the name of each additional AI tool and the tasks for which it was used. Do not list tools that you did not use.

## 3. Prompt history by development activity

The following are representative summaries of the main prompts used during the project. They are not guaranteed to be word-for-word copies of the original prompts.

### 3.1 Understanding the business requirements

**Prompt summary**

> Review the Credential Management System business context, objectives, entities, workflow, business rules, required data volumes, anomaly scenarios, and acceptance criteria. Organize these requirements into an implementation plan and identify the expected outputs and validation checks.

**How AI assisted**

- Helped organize requirements into master data, dependent records, lifecycle operations, anomaly cases, and evaluation.
- Helped identify the need for primary keys, foreign keys, deterministic identifiers, separate ground truth, and audit history.
- Helped distinguish core workflow requirements from optional features such as a graphical user interface.

**Candidate review**

The proposed scope was compared with the project brief. The candidate is responsible for explaining the final scope and implementation decisions.

### 3.2 Data model, schema, and documentation

**Prompt summary**

> Help define a data dictionary and ERD for the credential-management workflow. Specify entities, fields, primary keys, foreign keys, relationships, cardinalities, lifecycle states, and validation rules for issuance, verification, revocation, and audit events.

**How AI assisted**

- Helped organize the nine core entities: Learner, Course, CredentialRule, CompletionRecord, Credential, Issuer, VerificationRequest, Revocation, and AuditEvent.
- Helped plan the data dictionary and ERD documentation.
- Helped reason about parent-child dependencies and event history.

**Candidate review**

The staging database was compared with generated CSV data. The recorded validation found matching row counts, primary keys, and column values across ten database tables. JSON values were normalized during comparison.

### 3.3 Synthetic data generation

**Prompt summary**

> Help plan deterministic synthetic data generation for the credential-management entities. Generate parent records before dependent records, preserve valid references, use a fixed random seed, derive statuses and dates from source records, and meet the required dataset volumes.

**How AI assisted**

- Helped plan generation order and parent-child dependencies.
- Helped reason about deterministic IDs and fixed-seed generation.
- Helped identify that derived values should come from source records rather than independent random assignment.
- Helped plan separate ground-truth output for known anomaly fixtures.

**Candidate review**

The generated datasets were checked against the documented counts and staging database. The recorded full dataset contains 77,010 rows:

| Entity/table | Rows |
|--------------|-----:|
| Learner      | 20,000 |
| Course       | 1,000  |
| CredentialRule| 1,000 |
| CompletionRecord| 20,000 |
| Issuer       | 5 |
| IssuerKey    | 5 |
| Credential   | 10,000 |
| Revocation   | 500 |
| VerificationRequest | 5,000 |
| AuditEvent   | 15,500 |
| **Total**    | **77,010** |

The documented fixed seed is `20261022`.

### 3.4 MySQL setup and troubleshooting

**Prompt summary**

> Help troubleshoot MySQL 8 service, schema, import, and database connectivity issues. Explain the error messages and suggest safe checks without unnecessarily rebuilding a database that has already been validated.

**How AI assisted**

- Helped interpret MySQL service and connection messages.
- Helped troubleshoot database setup and import issues.
- Helped distinguish the corrected staging database from the older production-named database.

**Candidate review**

The corrected staging database was used for the recorded validation. The project was not rebuilt or re-imported after staging validation was completed.

### 3.5 Business-rule validation and anomaly evaluation

**Prompt summary**

> Help plan an evaluation process for four required anomaly scenarios: a credential issued before completion, a duplicate credential ID, a revoked credential verified as active, and an altered payload hash not detected. Keep ground-truth labels separate from input features and evaluate the rules using anomaly fixtures and normal controls.

**How AI assisted**

- Helped organize the independent rule checks and test cases.
- Helped plan separate ground-truth data.
- Helped interpret confusion-matrix values and evaluation metrics.
- Helped clarify that controlled synthetic rule-engine results must not be presented as machine-learning performance.

**Candidate review**

The candidate ran the unit tests and evaluation command. The recorded evaluation run produced:

| Metric | Result |
|---|---:|
| Total scored cases | 8 |
| Passed | 8 |
| Failed | 0 |
| True Positive (TP) | 4 |
| True Negative (TN) | 4 |
| False Positive (FP) | 0 |
| False Negative (FN) | 0 |
| Accuracy | 1.00 |
| Precision | 1.00 |
| Recall | 1.00 |
| F1 score | 1.00 |

These results apply only to four controlled anomaly fixtures and four normal controls. They do not demonstrate real-world generalization and are not the performance of a trained machine-learning model. The recorded evaluation also reported zero source data-quality findings for that run.

### 3.6 Tests and validation evidence

**Prompt summary**

> Help identify validation checks and test commands for the credential-management project, including key uniqueness, foreign-key integrity, lifecycle rules, anomaly detection, and comparison between generated CSV files and MySQL records.

**How AI assisted**

- Helped organize validation checks and test execution.
- Helped interpret test output and distinguish warnings from failures.
- Helped summarize evidence for the validation report.

**Candidate review**

The candidate executed these commands in the local project environment:

```powershell
python -m unittest tests.test_evaluation_rules -v
python -m src.data_generation.evaluate
```

The recorded database validation also reported:
- CSV-to-MySQL row counts, primary keys, and column values matched across ten tables.
- Foreign-key checks passed.
- 24 business-rule validation checks passed with zero findings.

### 3.7 README and technical documentation

**Prompt summary**

> Help organize project documentation covering setup, configuration, data generation, database use, evaluation, data dictionary, ERD, validation results, assumptions, and limitations.

**How AI assisted**

- Helped structure the README and supporting documentation.
- Helped draft explanations for the schema, data dictionary, ERD, and validation report.
- Helped make setup and execution instructions clearer.

**Candidate review**

The candidate added the documentation files to the project and checked that the expected files existed before committing the changes.

### 3.8 Git and GitHub workflow

**Prompt summary**

> Help verify Git status, check that local secrets are excluded, configure the GitHub remote, and push the committed project to the repository.

**How AI assisted**

- Explained Git status and remote configuration.
- Helped correct a malformed `git remote add` command.
- Provided commands for pushing and verifying the repository connection.

**Candidate review**

The candidate executed the Git commands. The project was successfully pushed to the `main` branch of the repository listed at the top of this document. The `.env` file was checked as ignored and was not tracked in Git.

## 4. Work personally reviewed and validated by the candidate

Based on the recorded local command outputs and validation results, the candidate performed the following activities:

1. Ran project commands in the local Python virtual environment.
2. Generated synthetic datasets using the documented fixed seed.
3. Used the corrected staging database for CSV-to-MySQL comparison.
4. Reviewed row counts, primary keys, column values, and foreign-key checks.
5. Ran the business-rule validation checks.
6. Ran the evaluation unit tests and evaluation script.
7. Reviewed the evaluation metrics and their limitations.
8. Checked that `.env` was ignored and not tracked by Git.
9. Committed the project and pushed the `main` branch to GitHub.
10. Added and checked the project documentation files.

Keep only statements that you can personally explain and demonstrate during the project review.

## 5. Assumptions and limitations

- The datasets are synthetic. They do not represent real learners or real institutional credential records.
- The evaluation uses a small controlled set of four anomaly fixtures and four normal controls. The 100% scores apply only to those eight test cases.
- The evaluation is a rule-engine test, not evidence of a trained machine-learning model's real-world accuracy.
- Hashes and signature-related metadata are simulated for this project. They should not be described as a production-grade digital-signature or key-management infrastructure.
- A graphical user interface and hosted live demo were not treated as mandatory requirements in the supplied project FAQ. The solution is demonstrated through scripts, database records, tests, and reports.
- A fixed seed is documented. Do not claim that two independent runs produced matching checksums unless that comparison has actually been executed and recorded.
- Explain any remaining limitations or deviations honestly during submission.

## 6. AI-use disclosure statement

I used ChatGPT to assist with requirement analysis, implementation planning, troubleshooting, validation planning, documentation drafting, interpretation of test results, and Git workflow guidance.

I reviewed the suggestions, ran the project in my local environment, checked the generated data and database records, executed the tests and evaluation, and documented the observed results and limitations. AI assistance was used as a support tool. I take responsibility for understanding the project, explaining its design decisions, and answering questions about its implementation and validation evidence.

## 7. Final checklist before submission

- [ ] Add any missing prompts from every AI tool used. This file is a reconstructed summary, not a complete verbatim export.
- [ ] Confirm that the GitHub repository is public.
- [ ] Confirm that no `.env` file, password, API key, or other secret is committed.
- [ ] If possible, test the documented setup and run instructions from a clean environment.
- [ ] Perform and record a two-run fixed-seed reproducibility comparison before claiming checksum reproducibility.
- [ ] Ensure the README accurately describes what works and the known limitations.
- [ ] Be ready to explain the schema, issuance rules, verification, revocation, audit events, anomaly checks, and evaluation metrics.

---

**End of AI usage disclosure and prompt-history summary.**
