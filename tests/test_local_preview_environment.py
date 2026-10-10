"""Preview must not inherit a production database, key, or external helpers."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import local_demo


class LocalPreviewEnvironmentTests(unittest.TestCase):
    def test_preview_forces_local_database_and_disables_remote_services(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(local_demo, "ROOT", Path(directory)), mock.patch.object(os, "chdir"):
                with mock.patch.dict(os.environ, {
                    "DATABASE_URL": "postgresql://fake.invalid/never-open",
                    "LLM_API_KEY": "inherited-key-not-real",
                    "SOCKETIO_REDIS_URL": "redis://fake.invalid/0",
                    "MEILISEARCH_URL": "http://fake.invalid:7700",
                    "FCM_ENDPOINT": "http://fake.invalid/push",
                }):
                    _path, values = local_demo.configure_local_environment(5091)
                    self.assertEqual(os.environ["DATABASE_URL"], "sqlite:///" + (Path(directory) / "instance/local-demo.db").as_posix())
                    self.assertEqual(os.environ["LLM_API_KEY"], "")
                    for key in ("SOCKETIO_REDIS_URL", "MEILISEARCH_URL", "FCM_ENDPOINT"):
                        self.assertEqual(os.environ[key], "")
                    self.assertNotEqual(values["MINGJIAN_LOCAL_ADMIN_PASSWORD"], values["MINGJIAN_LOCAL_TEST_PASSWORD"])
                    self.assertGreaterEqual(len(values["MINGJIAN_LOCAL_TEST_PASSWORD"]), 12)
                    self.assertEqual(os.environ["LLM_MODEL"], "deepseek-flash")

    def test_restarting_does_not_regenerate_initial_passwords(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(local_demo, "ROOT", Path(directory)), mock.patch.object(os, "chdir"), mock.patch.dict(os.environ):
                _first_path, first = local_demo.configure_local_environment()
                _second_path, second = local_demo.configure_local_environment()
                for key in ("SECRET_KEY", "MINGJIAN_LOCAL_ADMIN_PASSWORD", "MINGJIAN_LOCAL_TEST_PASSWORD"):
                    self.assertEqual(first[key], second[key])


if __name__ == "__main__":
    unittest.main()
