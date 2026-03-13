import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from ohbm2026.enrichment import (
    DEFAULT_CLAIM_ANALYSES_OUTPUT,
    DEFAULT_CLLM_OPENAI_MAX_COMPLETION_TOKENS,
    DEFAULT_CLLM_OPENAI_MODEL,
    DEFAULT_CLLM_OPENAI_REASONING_EFFORT,
    DEFAULT_OPENAI_MAX_IMAGES_PER_REQUEST,
    DEFAULT_OPENAI_MAX_REQUEST_BYTES,
    DEFAULT_OPENAI_REQUEST_TIMEOUT_SECONDS,
    EnrichmentError,
    analyze_figures,
    build_claim_extraction_parser,
    build_cllm_environment,
    build_claim_manuscript_markdown,
    build_enrich_parser,
    build_figure_analysis_parser,
    build_sections_markdown,
    enrich_database,
    extract_claims_from_cllm_module,
    extract_claims_with_cllm,
    filter_content_questions_markdown,
    html_to_markdown,
    image_to_data_url,
    is_content_question,
    load_claim_analysis_cache,
    load_json,
    parse_jsonish_content,
    question_to_section,
    resolve_openai_api_key,
    render_abstract_markdown,
)


class EnrichmentHelpersTest(unittest.TestCase):
    def test_build_enrich_parser_defaults_to_openai_cache(self) -> None:
        args = build_enrich_parser().parse_args([])

        self.assertEqual(args.input, "data/abstracts.json")
        self.assertEqual(args.image_analyses_input, "data/image_analyses_openai.json")
        self.assertEqual(args.claim_analyses_input, DEFAULT_CLAIM_ANALYSES_OUTPUT)
        self.assertEqual(args.enriched_output, "data/abstracts_enriched.json")

    def test_build_claim_extraction_parser_defaults_to_openai_provider(self) -> None:
        args = build_claim_extraction_parser().parse_args([])

        self.assertEqual(args.input, "data/abstracts.json")
        self.assertEqual(args.image_analyses_input, "data/image_analyses_openai.json")
        self.assertEqual(args.claim_analyses_output, DEFAULT_CLAIM_ANALYSES_OUTPUT)
        self.assertEqual(args.llm_provider, "openai")
        self.assertEqual(args.openai_model, DEFAULT_CLLM_OPENAI_MODEL)
        self.assertEqual(args.openai_max_completion_tokens, DEFAULT_CLLM_OPENAI_MAX_COMPLETION_TOKENS)
        self.assertEqual(args.openai_reasoning_effort, DEFAULT_CLLM_OPENAI_REASONING_EFFORT)

    def test_html_to_markdown_handles_lists_and_emphasis(self) -> None:
        html = "<p>Hello <strong>world</strong></p><ol><li>One</li><li>Two</li></ol>"
        markdown = html_to_markdown(html)
        self.assertIn("Hello **world**", markdown)
        self.assertIn("1. One", markdown)
        self.assertIn("2. Two", markdown)

    def test_question_to_section_maps_expected_questions(self) -> None:
        self.assertEqual(question_to_section("Introduction"), "introduction")
        self.assertEqual(question_to_section("Methods"), "methods")
        self.assertEqual(question_to_section("Results Figure (Optional)"), None)

    def test_build_sections_markdown_collects_core_sections(self) -> None:
        abstract = {
            "responses": [
                {"question_name": "Introduction", "value": "<p>Intro text</p>"},
                {"question_name": "Methods", "value": "<p>Methods text</p>"},
                {"question_name": "Random", "value": "<p>Other text</p>"},
            ]
        }
        sections, unmapped = build_sections_markdown(abstract)
        self.assertEqual(sections["introduction"], "Intro text")
        self.assertEqual(sections["methods"], "Methods text")
        self.assertEqual(unmapped, [{"question_name": "Random", "markdown": "Other text", "response_index": 2}])

    def test_render_abstract_markdown_includes_section_headings(self) -> None:
        rendered = render_abstract_markdown("Title", {"introduction": "Intro", "results": "Result"})
        self.assertIn("# Title", rendered)
        self.assertIn("## Introduction", rendered)
        self.assertIn("## Results", rendered)

    def test_build_claim_manuscript_markdown_excludes_references_and_includes_figures(self) -> None:
        manuscript = build_claim_manuscript_markdown(
            "Title",
            {
                "introduction": "Intro",
                "references": "Reference block",
                "acknowledgement": "Thanks to everyone",
                "results": "Main result",
            },
            [{"question_name": "Keywords", "markdown": '["MRI"]'}],
            [
                {
                    "question_name": "Results Figure (Optional)",
                    "analysis": {
                        "caption_guess": "Figure caption",
                        "rich_markdown": "Figure **analysis**",
                        "ocr_text": "axis labels",
                        "notes": "Extra note",
                    },
                }
            ],
        )

        self.assertIn("# Title", manuscript)
        self.assertIn("## Results", manuscript)
        self.assertIn("## Figure Analyses", manuscript)
        self.assertIn("Figure **analysis**", manuscript)
        self.assertIn("## Additional Content", manuscript)
        self.assertIn("### Keywords", manuscript)
        self.assertNotIn("## References", manuscript)
        self.assertNotIn("Reference block", manuscript)
        self.assertNotIn("## Acknowledgement", manuscript)
        self.assertNotIn("Thanks to everyone", manuscript)

    def test_parse_jsonish_content_accepts_fenced_json(self) -> None:
        content = "```json\n{\"caption_guess\": \"Example\", \"keywords\": []}\n```"
        parsed = parse_jsonish_content(content)
        self.assertEqual(parsed["caption_guess"], "Example")

    def test_is_content_question_filters_admin_prompts(self) -> None:
        self.assertTrue(is_content_question("Keywords"))
        self.assertTrue(is_content_question("Which processing packages did you use for your study?"))
        self.assertFalse(is_content_question("Submitter Approval"))
        self.assertFalse(is_content_question("5. Country"))

    def test_filter_content_questions_preserves_response_order(self) -> None:
        ordered = filter_content_questions_markdown(
            [
                {
                    "question_name": "Keywords",
                    "markdown": '["MRI"]',
                    "response_index": 0,
                },
                {
                    "question_name": "Primary Parent Category & Sub-Category",
                    "markdown": '["Cognition"]',
                    "response_index": 1,
                },
                {
                    "question_name": "For human MRI, what field strength scanner do you use?",
                    "markdown": "3T",
                    "response_index": 2,
                },
            ]
        )

        self.assertEqual(
            [item["question_name"] for item in ordered],
            [
                "Keywords",
                "Primary Parent Category & Sub-Category",
                "For human MRI, what field strength scanner do you use?",
            ],
        )

    def test_enrich_database_adds_markdown_fields_and_removes_authors(self) -> None:
        base = {
            "event_ids": [1],
            "abstracts": [
                {
                    "id": 1,
                    "title": "Example",
                    "accepted_for": "Poster",
                    "authors": [{"id": 10}],
                    "responses": [
                        {"question_name": "Introduction", "value": "<p>Hello</p>"},
                        {"question_name": "Methods", "value": "<p>Method text</p>"},
                        {"question_name": "Keywords", "value": "[\"A\", \"B\"]"},
                        {"question_name": "Submitter Approval", "value": "yes"},
                    ],
                    "local_assets": [],
                }
            ],
        }
        enriched = enrich_database(base)
        abstract = enriched["abstracts"][0]
        self.assertEqual(sorted(abstract.keys()), [
            "accepted_for",
            "additional_content_questions_markdown",
            "figure_analyses",
            "figure_keywords",
            "id",
            "introduction_markdown",
            "methods_markdown",
        ])
        self.assertEqual(abstract["introduction_markdown"], "Hello")
        self.assertEqual(abstract["methods_markdown"], "Method text")
        self.assertEqual(
            abstract["additional_content_questions_markdown"],
            [{"question_name": "Keywords", "markdown": "[\"A\", \"B\"]"}],
        )

    def test_enrich_database_adds_claim_extraction_when_present(self) -> None:
        base = {
            "event_ids": [1],
            "abstracts": [
                {
                    "id": 1,
                    "title": "Example",
                    "accepted_for": "Poster",
                    "responses": [],
                    "local_assets": [],
                }
            ],
        }
        claim_cache = {
            "analyses": {
                "1": {
                    "status": "ok",
                    "backend": "cllm",
                    "llm_provider": "openai",
                    "llm_model": "gpt-4o-2024-08-06",
                    "claim_count": 1,
                    "claims": [
                        {
                            "claim_id": "C1",
                            "claim": "Memory scores improved.",
                            "claim_type": "result",
                            "source": "Results",
                            "source_type": "section",
                            "evidence": "p < 0.05",
                            "evidence_type": "statistical",
                        }
                    ],
                    "metrics": {"processing_time_seconds": 1.2},
                    "updated_at": "2026-03-12T00:00:00+00:00",
                }
            }
        }

        enriched = enrich_database(base, claim_analysis_cache=claim_cache)

        self.assertEqual(enriched["abstracts"][0]["claim_extraction"]["claim_count"], 1)
        self.assertEqual(enriched["abstracts"][0]["claim_extraction"]["claims"][0]["claim_id"], "C1")

    def test_enrich_database_orders_methods_figures_before_results_figures(self) -> None:
        base = {
            "event_ids": [1],
            "abstracts": [
                {
                    "id": 1,
                    "title": "Example",
                    "accepted_for": "Poster",
                    "responses": [],
                    "local_assets": [
                        {
                            "local_path": "/tmp/results.png",
                            "source_question_name": "Results Figure (Optional)",
                        },
                        {
                            "local_path": "/tmp/methods.png",
                            "source_question_name": "Methods Figure (Optional)",
                        },
                    ],
                }
            ],
        }
        image_cache = {
            "analyses": {
                "/tmp/results.png": {
                    "question_name": "Results Figure (Optional)",
                    "analysis": {"caption_guess": "Results caption"},
                },
                "/tmp/methods.png": {
                    "question_name": "Methods Figure (Optional)",
                    "analysis": {"caption_guess": "Methods caption"},
                },
            }
        }

        enriched = enrich_database(base, image_analysis_cache=image_cache)

        self.assertEqual(
            [item["question_name"] for item in enriched["abstracts"][0]["figure_analyses"]],
            ["Methods Figure (Optional)", "Results Figure (Optional)"],
        )

    def test_build_figure_analysis_parser_defaults_to_raw_database(self) -> None:
        parser = build_figure_analysis_parser()
        args = parser.parse_args([])

        self.assertEqual(args.input, "data/abstracts.json")
        self.assertEqual(args.vision_backend, "ollama")
        self.assertEqual(args.save_every, 1)
        self.assertEqual(args.enrich_every, 25)
        self.assertEqual(args.openai_max_images_per_request, DEFAULT_OPENAI_MAX_IMAGES_PER_REQUEST)
        self.assertEqual(args.openai_max_request_bytes, DEFAULT_OPENAI_MAX_REQUEST_BYTES)
        self.assertEqual(args.openai_request_timeout_seconds, DEFAULT_OPENAI_REQUEST_TIMEOUT_SECONDS)

    def test_resolve_openai_api_key_reads_env_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")

            api_key = resolve_openai_api_key(env_path, "OPENAI_API_KEY")

        self.assertEqual(api_key, "test-key")

    def test_build_cllm_environment_uses_openai_key(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")

            environment = build_cllm_environment(
                env_file=env_path,
                llm_provider="openai",
                openai_api_var="OPENAI_API_KEY",
                openai_model="gpt-4o-2024-08-06",
                anthropic_api_var="ANTHROPIC_API_KEY",
                anthropic_model="claude-sonnet",
            )

        self.assertEqual(environment["LLM_PROVIDER"], "openai")
        self.assertEqual(environment["OPENAI_API_KEY"], "test-key")
        self.assertEqual(environment["OPENAI_MODEL"], "gpt-4o-2024-08-06")

    def test_extract_claims_from_cllm_module_passes_openai_reasoning_effort_when_provided(self) -> None:
        parsed_response = mock.Mock(
            claims=[
                mock.Mock(
                    claim="Claim",
                    claim_type="EXPLICIT",
                    source="Source",
                    source_type=["TEXT"],
                    evidence="Evidence",
                    evidence_type=["DATA"],
                )
            ]
        )
        completion = mock.Mock(
            choices=[mock.Mock(message=mock.Mock(parsed=parsed_response, refusal=None))],
            usage=mock.Mock(prompt_tokens=10, completion_tokens=20),
        )
        parse_mock = mock.Mock(return_value=completion)
        fake_client = mock.Mock()
        fake_client.beta.chat.completions.parse = parse_mock
        fake_verification = mock.Mock()
        fake_verification.STAGE1_PROMPT_TEMPLATE = "$MANUSCRIPT_TEXT"
        fake_verification.MAX_PROMPT_TOKENS = 100000
        fake_verification.LLMClaimsResponseV3 = object()
        fake_verification.config.openai_model = "gpt-4o-2024-08-06"
        fake_verification.get_llm_client.return_value = fake_client

        claims, metrics = extract_claims_from_cllm_module(
            manuscript_text="Short abstract",
            cllm_verification=fake_verification,
            llm_provider="openai",
            openai_max_completion_tokens=4096,
            openai_reasoning_effort="minimal",
        )

        self.assertEqual(claims[0]["claim_id"], "C1")
        self.assertEqual(metrics["model"], "gpt-4o-2024-08-06")
        parse_mock.assert_called_once()
        self.assertEqual(parse_mock.call_args.kwargs["reasoning_effort"], "minimal")
        self.assertEqual(parse_mock.call_args.kwargs["max_completion_tokens"], 4096)

    def test_image_to_data_url_normalizes_jpg_to_jpeg(self) -> None:
        with TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "figure.jpg"
            image_path.write_bytes(b"jpeg-bytes")

            data_url = image_to_data_url(image_path)

        self.assertTrue(data_url.startswith("data:image/jpeg;base64,"))

    def test_extract_claims_with_cllm_writes_cache_with_openai_provider(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            env_path = root / ".env"
            cache_path = root / "claim_analyses.json"
            env_path.write_text("OPENAI_API_KEY=test-key\n", encoding="utf-8")
            base_database = {
                "event_ids": [1],
                "abstracts": [
                    {
                        "id": 1,
                        "title": "Example",
                        "accepted_for": "Poster",
                        "responses": [
                            {"question_name": "Introduction", "value": "<p>Hello</p>"},
                            {"question_name": "Results", "value": "<p>Result text</p>"},
                            {"question_name": "References", "value": "<p>Reference text</p>"},
                            {"question_name": "Acknowledgement", "value": "<p>Thanks</p>"},
                        ],
                        "local_assets": [{"local_path": str(root / "figure.png")}],
                    }
                ],
            }
            image_analysis_cache = {
                "analyses": {
                    str(root / "figure.png"): {
                        "question_name": "Results Figure (Optional)",
                        "analysis": {
                            "caption_guess": "Figure caption",
                            "rich_markdown": "Figure notes",
                            "ocr_text": "axis labels",
                            "notes": "extra note",
                        },
                    }
                }
            }

            fake_module = mock.Mock()
            with (
                mock.patch("ohbm2026.enrichment.load_cllm_verification_module", return_value=fake_module),
                mock.patch(
                    "ohbm2026.enrichment.extract_claims_from_cllm_module",
                    return_value=(
                        [
                            {
                                "claim_id": "C1",
                                "claim": "Result text",
                                "claim_type": "result",
                                "source": "Results",
                                "source_type": ["TEXT"],
                                "evidence": "Result text",
                                "evidence_type": ["DATA"],
                            }
                        ],
                        {"model": "gpt-4o-2024-08-06", "processing_time_seconds": 1.2},
                    ),
                ) as extract_mock,
            ):
                cache = extract_claims_with_cllm(
                    base_database=base_database,
                    cache_path=cache_path,
                    image_analysis_cache=image_analysis_cache,
                    env_file=env_path,
                    llm_provider="openai",
                    save_every=1,
                )

            self.assertEqual(cache["completed_count"], 1)
            self.assertTrue(cache_path.exists())
            saved_cache = load_claim_analysis_cache(cache_path)
            entry = saved_cache["analyses"]["1"]
            self.assertEqual(entry["status"], "ok")
            self.assertEqual(entry["llm_provider"], "openai")
            self.assertEqual(entry["claims"][0]["claim_id"], "C1")
            self.assertEqual(entry["llm_model"], "gpt-4o-2024-08-06")
            extract_mock.assert_called_once()
            manuscript_text = extract_mock.call_args.kwargs["manuscript_text"]
            self.assertIn("## Figure Analyses", manuscript_text)
            self.assertIn("Figure notes", manuscript_text)
            self.assertNotIn("Reference text", manuscript_text)
            self.assertNotIn("Thanks", manuscript_text)

    def test_analyze_figures_openai_writes_incremental_cache_and_enriched_output(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "figure.png"
            image_path.write_bytes(b"png-bytes")
            cache_path = root / "image_analyses_openai.json"
            enriched_output = root / "abstracts_enriched_openai.json"
            base_database = {
                "event_ids": [1],
                "abstracts": [
                    {
                        "id": 1,
                        "title": "Example",
                        "accepted_for": "Poster",
                        "responses": [
                            {"question_name": "Introduction", "value": "<p>Hello</p>"},
                            {"question_name": "Methods", "value": "<p>Method text</p>"},
                        ],
                        "local_assets": [
                            {
                                "local_path": str(image_path),
                                "source_question_name": "Methods Figure (Optional)",
                            }
                        ],
                    }
                ],
            }

            with mock.patch(
                "ohbm2026.enrichment.openai_chat_multimodal_batch",
                return_value={
                    str(image_path): {
                        "caption_guess": "Figure caption",
                        "rich_markdown": "Figure notes",
                        "ocr_text": "OCR",
                        "keywords": ["MRI", "Flowchart"],
                        "notes": "Notes",
                    }
                },
            ) as openai_chat:
                cache = analyze_figures(
                    base_database,
                    cache_path,
                    backend="openai",
                    model="gpt-4.1-mini",
                    openai_api_key="test-key",
                    save_every=1,
                    enriched_output_path=enriched_output,
                    enrich_every=1,
                )

            self.assertEqual(len(cache["analyses"]), 1)
            self.assertTrue(cache_path.exists())
            self.assertTrue(enriched_output.exists())
            saved_cache = load_json(cache_path)
            saved_enriched = load_json(enriched_output)
            analysis_entry = saved_cache["analyses"][str(image_path)]
            self.assertEqual(analysis_entry["backend"], "openai")
            self.assertEqual(analysis_entry["model"], "gpt-4.1-mini")
            self.assertEqual(saved_enriched["abstracts"][0]["figure_keywords"], ["MRI", "Flowchart"])
            self.assertEqual(saved_enriched["abstracts"][0]["figure_analyses"][0]["analysis"]["caption_guess"], "Figure caption")
            openai_chat.assert_called_once()

    def test_analyze_figures_continues_after_openai_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_one = root / "figure1.png"
            image_two = root / "figure2.png"
            image_one.write_bytes(b"png-bytes-1")
            image_two.write_bytes(b"png-bytes-2")
            cache_path = root / "image_analyses_openai.json"
            base_database = {
                "event_ids": [1],
                "abstracts": [
                    {
                        "id": 1,
                        "title": "Example",
                        "accepted_for": "Poster",
                        "responses": [],
                        "local_assets": [
                            {
                                "local_path": str(image_one),
                                "source_question_name": "Methods Figure (Optional)",
                            },
                            {
                                "local_path": str(image_two),
                                "source_question_name": "Results Figure (Optional)",
                            },
                        ],
                    }
                ],
            }

            with mock.patch(
                "ohbm2026.enrichment.openai_chat_multimodal_batch",
                side_effect=[
                    EnrichmentError("batch failed"),
                    EnrichmentError("bad json"),
                    {
                        str(image_two): {
                            "caption_guess": "Figure caption",
                            "rich_markdown": "Figure notes",
                            "ocr_text": "OCR",
                            "keywords": ["MRI"],
                            "notes": "Notes",
                        }
                    },
                ],
            ):
                cache = analyze_figures(
                    base_database,
                    cache_path,
                    backend="openai",
                    model="gpt-4.1-mini",
                    openai_api_key="test-key",
                    save_every=1,
                )

            self.assertEqual(cache["processed_count"], 2)
            self.assertEqual(cache["error_count"], 1)
            self.assertIn("error", cache["analyses"][str(image_one)])
            self.assertEqual(cache["analyses"][str(image_two)]["analysis"]["caption_guess"], "Figure caption")

    def test_analyze_figures_openai_batches_multiple_images_per_request(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_one = root / "figure1.png"
            image_two = root / "figure2.png"
            image_one.write_bytes(b"png-bytes-1")
            image_two.write_bytes(b"png-bytes-2")
            cache_path = root / "image_analyses_openai.json"
            base_database = {
                "event_ids": [1],
                "abstracts": [
                    {
                        "id": 1,
                        "title": "Example",
                        "accepted_for": "Poster",
                        "responses": [],
                        "local_assets": [
                            {
                                "local_path": str(image_one),
                                "source_question_name": "Methods Figure (Optional)",
                            },
                            {
                                "local_path": str(image_two),
                                "source_question_name": "Results Figure (Optional)",
                            },
                        ],
                    }
                ],
            }

            with mock.patch(
                "ohbm2026.enrichment.openai_chat_multimodal_batch",
                return_value={
                    str(image_one): {
                        "caption_guess": "Figure one",
                        "rich_markdown": "Figure notes one",
                        "ocr_text": "",
                        "keywords": ["MRI"],
                        "notes": "",
                    },
                    str(image_two): {
                        "caption_guess": "Figure two",
                        "rich_markdown": "Figure notes two",
                        "ocr_text": "",
                        "keywords": ["Connectivity"],
                        "notes": "",
                    },
                },
            ) as openai_batch:
                cache = analyze_figures(
                    base_database,
                    cache_path,
                    backend="openai",
                    model="gpt-4.1-mini",
                    openai_api_key="test-key",
                    openai_max_images_per_request=8,
                    save_every=2,
                )

            self.assertEqual(cache["processed_count"], 2)
            self.assertEqual(cache["error_count"], 0)
            self.assertEqual(cache["analyses"][str(image_one)]["analysis"]["caption_guess"], "Figure one")
            self.assertEqual(cache["analyses"][str(image_two)]["analysis"]["caption_guess"], "Figure two")
            openai_batch.assert_called_once()
            batch_assets = openai_batch.call_args.args[2]
            self.assertEqual([asset["cache_key"] for asset in batch_assets], [str(image_one), str(image_two)])


if __name__ == "__main__":
    unittest.main()
