# Security Review Checks

Use these checks to find launch blockers and high-risk issues. Verify by reading code, not by keyword matches alone.

## Secrets

P0 if real secrets are committed or exposed to the client.

Check for:

- `.env`, `.env.local`, private keys, service account JSON, database dumps.
- Hardcoded tokens in source, tests, docs, examples, or CI files.
- Server-only secrets referenced from browser/client bundles.
- Public environment variable prefixes used for private values.

## Injection

P0/P1 depending on reachability and data impact.

Check for:

- Shell commands built from user input.
- SQL built through string concatenation.
- Template injection, unsafe eval, dynamic imports from user input.
- Unsafe file paths, archive extraction, or upload filenames.

## Web/API controls

Check for:

- Missing auth on privileged routes.
- Missing authorization checks after authentication.
- Overly broad CORS.
- Missing CSRF protection on cookie-based state-changing requests.
- No rate limiting on login, signup, password reset, scraping, upload, or expensive AI endpoints.
- Unbounded request body size.

## File uploads

Check for:

- File type validation based only on extension.
- Public serving of uploaded files without scanning or content controls.
- Path traversal.
- No size limit.
- Uploads that can overwrite existing files.

## AI-specific risks

Check for:

- User prompts or documents logged with sensitive content.
- Tool calls that can access filesystem, shell, network, or private APIs without boundaries.
- Prompt-controlled URLs or commands.
- Missing tenant/user isolation in retrieval or memory systems.
- Provider API keys exposed to the frontend.

## Dependency and supply chain

Check for:

- Install scripts or postinstall behavior from untrusted packages.
- Unpinned deployment images for production-critical systems.
- CI workflows that run untrusted PR code with secrets.
- Package manager lockfile missing or inconsistent.
