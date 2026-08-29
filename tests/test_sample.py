import unittest
from types import SimpleNamespace

from value_leakage.sample import _flatten_response


class SampleResponseFlatteningTest(unittest.TestCase):
    def test_missing_choices_is_recorded_as_safe_error(self):
        response = SimpleNamespace(
            choices=None,
            model="openrouter/test-model",
            provider="test-provider",
            raw_payload="should not be serialized",
        )

        row = _flatten_response(3, response)

        self.assertEqual(row, {
            "i": 3,
            "error": "response contained no choices",
            "response_model": "openrouter/test-model",
            "response_provider": "test-provider",
        })

    def test_empty_choices_is_recorded_as_safe_error(self):
        response = SimpleNamespace(
            choices=[],
            model="openrouter/test-model",
            model_extra={"provider": "test-provider"},
        )

        row = _flatten_response(4, response)

        self.assertEqual(row, {
            "i": 4,
            "error": "response contained no choices",
            "response_model": "openrouter/test-model",
            "response_provider": "test-provider",
        })


if __name__ == "__main__":
    unittest.main()
