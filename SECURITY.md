# Security Policy

## Supported Versions

We actively issue security updates and patches for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of **Climate Digital Twin** seriously. If you discover a security vulnerability or potential credential exposure, please do **NOT** open a public GitHub issue.

Instead, please report it via one of the following channels:
- **Email**: Send details to `security@climatedigitaltwin.org` or notify repository maintainers privately.
- **GitHub Security Advisory**: Submit a private vulnerability report under the repository's **Security** tab.

### Report Information
Please include:
1. Description of the vulnerability and potential impact.
2. Steps to reproduce or proof-of-concept code.
3. Affected modules or endpoints.

We will acknowledge receipt within 48 hours and provide estimated patch timelines.

## Secret Scanning & Hardening

This repository integrates automated secret scanning using **Gitleaks** and **detect-secrets** in CI workflows. Real API keys, tokens, or private credentials must never be committed.
