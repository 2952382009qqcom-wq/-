import unittest

from core.llm_client import _parse_json_response


class LlmResponseShapeTests(unittest.TestCase):
    def test_json_object_is_returned(self):
        self.assertEqual(_parse_json_response('{"answer":"ok"}'), {"answer": "ok"})

    def test_non_object_json_is_rejected_safely(self):
        for raw, expected_type in (("[]", "list"), ("123", "int"), ('"text"', "str")):
            with self.subTest(raw=raw):
                result = _parse_json_response(raw)
                self.assertIn("error", result)
                self.assertEqual(result["invalid_response_type"], expected_type)


if __name__ == "__main__":
    unittest.main()
