# Security Policy

## Reporting a vulnerability

Do not open public issues for security-sensitive reports.

Until a dedicated private intake channel is published, report vulnerabilities directly to the project maintainer through a private channel and include:

- affected area
- reproduction steps
- impact assessment
- any suggested mitigation

## Response expectations

This project is currently an MVP. Best-effort triage and remediation will be provided, but no formal SLA is promised yet.

## Security notes for deployers

- Local development defaults are intentionally convenience-oriented and are not production-safe defaults.
- The development demo account is seeded only in development mode.
- Real deployments should use production env files, a private database location, and explicit account provisioning.
