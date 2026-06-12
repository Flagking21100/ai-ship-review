from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_scan_repo_json_output(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps({"scripts": {"build": "vite build", "test": "vitest"}}),
        encoding="utf-8",
    )
    (repo / ".env.example").write_text("DATABASE_URL=\n", encoding="utf-8")
    (repo / "app.ts").write_text("console.log(process.env.DATABASE_URL)\n", encoding="utf-8")

    script = Path(__file__).resolve().parents[1] / "scripts" / "scan_repo.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(repo), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    data = json.loads(completed.stdout)
    assert data["package_scripts"]["build"] == "vite build"
    assert "DATABASE_URL" in data["env_usage"]
    assert ".env.example" in data["files"]["env_files"]
