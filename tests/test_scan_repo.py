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
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (repo / ".env.example").write_text("DATABASE_URL=\n", encoding="utf-8")
    (repo / "app.ts").write_text("console.log(process.env.DATABASE_URL)\n", encoding="utf-8")
    (repo / "app.test.ts").write_text("it('works', () => {})\n", encoding="utf-8")

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
    assert data["repo_signals"] == []


def test_scan_repo_reports_risky_code_signals(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "api.ts").write_text(
        "\n".join(
            [
                "const isAllowed = () => {",
                "  // TODO: ensure user can only access their own customer",
                "  return true;",
                "}",
                "console.log(req.headers)",
                "res.setHeader('Access-Control-Allow-Origin', '*')",
                "const url = 'https://demo.example.com/account'",
            ]
        ),
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "scripts" / "scan_repo.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(repo), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    data = json.loads(completed.stdout)
    kinds = {hit["kind"] for hit in data["risky_code_signals"]}
    assert "auth-placeholder" in kinds
    assert "unconditional-allow" in kinds
    assert "request-sensitive-logging" in kinds
    assert "wide-cors" in kinds
    assert "hardcoded-url" in kinds


def test_scan_repo_detects_signed_download_without_auth_and_avoids_helper_return_true_noise(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "fileOps.ts").write_text(
        "\n".join(
            [
                "export const getDownloadFileSignedURL = async (rawArgs) => {",
                "  const { s3Key } = ensureArgsSchemaOrThrowHttpError(schema, rawArgs);",
                "  return await getDownloadFileSignedURLFromS3({ s3Key });",
                "};",
                "",
                "export const checkFileExistsInS3 = async ({ s3Key }) => {",
                "  await s3Client.send(new HeadObjectCommand({ Key: s3Key }));",
                "  return true;",
                "};",
            ]
        ),
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "scripts" / "scan_repo.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(repo), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    data = json.loads(completed.stdout)
    kinds = [hit["kind"] for hit in data["risky_code_signals"]]
    assert "signed-download-no-auth" in kinds
    assert "unconditional-allow" not in kinds


def test_scan_repo_detects_public_upload_access(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "route.ts").write_text(
        "\n".join(
            [
                "import { put } from '@vercel/blob';",
                "export async function POST(request: Request) {",
                "  const formData = await request.formData();",
                "  const file = formData.get('file') as Blob;",
                "  return await put('avatar.png', file, { access: 'public' });",
                "}",
            ]
        ),
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "scripts" / "scan_repo.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(repo), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    data = json.loads(completed.stdout)
    kinds = {hit["kind"] for hit in data["risky_code_signals"]}
    assert "public-upload-access" in kinds


def test_scan_repo_detects_seed_default_credentials(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "seed.ts").write_text(
        "\n".join(
            [
                "const email = 'test@test.com';",
                "const password = 'admin123';",
                "await db.insert(users).values({ email, passwordHash, role: 'owner' });",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "safe_seed.ts").write_text(
        "\n".join(
            [
                "const email = process.env.SEED_EMAIL;",
                "const password = process.env.SEED_PASSWORD;",
                "await db.insert(users).values({ email, passwordHash, role: 'owner' });",
            ]
        ),
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "scripts" / "scan_repo.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(repo), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    data = json.loads(completed.stdout)
    flagged = [hit for hit in data["risky_code_signals"] if hit["kind"] == "seed-default-credentials"]
    assert len(flagged) == 1
    assert flagged[0]["file"] == "seed.ts"
    assert flagged[0]["signal"] == "test@test.com / admin123"


def test_scan_repo_detects_python_env_and_weak_env_templates(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "config.py").write_text(
        "import os\nSECRET_KEY = os.getenv('ACCESS_TOKEN_SECRET', '')\n",
        encoding="utf-8",
    )
    (repo / "dot-env-template").write_text(
        "ACCESS_TOKEN_SECRET=secret\nPOSTGRES_PASSWORD=supersecretpassword\n",
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "scripts" / "scan_repo.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(repo), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    data = json.loads(completed.stdout)
    assert "ACCESS_TOKEN_SECRET" in data["env_usage"]
    assert "dot-env-template" in data["files"]["env_files"]
    assert {hit["kind"] for hit in data["env_template_risks"]} == {"weak-env-placeholder"}


def test_scan_repo_detects_openai_sdk_usage_and_implicit_env(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "route.ts").write_text(
        "\n".join(
            [
                "import OpenAI from 'openai'",
                "const openai = new OpenAI();",
                "const stream = await openai.beta.threads.runs.create(threadId, { assistant_id: newMessage.assistantId, stream: true });",
            ]
        ),
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "scripts" / "scan_repo.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(repo), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    data = json.loads(completed.stdout)
    assert "OPENAI_API_KEY" in data["env_usage"]
    kinds = {hit["kind"] for hit in data["risky_code_signals"]}
    assert "openai-sdk-usage" in kinds
    assert "client-controlled-ai-id" in kinds


def test_scan_repo_reports_missing_tests_and_ci(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "package.json").write_text(
        json.dumps({"scripts": {"build": "next build", "start": "next start"}}),
        encoding="utf-8",
    )

    script = Path(__file__).resolve().parents[1] / "scripts" / "scan_repo.py"
    completed = subprocess.run(
        [sys.executable, str(script), str(repo), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )

    data = json.loads(completed.stdout)
    kinds = {hit["kind"] for hit in data["repo_signals"]}
    assert "missing-tests" in kinds
    assert "missing-ci" in kinds
