#!/usr/bin/env python3
"""Lightweight repository inventory for AI Ship Review.

This script intentionally reports signals, not verdicts. Use it to find files and
patterns worth inspecting during a launch-readiness review.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".next",
    ".nuxt",
    "dist",
    "build",
    "coverage",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "__generated__",
}

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{30,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"\n]{12,}['\"]"),
]

ENV_READ_PATTERNS = [
    re.compile(r"process\.env\.([A-Z0-9_]+)"),
    re.compile(r"os\.environ(?:\.get)?\(['\"]([A-Z0-9_]+)['\"]\)"),
    re.compile(r"os\.getenv\(['\"]([A-Z0-9_]+)['\"]"),
    re.compile(r"import\.meta\.env\.([A-Z0-9_]+)"),
    re.compile(r"Deno\.env\.get\(['\"]([A-Z0-9_]+)['\"]\)"),
]

CODE_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".py",
    ".go",
    ".rs",
    ".rb",
    ".php",
}

RISKY_CODE_PATTERNS = [
    (
        "auth-placeholder",
        re.compile(r"(?i)(todo|fixme).{0,80}(auth|authori[sz]ation|permission|access|own customer)"),
        "Authorization-related TODO/FIXME needs manual review.",
    ),
    (
        "unconditional-allow",
        re.compile(r"\breturn\s+true\s*;?"),
        "Unconditional allow pattern; inspect if this is inside an auth/permission check.",
    ),
    (
        "request-sensitive-logging",
        re.compile(r"console\.log\(\s*(req\.(headers|body|query)|.*authorization|.*cookie)", re.IGNORECASE),
        "Request headers/body/query logging can expose tokens or sensitive data.",
    ),
    (
        "wide-cors",
        re.compile(r"Access-Control-Allow-Origin['\"]?\s*,\s*['\"]\*['\"]"),
        "Wildcard CORS found in server code.",
    ),
    (
        "hardcoded-url",
        re.compile(r"https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}[^\s'\"`)]*"),
        "Hardcoded external URL found outside docs/config.",
    ),
    (
        "openai-sdk-usage",
        re.compile(r"\b(import\s+OpenAI\s+from\s+['\"]openai['\"]|from\s+['\"]openai['\"]|new\s+OpenAI\s*\()"),
        "OpenAI SDK usage found; verify API key handling, auth, rate limits, logging, and tenant boundaries.",
    ),
    (
        "client-controlled-ai-id",
        re.compile(r"((assistantId|model|threadId)\s*:\s*(newMessage|req\.body|body|requestBody|params|data)\.|assistant_id\s*:\s*(newMessage|req\.body|body|requestBody|params|data)\.)"),
        "Client-controlled AI identifier found; verify users cannot access or run unintended AI resources.",
    ),
]

AUTH_CONTEXT_PATTERN = re.compile(
    r"(?i)(auth|authori[sz]ation|permission|access|customer|owner|tenant|isAllowed|can[A-Z])"
)

SIGNED_DOWNLOAD_OPERATION_PATTERN = re.compile(
    r"export\s+const\s+(?P<name>\w*(?:Download|SignedURL|Presign)\w*)\s*=\s*async\s*\((?P<params>[^)]*)\)\s*=>\s*{(?P<body>.*?)};",
    re.DOTALL,
)

PUBLIC_UPLOAD_ACCESS_PATTERN = re.compile(
    r"(?i)(access\s*:\s*['\"]public['\"]|acl\s*:\s*['\"]public-read['\"])"
)

UPLOAD_REQUEST_CONTEXT_PATTERN = re.compile(
    r"(?i)(request\.formData\(|formData\.get\(['\"]file['\"]\)|instanceof\s+Blob|multipart/form-data|req\.(file|files)|FileSchema)"
)

UPLOAD_STORAGE_CALL_PATTERN = re.compile(
    r"\b(put|upload|uploadBytes|uploadData)\s*\("
)

HTTP_HANDLER_CONTEXT_PATTERN = re.compile(
    r"(?i)(export\s+async\s+function\s+(POST|PUT)|new\s+NextResponse|Request\b|NextRequest\b)"
)

WEAK_ENV_VALUE_PATTERN = re.compile(
    r"(?i)^(?:[A-Z0-9_]*(?:SECRET|PASSWORD|TOKEN|KEY)[A-Z0-9_]*)=(secret|changeme|password|supersecretpassword|123|test|admin)$"
)


def iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.is_file():
                yield path


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def exists_any(root: Path, names: list[str]) -> list[str]:
    found = []
    name_set = set(names)
    for path in iter_files(root):
        if path.name in name_set:
            found.append(rel(path, root))
    return sorted(found)


def collect_env_usage(root: Path) -> list[str]:
    names = set()
    for path in iter_files(root):
        if path.suffix.lower() not in CODE_EXTENSIONS:
            continue
        text = read_text(path)
        for pattern in ENV_READ_PATTERNS:
            names.update(match.group(1) for match in pattern.finditer(text))
        if re.search(r"\b(import\s+OpenAI\s+from\s+['\"]openai['\"]|new\s+OpenAI\s*\()", text):
            names.add("OPENAI_API_KEY")
    return sorted(names)


def find_secret_signals(root: Path) -> list[dict[str, str]]:
    hits = []
    for path in iter_files(root):
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".lock"}:
            continue
        text = read_text(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in SECRET_PATTERNS):
                hits.append({"file": rel(path, root), "line": str(line_no), "signal": line.strip()[:160]})
                break
    return hits[:50]


def is_code_file(path: Path) -> bool:
    return path.suffix.lower() in CODE_EXTENSIONS


def is_doc_or_config(path: Path) -> bool:
    return path.suffix.lower() in {".md", ".txt", ".yaml", ".yml", ".json", ".toml"}


def find_risky_code_signals(root: Path) -> list[dict[str, str]]:
    hits = []
    for path in iter_files(root):
        if not is_code_file(path):
            continue
        text = read_text(path)
        lines = text.splitlines()
        for line_no, line in enumerate(lines, start=1):
            stripped_line = line.strip()
            for kind, pattern, message in RISKY_CODE_PATTERNS:
                if kind == "hardcoded-url" and is_doc_or_config(path):
                    continue
                if kind == "hardcoded-url" and (
                    stripped_line.startswith(("//", "#", "*"))
                    or "href=" in stripped_line
                    or "src=" in stripped_line
                ):
                    continue
                if kind == "unconditional-allow":
                    context_start = max(0, line_no - 3)
                    context_end = min(len(lines), line_no + 2)
                    context = "\n".join(lines[context_start:context_end])
                    if not AUTH_CONTEXT_PATTERN.search(context):
                        continue
                if pattern.search(line):
                    hits.append(
                        {
                            "file": rel(path, root),
                            "line": str(line_no),
                            "kind": kind,
                            "message": message,
                            "signal": line.strip()[:180],
                        }
                    )
        hits.extend(find_signed_download_auth_signals(path, root, text))
        hits.extend(find_public_upload_access_signals(path, root, text))
    return hits[:100]


def find_signed_download_auth_signals(path: Path, root: Path, text: str) -> list[dict[str, str]]:
    hits = []
    for match in SIGNED_DOWNLOAD_OPERATION_PATTERN.finditer(text):
        name = match.group("name")
        params = match.group("params")
        body = match.group("body")
        if not re.search(r"(?i)(download|signedurl|presign)", name):
            continue
        if not re.search(r"(?i)\b(rawArgs|args|context|request|req)\b", f"{params}\n{body[:200]}"):
            continue
        if not (
            "getSignedUrl(" in body
            or "SignedURLFromS3" in body
            or "GetObjectCommand" in body
            or "s3Key" in body
        ):
            continue
        if "context.user" in body or re.search(r"(?i)(owner|tenant|userId|where:\s*{\s*user)", body):
            continue
        line_no = text[: match.start()].count("\n") + 1
        hits.append(
            {
                "file": rel(path, root),
                "line": str(line_no),
                "kind": "signed-download-no-auth",
                "message": "Signed download URL operation lacks evident auth or ownership checks.",
                "signal": name,
            }
        )
    return hits


def find_public_upload_access_signals(path: Path, root: Path, text: str) -> list[dict[str, str]]:
    if not PUBLIC_UPLOAD_ACCESS_PATTERN.search(text):
        return []
    if not UPLOAD_REQUEST_CONTEXT_PATTERN.search(text):
        return []
    if not UPLOAD_STORAGE_CALL_PATTERN.search(text):
        return []
    if not (
        HTTP_HANDLER_CONTEXT_PATTERN.search(text)
        or "/api/" in rel(path, root)
    ):
        return []

    access_match = PUBLIC_UPLOAD_ACCESS_PATTERN.search(text)
    line_no = text[: access_match.start()].count("\n") + 1
    return [
        {
            "file": rel(path, root),
            "line": str(line_no),
            "kind": "public-upload-access",
            "message": "Upload route stores files with public access; verify this is intentional, non-sensitive, and uses unguessable object names.",
            "signal": access_match.group(0),
        }
    ]


def find_env_template_risks(root: Path) -> list[dict[str, str]]:
    hits = []
    for path in iter_files(root):
        name = path.name.lower()
        if not (
            name.startswith(".env")
            or "env-template" in name
            or name in {"env.example", "dotenv", "dot-env-template"}
        ):
            continue
        text = read_text(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if WEAK_ENV_VALUE_PATTERN.search(stripped):
                hits.append(
                    {
                        "file": rel(path, root),
                        "line": str(line_no),
                        "kind": "weak-env-placeholder",
                        "message": "Weak default secret/password placeholder found in an env template.",
                        "signal": stripped[:180],
                    }
                )
    return hits[:50]


def find_package_scripts(root: Path) -> dict[str, object]:
    package_json = root / "package.json"
    if not package_json.exists():
        return {}
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"error": "package.json could not be parsed"}
    return data.get("scripts", {})


def classify_files(root: Path) -> dict[str, list[str]]:
    files = [rel(path, root) for path in iter_files(root)]
    lower = [(f, f.lower()) for f in files]
    return {
        "docs": sorted(f for f, l in lower if Path(l).name in {"readme.md", "deployment.md", "ship_checklist.md", "risk_register.md", "release_notes.md"}),
        "env_files": sorted(
            f
            for f, l in lower
            if Path(l).name.startswith(".env")
            or "env-template" in Path(l).name
            or Path(l).name in {"env.example", "dotenv", "dot-env-template"}
        ),
        "ci": sorted(f for f, l in lower if ".github/workflows/" in l or Path(l).name in {"vercel.json", "netlify.toml", "dockerfile", "docker-compose.yml"}),
        "tests": sorted(f for f, l in lower if any(part in l for part in ["/test/", "/tests/", "__tests__"]) or re.search(r"(\.|_)(test|spec)\.", l)),
        "lockfiles": sorted(f for f, l in lower if Path(l).name in {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "poetry.lock", "requirements.txt", "go.sum", "cargo.lock"}),
    }


def collect_repo_signals(files: dict[str, list[str]]) -> list[dict[str, str]]:
    hits = []
    if not files["tests"]:
        hits.append(
            {
                "kind": "missing-tests",
                "message": "No automated test files found. Critical flows need manual inspection and launch risk is higher.",
            }
        )
    if not files["ci"]:
        hits.append(
            {
                "kind": "missing-ci",
                "message": "No CI or deployment workflow files found. Build, lint, and smoke checks may be manual only.",
            }
        )
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect launch-readiness signals for a repository.")
    parser.add_argument("repo", nargs="?", default=".", help="Path to the repository to scan")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    if not root.exists():
        raise SystemExit(f"Repository path does not exist: {root}")

    files = classify_files(root)
    result = {
        "repo": str(root),
        "package_scripts": find_package_scripts(root),
        "env_usage": collect_env_usage(root),
        "files": files,
        "repo_signals": collect_repo_signals(files),
        "secret_signals": find_secret_signals(root),
        "risky_code_signals": find_risky_code_signals(root),
        "env_template_risks": find_env_template_risks(root),
    }

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print(f"# AI Ship Review Inventory\n\nRepository: `{root}`\n")
    print("## Package scripts")
    scripts = result["package_scripts"]
    if scripts:
        for name, command in scripts.items():
            print(f"- `{name}`: `{command}`")
    else:
        print("- No package scripts found.")

    print("\n## Environment variables referenced")
    for name in result["env_usage"] or ["No environment variable references found."]:
        print(f"- `{name}`" if name.isupper() else f"- {name}")

    print("\n## Important files")
    for key, values in files.items():
        print(f"\n### {key}")
        if values:
            for value in values[:40]:
                print(f"- `{value}`")
            if len(values) > 40:
                print(f"- ...and {len(values) - 40} more")
        else:
            print("- None found.")

    if result["repo_signals"]:
        print("\n## Repository signals")
        for hit in result["repo_signals"]:
            print(f"- [{hit['kind']}] {hit['message']}")
    else:
        print("\n## Repository signals")
        print("- No repository-level launch-readiness signals found by this lightweight scan.")

    print("\n## Secret-like signals")
    if result["secret_signals"]:
        for hit in result["secret_signals"]:
            print(f"- `{hit['file']}:{hit['line']}` contains a secret-like pattern. Inspect manually.")
    else:
        print("- No secret-like patterns found by this lightweight scan.")

    print("\n## Risky code signals")
    if result["risky_code_signals"]:
        for hit in result["risky_code_signals"]:
            print(
                f"- `{hit['file']}:{hit['line']}` [{hit['kind']}] {hit['message']} "
                f"Signal: `{hit['signal']}`"
            )
    else:
        print("- No risky code signals found by this lightweight scan.")

    print("\n## Environment template risks")
    if result["env_template_risks"]:
        for hit in result["env_template_risks"]:
            print(
                f"- `{hit['file']}:{hit['line']}` [{hit['kind']}] {hit['message']} "
                f"Signal: `{hit['signal']}`"
            )
    else:
        print("- No weak env template placeholders found by this lightweight scan.")

    print("\nNote: This inventory is not a security audit. Inspect high-risk code paths manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
