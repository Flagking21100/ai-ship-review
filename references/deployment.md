# Deployment And Operations Checks

Use this reference when reviewing production readiness.

## Build and runtime

Check for:

- Documented install, build, test, and start commands.
- Production build succeeds from a clean checkout.
- Runtime version is pinned or documented.
- Required services are listed: database, cache, object storage, queue, email, AI provider, payment provider.
- Static/client builds do not include server secrets.

## Environment

Check for:

- `.env.example` has all required variables.
- Variables are grouped by required/optional and development/production.
- Dangerous dev defaults are disabled in production.
- Missing critical variables fail during startup or build.

## Database and migrations

Check for:

- Migration command is documented.
- Migration order is clear.
- Rollback or backup guidance exists for risky schema changes.
- Seed scripts cannot be accidentally run against production.

## Observability

Check for:

- Errors are logged with enough context to debug.
- Logs avoid secrets and personal data.
- Health check or smoke test exists.
- External service failures are visible.
- Background jobs have retry/dead-letter behavior when relevant.

## Rollback

Check for:

- Previous release can be restored.
- Database changes do not make rollback impossible without a plan.
- Feature flags or kill switches exist for high-risk launches.
- Release notes mention known limitations.
