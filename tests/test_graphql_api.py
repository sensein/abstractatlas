import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ohbm2026.graphql_api import (
    chunked,
    extract_value_field,
    is_valid_external_url,
    load_dotenv,
    timeout_sequence,
)


class GraphQLAPIHelpersTest(unittest.TestCase):
    def test_load_dotenv_parses_simple_pairs(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "OHBM2026_API=test-key\n# comment\nOTHER=value\n",
                encoding="utf-8",
            )

            parsed = load_dotenv(env_file)

        self.assertEqual(parsed["OHBM2026_API"], "test-key")
        self.assertEqual(parsed["OTHER"], "value")

    def test_extract_value_field_handles_list_backed_value(self) -> None:
        self.assertEqual(extract_value_field([{"value": "A title"}]), "A title")
        self.assertEqual(extract_value_field({"value": "Poster"}), "Poster")

    def test_timeout_sequence_doubles_and_caps(self) -> None:
        self.assertEqual(
            timeout_sequence(start_seconds=0.1, limit_seconds=10.0),
            [0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 10.0],
        )

    def test_chunked_preserves_order(self) -> None:
        self.assertEqual(chunked([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])

    def test_is_valid_external_url_rejects_invalid_port(self) -> None:
        self.assertTrue(is_valid_external_url("https://doi.org/10.1038/s41586-020-2649-2"))
        self.assertFalse(is_valid_external_url("https://doi.org:10.1038/s41586-020-2649-2"))


if __name__ == "__main__":
    unittest.main()
