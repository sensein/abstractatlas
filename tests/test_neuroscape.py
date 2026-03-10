import unittest

from ohbm2026.neuroscape import (
    DEFAULT_EMBEDDING_FIELDS,
    build_embedding_text,
    build_embedding_texts,
    embedding_variant_name,
    normalize_embedding_fields,
)


class NeuroScapeHelpersTest(unittest.TestCase):
    def test_build_embedding_text_uses_default_fields(self) -> None:
        abstract = {
            "id": 1,
            "title": "Example",
            "introduction_markdown": "Intro",
            "methods_markdown": "Methods",
            "results_markdown": "Results",
            "conclusion_markdown": "Conclusion",
            "discussion_markdown": "Discussion",
        }

        text = build_embedding_text(abstract)

        self.assertIn("Example", text)
        self.assertIn("Introduction:\nIntro", text)
        self.assertIn("Methods:\nMethods", text)
        self.assertIn("Results:\nResults", text)
        self.assertIn("Conclusion:\nConclusion", text)
        self.assertNotIn("Discussion:\nDiscussion", text)

    def test_build_embedding_text_supports_custom_fields(self) -> None:
        abstract = {
            "id": 1,
            "title": "Example",
            "introduction_markdown": "Intro",
            "discussion_markdown": "Discussion",
        }

        text = build_embedding_text(abstract, ["discussion"])

        self.assertEqual(text, "Discussion:\nDiscussion")

    def test_build_embedding_texts_preserves_order(self) -> None:
        abstracts = [
            {"id": 1, "introduction_markdown": "A"},
            {"id": 2, "introduction_markdown": "B"},
        ]

        texts = build_embedding_texts(abstracts, ["title", "introduction"], title_lookup={1: "First", 2: "Second"})

        self.assertEqual(texts[0], "First\n\nIntroduction:\nA")
        self.assertEqual(texts[1], "Second\n\nIntroduction:\nB")

    def test_normalize_embedding_fields_deduplicates(self) -> None:
        self.assertEqual(
            normalize_embedding_fields(["title", "methods", "title", "results"]),
            ["title", "methods", "results"],
        )

    def test_embedding_variant_name_defaults_to_stage1(self) -> None:
        self.assertEqual(embedding_variant_name(DEFAULT_EMBEDDING_FIELDS), "stage1")
        self.assertEqual(embedding_variant_name(["title", "methods"]), "title-methods")


if __name__ == "__main__":
    unittest.main()
