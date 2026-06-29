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

## Case 6: vercel/ai-chatbot

Repository: https://github.com/vercel/ai-chatbot

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: Next.js AI chatbot starter with auth, Postgres persistence, Redis rate limits, and Vercel Blob uploads

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 76 / 100
Decision: Reasonable AI starter structure, but review upload privacy defaults and signup abuse controls before production launch.
```

### What AI Ship Review Caught Well

- The reviewed chat API route requires `session.user`, checks ownership on existing chats, and applies IP plus per-user rate limits before continuing AI work.
- The reviewed auth and DB files clearly require production secrets such as `AUTH_SECRET`, `AI_GATEWAY_API_KEY`, `BLOB_READ_WRITE_TOKEN`, `POSTGRES_URL`, and `REDIS_URL`.
- The package scripts and inspected routes suggest the starter expects migrations and Playwright coverage rather than being a zero-ops demo.

### Main Launch Risks

- `app/(chat)/api/files/upload/route.ts` uploads user-supplied files with `access: "public"`, which makes attachment privacy a product decision rather than a safe default. If this starter is adapted for sensitive uploads or private workspaces, public blob URLs are a real disclosure risk.
- The same upload route preserves a sanitized version of the original filename in the blob key. Even if the storage backend adds randomness, teams should confirm object names remain unguessable and avoid leaking user-provided names unnecessarily.
- `app/(auth)/actions.ts` allows direct credential registration with only a six-character password minimum in the reviewed path; email verification, signup throttling, and anti-abuse controls were not evident from the inspected files.

### False Positives

- The reconstructed local snapshot necessarily lacked the full repository test tree and workflow files, so `missing-tests` and `missing-ci` scanner signals were not treated as evidence about the real repository.

### Missed Or Weak Signals

- Initial scanner output did not flag request-handled upload routes that explicitly store files with public object/blob access.
- The scanner still does not reason about auth-abuse controls such as signup throttling, email verification, or disposable guest-account cleanup; that remains manual review territory.

### Scanner Improvements Made

- Added a `public-upload-access` risky-code signal for upload handlers that combine request/file handling with explicit public object storage settings such as `access: "public"` or `ACL: "public-read"`.

## Case 7: nextjs/saas-starter

Repository: https://github.com/nextjs/saas-starter

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: Next.js SaaS starter with Stripe billing, Postgres, seeded owner account, and deployment-oriented scripts

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 73 / 100
Decision: Sensible starter baseline, but do not carry the seeded owner credentials or assume production verification depth from the starter alone.
```

### What AI Ship Review Caught Well

- The reviewed webhook route verifies Stripe signatures with `stripe.webhooks.constructEvent(...)`, so the billing webhook path is not obviously accepting forged events.
- The inspected env example documents production-sensitive settings such as `POSTGRES_URL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `BASE_URL`, and `AUTH_SECRET`.
- Package scripts include explicit database setup and migration commands, which is better operational scaffolding than many lightweight starters provide.

### Main Launch Risks

- `lib/db/seed.ts` hardcodes a seeded owner account with `test@test.com` and password `admin123`. That is acceptable for local bootstrap only if teams guarantee the seed path never runs in shared or production environments and the account is removed immediately.
- No automated tests or CI/workflow files were evident in the inspected snapshot, so release confidence for auth, billing, and migrations still appears thin.
- The reviewed public files did not show rollback, incident, or production smoke-test guidance beyond basic setup commands, so operational readiness remains only partially evidenced.

### False Positives

- None from this case after the scanner change. The new seeded-credential rule stayed scoped to setup/seed-style files and did not trigger on env examples or ordinary source files.

### Missed Or Weak Signals

- Initial scanner output did not flag hardcoded default credentials embedded in seed/setup code, even when the seeded account was created with an elevated `owner` role.
- Because the evaluation used a partial snapshot, missing tests/CI signals were treated as review prompts rather than definitive claims about the full upstream repository.

### Scanner Improvements Made

- Added a `seed-default-credentials` risky-code signal for setup/seed files that combine a hardcoded email, a weak literal password, and an owner/admin role assignment.

## Case 8: vercel/nextjs-subscription-payments

Repository: https://github.com/vercel/nextjs-subscription-payments

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: Next.js subscription starter with Supabase auth, Stripe webhooks, and deployment-oriented helpers

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 74 / 100
Decision: Good billing/auth starter coverage, but review callback redirect host trust before treating it as production-safe in non-Vercel or proxy-heavy deployments.
```

### What AI Ship Review Caught Well

- The reviewed webhook route verifies Stripe events with `stripe.webhooks.constructEvent(...)`, so the payment webhook path is not obviously accepting forged requests.
- The inspected helper code already has a configured-site-URL helper (`getURL`) and the env example documents third-party auth settings, which is better operational guidance than many starters provide.
- Package scripts show explicit local Stripe forwarding and Supabase startup commands, which helps deployment/setup review.

### Main Launch Risks

- `app/auth/callback/route.ts` builds signin/account redirects from `new URL(request.url).origin`. In starter code reused behind custom proxies or untrusted host-header setups, that can create host-trust or open-redirect style risk unless the deployment strictly normalizes the incoming origin.
- The same callback route does not appear to reuse the configured site URL helper, so redirect safety depends on infrastructure behavior rather than application-level configuration.
- The reconstructed snapshot did not include the full test tree or workflow files, so CI/test coverage could not be verified from this local case alone.

### False Positives

- The new callback-origin rule stayed quiet on the general `utils/helpers.ts` site URL helper because it only fires inside auth/callback-style routes that also perform redirects.

### Missed Or Weak Signals

- Initial scanner output did not flag auth callback redirects whose base URL is derived from the incoming request origin instead of a configured canonical site URL.
- As with prior partial snapshots, `missing-tests` and `missing-ci` remained prompts for manual follow-up rather than definitive claims about the upstream repository.

### Scanner Improvements Made

- Added an `auth-callback-request-origin` risky-code signal for auth callback routes that derive redirect targets from `request.url` / request origin, prompting reviewers to verify trusted-host handling or switch to a configured site URL.

## Case 9: dubinc/dub

Repository: https://github.com/dubinc/dub

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: Next.js SaaS application with auth, billing, storage, middleware logging, and deployment-oriented local infrastructure

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 78 / 100
Decision: Stronger operational baseline than most starters, but teams should not reuse the local Docker stack unchanged because it explicitly weakens database authentication for convenience.
```

### What AI Ship Review Caught Well

- The inspected env example documents a broad set of production-sensitive integrations, including Stripe, Shopify, storage, Anthropic, Axiom, and support webhooks.
- The reviewed storage helper includes explicit SSRF-style protections before fetching arbitrary image URLs, including protocol checks, DNS resolution, and private-address blocking.
- The reconstructed snapshot included visible CI/test structure, so this case did not collapse into the common "missing tests/CI" starter pattern.

### Main Launch Risks

- `apps/web/docker-compose.yml` explicitly sets `MYSQL_ALLOW_EMPTY_PASSWORD: "yes"` while exposing MySQL on `3306` and the local PlanetScale proxy on `3900`. The file warns it is for local development only, but this is still a real launch-readiness risk if a team copies the stack into a shared preview or production-like environment.
- The same compose file exposes MailHog on `8025`, which is fine for local debugging but should never appear on an internet-facing deployment.
- `apps/web/middleware.ts` logs `transformMiddlewareRequest(req)` to Axiom. That may be perfectly acceptable, but from the inspected files alone the exact logged fields were not verifiable, so request-header/cookie/query redaction still deserves manual privacy review.

### False Positives

- The scanner flagged `https://wsrv.nl` in `apps/web/lib/storage.ts` as a generic `hardcoded-url`. Manual review showed this is a deliberate image-proxy dependency paired with SSRF fallback checks, not a launch blocker by itself.

### Missed Or Weak Signals

- Initial scanner output did not flag Docker Compose files that explicitly disable database passwords or enable trust-style local auth shortcuts.
- The scanner still does not reason about structured request logging helpers such as `transformMiddlewareRequest(req)`; that remains manual review territory because the signal-to-noise tradeoff is unclear without helper expansion.
- Because this evaluation used a partial snapshot, conclusions about the full upstream release process remain bounded by the inspected files rather than the whole repository.

### Scanner Improvements Made

- Added deployment-config signals for insecure local database auth shortcuts in compose files: `compose-empty-db-password` for MySQL and `compose-trust-db-auth` for PostgreSQL.

## Case 10: papermark/papermark

Repository: https://github.com/papermark/papermark

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: Next.js document-sharing SaaS with auth, blob storage, AI, payments, queueing, and deployment-oriented secrets

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 75 / 100
Decision: Solid SaaS surface area and some visible auth hardening, but production teams should tighten secret/bootstrap guidance and verify broader release coverage before treating the template as launch-ready.
```

### What AI Ship Review Caught Well

- The reviewed auth handler in `pages/api/auth/[...nextauth].ts` applies rate limiting before allowing sign-in, which is stronger abuse-control posture than many starter kits show.
- The inspected package scripts include explicit deploy-adjacent commands such as `prisma migrate deploy`, Stripe webhook forwarding, and Trigger.dev deployment, so the project does expose real operational surfaces rather than only local dev scripts.
- The env example documents a broad production integration set, including blob storage, email, queue/webhook signing, auth, and document-password secrets.

### Main Launch Risks

- `.env.example` uses placeholder-sensitive values such as `NEXTAUTH_SECRET=my-superstrong-secret`, `HANKO_API_KEY=add-your-hanko-api-key`, and `NEXT_PRIVATE_DOCUMENT_PASSWORD_KEY=my-superstrong-document-secret`. Those are safer than real secrets, but they are still important review prompts because teams frequently ship starters with placeholder secret material left unchanged.
- The inspected workflow evidence was thin: the reconstructed public snapshot only surfaced `.github/workflows/cla.yml`, and `package.json` did not expose a test script. That does not prove the full upstream repo lacks meaningful CI or tests, but it does mean launch confidence cannot be inferred from the inspected files alone.
- Because this was a partial snapshot, higher-risk paths such as upload privacy, signed document access, webhook verification, and tenant isolation could not be fully verified from the reviewed files alone.

### False Positives

- None from this case after the scanner change. The new placeholder-secret heuristic stayed scoped to secret-like env variable names and did not flag ordinary example values such as `NEXT_PUBLIC_SITE_URL=https://example.com`.

### Missed Or Weak Signals

- Initial scanner output only reported `missing-tests` for the Papermark snapshot and completely missed placeholder secret values in `.env.example`.
- The previous weak-env heuristic only caught obvious literals like `secret` or `supersecretpassword`, leaving more realistic starter placeholders such as `my-superstrong-secret` and `add-your-hanko-api-key` invisible.

### Scanner Improvements Made

- Expanded env-template placeholder detection so secret-like variable names are flagged when they use obvious placeholder values such as `my-...-secret`, `add-your-...-api-key`, and similar setup text, while still ignoring non-sensitive example values.

## Case 11: wasp-lang/open-saas (AI/upload follow-up)

Repository: https://github.com/wasp-lang/open-saas

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: AI-enabled SaaS starter with authenticated AI operations, signed S3 upload/download helpers, and starter payment wiring

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 72 / 100
Decision: The inspected AI and file flows show reasonable starter auth checks, but the download-signing path still needs ownership enforcement and the snapshot remains too partial for a broad production-ready claim.
```

### What AI Ship Review Caught Well

- `template/app/src/file-upload/operations.ts` still exposes a real `signed-download-no-auth` concern: `getDownloadFileSignedURL` signs an S3 object from raw `s3Key` input without an evident `context.user` or ownership check.
- The same file shows stronger patterns on adjacent flows: upload URL creation, file listing, and delete operations all check `context.user`, which makes the unauthenticated download signer stand out as a real asymmetry instead of generic scanner noise.
- `template/app/src/demo-ai-app/operations.ts` authenticates the AI operation before calling OpenAI and decrements credits inside a transaction, which is better operational discipline than many AI starter demos.

### Main Launch Risks

- The inspected signed-download operation remains the main launch-readiness risk in this snapshot because possession of an `s3Key` appears sufficient to mint a download URL.
- `template/app/.env.server.example` still includes placeholder-sensitive values such as `LEMONSQUEEZY_WEBHOOK_SECRET=my-webhook-secret`, which is safe as an example but risky if downstream teams deploy without replacing it.
- The snapshot still lacks visible CI/test evidence, so conclusions remain bounded to the inspected starter files rather than a verified full release process.

### False Positives

- The scanner previously emitted two `openai-sdk-usage` findings from `template/app/src/demo-ai-app/operations.ts`: one for `import OpenAI` and another for `new OpenAI(...)`. Manual review showed those lines represent one underlying review prompt, so the duplicate was noise rather than extra risk.

### Missed Or Weak Signals

- This follow-up did not reveal a stronger new blocker than the existing signed-download finding, but it did show that file-level AI SDK presence should be reported once per file instead of once per matching line.

### Scanner Improvements Made

- Deduplicated `openai-sdk-usage` to one file-level hit per source file so AI review prompts stay visible without repeated noise from import-plus-constructor patterns.

## Case 12: wasp-lang/open-saas (file ownership follow-up)

Repository: https://github.com/wasp-lang/open-saas

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: Wasp SaaS template with auth, payments, AI demo, S3 uploads, and deployment tooling

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 66 / 100
Decision: The upload flow still should not ship unchanged because file metadata can be claimed with any existing object key, and the signed-download path remains under-protected.
```

### What AI Ship Review Caught Well

- `template/app/src/file-upload/s3Utils.ts` namespaces upload keys under `${userId}/...`, which made the intended ownership model explicit enough to verify manually.
- The scanner still surfaced `getDownloadFileSignedURL` as a missing-auth review point and continued to flag the weak webhook placeholder in `.env.server.example`.
- The snapshot still exposes no visible CI or automated tests, so the skill correctly keeps the confidence level below production-ready.

### Main Launch Risks

- `template/app/src/file-upload/operations.ts` lets an authenticated caller submit any `s3Key`, performs only `checkFileExistsInS3({ s3Key: args.s3Key })`, and then stores that key under `context.user.id` via `context.entities.File.create(...)`. If another valid object key is discovered, a user can claim metadata for someone else's uploaded file.
- `template/app/src/file-upload/operations.ts` also still returns signed download URLs directly from caller-supplied `s3Key` values without evident ownership enforcement.
- The partial snapshot still does not show tests or operator guidance that would reduce confidence risks around upload abuse, cleanup, and incident response.

### False Positives

- None from this follow-up. The new ownership signal stayed narrow in regression coverage and did not fire on a safe variant that verifies `args.s3Key.startsWith(\`${context.user.id}/\`)` before persisting the file record.

### Missed Or Weak Signals

- Before this run, the scanner noticed unauthenticated signed downloads but not the adjacent file-claim path that persists user-supplied storage keys after only an existence check.
- The scanner still does not reason about whether upload object names are unguessable enough in templates that expose them back to the client.

### Scanner Improvements Made

- Added `file-key-claim-no-ownership` for file metadata operations that attach a caller-supplied storage key to the current user after only an existence check and without visible ownership or prefix validation.

## Case 13: midday-ai/midday (env template follow-up)

Repository: https://github.com/midday-ai/midday

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: AI-enabled finance/SaaS platform with assistant tooling, webhook integrations, and broad third-party secret surface area

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 74 / 100
Decision: The inspected assistant wiring looks reasonably scoped, but the checked-in env templates still normalize weak copy-paste secret defaults that production teams should replace before deployment.
```

### What AI Ship Review Caught Well

- `apps/api/src/bot/runtime.ts` builds the assistant MCP context from a connected conversation's team and user identifiers, and `apps/api/src/chat/assistant-runtime.ts` keeps the model/tool loop server-side rather than exposing raw tool execution to the client.
- The scanner already caught several weak env-template placeholders in the snapshot, including `INVOICE_JWT_SECRET=secret` and `FILE_KEY_SECRET=secret`.
- The partial snapshot made the confidence boundary explicit: missing CI/tests in the local snapshot are treated as a limitation of the evaluation method, not proof that the repository lacks them globally.

### Main Launch Risks

- `apps/dashboard/.env-example` includes `WEBHOOK_SECRET_KEY=6c369443-1a88-444e-b459-7e662c1fff9e`, a fixed UUID-shaped secret value that looks plausible enough to be copied unchanged into real deployments. That is safer than a real leaked secret, but still weak bootstrap guidance for webhook auth.
- The inspected env templates also include multiple other placeholder-sensitive values such as `INVOICE_JWT_SECRET=secret`, `FILE_KEY_SECRET=secret`, and `STRIPE_CONNECT_WEBHOOK_SECRET=your_webhook_secret_here`, so operators still need stronger replace-before-run discipline.
- This snapshot was too narrow to verify rate limits, webhook verification paths, or broader deployment/rollback coverage across the full repository.

### False Positives

- The scanner's `hardcoded-url` hit on `apps/api/src/bot/runtime.ts` for the fallback `https://api.midday.ai` is review noise in this case; it is a normal canonical API base URL default rather than an operational secret or launch blocker.

### Missed Or Weak Signals

- Before this run, env-template scanning did not flag UUID-shaped fixed values assigned to sensitive names such as `WEBHOOK_SECRET_KEY`, even though those values are easy to ship unchanged by mistake.

### Scanner Improvements Made

- Expanded `weak-env-placeholder` detection so sensitive env vars using fixed UUID values in checked-in templates are flagged alongside simpler placeholders like `secret` and `your_webhook_secret_here`.

## Case 14: papermark/papermark (auth abuse-control follow-up)

Repository: https://github.com/papermark/papermark

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: Next.js document-sharing SaaS with NextAuth, rate limiting, blob storage, AI, and payment/deployment integrations

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 73 / 100
Decision: Reasonable starter posture, but the inspected auth flow should fail closed when abuse-protection checks break.
```

### What AI Ship Review Caught Well

- `pages/api/auth/[...nextauth].ts` clearly applies a sign-in rate limit through `checkRateLimit(rateLimiters.auth, clientIP)`, so the project does show real abuse-control intent rather than omitting the check entirely.
- The snapshot still documents sensitive production configuration in `.env.example`, including auth and document-password secrets, which remains useful operational context.
- The partial-snapshot review kept its confidence boundary explicit: missing tests were treated as a visible risk in the inspected files, not a claim about the entire upstream repository.

### Main Launch Risks

- `pages/api/auth/[...nextauth].ts` wraps the sign-in rate-limit call in `try { ... } catch (error) {}` and then falls through to `return !!user.email;`. If the rate-limit backend throws or becomes unavailable, login appears to fail open instead of denying or degrading safely.
- The same file therefore converts an abuse-protection outage into silently weaker auth hardening, which is especially relevant on public sign-in routes that are likely to attract credential-stuffing or signup abuse.
- The reviewed snapshot still did not expose broader auth verification coverage, so this finding should be read as a concrete inspected risk rather than a complete auth audit.

### False Positives

- None from this follow-up. The new rule stayed narrow by requiring a sign-in callback, a rate-limit/security check, an empty catch block, and an allow-style return.

### Missed Or Weak Signals

- Before this run, the scanner did not detect fail-open auth flows where a sign-in callback swallows rate-limit/security errors and then still allows the user path to proceed.

### Scanner Improvements Made

- Added `auth-rate-limit-fail-open` for sign-in/auth callback code that combines a rate-limit check, an empty catch block, and a subsequent allow-style return such as `return true` or `return !!user.email`.

## Case 15: vercel/ai-chatbot (guest account abuse-control follow-up)

Repository: https://github.com/vercel/ai-chatbot

Local test method: partial local snapshot reconstructed from inspected public files because network-restricted shell access prevented cloning.

Type: Next.js AI chatbot starter with guest auth, Postgres persistence, Redis-backed chat throttling, and public blob uploads

### Ship Decision

```text
Ship Readiness: Ready with caution
Score: 72 / 100
Decision: The inspected chat path is reasonably guarded, but anonymous account creation should not ship broadly without abuse controls on the guest login path.
```

### What AI Ship Review Caught Well

- `app/(chat)/api/chat/route.ts` requires `session.user`, rate-limits by IP via `checkIpRateLimit(ipAddress(request))`, and enforces a per-user message cap before continuing the chat flow.
- `app/(chat)/api/files/upload/route.ts` still surfaces the earlier `public-upload-access` review prompt, which remains relevant for teams adapting the starter to sensitive file uploads.
- `.env.example` uses masked placeholders (`****`) rather than teaching copy-pasteable weak secrets, which is better bootstrap hygiene than many starter templates.

### Main Launch Risks

- `app/(auth)/auth.ts` defines a `Credentials({ id: "guest", ... })` provider whose `authorize()` body calls `createGuestUser()` directly and returns a fresh account without any visible rate limit, CAPTCHA, proof-of-work, or similar abuse control in the inspected path.
- `lib/db/queries.ts` implements `createGuestUser()` by inserting a new user record with an email derived from `Date.now()`, so repeated anonymous auth hits can create durable database rows rather than ephemeral session-only guests.
- `app/(auth)/actions.ts` also allows direct credential registration with only a six-character password minimum, and the inspected snapshot still did not show email verification or signup throttling. That makes the missing guest-path abuse control more important, not less.

### False Positives

- `missing-tests` and `missing-ci` remained snapshot-bound noise for this local reconstruction because `package.json` advertises a Playwright test command even though the corresponding files were not present in the partial snapshot.

### Missed Or Weak Signals

- Before this run, the scanner did not flag guest or anonymous auth providers that create persisted user accounts without visible abuse controls.
- The scanner still does not reason about lifecycle cleanup for guest users after creation; that remains manual review territory.

### Scanner Improvements Made

- Added `guest-auth-no-rate-limit` for guest-account auth providers that create users in `authorize()` without visible rate limiting or throttling nearby.
