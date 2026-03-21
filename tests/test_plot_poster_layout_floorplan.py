import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def _load_floorplan_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "plot_poster_layout_floorplan.py"
    spec = importlib.util.spec_from_file_location("plot_poster_layout_floorplan", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load plot_poster_layout_floorplan module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PosterLayoutFloorplanPlotTest(unittest.TestCase):
    def test_main_writes_primary_and_semantic_floorplans(self) -> None:
        module = _load_floorplan_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            proposal_dir = Path(tmpdir) / "proposal"
            proposal_dir.mkdir(parents=True, exist_ok=True)
            proposal = {
                "assignments": [
                    {
                        "abstract_id": 1,
                        "title": "One",
                        "standby_session": 1,
                        "standby_session_label": "June 15 standby",
                        "block_id": 1,
                        "block_label": "June 15-16 block",
                        "block_position": 1,
                        "poster_number": 1,
                        "primary_category": "Parent A :: Sub A",
                        "claims_cluster_label": "cluster alpha",
                    },
                    {
                        "abstract_id": 2,
                        "title": "Two",
                        "standby_session": 3,
                        "standby_session_label": "June 17 standby",
                        "block_id": 2,
                        "block_label": "June 17-18 block",
                        "block_position": 1,
                        "poster_number": 1611,
                        "primary_category": "Parent B :: Sub B",
                        "claims_cluster_label": "cluster beta",
                    },
                ]
            }
            (proposal_dir / "proposal.json").write_text(json.dumps(proposal, indent=2), encoding="utf-8")

            result = module.main(["--proposal-dir", str(proposal_dir)])
            primary_html = (proposal_dir / "layout_primary_category.html").read_text(encoding="utf-8")
            semantic_html = (proposal_dir / "layout_semantic_category.html").read_text(encoding="utf-8")

        self.assertEqual(result, 0)
        self.assertIn("Poster floorplan by primary category", primary_html)
        self.assertIn("June 15-16 block", primary_html)
        self.assertIn("Board", primary_html)
        self.assertIn("Dots are colored by the selected category view", primary_html)
        self.assertIn("legendonly", primary_html)
        self.assertIn("Poster floorplan by semantic claims category", semantic_html)
        self.assertIn("cluster alpha", semantic_html)


if __name__ == "__main__":
    unittest.main()
