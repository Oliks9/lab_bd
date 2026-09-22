import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"


@unittest.skipUnless(POWERSHELL.is_file(), "Windows PowerShell is required")
class GitLabUploadTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="quiz upload ")
        self.release = Path(self.directory.name)
        self.local = {
            "README.md": "Инструкция по развёртыванию".encode(),
            "OracleQuizPlatform.exe": bytes(range(256)) + b"\0binary",
            "app/quiz_app.py": b"print('test')\n",
            "app/quiz_client/__init__.py": b"",
            "sql/install.sql": b"SELECT 1 FROM dual;\n",
            "rebuild.ps1": b"exit 0\n",
            "requirements.txt": b"oracledb\n",
        }
        for name, content in self.local.items():
            target = self.release / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        (self.release / ".env").write_text("PRIVATE_PASSWORD=do-not-upload", encoding="utf-8")
        self.remote = {"README.md": b"Old README", "keep.txt": b"Unrelated file"}
        self.posts = []
        self.requests = []
        self.blocked = False
        self.auth_error = False
        self.redirect = False
        self.race = False
        self.reject_upload = False
        self.bad_verification = False
        self.head_requests = 0
        self.revision = "a" * 40
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def respond(self, status, payload=None, headers=None):
                data = json.dumps(payload or {}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(data)

            def dispatch(self):
                owner.requests.append((self.command, self.path))
                if owner.auth_error or self.headers.get("PRIVATE-TOKEN") != "local-test-token":
                    self.respond(401)
                    return
                path = unquote(urlsplit(self.path).path)
                if owner.redirect:
                    self.respond(302, headers={"Location": "/redirected"})
                elif path.endswith("/projects/group/demo"):
                    self.respond(200, {"id": 1, "path_with_namespace": "group/demo"})
                elif path.endswith("/repository/branches/main"):
                    owner.head_requests += 1
                    revision = "c" * 40 if owner.race and owner.head_requests > 1 else owner.revision
                    self.respond(200, {"can_push": not owner.blocked, "commit": {"id": revision}})
                elif "/repository/files/" in path:
                    name = path.split("/repository/files/", 1)[1]
                    if name not in owner.remote:
                        self.respond(404)
                        return
                    digest = hashlib.sha256(owner.remote[name]).hexdigest()
                    if owner.bad_verification and owner.posts:
                        digest = "0" * 64
                    self.respond(200, headers={
                        "X-Gitlab-Content-Sha256": digest,
                        "X-Gitlab-Last-Commit-Id": owner.revision,
                    })
                elif path.endswith("/repository/commits") and self.command == "POST":
                    payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    owner.posts.append(payload)
                    if owner.reject_upload:
                        self.respond(413)
                        return
                    for action in payload["actions"]:
                        owner.remote[action["file_path"]] = base64.b64decode(action["content"])
                    owner.revision = "b" * 40
                    self.respond(201, {"id": owner.revision})
                else:
                    self.respond(404)

            do_GET = dispatch
            do_HEAD = dispatch
            do_POST = dispatch

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def run_upload(self, flags="-AllowHttp", confirmation="UPLOAD"):
        script = str(ROOT / "build/publish_gitlab.ps1").replace("'", "''")
        source = str(self.release).replace("'", "''")
        wrapper = (
            "function global:Read-Host { param([string]$Prompt, [switch]$AsSecureString) "
            "if ($AsSecureString) { ConvertTo-SecureString 'local-test-token' -AsPlainText -Force } "
            f"else {{ '{confirmation}' }} }}; "
            f"& '{script}' -SourceDirectory '{source}' "
            f"-RepositoryUrl 'http://127.0.0.1:{self.server.server_port}/group/demo.git' {flags}"
        )
        result = subprocess.run(
            [str(POWERSHELL), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", wrapper],
            capture_output=True, timeout=60,
            env={**os.environ, "PSModulePath": str(POWERSHELL.parent / "Modules")},
        )
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        self.assertNotIn("local-test-token", output)
        return result.returncode, output

    def test_upload_root_overwrite_readme_preserve_binary_and_other_files(self):
        code, output = self.run_upload()
        self.assertEqual(code, 0, output)
        self.assertIn("Upload verified", output)
        self.assertEqual(len(self.posts), 1)
        payload = self.posts[0]
        self.assertEqual(payload["branch"], "main")
        self.assertNotIn("force", payload)
        actions = {a["file_path"]: a for a in payload["actions"]}
        self.assertEqual(set(actions), set(self.local))
        self.assertEqual(actions["README.md"]["action"], "update")
        self.assertEqual(actions["README.md"]["last_commit_id"], "a" * 40)
        for path, content in self.local.items():
            self.assertEqual(self.remote[path], content)
        self.assertEqual(self.remote["keep.txt"], b"Unrelated file")
        code, output = self.run_upload()
        self.assertEqual(code, 0, output)
        self.assertIn("No commit is needed", output)
        self.assertEqual(len(self.posts), 1)

    def test_dry_run_has_no_network_requests(self):
        code, output = self.run_upload("-DryRun")
        self.assertEqual(code, 0, output)
        self.assertFalse(self.requests)

    def test_http_requires_explicit_permission(self):
        code, output = self.run_upload("")
        self.assertNotEqual(code, 0)
        self.assertIn("-AllowHttp", output)
        self.assertFalse(self.requests)

    def test_cancel_has_no_network_requests(self):
        code, output = self.run_upload(confirmation="CANCEL")
        self.assertEqual(code, 0, output)
        self.assertFalse(self.requests)

    def test_protected_branch_does_not_upload(self):
        self.blocked = True
        code, output = self.run_upload()
        self.assertNotEqual(code, 0)
        self.assertIn("cannot write", output)
        self.assertFalse(self.posts)

    def test_invalid_token_is_not_printed(self):
        self.auth_error = True
        code, output = self.run_upload()
        self.assertNotEqual(code, 0)
        self.assertIn("HTTP 401", output)
        self.assertFalse(self.posts)

    def test_changed_branch_does_not_upload(self):
        self.race = True
        code, output = self.run_upload()
        self.assertNotEqual(code, 0)
        self.assertIn("branch changed", output)
        self.assertFalse(self.posts)

    def test_size_rejection_is_not_retried(self):
        self.reject_upload = True
        code, output = self.run_upload()
        self.assertNotEqual(code, 0)
        self.assertIn("HTTP 413", output)
        self.assertEqual(len(self.posts), 1)

    def test_redirect_is_not_followed(self):
        self.redirect = True
        code, output = self.run_upload()
        self.assertNotEqual(code, 0)
        self.assertEqual(len(self.requests), 1)
        self.assertFalse(self.posts)

    def test_verification_mismatch_reports_existing_commit(self):
        self.bad_verification = True
        code, output = self.run_upload()
        self.assertNotEqual(code, 0)
        self.assertIn("Commit created, but verification failed", output)
        self.assertEqual(len(self.posts), 1)

    def run_launcher(self):
        for name in ("publish_gitlab.ps1", "upload_gitlab.cmd"):
            (self.release / name).write_bytes((ROOT / "build" / name).read_bytes())
        command = f'"{os.environ["COMSPEC"]}" /d /c ""{self.release / "upload_gitlab.cmd"}" -DryRun"'
        return subprocess.run(
            command, input=b"\r\n", capture_output=True, timeout=60,
            env={**os.environ, "PSModulePath": str(POWERSHELL.parent / "Modules")},
        )

    def test_launcher_works_with_spaces_and_waits_at_end(self):
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(b"Dry run finished", result.stdout)
        self.assertIn(b"Finished. Read the result above", result.stdout)
        self.assertFalse(self.requests)
        self.assertIn("pause", (ROOT / "build/upload_gitlab.cmd").read_text())

    def test_launcher_reports_failure_and_preserves_exit_code(self):
        (self.release / "sql/install.sql").unlink()
        result = self.run_launcher()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"Upload failed. Read the error above", result.stdout)
        self.assertIn(b"Missing: sql/install.sql", result.stderr)
        self.assertFalse(self.requests)


if __name__ == "__main__":
    unittest.main()
