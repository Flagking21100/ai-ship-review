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

Copy this folder into your Codex skills directory:

```text
~/.codex/skills/ai-ship-review
```

On Windows, the usual location is:

```text
C:\Users\<you>\.codex\skills\ai-ship-review
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
