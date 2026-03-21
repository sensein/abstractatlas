from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ohbm2026.neuroscape import build_distinct_color_map
from ohbm2026.poster_layout import layout_slot_for_block_position, load_layout_geometry


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot a poster proposal on the venue floorplan layout")
    parser.add_argument("--proposal-dir", required=True)
    parser.add_argument("--output-primary-html")
    parser.add_argument("--output-semantic-html")
    return parser


def _assignments_with_layout(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    for assignment in proposal.get("assignments", []):
        if (
            "hall_id" in assignment
            and "hall_x" in assignment
            and "hall_y" in assignment
            and "hall_edge_x0" in assignment
            and "hall_edge_y0" in assignment
            and "hall_edge_x1" in assignment
            and "hall_edge_y1" in assignment
            and "board_number" in assignment
            and "board_side" in assignment
        ):
            assignments.append(dict(assignment))
            continue
        layout_slot = layout_slot_for_block_position(int(assignment["block_position"]))
        assignments.append({**assignment, **layout_slot})
    return assignments


def _background_boards() -> list[dict[str, Any]]:
    geometry = load_layout_geometry()
    boards = geometry.get("boards", [])
    return [dict(board) for board in boards]


def _hover_customdata(record: dict[str, Any]) -> list[Any]:
    return [
        int(record.get("poster_number") or 0),
        str(record.get("board_label") or "Unknown"),
        str(record.get("title") or "Untitled"),
        str(record.get("standby_session_label") or "Unknown"),
        str(record.get("primary_category") or "Unknown"),
        str(record.get("claims_cluster_label") or "Unknown"),
        str(record.get("block_label") or "Unknown"),
        int(record.get("board_number") or 0),
        str(record.get("board_side") or "Unknown"),
        int(record.get("hall_row") or 0),
        int(record.get("hall_segment") or 0),
        int(record.get("hall_face_position") or 0),
    ]


def _edge_arrays(records: list[dict[str, Any]]) -> tuple[list[float | None], list[float | None]]:
    x_values: list[float | None] = []
    y_values: list[float | None] = []
    for record in records:
        x_values.extend([float(record["hall_edge_x0"]), float(record["hall_edge_x1"]), None])
        y_values.extend([float(record["hall_edge_y0"]), float(record["hall_edge_y1"]), None])
    return x_values, y_values


def _background_face_arrays(records: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
    x_values: list[float] = []
    y_values: list[float] = []
    for record in records:
        x_values.extend([float(record["hall_face_a_x"]), float(record["hall_face_b_x"])])
        y_values.extend([float(record["hall_face_a_y"]), float(record["hall_face_b_y"])])
    return x_values, y_values


def _assignment_face_arrays(records: list[dict[str, Any]]) -> tuple[list[float], list[float], list[list[Any]]]:
    x_values: list[float] = []
    y_values: list[float] = []
    customdata: list[list[Any]] = []
    for record in records:
        x_values.append(float(record["hall_x"]))
        y_values.append(float(record["hall_y"]))
        customdata.append(_hover_customdata(record))
    return x_values, y_values, customdata


def _plot_category_floorplan(
    assignments: list[dict[str, Any]],
    color_field: str,
    title: str,
    output_html: Path,
) -> None:
    background = _background_boards()
    background_edge_x, background_edge_y = _edge_arrays(background)
    background_face_x, background_face_y = _background_face_arrays(background)
    distinct_values = [str(record.get(color_field) or "Unknown") for record in assignments]
    color_map = build_distinct_color_map(distinct_values)
    show_legend = len(color_map) <= 40
    geometry_metadata = dict(load_layout_geometry().get("metadata") or {})
    x_min = float(geometry_metadata.get("x_min") or 0.0) - 10.0
    x_max = float(geometry_metadata.get("x_max") or 0.0) + 10.0
    y_min = float(geometry_metadata.get("y_min") or 0.0) - 10.0
    y_max = float(geometry_metadata.get("y_max") or 0.0) + 10.0

    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("June 15-16 block", "June 17-18 block"),
        horizontal_spacing=0.06,
    )
    shown_categories: set[str] = set()
    background_trace_indices: list[int] = []
    category_trace_indices: list[int] = []
    for block_id in (1, 2):
        col = block_id
        figure.add_trace(
            go.Scattergl(
                x=background_edge_x,
                y=background_edge_y,
                mode="lines",
                line={"width": 2, "color": "rgba(140,140,140,0.35)"},
                name="Board edges",
                showlegend=(block_id == 1),
                hoverinfo="skip",
            ),
            row=1,
            col=col,
        )
        background_trace_indices.append(len(figure.data) - 1)
        figure.add_trace(
            go.Scattergl(
                x=background_face_x,
                y=background_face_y,
                mode="markers",
                marker={"size": 4, "color": "rgba(160,160,160,0.35)"},
                name="Poster faces",
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1,
            col=col,
        )
        background_trace_indices.append(len(figure.data) - 1)

        block_assignments = [record for record in assignments if int(record["block_id"]) == block_id]
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in block_assignments:
            grouped[str(record.get(color_field) or "Unknown")].append(record)

        for category in sorted(grouped):
            category_color = color_map.get(category, "hsl(0, 0%, 50%)")
            dot_x, dot_y, dot_customdata = _assignment_face_arrays(grouped[category])
            figure.add_trace(
                go.Scatter(
                    x=dot_x,
                    y=dot_y,
                    mode="markers",
                    marker={
                        "size": 7,
                        "color": category_color,
                        "line": {"width": 0.8, "color": "#111111"},
                    },
                    name=category,
                    showlegend=show_legend and category not in shown_categories,
                    legendgroup=category,
                    customdata=dot_customdata,
                    hovertemplate=(
                        "Poster %{customdata[0]}<br>"
                        "Board %{customdata[1]}<br>"
                        "%{customdata[2]}<br>"
                        "%{customdata[3]}<br>"
                        "Primary category: %{customdata[4]}<br>"
                        "Semantic category: %{customdata[5]}<br>"
                        "%{customdata[6]}<br>"
                        "Board %{customdata[7]} side %{customdata[8]} | Row %{customdata[9]}, unit %{customdata[10]}, edge %{customdata[11]}<extra></extra>"
                    ),
                ),
                row=1,
                col=col,
            )
            category_trace_indices.append(len(figure.data) - 1)
            shown_categories.add(category)

        figure.update_xaxes(
            range=[x_min, x_max],
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            row=1,
            col=col,
        )
        figure.update_yaxes(
            range=[y_min, y_max],
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            scaleanchor=f"x{'' if col == 1 else col}",
            scaleratio=1,
            row=1,
            col=col,
        )

    legend_note = ""
    if not show_legend:
        legend_note = (
            "<br><sup>Legend suppressed because this view contains many distinct categories; "
            "use hover to inspect exact values.</sup>"
        )
    visible_all = [True] * len(figure.data)
    visible_background_only = [
        True if index in background_trace_indices else "legendonly"
        for index in range(len(figure.data))
    ]
    figure.update_layout(
        title=(
            title
            + "<br><sup>Dots are colored by the selected category view. Hover to see standby time and board details.</sup>"
            + legend_note
        ),
        template="plotly_white",
        height=760,
        width=1600,
        legend={"orientation": "v", "y": 1.0, "x": 1.02},
        updatemenus=[
            {
                "type": "buttons",
                "direction": "left",
                "x": 0.0,
                "y": 1.12,
                "buttons": [
                    {
                        "label": "Select all",
                        "method": "update",
                        "args": [{"visible": visible_all}],
                    },
                    {
                        "label": "Unselect all",
                        "method": "update",
                        "args": [{"visible": visible_background_only}],
                    },
                ],
            }
        ],
    )
    output_html.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(str(output_html), include_plotlyjs="cdn")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    proposal_dir = Path(args.proposal_dir)
    primary_output = (
        Path(args.output_primary_html) if args.output_primary_html else proposal_dir / "layout_primary_category.html"
    )
    semantic_output = (
        Path(args.output_semantic_html) if args.output_semantic_html else proposal_dir / "layout_semantic_category.html"
    )

    proposal = load_json(proposal_dir / "proposal.json")
    assignments = _assignments_with_layout(proposal)
    _plot_category_floorplan(
        assignments,
        color_field="primary_category",
        title=f"Poster floorplan by primary category: {proposal_dir.name}",
        output_html=primary_output,
    )
    _plot_category_floorplan(
        assignments,
        color_field="claims_cluster_label",
        title=f"Poster floorplan by semantic claims category: {proposal_dir.name}",
        output_html=semantic_output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
