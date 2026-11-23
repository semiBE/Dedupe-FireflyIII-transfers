import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main


class ConfigurationTests(unittest.TestCase):
    def run_main(self, env_file=None, environment=None, args=None):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "main.py"
            if env_file is not None:
                script.with_name(".env").write_text(env_file, encoding="utf-8")
            response = mock.Mock()
            response.json.return_value = {"data": [], "meta": {"pagination": {"total_pages": 1}}}
            with (
                mock.patch.object(main, "__file__", str(script)),
                mock.patch.dict(os.environ, environment or {}, clear=True),
                mock.patch.object(main.sys, "argv", ["main.py", *(args or [])]),
                mock.patch.object(main.requests, "get", return_value=response) as get,
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()) as stderr,
            ):
                try:
                    main.main()
                except SystemExit as exc:
                    return exc.code, stderr.getvalue(), get
                return 0, stderr.getvalue(), get

    def test_dotenv_overrides_environment_and_normalizes_url(self):
        code, _, get = self.run_main(
            "FIREFLY_URL=https://file.example///\nFIREFLY_TOKEN=file-token\n",
            {"FIREFLY_URL": "https://env.example", "FIREFLY_TOKEN": "env-token"},
        )
        self.assertEqual(code, 0)
        self.assertEqual(get.call_args.args[0], "https://file.example/api/v1/transactions")
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer file-token")

    def test_process_environment_is_used_without_dotenv(self):
        code, _, get = self.run_main(
            environment={"FIREFLY_URL": "https://env.example/", "FIREFLY_TOKEN": "env-token"}
        )
        self.assertEqual(code, 0)
        self.assertEqual(get.call_args.args[0], "https://env.example/api/v1/transactions")
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer env-token")

    def test_missing_and_blank_values_fail_without_network_request(self):
        for env_file in (None, "FIREFLY_URL=  \nFIREFLY_TOKEN=\n"):
            with self.subTest(env_file=env_file):
                code, error, get = self.run_main(env_file)
                self.assertEqual(code, 2)
                self.assertIn("FIREFLY_URL, FIREFLY_TOKEN", error)
                get.assert_not_called()

    def test_blank_dotenv_value_overrides_process_environment(self):
        code, error, get = self.run_main(
            "FIREFLY_TOKEN=\n",
            {"FIREFLY_URL": "https://env.example", "FIREFLY_TOKEN": "env-token"},
        )
        self.assertEqual(code, 2)
        self.assertIn("FIREFLY_TOKEN", error)
        self.assertNotIn("env-token", error)
        get.assert_not_called()

    def test_help_does_not_require_configuration(self):
        code, _, get = self.run_main(args=["--help"])
        self.assertEqual(code, 0)
        get.assert_not_called()

    def test_delete_uses_configured_url_and_token(self):
        transaction = {
            "date": "2026-01-01",
            "amount": "10",
            "source_id": "1",
            "destination_id": "2",
            "description": "transfer",
        }
        response = mock.Mock()
        response.json.return_value = {
            "data": [
                {"id": "1", "attributes": {"transactions": [transaction]}},
                {"id": "2", "attributes": {"transactions": [transaction]}},
            ],
            "meta": {"pagination": {"total_pages": 1}},
        }
        with tempfile.TemporaryDirectory() as directory:
            with (
                mock.patch.object(main, "__file__", str(Path(directory) / "main.py")),
                mock.patch.dict(
                    os.environ,
                    {"FIREFLY_URL": "https://env.example/", "FIREFLY_TOKEN": "env-token"},
                    clear=True,
                ),
                mock.patch.object(main.sys, "argv", ["main.py", "--delete"]),
                mock.patch.object(main.requests, "get", return_value=response),
                mock.patch.object(main.requests, "delete") as delete,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                delete.return_value.status_code = 204
                main.main()
                delete.assert_called_once_with(
                    "https://env.example/api/v1/transactions/2",
                    headers={"Authorization": "Bearer env-token", "Accept": "application/json"},
                    timeout=30,
                )


if __name__ == "__main__":
    unittest.main()
