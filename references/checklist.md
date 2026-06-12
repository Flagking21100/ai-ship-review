# Launch Readiness Checklist

Use this scoring model as a guide. Adjust for application type and user impact.

## Scoring

Start at 100 and subtract:

- P0 blocker: -25 each
- P1 high risk: -10 each
- P2 medium risk: -4 each
- P3 low risk: -1 each

Decision thresholds:

- 85-100: Ready or ready with caution
- 65-84: Ready with caution, unless any P0 exists
- 0-64: Not ready
- Any P0: Not ready

## Core Areas

### Repository basics

- README explains what the app does, how to run it, and how to deploy it.
- License is present for open source projects.
- Build, test, and lint commands are documented.
- Dependency manager and lockfile are consistent.
- Generated files, secrets, local databases, and build outputs are ignored.

### Configuration

- `.env.example` exists with safe placeholders.
- Required environment variables are documented.
- Development and production settings are separated.
- Default settings are not dangerous in production.
- Missing env vars fail loudly for critical services.

### Critical workflows

- Main user journey works from a clean checkout.
- Error, loading, and empty states exist for core flows.
- Destructive actions require confirmation or safeguards.
- External service failure does not corrupt state.

### Data

- Schema migrations are tracked.
- Rollback or recovery path exists for risky migrations.
- User data deletion/export requirements are considered when relevant.
- Logs avoid secrets, tokens, passwords, payment data, and personal data.

### Testing

- Critical paths have tests or manual verification steps.
- Auth, payments, data writes, and destructive actions receive extra scrutiny.
- Smoke test instructions exist for production deploys.

### Operations

- Production build command works.
- Deploy target is documented.
- Health check or smoke test exists.
- Rollback path is documented.
- Basic monitoring/logging exists for production failures.
