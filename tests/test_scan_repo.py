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


def test_scan_repo_detects_file_key_claim_without_ownership_check(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "fileOps.ts").write_text(
        "\n".join(
            [
                "export const addFileToDb = async (rawArgs, context) => {",
                "  if (!context.user) throw new HttpError(401);",
                "  const args = ensureArgsSchemaOrThrowHttpError(schema, rawArgs);",
                "  const fileExists = await checkFileExistsInS3({ s3Key: args.s3Key });",
                "  if (!fileExists) throw new HttpError(404);",
                "  return context.entities.File.create({",
                "    data: {",
                "      s3Key: args.s3Key,",
                "      user: { connect: { id: context.user.id } },",
                "    },",
                "  });",
                "};",
                "",
                "export const addFileToDbSafely = async (rawArgs, context) => {",
                "  if (!context.user) throw new HttpError(401);",
                "  const args = ensureArgsSchemaOrThrowHttpError(schema, rawArgs);",
                "  if (!args.s3Key.startsWith(`${context.user.id}/`)) throw new HttpError(403);",
                "  const fileExists = await checkFileExistsInS3({ s3Key: args.s3Key });",
                "  if (!fileExists) throw new HttpError(404);",
                "  return context.entities.File.create({",
                "    data: {",
                "      s3Key: args.s3Key,",
                "      user: { connect: { id: context.user.id } },",
                "    },",
                "  });",
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
    flagged = [hit for hit in data["risky_code_signals"] if hit["kind"] == "file-key-claim-no-ownership"]
    assert len(flagged) == 1
    assert flagged[0]["file"] == "fileOps.ts"
    assert flagged[0]["signal"] == "addFileToDb"


def test_scan_repo_detects_auth_callback_request_origin_redirect_and_ignores_general_site_url_helpers(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "sample"
    (repo / "app" / "auth" / "callback").mkdir(parents=True)
    (repo / "utils").mkdir()
    (repo / "app" / "auth" / "callback" / "route.ts").write_text(
        "\n".join(
            [
                "import { NextRequest, NextResponse } from 'next/server';",
                "export async function GET(request: NextRequest) {",
                "  const requestUrl = new URL(request.url);",
                "  return NextResponse.redirect(`${requestUrl.origin}/account`);",
                "}",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "utils" / "helpers.ts").write_text(
        "\n".join(
            [
                "export const getURL = () => {",
                "  return process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';",
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
    flagged = [hit for hit in data["risky_code_signals"] if hit["kind"] == "auth-callback-request-origin"]
    assert len(flagged) == 1
    assert flagged[0]["file"] == "app/auth/callback/route.ts"


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


def test_scan_repo_detects_placeholder_secret_values_in_env_templates(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / ".env.example").write_text(
        "\n".join(
            [
                "NEXTAUTH_SECRET=my-superstrong-secret",
                "HANKO_API_KEY=add-your-hanko-api-key",
                "WEBHOOK_SECRET_KEY=6c369443-1a88-444e-b459-7e662c1fff9e",
                "SMTP_PASSWORD=smtpPassword",
                "STRIPE_PUBLISHABLE_KEY=your_publishable_key_here",
                "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=your_publishable_key_here",
                "NEXT_PUBLIC_GOOGLE_API_KEY=secret",
                "NEXT_PUBLIC_SITE_URL=https://example.com",
                "NORMAL_NAME=example-value",
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
    signals = {hit["signal"] for hit in data["env_template_risks"]}
    assert "NEXTAUTH_SECRET=my-superstrong-secret" in signals
    assert "HANKO_API_KEY=add-your-hanko-api-key" in signals
    assert "WEBHOOK_SECRET_KEY=6c369443-1a88-444e-b459-7e662c1fff9e" in signals
    assert "SMTP_PASSWORD=smtpPassword" in signals
    assert "STRIPE_PUBLISHABLE_KEY=your_publishable_key_here" not in signals
    assert "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=your_publishable_key_here" not in signals
    assert "NEXT_PUBLIC_GOOGLE_API_KEY=secret" not in signals
    assert "NEXT_PUBLIC_SITE_URL=https://example.com" not in signals


def test_scan_repo_detects_insecure_compose_database_auth(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "docker-compose.yml").write_text(
        "\n".join(
            [
                "services:",
                "  mysql:",
                "    image: mysql:8.0",
                "    environment:",
                "      MYSQL_ALLOW_EMPTY_PASSWORD: 'yes'",
                "  postgres:",
                "    image: postgres:16",
                "    environment:",
                "      POSTGRES_HOST_AUTH_METHOD: trust",
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
    kinds = {hit["kind"] for hit in data["deployment_config_risks"]}
    assert "compose-empty-db-password" in kinds
    assert "compose-trust-db-auth" in kinds


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
    risky_hits = data["risky_code_signals"]
    kinds = {hit["kind"] for hit in risky_hits}
    assert "openai-sdk-usage" in kinds
    assert "client-controlled-ai-id" in kinds
    openai_hits = [hit for hit in risky_hits if hit["kind"] == "openai-sdk-usage"]
    assert len(openai_hits) == 1
    assert openai_hits[0]["line"] == "1"


def test_scan_repo_detects_auth_rate_limit_fail_open(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "auth.ts").write_text(
        "\n".join(
            [
                "const authOptions = {",
                "  callbacks: {",
                "    signIn: async ({ user }) => {",
                "      try {",
                "        const rateLimitResult = await checkRateLimit(rateLimiters.auth, clientIP);",
                "        if (!rateLimitResult.success) {",
                "          return false;",
                "        }",
                "      } catch (error) {}",
                "      return !!user.email;",
                "    },",
                "  },",
                "};",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "safe_auth.ts").write_text(
        "\n".join(
            [
                "const authOptions = {",
                "  callbacks: {",
                "    signIn: async ({ user }) => {",
                "      try {",
                "        const rateLimitResult = await checkRateLimit(rateLimiters.auth, clientIP);",
                "        if (!rateLimitResult.success) {",
                "          return false;",
                "        }",
                "      } catch (error) {",
                "        return false;",
                "      }",
                "      return !!user.email;",
                "    },",
                "  },",
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
    flagged = [hit for hit in data["risky_code_signals"] if hit["kind"] == "auth-rate-limit-fail-open"]
    assert len(flagged) == 1
    assert flagged[0]["file"] == "auth.ts"
    assert flagged[0]["signal"] == "catch (error) {}"


def test_scan_repo_detects_guest_auth_without_rate_limit(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "auth.ts").write_text(
        "\n".join(
            [
                "import Credentials from 'next-auth/providers/credentials';",
                "providers: [",
                "  Credentials({",
                "    id: 'guest',",
                "    credentials: {},",
                "    async authorize() {",
                "      const [guestUser] = await createGuestUser();",
                "      return { ...guestUser, type: 'guest' };",
                "    },",
                "  }),",
                "]",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "safe_auth.ts").write_text(
        "\n".join(
            [
                "import Credentials from 'next-auth/providers/credentials';",
                "providers: [",
                "  Credentials({",
                "    id: 'guest',",
                "    credentials: {},",
                "    async authorize() {",
                "      await checkRateLimit(rateLimiters.guest, clientIP);",
                "      const [guestUser] = await createGuestUser();",
                "      return { ...guestUser, type: 'guest' };",
                "    },",
                "  }),",
                "]",
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
    flagged = [hit for hit in data["risky_code_signals"] if hit["kind"] == "guest-auth-no-rate-limit"]
    assert len(flagged) == 1
    assert flagged[0]["file"] == "auth.ts"
    assert flagged[0]["signal"] == "id: 'guest'"


def test_scan_repo_detects_nextauth_credentials_without_rate_limit(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "auth.ts").write_text(
        "\n".join(
            [
                "import Credentials from 'next-auth/providers/credentials';",
                "providers: [",
                "  Credentials({",
                "    credentials: {",
                "      email: { type: 'email' },",
                "      password: { type: 'password' },",
                "    },",
                "    async authorize(credentials) {",
                "      const users = await getUser(credentials.email);",
                "      const passwordsMatch = await compare(credentials.password, users[0].password);",
                "      if (!passwordsMatch) return null;",
                "      return users[0];",
                "    },",
                "  }),",
                "  Credentials({",
                "    id: 'guest',",
                "    credentials: {},",
                "    async authorize() {",
                "      const [guestUser] = await createGuestUser();",
                "      return { ...guestUser, type: 'guest' };",
                "    },",
                "  }),",
                "]",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "safe_auth.ts").write_text(
        "\n".join(
            [
                "import Credentials from 'next-auth/providers/credentials';",
                "providers: [",
                "  Credentials({",
                "    credentials: {",
                "      email: { type: 'email' },",
                "      password: { type: 'password' },",
                "    },",
                "    async authorize(credentials) {",
                "      await checkRateLimit(rateLimiters.auth, clientIP);",
                "      const users = await getUser(credentials.email);",
                "      const passwordsMatch = await compare(credentials.password, users[0].password);",
                "      if (!passwordsMatch) return null;",
                "      return users[0];",
                "    },",
                "  }),",
                "]",
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
    flagged = [
        hit for hit in data["risky_code_signals"] if hit["kind"] == "nextauth-credentials-no-rate-limit"
    ]
    assert len(flagged) == 1
    assert flagged[0]["file"] == "auth.ts"
    assert flagged[0]["signal"] == "Credentials("


def test_scan_repo_detects_password_auth_without_rate_limit(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "actions.ts").write_text(
        "\n".join(
            [
                "'use server';",
                "export async function signIn(formData: FormData) {",
                "  const user = await db.query.users.findFirst({ where: eq(users.email, email) });",
                "  const passwordMatch = await comparePasswords(password, user.passwordHash);",
                "  if (!passwordMatch) return { error: 'Invalid credentials' };",
                "  await setSession(user);",
                "}",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "safe_actions.ts").write_text(
        "\n".join(
            [
                "'use server';",
                "export async function signIn(formData: FormData) {",
                "  await checkRateLimit(rateLimiters.auth, clientIP);",
                "  const user = await db.query.users.findFirst({ where: eq(users.email, email) });",
                "  const passwordMatch = await comparePasswords(password, user.passwordHash);",
                "  if (!passwordMatch) return { error: 'Invalid credentials' };",
                "  await setSession(user);",
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
    flagged = [hit for hit in data["risky_code_signals"] if hit["kind"] == "password-auth-no-rate-limit"]
    assert len(flagged) == 1
    assert flagged[0]["file"] == "actions.ts"
    assert flagged[0]["signal"] == "signIn"


def test_scan_repo_detects_storage_delete_noop(tmp_path: Path) -> None:
    repo = tmp_path / "sample"
    repo.mkdir()
    (repo / "s3Utils.ts").write_text(
        "\n".join(
            [
                "export const deleteFileFromS3 = async ({ s3Key }) => {",
                "  return s3Key;",
                "};",
                "",
                "export const deleteFileFromS3Safely = async ({ s3Key }) => {",
                "  const command = new DeleteObjectCommand({ Key: s3Key });",
                "  return await s3Client.send(command);",
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
    flagged = [hit for hit in data["risky_code_signals"] if hit["kind"] == "storage-delete-noop"]
    assert len(flagged) == 1
    assert flagged[0]["file"] == "s3Utils.ts"
    assert flagged[0]["signal"] == "deleteFileFromS3"


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
