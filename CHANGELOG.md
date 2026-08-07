# Changelog

All notable changes to the **Climate Digital Twin** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-08-07

### Added
- Automated dataset download and synthetic data generator script (`scripts/download_data.py`, `make download-data`).
- Integrated secret scanning via Gitleaks and `detect-secrets` into GitHub Actions CI workflow.
- Added comprehensive Open Source governance files: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md`.
- Added real Codecov coverage XML reporting and README coverage badge integration.

### Changed
- Refactored internal slang (`bhai`) modules to canonical production names: `twin_config.py` and `twin_state_manager.py`.
- Reorganized Streamlit dashboard page numbering (`08_knowledge_base`, `09_spatial_grid`, `10_feedback`).
- Hardened security by replacing real CDS API key UUIDs with standard placeholders (`your-cds-api-key`).

### Removed
- Untracked raw datasets (NetCDF `.nc`, Parquet `.parquet`, CSV) and binary vector indexes (`metadata.pkl`) from Git index.
- Removed legacy test exclusion filters (`-k "not ..."`) from CI workflow.

### Fixed
- Fixed 202+ Ruff linter errors across all packages and test suites.
- Fixed 100% of unit and integration test suite failures.
- Fixed Docker Compose syntax and version warnings.
