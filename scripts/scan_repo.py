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
    re.compile(r"import\.meta\.env\.([A-Z0-9_]+)"),
    re.compile(r"Deno\.env\.get\(['\"]([A-Z0-9_]+)['\"]\)"),
]


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
        if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".go", ".rs", ".rb", ".php"}:
            continue
        text = read_text(path)
        for pattern in ENV_READ_PATTERNS:
            names.update(match.group(1) for match in pattern.finditer(text))
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
        "env_files": sorted(f for f, l in lower if Path(l).name.startswith(".env")),
        "ci": sorted(f for f, l in lower if ".github/workflows/" in l or Path(l).name in {"vercel.json", "netlify.toml", "dockerfile", "docker-compose.yml"}),
        "tests": sorted(f for f, l in lower if any(part in l for part in ["/test/", "/tests/", "__tests__"]) or re.search(r"(\.|_)(test|spec)\.", l)),
        "lockfiles": sorted(f for f, l in lower if Path(l).name in {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "poetry.lock", "requirements.txt", "go.sum", "cargo.lock"}),
    }


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
        "secret_signals": find_secret_signals(root),
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

    print("\n## Secret-like signals")
    if result["secret_signals"]:
        for hit in result["secret_signals"]:
            print(f"- `{hit['file']}:{hit['line']}` contains a secret-like pattern. Inspect manually.")
    else:
        print("- No secret-like patterns found by this lightweight scan.")

    print("\nNote: This inventory is not a security audit. Inspect high-risk code paths manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
