"""Provider URLs must keep API credentials on known, exact HTTPS endpoints."""

import unittest

from core.model_settings import DEFAULT_BASE_URL, DEFAULT_MODEL, normalize_provider_url, validate_model_name


class ModelSettingsTests(unittest.TestCase):
    def test_defaults_and_supported_provider_urls(self):
        self.assertEqual(DEFAULT_MODEL, "deepseek-flash")
        self.assertEqual(DEFAULT_BASE_URL, "https://api.deepseek.com/v1")
        for url in (
            DEFAULT_BASE_URL,
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "https://open.bigmodel.cn/api/paas/v4",
            "https://api.moonshot.cn/v1",
            "https://api.openai.com/v1",
        ):
            with self.subTest(url=url):
                self.assertEqual(normalize_provider_url(url), url)
                self.assertEqual(normalize_provider_url(url + "/"), url)
        self.assertEqual(normalize_provider_url(" HTTPS://API.DEEPSEEK.COM:443/v1/ "), DEFAULT_BASE_URL)

    def test_other_destinations_and_ambiguous_urls_are_rejected(self):
        for url in (
            None, [], "", "http://api.deepseek.com/v1",
            "https://collector.example/v1", "https://127.0.0.1/v1",
            "https://api.deepseek.com.collector.example/v1", "https://api.deepseek.com./v1",
            "https://user:password@api.deepseek.com/v1", "https://user@api.deepseek.com/v1",
            "https://api.deepseek.com:8443/v1", "https://api.deepseek.com:0443/v1",
            "https://api.deepseek.com:/v1", "https://api.deepseek.com:invalid/v1",
            "https://api.deepseek.com/v1?api_key=private", "https://api.deepseek.com/v1?",
            "https://api.deepseek.com/v1#fragment", "https://api.deepseek.com/v1#",
            "https://api.deepseek.com", "https://api.deepseek.com/v1/chat/completions",
            "https://api.deepseek.com//v1", "https://api.deepseek.com/%76%31",
            "https://api.deepseek.com/v1/../other", "https://api.deepseek.com\\@collector.example/v1",
            "https://api.deepseek.com/\nv1", "\thttps://api.deepseek.com/v1",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    normalize_provider_url(url)

    def test_model_identifier_accepts_supported_characters_and_limit(self):
        for value in (DEFAULT_MODEL, "gpt-4o", "Vendor/model:Version_1.0", "x" * 100):
            self.assertEqual(validate_model_name(value), value)
        for value in (None, [], "", " ", " model", "model ", "bad model", "model\n", "model\r\n", "model\t", "model?key=x", "模型", "x" * 101):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_model_name(value)


if __name__ == "__main__":
    unittest.main()
