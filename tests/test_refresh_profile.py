"""Source observation must precede successful profile-refresh outcomes."""

import importlib.util
import io
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "refresh-profile.py"
SPEC = importlib.util.spec_from_file_location("refresh_profile", SCRIPT)
refresh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh)

PROJECTION = "# meta-organvm\n\nA sourced profile.\n"


class RefreshProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.profile = Path(self.temp.name) / "profile" / "README.md"
        self.profile.parent.mkdir()
        self.profile.write_text("Existing approved profile.\n")

    def run_refresh(self, *, check=False, projection=PROJECTION, error=None):
        output, errors = io.StringIO(), io.StringIO()
        argv = [str(SCRIPT)] + (["--check"] if check else [])
        with (
            patch.object(refresh, "PROFILE_PATH", self.profile),
            patch.object(refresh, "fetch", return_value=projection, side_effect=error),
            patch("sys.argv", argv),
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            result = refresh.main()
        return result, output.getvalue(), errors.getvalue()

    def test_http_failure_is_unavailable_in_both_modes(self):
        for check in (False, True):
            for status in (403, 404, 500):
                with self.subTest(check=check, status=status):
                    before = self.profile.read_bytes()
                    error = urllib.error.HTTPError(refresh.SOURCE_URL, status, "unavailable", {}, None)
                    result, output, errors = self.run_refresh(check=check, error=error)
                    self.assertEqual(result, 2)
                    self.assertIn("UNAVAILABLE:", errors)
                    self.assertEqual(output, "")
                    self.assertEqual(self.profile.read_bytes(), before)

    def test_transport_and_decode_failure_are_unavailable(self):
        for error in (urllib.error.URLError("offline"), TimeoutError("timeout"),
                      UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid")):
            with self.subTest(error=type(error).__name__):
                before = self.profile.read_bytes()
                result, output, errors = self.run_refresh(check=True, error=error)
                self.assertEqual(result, 2)
                self.assertIn("UNAVAILABLE:", errors)
                self.assertEqual(output, "")
                self.assertEqual(self.profile.read_bytes(), before)

    def test_invalid_projection_is_not_parity_or_written(self):
        for check in (False, True):
            for projection in ("", " \n", "<html>Sign in</html>", "# Unrelated page\n"):
                with self.subTest(check=check, projection=projection):
                    before = self.profile.read_bytes()
                    result, output, errors = self.run_refresh(check=check, projection=projection)
                    self.assertEqual(result, 2)
                    self.assertIn("INVALID:", errors)
                    self.assertEqual(output, "")
                    self.assertEqual(self.profile.read_bytes(), before)

    def test_observed_drift_returns_one_without_writing(self):
        before = self.profile.read_bytes()
        result, output, errors = self.run_refresh(check=True)
        self.assertEqual(result, 1)
        self.assertIn("DRIFT:", errors)
        self.assertEqual(output, "")
        self.assertEqual(self.profile.read_bytes(), before)

    def test_observed_parity_returns_zero(self):
        self.profile.write_text(PROJECTION)
        result, output, errors = self.run_refresh(check=True)
        self.assertEqual(result, 0)
        self.assertIn("already matches", output)
        self.assertEqual(errors, "")

    def test_successful_update_then_parity_preserves_owned_hub(self):
        hub = "<!-- PORTFOLIO-HUB-START -->\n[Portfolio](https://example.org/)\n<!-- PORTFOLIO-HUB-END -->"
        self.profile.write_text("Existing profile\n\n" + hub + "\n")
        result, output, errors = self.run_refresh()
        self.assertEqual(result, 0)
        self.assertIn("Updated", output)
        self.assertEqual(errors, "")
        self.assertTrue(self.profile.read_text().startswith(PROJECTION))
        self.assertEqual(self.profile.read_text().count(hub), 1)
        self.assertEqual(self.run_refresh(check=True)[0], 0)

    def test_unavailable_source_does_not_create_missing_profile(self):
        self.profile.unlink()
        self.assertEqual(self.run_refresh(error=TimeoutError())[0], 2)
        self.assertFalse(self.profile.exists())


if __name__ == "__main__":
    unittest.main()
