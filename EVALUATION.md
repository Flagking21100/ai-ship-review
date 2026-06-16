# Evaluation Notes

This document tracks real-world testing of AI Ship Review. Use it to identify what the skill catches well, where it needs manual judgment, and what should become scanner automation.

## Evaluation Method

For each repository:

1. Run `scripts/scan_repo.py`.
2. Read README, package/build files, environment examples, deployment files, auth/payment/data code, and generated scanner signals.
3. Produce a ship decision using the `SKILL.md` severity model.
4. Record useful findings, false positives, missed opportunities, and scanner improvements.

## Case 1: nhost/nextjs-stripe-starter

Repository: https://github.com/nhost/nextjs-stripe-starter

Local test commit: `686d3d7`

Type: Next.js + Nhost + Stripe SaaS starter

### Ship Decision

```text
Ship Readiness: Not ready
Score: 54 / 100
Decision: Do not ship yet.
```

### What AI Ship Review Caught Well

- Missing effective Stripe customer authorization in `functions/graphql/stripe.ts`.
- Request body/query/header logging in a payment-adjacent function.
- Broad CORS on an authenticated checkout endpoint.
- Hardcoded demo/production URLs in frontend and checkout flows.
- No tests or CI signals.
- Webhook signature verification was present, so this should not be reported as a blocker.

### False Positives

- The scanner flagged generated GraphQL files as secret-like. Manual review showed these were likely type/schema strings, not committed credentials.

### Missed Or Weak Signals

- The scanner did not automatically detect authorization placeholders such as `TODO` plus `return true`.
- The scanner did not detect hardcoded service URLs.
- The scanner did not detect `console.log(req.headers)` in payment-adjacent functions.
- The scanner did not classify broad CORS differently when found inside authenticated or payment-related endpoints.

### Scanner Improvements Suggested

- Detect `TODO`/`FIXME` near authorization words and unconditional `return true`.
- Detect hardcoded URLs outside documentation and config.
- Detect logging of `req.headers`, `authorization`, cookies, request bodies, and query params.
- Detect `Access-Control-Allow-Origin: *` in server/API/function files.
- Suppress generated files such as `__generated__` by default for secret-like scans.

## Case 2: bibektimilsina000/FastAPI-PgStarterKit

Repository: https://github.com/bibektimilsina000/FastAPI-PgStarterKit

Type: FastAPI + PostgreSQL + Docker starter

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 74 / 100
Decision: Do not use as-is for production; acceptable as a local/dev starter after hardening.
```

### What AI Ship Review Caught Well

- Docker and PostgreSQL setup are present.
- Alembic migrations are present.
- Tests are present across API, CRUD, settings, and utilities.
- `.env` is excluded from git and README explicitly warns not to commit it.

### Main Launch Risks

- Weak default values in `dot-env-template`, including `ACCESS_TOKEN_SECRET=secret`, `FIRST_SUPERUSER_PASSWORD=supersecretpassword`, `POSTGRES_PASSWORD=supersecretpassword`, and `PGADMIN_DEFAULT_PASSWORD=supersecretpassword`.
- The local Docker command runs Uvicorn with `--reload`, which is appropriate for development but should not be copied into production.
- PostgreSQL and pgAdmin ports are exposed in `docker-compose.yml`, which is fine for local development but risky if reused on an internet-facing host.
- README is lively but not operationally precise; it lacks production hardening, backup, migration, and rollback guidance.

### False Positives

- Hardcoded documentation URLs in comments are not launch risks. Hardcoded URL detection needs better classification.

### Missed Or Weak Signals

- Initial scanner did not detect Python `os.getenv(...)` environment variable usage.
- Initial scanner did not recognize `dot-env-template` as an env example file.
- Initial scanner did not flag weak placeholder secrets/passwords in env templates.

### Scanner Improvements Suggested

- Detect Python `os.getenv(...)` environment reads.
- Treat `dot-env-template` and similar files as env examples.
- Flag weak placeholder secrets/passwords in env templates.
- Detect dev-server commands such as `uvicorn --reload`, `next dev`, or `flask --debug` when they appear in deployment-like files.
- Detect public database/admin ports in Docker Compose and classify them as deployment hardening signals.

## Case 3: Superexpert/openai-assistant-starter-kit

Repository: https://github.com/Superexpert/openai-assistant-starter-kit

Type: Next.js + OpenAI Assistant starter

### Ship Decision

```text
Ship Readiness: Not ready
Score: 61 / 100
Decision: Fine as a learning starter; not ready for public production use without auth and abuse controls.
```

### What AI Ship Review Caught Well

- No tests or CI signals.
- No env example file, even though README requires `OPENAI_API_KEY`.
- OpenAI API route is publicly callable and creates/continues Assistant threads.
- Client sends `assistantId`, `threadId`, and prompt content to the API route.

### Main Launch Risks

- The API route calls OpenAI without authentication, authorization, user ownership checks, or rate limiting.
- The client controls `assistantId` and `threadId`; a production app should not let arbitrary users select or continue unintended AI resources without server-side validation.
- The route depends on OpenAI SDK implicit `OPENAI_API_KEY` behavior, so simple environment scanning initially missed the required secret.
- README instructs users to put `OPENAI_API_KEY` into a shell profile, but there is no `.env.example` or deployment-specific secret guidance.

### False Positives

- Hardcoded URL detection flagged source links and documentation links. These are low-risk and should be classified separately from service endpoint URLs.

### Missed Or Weak Signals

- Initial scanner did not infer `OPENAI_API_KEY` from `new OpenAI()`.
- Initial scanner did not identify client-controlled AI resource IDs.
- The skill needs sharper AI-specific guidance: rate limits, prompt/user-content logging, tenant isolation, API cost controls, and abuse prevention.

### Scanner Improvements Suggested

- Infer `OPENAI_API_KEY` when the OpenAI SDK is imported or instantiated.
- Flag OpenAI SDK usage as a review hotspot.
- Flag client-controlled `assistantId`, `threadId`, or `model` fields.
- Add AI endpoint checks for auth, rate limiting, request size limits, and logging of prompts/responses.

## Current Scanner Boundary Notes

- Hardcoded URL detection is useful for service endpoints and production redirect URLs, but still needs better classification for reserved claim URLs such as `https://hasura.io/jwt/claims`.
- Scanner output should remain framed as signals, not verdicts. The skill must still inspect code manually before assigning severity.
- Good next step: group signals into categories such as `security`, `configuration`, `ai-abuse`, `deployment`, and `noise-likely`.

## Boundary Case: tomphill/nextjs-openai-starter

Repository: https://github.com/tomphill/nextjs-openai-starter

Type: Minimal Next.js starter

### Observation

The repository name and README imply OpenAI/GPT, but the scanned code mostly contains a basic Next.js/MongoDB setup. This is a useful boundary case: AI Ship Review must not infer AI risks from repository names alone. It should inspect code paths and say when expected AI functionality is not present.

## Case 4: vercel/nextjs-subscription-payments

Repository: https://github.com/vercel/nextjs-subscription-payments

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: Next.js + Supabase + Stripe subscription starter

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 72 / 100
Decision: Reasonable starter structure, but not strong enough to treat as production-ready without adding test and operational guardrails.
```

### What AI Ship Review Caught Well

- Webhook signature verification is implemented in `app/api/webhooks/route.ts` via `stripe.webhooks.constructEvent(...)`.
- The reviewed files clearly require privileged and payment-related secrets such as `SUPABASE_SERVICE_ROLE_KEY` and `STRIPE_WEBHOOK_SECRET`.
- The starter separates middleware, admin Supabase access, and Stripe webhook handling in understandable server-side files.

### Main Launch Risks

- No automated tests were evident in the inspected repository paths, which is thin coverage for auth, billing, and webhook behavior.
- No CI or deployment workflow files were evident in the inspected repository paths, so build and smoke-check confidence appears manual.
- The starter relies on privileged Supabase admin access and payment webhooks, but the reviewed docs/files did not show rollback, incident, or operator-focused release guidance.

### False Positives

- `.env.local.example` contains a long demo `NEXT_PUBLIC_SUPABASE_ANON_KEY` value. This looks secret-like but is expected starter configuration, so secret scanning should remain cautious around env examples and public anon keys.

### Missed Or Weak Signals

- The scanner only listed empty `tests` and `ci` inventories; it did not elevate those absences into explicit launch-readiness signals.
- The scanner still does not distinguish "public/demo config present" from "sensitive secret committed" in env examples, so manual judgment remains necessary.

### Scanner Improvements Made

- Added repository-level signals for `missing-tests` and `missing-ci`, so obvious launch-readiness gaps surface directly in scanner output instead of being buried in file inventories.

## Case 5: wasp-lang/open-saas

Repository: https://github.com/wasp-lang/open-saas

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: Wasp SaaS template with auth, payments, AI demo, S3 uploads, and deployment tooling

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 69 / 100
Decision: Strong starter breadth, but not safe to ship unchanged because the file download path appears to miss server-side authorization.
```

### What AI Ship Review Caught Well

- The template clearly documents privileged production configuration in `.env.server.example`, including payment, OpenAI, analytics, and S3 variables.
- Auth checks are present in the reviewed payment and upload-creation operations such as `generateCheckoutSession`, `getCustomerPortalUrl`, `createFileUploadUrl`, `addFileToDb`, `getAllFilesByUser`, and `deleteFile`.
- The AI demo operation charges credits for non-subscribed users and requires `context.user`, so the reviewed path is not an obvious anonymous cost-exposure bug.

### Main Launch Risks

- `template/app/src/file-upload/operations.ts` exports `getDownloadFileSignedURL` as a query that accepts raw `s3Key` input and returns a signed S3 download URL without checking `context.user` or file ownership.
- `template/app/main.wasp` wires `getDownloadFileSignedURL` as a query, so this looks externally callable rather than a private helper.
- The reviewed snapshot did not include the underlying payment processor webhook implementation, so webhook-signature handling could not be verified from the inspected files alone.

### False Positives

- The previous scanner heuristic flagged helper-level `return true` patterns in storage code such as `checkFileExistsInS3`. In this case that was noise, not an auth bypass.

### Missed Or Weak Signals

- Initial scanner output did not flag signed download URL operations that lack evident auth or ownership checks.
- Initial scanner output surfaced a noisy `unconditional-allow` hit from a non-auth helper, which diluted review attention in upload-heavy code.
- Because the evaluation used a partial snapshot, scanner output about missing CI/tests was not treated as evidence about the real repository.

### Scanner Improvements Made

- Added a `signed-download-no-auth` risky-code signal for request-facing download/presign operations that generate object-storage access without evident auth or ownership checks.
- Reduced `unconditional-allow` noise by requiring nearby auth/permission context before flagging `return true`.
