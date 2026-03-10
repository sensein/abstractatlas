import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from ohbm2026.openalex import (
    add_query_parameter,
    build_reference_key,
    collect_reference_cache,
    extract_dois,
    extract_pmid,
    extract_reference_entries,
    get_openalex_api_key,
    guess_reference_title,
    normalize_doi,
    normalize_openalex_work,
    openalex_request,
    title_similarity,
)


class OpenAlexHelpersTest(unittest.TestCase):
    def tearDown(self) -> None:
        get_openalex_api_key.cache_clear()

    def test_extract_reference_entries_splits_html_list(self) -> None:
        html = "<ol><li>Smith A. Interesting title. Journal. 2024.</li><li>Jones B. Another title. Journal. 2023.</li></ol>"

        entries = extract_reference_entries(html)

        self.assertEqual(
            entries,
            [
                "Smith A. Interesting title. Journal. 2024.",
                "Jones B. Another title. Journal. 2023.",
            ],
        )

    def test_normalize_doi_strips_prefix_and_punctuation(self) -> None:
        self.assertEqual(
            normalize_doi("https://doi.org/10.1038/s42256-023-00702-9."),
            "10.1038/s42256-023-00702-9",
        )
        self.assertEqual(
            normalize_doi("10.1097/wco.0000000000000829.PMID:12345678"),
            "10.1097/wco.0000000000000829",
        )

    def test_extract_dois_and_pmid(self) -> None:
        reference = "D'Sa K. Prediction. Nature. 2023. doi:https://doi.org/10.1038/s42256-023-00702-9 PMID: 12345678"

        self.assertEqual(extract_dois(reference), ["10.1038/s42256-023-00702-9"])
        self.assertEqual(extract_pmid(reference), "12345678")

    def test_guess_reference_title_prefers_second_sentence(self) -> None:
        reference = "Ashina M, Terwindt GM. Migraine: disease characterisation, biomarkers, and precision medicine. The Lancet. 2021;397(10283):1496-1504."

        self.assertEqual(
            guess_reference_title(reference),
            "Migraine: disease characterisation, biomarkers, and precision medicine",
        )

    def test_build_reference_key_prefers_doi_then_pmid(self) -> None:
        self.assertEqual(build_reference_key("x", doi="10.1/abc", pmid="123"), "doi:10.1/abc")
        self.assertEqual(build_reference_key("x", doi=None, pmid="123"), "pmid:123")
        self.assertTrue(build_reference_key("x").startswith("text:"))

    def test_title_similarity_recognizes_close_titles(self) -> None:
        score = title_similarity(
            "Migraine disease characterisation biomarkers and precision medicine",
            "Migraine: disease characterisation, biomarkers, and precision medicine",
        )
        self.assertGreater(score, 0.9)

    def test_normalize_openalex_work_extracts_needed_fields(self) -> None:
        work = {
            "id": "https://openalex.org/W123",
            "doi": "https://doi.org/10.1000/test",
            "ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/12345678/"},
            "display_name": "Example review",
            "publication_year": 2024,
            "publication_date": "2024-01-01",
            "primary_location": {"source": {"display_name": "NeuroImage"}},
            "type": "review",
            "type_crossref": "review-article",
            "cited_by_count": 42,
            "referenced_works": ["https://openalex.org/W1"],
            "referenced_works_count": 1,
        }

        normalized = normalize_openalex_work(work)

        self.assertEqual(normalized["openalex_id"], "https://openalex.org/W123")
        self.assertEqual(normalized["doi"], "10.1000/test")
        self.assertEqual(normalized["pmid"], "12345678")
        self.assertTrue(normalized["is_review"])
        self.assertEqual(normalized["journal"], "NeuroImage")

    def test_add_query_parameter_preserves_existing_query(self) -> None:
        url = add_query_parameter("https://api.openalex.org/works?per-page=5", "api_key", "secret")

        self.assertEqual(url, "https://api.openalex.org/works?per-page=5&api_key=secret")

    @patch.dict("os.environ", {"OPENALEX_API": "secret-key"}, clear=False)
    def test_openalex_request_appends_api_key_from_environment(self) -> None:
        class DummyResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self) -> bytes:
                return b'{"results": []}'

        captured: dict[str, str] = {}

        def fake_urlopen(request):
            captured["url"] = request.full_url
            return DummyResponse()

        with patch("ohbm2026.openalex.urlopen_with_retries", side_effect=fake_urlopen):
            parsed = openalex_request("https://api.openalex.org/works?per-page=1")

        self.assertEqual(parsed, {"results": []})
        self.assertEqual(
            captured["url"],
            "https://api.openalex.org/works?per-page=1&api_key=secret-key",
        )

    def test_collect_reference_cache_recomputes_counts_from_input(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "reference_metadata.json"
            output_path.write_text(
                """
                {
                  "references": [
                    {
                      "reference_key": "doi:10.1000/test",
                      "raw_text": "Smith A. Example title. doi:10.1000/test",
                      "doi": "10.1000/test",
                      "matched": true,
                      "match_method": "doi",
                      "openalex": {"openalex_id": "https://openalex.org/W1"},
                      "source_count": 7,
                      "raw_text_examples": ["old"],
                      "doi_lookup_completed": true,
                      "pmid_lookup_completed": true,
                      "title_lookup_completed": false
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )
            database = {
                "abstracts": [
                    {
                        "id": 1,
                        "responses": [
                            {
                                "question_name": "References/Citations",
                                "value": "<ol><li>Smith A. Example title. doi:10.1000/test</li></ol>",
                            }
                        ],
                    }
                ]
            }

            _, reference_cache = collect_reference_cache(database, output_path)

        cached = reference_cache["doi:10.1000/test"]
        self.assertTrue(cached["matched"])
        self.assertEqual(cached["source_count"], 1)
        self.assertEqual(cached["raw_text_examples"], ["Smith A. Example title. doi:10.1000/test"])


if __name__ == "__main__":
    unittest.main()
