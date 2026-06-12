# AI Ship Review

AI Ship Review is a Codex skill for answering the question every fast-built app eventually faces:

> Is this actually ready to ship?

It reviews AI-built, vibe-coded, and rapidly prototyped applications for launch blockers across security, configuration, data, auth, payments, deployment, testing, and operations.

## What it does

- Finds release blockers before users do.
- Produces a clear ship decision: `Ready`, `Ready with caution`, or `Not ready`.
- Scores launch readiness from 0 to 100.
- Prioritizes P0/P1 risks with evidence and fixes.
- Generates practical shipping artifacts such as `SHIP_CHECKLIST.md`, `RISK_REGISTER.md`, `DEPLOYMENT.md`, and `.env.example`.
- Includes a lightweight repository scanner for launch-readiness signals.

## Why this exists

AI coding tools make it easier than ever to build an app quickly. They do not automatically make the app safe to deploy, easy to operate, or ready for real users.

This skill focuses on the gap between "it runs locally" and "we can responsibly ship it."

## Install

Clone or copy this folder into your Codex skills directory:

```text
~/.codex/skills/ai-ship-review
```

On Windows, the usual location is:

```text
C:\Users\<you>\.codex\skills\ai-ship-review
```

Example:

```bash
git clone https://github.com/Flagking21100/ai-ship-review ~/.codex/skills/ai-ship-review
```

Then ask Codex:

```text
Use ai-ship-review to review this repository for launch readiness.
```

## Example output

```markdown
## Ship Readiness: Not ready

Score: 58 / 100
Decision: Do not ship yet.

### P0 Blockers
- [P0] Payment webhook accepts unsigned events
  Evidence: `src/api/stripe/webhook.ts` parses events without signature verification.
  Risk: Attackers can forge subscription updates.
  Fix: Verify the provider signature using the raw request body and webhook secret.

### Before launch
- Verify webhook signatures.
- Add `.env.example` with safe placeholders.
- Add production smoke test instructions.
- Document rollback.
```

## Real case study

I tested AI Ship Review on [`nhost/nextjs-stripe-starter`](https://github.com/nhost/nextjs-stripe-starter), a public Next.js + Nhost + Stripe SaaS starter.

The project looks complete at first glance: it has auth, Stripe Checkout, Stripe webhooks, Nhost metadata, migrations, and deployment notes. AI Ship Review still found several launch-readiness risks that are easy to miss in a normal code skim.

```text
Ship Readiness: Not ready
Score: 54 / 100
Decision: Do not ship yet.
```

Key findings:

- `P0` Stripe customer access control was not implemented. The Stripe GraphQL function contained a TODO to ensure users can only access their own Stripe customer, but the authorization check returned `true`.
- `P1` The checkout function logged request body, query, and headers, which can leak tokens or sensitive payment/session data into production logs.
- `P1` The payment function used broad CORS with `Access-Control-Allow-Origin: *`.
- `P1` Demo/production URLs were hardcoded in checkout and frontend pricing flows.
- `P2` The repository had no tests or CI signals.

Positive finding:

- Stripe webhook signature verification was implemented with `stripe.webhooks.constructEvent(...)`.

This is the kind of gap AI Ship Review is designed to catch: not "does the demo run locally?", but "what would make this risky to put in front of real users?"

## Scanner

The included scanner is intentionally lightweight. It inventories useful signals; it does not replace manual review.

```bash
python scripts/scan_repo.py /path/to/repo
python scripts/scan_repo.py /path/to/repo --json
```

It checks for:

- Environment variables referenced in code
- `.env` and `.env.example` files
- README and shipping docs
- CI/deployment files
- Test files
- Package scripts
- Secret-like patterns that need manual inspection
- Risky code signals such as auth TODOs, unconditional allows, broad CORS, sensitive request logging, hardcoded service URLs, OpenAI SDK usage, and client-controlled AI resource IDs
- Weak default secrets/passwords in env template files

## Best use cases

- Reviewing a project before first launch
- Auditing a vibe-coded app before sharing it publicly
- Preparing an open source project for GitHub
- Creating deployment and launch checklists
- Finding the highest-risk gaps in an AI-generated codebase

## Not a replacement for

- A full security audit
- Legal/compliance review
- Load testing
- Production incident response planning

It is designed to catch the most common, expensive mistakes early.

## Repository structure

```text
ai-ship-review/
  SKILL.md
  agents/openai.yaml
  references/
    checklist.md
    security.md
    auth-payments.md
    deployment.md
  scripts/
    scan_repo.py
```

## Contributing

Good contributions add concrete, reviewable launch checks. Prefer specific risks, evidence patterns, and fixes over generic advice.

Useful additions:

- Framework-specific checks for Next.js, Django, Rails, Laravel, FastAPI, Supabase, Firebase, Vercel, or Cloudflare.
- Payment provider checks for Stripe, Lemon Squeezy, Paddle, or Polar.
- More scanner signals with low false-positive rates.

## License

MIT
