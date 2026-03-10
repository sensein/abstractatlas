import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from ohbm2026.neuroscape import (
    DEFAULT_EMBEDDING_FIELDS,
    align_semantic_records,
    build_visualization_records,
    build_knn_graph,
    build_semantic_analysis_parser,
    build_umap_parser,
    build_embedding_text,
    build_embedding_texts,
    extract_raw_keywords,
    detect_semantic_communities,
    detect_stage2_communities,
    embedding_variant_name,
    load_annotation_lookup,
    load_stage1_bundle,
    normalize_embedding_fields,
    normalize_hidden_dimensions,
    parse_string_list_value,
    semantic_analysis_main,
    split_stage2_matrix,
    summarize_semantic_clusters,
    summarize_stage2_clusters,
    umap_main,
    write_stage2_bundle,
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

    def test_normalize_hidden_dimensions_requires_three_values(self) -> None:
        self.assertEqual(normalize_hidden_dimensions([12, 8, 4]), (12, 8, 4))
        with self.assertRaises(Exception):
            normalize_hidden_dimensions([12, 8])

    def test_parse_string_list_value_handles_json_list(self) -> None:
        self.assertEqual(parse_string_list_value('["A", "B"]'), ["A", "B"])
        self.assertEqual(parse_string_list_value("Single"), ["Single"])

    def test_extract_raw_keywords_reads_keywords_response(self) -> None:
        abstract = {
            "responses": [
                {"question_name": "Keywords", "value": '["MRI", "Connectivity"]'},
            ]
        }

        self.assertEqual(extract_raw_keywords(abstract), ["MRI", "Connectivity"])

    def test_split_stage2_matrix_preserves_row_count(self) -> None:
        import numpy as np

        matrix = np.arange(200, dtype=np.float32).reshape(20, 10)
        train_matrix, validation_matrix = split_stage2_matrix(matrix, validation_size=0.2, seed=7)

        self.assertEqual(train_matrix.shape[0] + validation_matrix.shape[0], 20)
        self.assertEqual(validation_matrix.shape[0], 4)

    def test_write_stage2_bundle_uses_stage1_metadata(self) -> None:
        import json
        import numpy as np
        import torch

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "stage2"
            stage1_bundle = {
                "ids": [1, 2],
                "metadata": [{"id": 1, "accepted_for": "Poster"}, {"id": 2, "accepted_for": "Oral"}],
                "source_metadata": {
                    "embedding_name": "minilm_stage1",
                    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                    "embedding_fields": ["title", "methods"],
                },
            }
            projected_matrix = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
            model = torch.nn.Linear(2, 2)

            write_stage2_bundle(
                output_dir,
                stage1_bundle,
                projected_matrix,
                model,
                {"device": "cpu", "epochs": 2, "batch_size": 4, "best_validation_loss": 0.12},
                hidden_dimensions=(8, 4, 2),
                output_dimension=2,
                dropout=0.1,
            )

            metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["embedding_name"], "stage2")
            self.assertEqual(metadata["source_embedding_name"], "minilm_stage1")
            self.assertEqual(metadata["count"], 2)
            self.assertTrue((output_dir / "vectors.npy").exists())
            self.assertTrue((output_dir / "neighbors.json").exists())
            self.assertTrue((output_dir / "domain_embedding_model_best.pth").exists())

    def test_load_stage1_bundle_reads_saved_files(self) -> None:
        import json
        import numpy as np

        with TemporaryDirectory() as temp_dir:
            bundle_dir = Path(temp_dir)
            np.save(bundle_dir / "vectors.npy", np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32))
            (bundle_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "ids": [10, 11],
                        "metadata": [{"id": 10}, {"id": 11}],
                        "embedding_name": "minilm_stage1",
                    }
                ),
                encoding="utf-8",
            )

            bundle = load_stage1_bundle(bundle_dir)

            self.assertEqual(bundle["ids"], [10, 11])
            self.assertEqual(tuple(bundle["matrix"].shape), (2, 2))

    def test_build_knn_graph_adds_weighted_edges(self) -> None:
        import numpy as np

        ids = [1, 2, 3, 4]
        matrix = np.asarray(
            [
                [1.0, 0.0],
                [0.95, 0.05],
                [0.0, 1.0],
                [0.05, 0.95],
            ],
            dtype=np.float32,
        )

        graph = build_knn_graph(ids, matrix, num_neighbors=2)

        self.assertEqual(graph.number_of_nodes(), 4)
        self.assertGreater(graph.number_of_edges(), 0)
        self.assertIn("weight", next(iter(graph.edges(data=True)))[2])

    def test_detect_stage2_communities_assigns_each_node(self) -> None:
        import networkx as nx

        graph = nx.Graph()
        graph.add_edge(1, 2, weight=1.0)
        graph.add_edge(3, 4, weight=1.0)
        graph.add_edge(2, 3, weight=0.01)

        result = detect_stage2_communities(graph, num_resolution_parameter=4, max_resolution_parameter=1.0)

        self.assertEqual(set(result["assignments"]), {1, 2, 3, 4})
        self.assertGreaterEqual(len(result["communities"]), 1)
        self.assertGreaterEqual(len(result["history"]), 1)

    def test_detect_semantic_communities_assigns_each_node(self) -> None:
        import networkx as nx

        graph = nx.Graph()
        graph.add_edge(10, 11, weight=1.0)
        graph.add_edge(12, 13, weight=1.0)
        graph.add_edge(11, 12, weight=0.01)

        result = detect_semantic_communities(graph, num_resolution_parameter=4, max_resolution_parameter=1.0)

        self.assertEqual(set(result["assignments"]), {10, 11, 12, 13})
        self.assertGreaterEqual(len(result["communities"]), 1)

    def test_summarize_stage2_clusters_returns_representatives(self) -> None:
        import numpy as np

        ids = [1, 2, 3, 4]
        matrix = np.asarray(
            [
                [1.0, 0.0],
                [0.9, 0.1],
                [0.0, 1.0],
                [0.1, 0.9],
            ],
            dtype=np.float32,
        )
        records = [
            {"id": 1, "title": "Memory encoding", "accepted_for": "Poster", "cluster_document": "memory hippocampus"},
            {"id": 2, "title": "Memory retrieval", "accepted_for": "Poster", "cluster_document": "memory recall"},
            {"id": 3, "title": "Visual cortex", "accepted_for": "Oral", "cluster_document": "vision cortex"},
            {"id": 4, "title": "Visual attention", "accepted_for": "Oral", "cluster_document": "vision attention"},
        ]
        assignments = {1: 0, 2: 0, 3: 1, 4: 1}

        summaries = summarize_stage2_clusters(ids, matrix, records, assignments, max_keywords=3, max_representatives=2)

        self.assertEqual(len(summaries), 2)
        self.assertEqual(summaries[0]["size"], 2)
        self.assertEqual(len(summaries[0]["representative_abstracts"]), 2)
        self.assertIn("accepted_for_counts", summaries[0])

    def test_summarize_semantic_clusters_returns_representatives(self) -> None:
        import numpy as np

        ids = [1, 2, 3, 4]
        matrix = np.asarray(
            [
                [1.0, 0.0],
                [0.9, 0.1],
                [0.0, 1.0],
                [0.1, 0.9],
            ],
            dtype=np.float32,
        )
        records = [
            {"id": 1, "title": "Memory encoding", "accepted_for": "Poster", "cluster_document": "memory hippocampus"},
            {"id": 2, "title": "Memory retrieval", "accepted_for": "Poster", "cluster_document": "memory recall"},
            {"id": 3, "title": "Visual cortex", "accepted_for": "Oral", "cluster_document": "vision cortex"},
            {"id": 4, "title": "Visual attention", "accepted_for": "Oral", "cluster_document": "vision attention"},
        ]
        assignments = {1: 0, 2: 0, 3: 1, 4: 1}

        summaries = summarize_semantic_clusters(ids, matrix, records, assignments, max_keywords=3, max_representatives=2)

        self.assertEqual(len(summaries), 2)
        self.assertEqual(summaries[0]["size"], 2)
        self.assertEqual(len(summaries[0]["representative_abstracts"]), 2)

    def test_align_semantic_records_uses_title_lookup(self) -> None:
        records = align_semantic_records(
            [1],
            {1: {"id": 1, "accepted_for": "Poster", "introduction_markdown": "Intro"}},
            title_lookup={1: "Example title"},
        )

        self.assertEqual(records[0]["title"], "Example title")
        self.assertIn("Introduction:\nIntro", records[0]["cluster_document"])

    def test_load_annotation_lookup_merges_raw_and_figure_keywords(self) -> None:
        import json

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_path = root / "abstracts.json"
            enriched_path = root / "abstracts_enriched.json"
            raw_path.write_text(
                json.dumps(
                    {
                        "abstracts": [
                            {
                                "id": 1,
                                "title": "Example",
                                "accepted_for": "Poster",
                                "responses": [{"question_name": "Keywords", "value": '["MRI"]'}],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            enriched_path.write_text(
                json.dumps({"abstracts": [{"id": 1, "figure_keywords": ["cortex", "MRI"]}]}),
                encoding="utf-8",
            )

            lookup = load_annotation_lookup(raw_path, enriched_path)

        self.assertEqual(lookup[1]["title"], "Example")
        self.assertEqual(lookup[1]["keywords"], ["MRI", "cortex"])

    def test_build_visualization_records_preserves_id_order(self) -> None:
        records = build_visualization_records(
            [2, 1],
            {
                1: {"title": "One", "accepted_for": "Poster", "keywords": ["a"]},
                2: {"title": "Two", "accepted_for": "Oral", "keywords": ["b"]},
            },
        )

        self.assertEqual([record["id"] for record in records], [2, 1])
        self.assertEqual(records[0]["title"], "Two")

    def test_build_semantic_analysis_parser_defaults_to_minilm_bundle(self) -> None:
        parser = build_semantic_analysis_parser()
        args = parser.parse_args([])

        self.assertEqual(args.embeddings_dir, "data/embeddings/minilm_stage1")
        self.assertEqual(args.output_dir, "data/embeddings/minilm_stage1/semantic_analysis")

    def test_build_umap_parser_defaults_to_minilm_bundle(self) -> None:
        parser = build_umap_parser()
        args = parser.parse_args([])

        self.assertEqual(args.embeddings_dir, "data/embeddings/minilm_stage1")
        self.assertEqual(args.output_html, "data/embeddings/minilm_stage1/umap_2d.html")
        self.assertEqual(args.output_json, "data/embeddings/minilm_stage1/umap_2d.json")

    def test_semantic_analysis_main_writes_outputs(self) -> None:
        import json
        import numpy as np

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            embeddings_dir = root / "bundle"
            output_dir = root / "analysis"
            input_path = root / "abstracts_enriched.json"
            title_input = root / "abstracts.json"
            embeddings_dir.mkdir(parents=True, exist_ok=True)
            np.save(
                embeddings_dir / "vectors.npy",
                np.asarray(
                    [
                        [1.0, 0.0],
                        [0.95, 0.05],
                        [0.0, 1.0],
                        [0.05, 0.95],
                    ],
                    dtype=np.float32,
                ),
            )
            (embeddings_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "ids": [1, 2, 3, 4],
                        "metadata": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}],
                        "embedding_name": "minilm_stage1",
                    }
                ),
                encoding="utf-8",
            )
            input_path.write_text(
                json.dumps(
                    {
                        "abstracts": [
                            {"id": 1, "accepted_for": "Poster", "introduction_markdown": "memory intro"},
                            {"id": 2, "accepted_for": "Poster", "introduction_markdown": "memory retrieval"},
                            {"id": 3, "accepted_for": "Oral", "introduction_markdown": "visual cortex"},
                            {"id": 4, "accepted_for": "Oral", "introduction_markdown": "visual attention"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            title_input.write_text(
                json.dumps(
                    {
                        "abstracts": [
                            {"id": 1, "title": "Memory encoding"},
                            {"id": 2, "title": "Memory retrieval"},
                            {"id": 3, "title": "Visual cortex"},
                            {"id": 4, "title": "Visual attention"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch("builtins.print") as fake_print:
                result = semantic_analysis_main(
                    [
                        "--embeddings-dir",
                        str(embeddings_dir),
                        "--input",
                        str(input_path),
                        "--title-input",
                        str(title_input),
                        "--output-dir",
                        str(output_dir),
                        "--num-neighbors",
                        "2",
                        "--num-resolution-parameter",
                        "4",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertTrue((output_dir / "article_similarity.graphml").exists())
            self.assertTrue((output_dir / "community_detection.json").exists())
            self.assertTrue((output_dir / "cluster_assignments.json").exists())
            self.assertTrue((output_dir / "cluster_summaries.json").exists())
            fake_print.assert_called_once()

    def test_umap_main_writes_outputs(self) -> None:
        import json
        import numpy as np

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            embeddings_dir = root / "bundle"
            raw_path = root / "abstracts.json"
            enriched_path = root / "abstracts_enriched.json"
            output_html = root / "umap.html"
            output_json = root / "umap.json"
            embeddings_dir.mkdir(parents=True, exist_ok=True)
            np.save(
                embeddings_dir / "vectors.npy",
                np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
            )
            (embeddings_dir / "metadata.json").write_text(
                json.dumps(
                    {
                        "ids": [1, 2],
                        "metadata": [{"id": 1}, {"id": 2}],
                        "embedding_name": "minilm_stage1",
                    }
                ),
                encoding="utf-8",
            )
            raw_path.write_text(
                json.dumps(
                    {
                        "abstracts": [
                            {
                                "id": 1,
                                "title": "One",
                                "accepted_for": "Poster",
                                "responses": [{"question_name": "Keywords", "value": '["MRI"]'}],
                            },
                            {
                                "id": 2,
                                "title": "Two",
                                "accepted_for": "Oral",
                                "responses": [{"question_name": "Keywords", "value": '["EEG"]'}],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            enriched_path.write_text(
                json.dumps({"abstracts": [{"id": 1, "figure_keywords": ["cortex"]}, {"id": 2, "figure_keywords": []}]}),
                encoding="utf-8",
            )

            with mock.patch("ohbm2026.neuroscape.compute_umap_projection", return_value=np.asarray([[0.1, 0.2], [0.3, 0.4]])), \
                 mock.patch("ohbm2026.neuroscape.write_umap_outputs") as write_umap_outputs_mock, \
                 mock.patch("builtins.print") as fake_print:
                result = umap_main(
                    [
                        "--embeddings-dir",
                        str(embeddings_dir),
                        "--raw-input",
                        str(raw_path),
                        "--enriched-input",
                        str(enriched_path),
                        "--output-html",
                        str(output_html),
                        "--output-json",
                        str(output_json),
                    ]
                )

            self.assertEqual(result, 0)
            write_umap_outputs_mock.assert_called_once()
            args = write_umap_outputs_mock.call_args.args
            self.assertEqual(args[0], output_html)
            self.assertEqual(args[1], output_json)
            self.assertEqual(args[3][0]["keywords"], ["MRI", "cortex"])
            fake_print.assert_called_once()


if __name__ == "__main__":
    unittest.main()
