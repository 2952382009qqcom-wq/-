"""Offline SDK mocks verify credential binding, errors, and bounded caching."""

import os
from threading import Event, Thread
from types import SimpleNamespace
import unittest
from unittest import mock

import httpx
from openai import APIError, AuthenticationError

with mock.patch.dict(os.environ, {"LLM_API_KEY": "sk-placeholder-gateway-import"}):
    from core import llm_client

from core.model_settings import DEFAULT_BASE_URL, DEFAULT_MODEL


class DeepSeekGatewayTests(unittest.TestCase):
    shared_key = "sk-unit-test-shared-never-used-online"

    def setUp(self):
        for patcher in (
            mock.patch.dict(os.environ, {
                "LLM_API_KEY": self.shared_key, "LLM_BASE_URL": "", "LLM_MODEL": "", "LLM_TIMEOUT": "300",
            }),
            mock.patch.object(llm_client, "_config", {}),
            mock.patch.object(llm_client, "_clients", {}),
            mock.patch.object(llm_client, "_client", None),
            mock.patch.object(llm_client, "DEMO_MODE", False),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.sdk_clients = []
        constructor = mock.patch.object(llm_client, "OpenAI", side_effect=self.make_sdk_client)
        self.openai = constructor.start()
        self.addCleanup(constructor.stop)

    def make_sdk_client(self, **kwargs):
        def create(**request):
            if request.get("stream"):
                return iter([
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content='{"answer":'))]),
                    SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content='"ok"}'))]),
                ])
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"answer":"ok"}'))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=mock.Mock(side_effect=create))))
        self.sdk_clients.append(client)
        return client

    def assert_safe_error(self, value):
        self.assertNotIn(self.shared_key, str(value))
        self.assertNotIn("private-personal-key", str(value))
        self.assertNotIn("upstream-secret-detail", str(value))

    def test_default_sync_and_stream_use_deepseek_flash_and_same_provider(self):
        self.assertEqual(llm_client.call_llm_json("system", "user"), {"answer": "ok"})
        chunks = list(llm_client.call_llm_stream_json("system", "user"))
        self.assertEqual(chunks[-1], {"answer": "ok"})
        self.openai.assert_called_once_with(api_key=self.shared_key, base_url=DEFAULT_BASE_URL)
        requests = self.sdk_clients[0].chat.completions.create.call_args_list
        self.assertEqual([request.kwargs["model"] for request in requests], [DEFAULT_MODEL, DEFAULT_MODEL])
        self.assertNotIn("stream", requests[0].kwargs)
        self.assertIs(requests[1].kwargs["stream"], True)

    def test_endpoint_and_model_overrides_without_key_cannot_reroute_shared_key(self):
        for key in (None, "", "   "):
            override = {"api_key": key, "base_url": "https://collector.example/v1", "model": "other-model"}
            merged = llm_client._merged_config(override)
            self.assertEqual(merged["api_key"], self.shared_key)
            self.assertEqual(merged["base_url"], DEFAULT_BASE_URL)
            self.assertEqual(merged["model"], DEFAULT_MODEL)
            self.assertEqual(llm_client.call_llm_json("system", "user", model_override="legacy-user-model", config_override=override), {"answer": "ok"})
            self.assertEqual(list(llm_client.call_llm_stream_json("system", "user", model_override="legacy-user-model", config_override=override))[-1], {"answer": "ok"})
        self.openai.assert_called_once_with(api_key=self.shared_key, base_url=DEFAULT_BASE_URL)
        for request in self.sdk_clients[0].chat.completions.create.call_args_list:
            self.assertEqual(request.kwargs["model"], DEFAULT_MODEL)

    def test_personal_key_missing_settings_uses_own_defaults(self):
        with mock.patch.dict(os.environ, {"LLM_BASE_URL": "https://api.openai.com/v1", "LLM_MODEL": "gpt-4o"}):
            override = {"api_key": "private-personal-key"}
            self.assertEqual(llm_client._merged_config(override), {
                "api_key": "private-personal-key", "base_url": DEFAULT_BASE_URL, "model": DEFAULT_MODEL,
            })
            self.assertEqual(llm_client.call_llm_json("system", "user", config_override=override), {"answer": "ok"})
            self.openai.assert_called_once_with(api_key="private-personal-key", base_url=DEFAULT_BASE_URL)

    def test_server_authorized_model_override_applies_without_changing_shared_provider(self):
        override = {'_allow_shared_model': True, 'base_url': 'https://collector.invalid/v1'}
        self.assertEqual(llm_client.call_llm_json('system', 'user', model_override='deepseek-v4-pro', config_override=override), {'answer': 'ok'})
        self.assertEqual(list(llm_client.call_llm_stream_json('system', 'user', model_override='deepseek-v4-pro', config_override=override))[-1], {'answer': 'ok'})
        self.openai.assert_called_once_with(api_key=self.shared_key, base_url=DEFAULT_BASE_URL)
        for request in self.sdk_clients[0].chat.completions.create.call_args_list:
            self.assertEqual(request.kwargs['model'], 'deepseek-v4-pro')

    def test_personal_provider_and_model_are_bound_for_sync_and_stream(self):
        override = {"api_key": "private-personal-key", "base_url": "https://api.moonshot.cn:443/v1/", "model": "moonshot-v1-8k"}
        self.assertEqual(llm_client.call_llm_json("system", "user", config_override=override), {"answer": "ok"})
        self.assertEqual(list(llm_client.call_llm_stream_json("system", "user", config_override=override))[-1], {"answer": "ok"})
        self.openai.assert_called_once_with(api_key="private-personal-key", base_url="https://api.moonshot.cn/v1")
        for request in self.sdk_clients[0].chat.completions.create.call_args_list:
            self.assertEqual(request.kwargs["model"], "moonshot-v1-8k")

    def test_bad_personal_key_is_an_error_and_does_not_change_shared_mode(self):
        override = {"api_key": "private-personal-key", "base_url": DEFAULT_BASE_URL, "model": DEFAULT_MODEL}
        client = llm_client.get_client(override)
        request = httpx.Request("POST", DEFAULT_BASE_URL + "/chat/completions")
        failure = AuthenticationError(
            f"private-personal-key upstream-secret-detail {self.shared_key}",
            response=httpx.Response(401, request=request), body={"error": "upstream-secret-detail"},
        )
        client.chat.completions.create.side_effect = failure
        sync = llm_client.call_llm_json("system", "user", config_override=override)
        streamed = list(llm_client.call_llm_stream_json("system", "user", config_override=override))
        self.assertIn("error", sync)
        self.assertIn("API Key", sync["error"])
        self.assertIn("error", streamed[-1])
        self.assert_safe_error(sync)
        self.assert_safe_error(streamed)
        self.assertFalse(llm_client.DEMO_MODE)
        self.assertFalse(llm_client.is_demo_mode())
        self.assertEqual(llm_client.call_llm_json("system", "user"), {"answer": "ok"})
        self.assertEqual(list(llm_client.call_llm_stream_json("system", "user"))[-1], {"answer": "ok"})
        self.assertEqual(self.openai.call_args.kwargs["api_key"], self.shared_key)

    def test_api_and_unexpected_errors_never_echo_upstream_details(self):
        client = llm_client.get_client()
        request = httpx.Request("POST", DEFAULT_BASE_URL + "/chat/completions")
        message = f"private-personal-key upstream-secret-detail {self.shared_key}"
        for failure in (APIError(message, request=request, body={"error": message}), RuntimeError(message)):
            with self.subTest(failure=type(failure).__name__):
                client.chat.completions.create.side_effect = failure
                sync = llm_client.call_llm_json("system", "user")
                streamed = list(llm_client.call_llm_stream_json("system", "user"))
                connection = llm_client.test_llm_connection(self.shared_key, DEFAULT_BASE_URL, DEFAULT_MODEL)
                self.assertIn("error", sync)
                self.assertIn("error", streamed[-1])
                self.assertFalse(connection[0])
                for value in (sync, streamed, connection):
                    self.assert_safe_error(value)
                self.assertFalse(llm_client.DEMO_MODE)

    def test_invalid_personal_url_or_model_stops_before_sdk_construction(self):
        for override in (
            {"api_key": "private-personal-key", "base_url": "https://collector.example/v1"},
            {"api_key": "private-personal-key", "base_url": DEFAULT_BASE_URL, "model": "model\n"},
        ):
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    llm_client.get_client(override)
                self.assertIn("error", llm_client.call_llm_json("system", "user", config_override=override))
                self.assertIn("error", list(llm_client.call_llm_stream_json("system", "user", config_override=override))[-1])
                result = llm_client.test_llm_connection(override["api_key"], override["base_url"], override.get("model", DEFAULT_MODEL))
                self.assertFalse(result[0])
                self.assert_safe_error(result)
        self.openai.assert_not_called()

    def test_missing_or_placeholder_key_keeps_demo_without_sdk_requests(self):
        for key in ("", "sk-placeholder-local-only"):
            with mock.patch.dict(os.environ, {"LLM_API_KEY": key, "LLM_BASE_URL": "http://127.0.0.1:9/v1"}):
                self.assertTrue(llm_client.is_demo_mode())
                self.assertEqual(llm_client.call_llm_json("system", "user"), {"demo_mode": True})
                self.assertEqual(list(llm_client.call_llm_stream_json("system", "user")), [{"demo_mode": True}])
                self.assertFalse(llm_client.test_llm_connection(key, DEFAULT_BASE_URL, DEFAULT_MODEL)[0])
        self.openai.assert_not_called()

    def test_shared_config_updates_clear_all_cached_clients(self):
        llm_client.get_client()
        llm_client.get_client({"api_key": "private-personal-key"})
        self.assertEqual(len(llm_client._clients), 2)
        llm_client.update_config(api_key="new-shared-test-key", base_url=DEFAULT_BASE_URL, model=DEFAULT_MODEL)
        self.assertEqual(llm_client._clients, {})
        self.assertIsNone(llm_client._client)
        self.assertEqual(llm_client.call_llm_json("system", "user"), {"answer": "ok"})
        self.assertEqual(self.openai.call_args.kwargs["api_key"], "new-shared-test-key")

    def test_client_cache_has_128_limit_and_keeps_recently_used_clients(self):
        for index in range(128):
            llm_client.get_client({"api_key": f"cache-test-key-{index}"})
        recently_used = llm_client.get_client({"api_key": "cache-test-key-0"})
        llm_client.get_client({"api_key": "cache-test-key-128"})
        self.assertEqual(len(llm_client._clients), 128)
        self.assertNotIn(("cache-test-key-1", DEFAULT_BASE_URL), llm_client._clients)
        self.assertIn(("cache-test-key-0", DEFAULT_BASE_URL), llm_client._clients)
        self.assertIs(llm_client.get_client({"api_key": "cache-test-key-0"}), recently_used)

    def assert_update_waits_for_request_snapshot(self, function_name, clear_key=False):
        selected = Event()
        release = Event()
        update_started = Event()
        updated = Event()
        original = getattr(llm_client, function_name)
        first = True
        result = []

        def paused(*args, **kwargs):
            nonlocal first
            value = original(*args, **kwargs)
            if first:
                first = False
                selected.set()
                if not release.wait(2):
                    raise RuntimeError("test snapshot wait timed out")
            return value

        def update():
            update_started.set()
            llm_client.update_config(api_key="" if clear_key else "new-shared-test-key", base_url=DEFAULT_BASE_URL, model=DEFAULT_MODEL)
            updated.set()

        with mock.patch.object(llm_client, function_name, side_effect=paused):
            worker = Thread(target=lambda: result.append(llm_client.call_llm_json("system", "user")), daemon=True)
            updater = Thread(target=update, daemon=True)
            worker.start()
            try:
                self.assertTrue(selected.wait(2))
                updater.start()
                self.assertTrue(update_started.wait(2))
                self.assertFalse(updated.wait(0.05))
            finally:
                release.set()
                worker.join(2)
                if updater.ident is not None:
                    updater.join(2)
            self.assertFalse(worker.is_alive())
            self.assertFalse(updater.is_alive())
        self.assertTrue(updated.is_set())
        self.assertEqual(result, [{"answer": "ok"}])
        self.openai.assert_called_once_with(api_key=self.shared_key, base_url=DEFAULT_BASE_URL)
        self.assertEqual(llm_client._clients, {})
        self.assertIsNone(llm_client._client)
        if clear_key:
            self.assertEqual(llm_client.call_llm_json("system", "user"), {"demo_mode": True})
            self.openai.assert_called_once()

    def test_demo_decision_uses_same_snapshot_as_request_after_key_clear(self):
        self.assert_update_waits_for_request_snapshot("_selected_api_key", clear_key=True)

    def test_configuration_update_cannot_repopulate_cache_with_old_key(self):
        self.assert_update_waits_for_request_snapshot("_merged_config")


if __name__ == "__main__":
    unittest.main()
