import unittest

from abstractatlas import artifacts
from abstractatlas.titles import build_title_modification_report, normalize_abstract_title


class TitleHelpersTest(unittest.TestCase):
    def test_normalize_abstract_title_removes_leading_marker(self) -> None:
        cleaned, reasons = normalize_abstract_title("•\tMapping neuro-molecular profiles")

        self.assertEqual(cleaned, "Mapping neuro-molecular profiles")
        self.assertIn("remove_leading_marker", reasons)

    def test_normalize_abstract_title_removes_wrapping_quotes(self) -> None:
        cleaned, reasons = normalize_abstract_title("“Mirror and mentalizing network disruptions”")

        self.assertEqual(cleaned, "Mirror and mentalizing network disruptions")
        self.assertIn("remove_wrapping_quotes", reasons)

    def test_build_title_modification_report_tracks_only_changed_titles(self) -> None:
        report = build_title_modification_report(
            {
                "abstracts": [
                    {"id": 1, "title": "• Example title"},
                    {"id": 2, "title": "Normal title"},
                ]
            },
            input_path=str(artifacts.PRIMARY_ABSTRACTS_PATH),
        )

        self.assertEqual(report["input"], str(artifacts.PRIMARY_ABSTRACTS_PATH))
        self.assertEqual(report["modified_count"], 1)
        self.assertEqual(
            report["modifications"],
            [
                {
                    "abstract_id": 1,
                    "original_title": "• Example title",
                    "cleaned_title": "Example title",
                    "reasons": ["remove_leading_marker"],
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
