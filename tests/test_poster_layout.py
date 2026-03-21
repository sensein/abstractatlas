import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from ohbm2026 import poster_layout


def _response(parent: str, subcategory: str) -> dict[str, str]:
    return {
        "question_name": "Primary Parent Category & Sub-Category",
        "value": json.dumps([parent, subcategory]),
    }


def _abstract(
    abstract_id: int,
    accepted_for: str,
    title: str,
    parent: str,
    subcategory: str,
    first_author_id: int,
) -> dict[str, object]:
    return {
        "id": abstract_id,
        "accepted_for": accepted_for,
        "title": title,
        "authors": [{"author_order": 0, "id": first_author_id}],
        "responses": [_response(parent, subcategory)],
    }


class PosterLayoutTest(unittest.TestCase):
    def _build_fixture(self, root: Path) -> tuple[Path, Path]:
        abstracts = [
            _abstract(1, "Poster", "A1 poster 1", "Systems", "Memory", 100),
            _abstract(2, "Poster", "A1 poster 2", "Systems", "Memory", 101),
            _abstract(3, "Poster", "A2 poster 1", "Systems", "Language", 100),
            _abstract(4, "Poster", "A2 poster 2", "Systems", "Language", 102),
            _abstract(5, "Poster", "B1 poster 1", "Methods", "Modeling", 103),
            _abstract(6, "Poster", "B1 poster 2", "Methods", "Modeling", 104),
            _abstract(7, "Poster", "B2 poster 1", "Methods", "Connectivity", 105),
            _abstract(8, "Poster", "B2 poster 2", "Methods", "Connectivity", 106),
            _abstract(9, "Oral", "A oral", "Systems", "Memory", 200),
            _abstract(10, "Oral", "B oral", "Methods", "Modeling", 201),
        ]
        raw_input = root / "abstracts.json"
        raw_input.write_text(json.dumps({"abstracts": abstracts}, indent=2), encoding="utf-8")

        embeddings_dir = root / "embeddings"
        embeddings_dir.mkdir(parents=True, exist_ok=True)
        matrix = np.asarray(
            [
                [1.0, 0.0, 0.0],
                [0.98, 0.02, 0.0],
                [0.9, 0.1, 0.0],
                [0.88, 0.12, 0.0],
                [0.0, 1.0, 0.0],
                [0.02, 0.98, 0.0],
                [0.0, 0.9, 0.1],
                [0.0, 0.88, 0.12],
                [0.96, 0.04, 0.0],
                [0.04, 0.96, 0.0],
            ],
            dtype=np.float32,
        )
        np.save(embeddings_dir / "vectors.npy", matrix)
        (embeddings_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "embedding_name": "minilm_claims",
                    "embedding_fields": ["claims"],
                    "ids": list(range(1, 11)),
                    "metadata": [{"id": abstract_id, "accepted_for": "Poster", "title": str(abstract_id)} for abstract_id in range(1, 11)],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return raw_input, embeddings_dir

    def test_load_layout_inputs_extracts_posters_and_orals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_input, embeddings_dir = self._build_fixture(Path(tmpdir))

            inputs = poster_layout.load_layout_inputs(raw_input, embeddings_dir)

        self.assertEqual(len(inputs.records), 10)
        self.assertEqual(len(inputs.poster_records), 8)
        self.assertEqual(len(inputs.oral_records), 2)
        self.assertEqual(inputs.poster_records[0].primary_parent_category, "Systems")
        self.assertEqual(inputs.poster_records[0].primary_subcategory, "Memory")

    def test_optimize_main_writes_balanced_conflict_free_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_input, embeddings_dir = self._build_fixture(root)
            output_dir = root / "poster_layout"

            result = poster_layout.optimize_main(
                [
                    "--raw-input",
                    str(raw_input),
                    "--embeddings-dir",
                    str(embeddings_dir),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            self.assertEqual(result, 0)
            proposal = json.loads((output_dir / "proposal.json").read_text(encoding="utf-8"))

        assignments = proposal["assignments"]
        self.assertEqual(len(assignments), 10)
        self.assertEqual([item["poster_number"] for item in assignments], list(range(1, 11)))
        session_counts = {
            session_id: sum(1 for item in assignments if item["standby_session"] == session_id)
            for session_id in poster_layout.SESSION_IDS
        }
        self.assertEqual(session_counts, {1: 3, 2: 3, 3: 2, 4: 2})
        assignments_by_id = {item["abstract_id"]: item for item in assignments}
        self.assertNotEqual(assignments_by_id[1]["standby_session"], assignments_by_id[3]["standby_session"])
        self.assertEqual(assignments[0]["hall_id"], 1)
        self.assertEqual(assignments[0]["hall_slot"], 1)
        self.assertEqual(assignments[0]["hall_row"], 1)
        self.assertEqual(assignments[0]["board_number"], 1)
        self.assertEqual(assignments[0]["board_side"], "A")
        self.assertEqual(assignments[0]["board_label"], "1A")
        self.assertAlmostEqual(assignments[0]["hall_edge_x0"], 232.0)
        self.assertAlmostEqual(assignments[0]["hall_edge_x1"], 240.7, places=1)

    def test_analyze_main_reports_zero_conflicts_and_nearby_orals(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            raw_input, embeddings_dir = self._build_fixture(root)
            output_dir = root / "poster_layout"
            poster_layout.optimize_main(
                [
                    "--raw-input",
                    str(raw_input),
                    "--embeddings-dir",
                    str(embeddings_dir),
                    "--output-dir",
                    str(output_dir),
                ]
            )

            result = poster_layout.analyze_main(
                [
                    "--assignment",
                    str(output_dir / "proposal.json"),
                    "--raw-input",
                    str(raw_input),
                    "--embeddings-dir",
                    str(embeddings_dir),
                    "--output",
                    str(output_dir / "analysis.json"),
                    "--window-size",
                    "3",
                    "--oral-top-k",
                    "2",
                ]
            )

            self.assertEqual(result, 0)
            analysis = json.loads((output_dir / "analysis.json").read_text(encoding="utf-8"))

        self.assertEqual(len(analysis["oral_presentations"]), 2)
        for session_id in poster_layout.SESSION_IDS:
            session_summary = analysis["session_analysis"][str(session_id)]
            self.assertEqual(session_summary["author_conflicts"]["conflict_count"], 0)
            self.assertLessEqual(len(session_summary["nearest_oral_presentations"]), 2)
        self.assertTrue(all(item.get("assigned_session_id") in poster_layout.SESSION_IDS for item in analysis["oral_presentations"]))

    def test_layout_slot_for_block_position_snakes_across_rows(self) -> None:
        first = poster_layout.layout_slot_for_block_position(1)
        second = poster_layout.layout_slot_for_block_position(2)
        twentieth = poster_layout.layout_slot_for_block_position(20)
        twenty_first = poster_layout.layout_slot_for_block_position(21)
        sixtieth = poster_layout.layout_slot_for_block_position(60)
        sixty_first = poster_layout.layout_slot_for_block_position(61)
        one_hundred_twentieth = poster_layout.layout_slot_for_block_position(120)
        one_hundred_twenty_first = poster_layout.layout_slot_for_block_position(121)
        sixteen_hundred_eightieth = poster_layout.layout_slot_for_block_position(1680)

        self.assertEqual(first["hall_id"], 1)
        self.assertEqual(first["board_number"], 1)
        self.assertEqual(first["board_side"], "A")
        self.assertEqual(first["hall_row"], 1)
        self.assertEqual(first["hall_segment"], 1)
        self.assertEqual(first["hall_face_position"], 1)
        self.assertEqual(first["hall_row_direction"], "left_to_right")
        self.assertAlmostEqual(first["hall_edge_x0"], 232.0)
        self.assertAlmostEqual(first["hall_edge_x1"], 240.7, places=1)
        self.assertEqual(first["board_label"], "1A")

        self.assertEqual(second["board_number"], 2)
        self.assertEqual(second["board_side"], "A")
        self.assertEqual(second["hall_segment"], 1)
        self.assertEqual(second["hall_face_position"], 2)

        self.assertEqual(twentieth["board_number"], 20)
        self.assertEqual(twentieth["board_side"], "A")
        self.assertEqual(twentieth["hall_segment"], 2)
        self.assertEqual(twentieth["hall_face_position"], 10)
        self.assertEqual(twenty_first["board_number"], 21)
        self.assertEqual(twenty_first["board_side"], "A")
        self.assertEqual(twenty_first["hall_segment"], 3)
        self.assertEqual(twenty_first["hall_face_position"], 1)

        self.assertEqual(sixtieth["board_number"], 60)
        self.assertEqual(sixtieth["board_side"], "A")
        self.assertEqual(sixtieth["hall_row"], 1)
        self.assertEqual(sixtieth["hall_segment"], 6)
        self.assertEqual(sixtieth["hall_face_position"], 10)

        self.assertEqual(sixty_first["board_number"], 1)
        self.assertEqual(sixty_first["board_side"], "B")
        self.assertEqual(sixty_first["hall_row"], 1)
        self.assertEqual(sixty_first["hall_segment"], 1)
        self.assertEqual(sixty_first["hall_face_position"], 1)

        self.assertEqual(one_hundred_twentieth["board_number"], 60)
        self.assertEqual(one_hundred_twentieth["hall_row"], 1)
        self.assertEqual(one_hundred_twentieth["hall_segment"], 6)
        self.assertEqual(one_hundred_twentieth["hall_face_position"], 10)
        self.assertEqual(one_hundred_twentieth["board_side"], "B")

        self.assertEqual(one_hundred_twenty_first["board_number"], 61)
        self.assertEqual(one_hundred_twenty_first["hall_row"], 2)
        self.assertEqual(one_hundred_twenty_first["hall_segment"], 6)
        self.assertEqual(one_hundred_twenty_first["hall_face_position"], 10)
        self.assertEqual(one_hundred_twenty_first["hall_row_direction"], "right_to_left")
        self.assertEqual(one_hundred_twenty_first["board_side"], "A")

        self.assertEqual(sixteen_hundred_eightieth["board_number"], 840)
        self.assertEqual(sixteen_hundred_eightieth["board_side"], "B")
        self.assertEqual(sixteen_hundred_eightieth["hall_row"], 14)

    def test_assign_block_sequences_to_sessions_prefers_alternating_within_block(self) -> None:
        records_by_id = {
            1: poster_layout.AcceptedAbstract(1, 0, "Poster", "One", "A", "A1", "A :: A1", 11, None, None),
            2: poster_layout.AcceptedAbstract(2, 1, "Poster", "Two", "A", "A1", "A :: A1", 12, None, None),
            3: poster_layout.AcceptedAbstract(3, 2, "Poster", "Three", "A", "A1", "A :: A1", 13, None, None),
            4: poster_layout.AcceptedAbstract(4, 3, "Poster", "Four", "A", "A1", "A :: A1", 14, None, None),
            5: poster_layout.AcceptedAbstract(5, 4, "Poster", "Five", "B", "B1", "B :: B1", 15, None, None),
            6: poster_layout.AcceptedAbstract(6, 5, "Poster", "Six", "B", "B1", "B :: B1", 16, None, None),
            7: poster_layout.AcceptedAbstract(7, 6, "Poster", "Seven", "B", "B1", "B :: B1", 17, None, None),
            8: poster_layout.AcceptedAbstract(8, 7, "Poster", "Eight", "B", "B1", "B :: B1", 18, None, None),
        }

        assignments = poster_layout.assign_block_sequences_to_sessions(
            {1: [1, 2, 3, 4], 2: [5, 6, 7, 8]},
            records_by_id,
        )

        self.assertEqual([assignments[1], assignments[2], assignments[3], assignments[4]], [1, 2, 1, 2])
        self.assertEqual([assignments[5], assignments[6], assignments[7], assignments[8]], [3, 4, 3, 4])


if __name__ == "__main__":
    unittest.main()
