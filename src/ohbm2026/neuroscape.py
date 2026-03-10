from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ohbm2026.graphql_api import chunked

DEFAULT_VOYAGE_MODEL = "voyage-large-2-instruct"
DEFAULT_MINILM_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_FIELDS = ("title", "introduction", "methods", "results", "conclusion")
DEFAULT_STAGE2_OUTPUT_DIMENSION = 64
DEFAULT_STAGE2_HIDDEN_DIMENSIONS = (192, 96, 64)
DEFAULT_UMAP_NEIGHBORS = 15
DEFAULT_UMAP_MIN_DIST = 0.1
ALLOWED_EMBEDDING_FIELDS = {
    "title",
    "introduction",
    "methods",
    "results",
    "discussion",
    "conclusion",
    "references",
    "acknowledgement",
}
SECTION_HEADINGS = {
    "introduction": "Introduction",
    "methods": "Methods",
    "results": "Results",
    "discussion": "Discussion",
    "conclusion": "Conclusion",
    "references": "References",
    "acknowledgement": "Acknowledgement",
}
SECTION_MARKDOWN_KEYS = {
    "introduction": "introduction_markdown",
    "methods": "methods_markdown",
    "results": "results_markdown",
    "discussion": "discussion_markdown",
    "conclusion": "conclusion_markdown",
    "references": "references_markdown",
    "acknowledgement": "acknowledgement_markdown",
}


class NeuroScapeError(RuntimeError):
    """Raised when embedding or relationship generation fails."""


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def parse_string_list_value(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        text = raw_value.strip()
        return [text] if text else []
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, str):
        text = parsed.strip()
        return [text] if text else []
    return []


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def load_title_lookup(path: Path) -> dict[int, str]:
    database = json.loads(path.read_text(encoding="utf-8"))
    return {
        abstract["id"]: abstract.get("title", "")
        for abstract in database.get("abstracts", [])
        if isinstance(abstract.get("id"), int)
    }


def extract_raw_keywords(abstract: dict[str, Any]) -> list[str]:
    for response in abstract.get("responses", []):
        if str(response.get("question_name") or "").strip().lower() == "keywords":
            return parse_string_list_value(response.get("value"))
    return []


def load_annotation_lookup(
    raw_path: Path,
    enriched_path: Path | None = None,
) -> dict[int, dict[str, Any]]:
    raw_database = json.loads(raw_path.read_text(encoding="utf-8"))
    enriched_lookup: dict[int, dict[str, Any]] = {}
    if enriched_path and enriched_path.exists():
        enriched_database = json.loads(enriched_path.read_text(encoding="utf-8"))
        enriched_lookup = {
            abstract["id"]: abstract
            for abstract in enriched_database.get("abstracts", [])
            if isinstance(abstract.get("id"), int)
        }

    annotations: dict[int, dict[str, Any]] = {}
    for abstract in raw_database.get("abstracts", []):
        abstract_id = abstract.get("id")
        if not isinstance(abstract_id, int):
            continue
        enriched = enriched_lookup.get(abstract_id, {})
        keywords = unique_strings(
            extract_raw_keywords(abstract)
            + [str(keyword).strip() for keyword in enriched.get("figure_keywords", []) if str(keyword).strip()]
        )
        annotations[abstract_id] = {
            "id": abstract_id,
            "title": abstract.get("title") or "",
            "accepted_for": abstract.get("accepted_for") or "Unknown",
            "keywords": keywords,
        }
    return annotations


def build_visualization_records(
    ids: list[int],
    annotation_lookup: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for abstract_id in ids:
        annotation = annotation_lookup.get(int(abstract_id), {})
        records.append(
            {
                "id": int(abstract_id),
                "title": annotation.get("title") or "",
                "accepted_for": annotation.get("accepted_for") or "Unknown",
                "keywords": list(annotation.get("keywords") or []),
            }
        )
    return records


def normalize_embedding_fields(fields: list[str] | tuple[str, ...] | None) -> list[str]:
    raw_fields = list(fields or DEFAULT_EMBEDDING_FIELDS)
    normalized_fields: list[str] = []
    seen: set[str] = set()
    for field in raw_fields:
        normalized = field.strip().lower()
        if normalized not in ALLOWED_EMBEDDING_FIELDS:
            raise NeuroScapeError(f"Unsupported embedding field: {field}")
        if normalized not in seen:
            seen.add(normalized)
            normalized_fields.append(normalized)
    if not normalized_fields:
        raise NeuroScapeError("At least one embedding field is required")
    return normalized_fields


def build_embedding_text(
    abstract: dict[str, Any],
    fields: list[str] | tuple[str, ...] | None = None,
    title_lookup: dict[int, str] | None = None,
) -> str:
    selected_fields = normalize_embedding_fields(fields)
    parts: list[str] = []

    for field in selected_fields:
        if field == "title":
            title = (abstract.get("title") or "").strip()
            if not title and title_lookup and isinstance(abstract.get("id"), int):
                title = (title_lookup.get(abstract["id"]) or "").strip()
            if title:
                parts.append(title)
            continue
        section_key = SECTION_MARKDOWN_KEYS[field]
        section_text = (abstract.get(section_key) or "").strip()
        if section_text:
            parts.append(f"{SECTION_HEADINGS[field]}:\n{section_text}")

    return "\n\n".join(parts).strip()


def build_embedding_texts(
    abstracts: list[dict[str, Any]],
    fields: list[str] | tuple[str, ...] | None = None,
    title_lookup: dict[int, str] | None = None,
) -> list[str]:
    selected_fields = normalize_embedding_fields(fields)
    return [build_embedding_text(abstract, selected_fields, title_lookup=title_lookup) for abstract in abstracts]


def embedding_variant_name(fields: list[str] | tuple[str, ...] | None = None) -> str:
    selected_fields = normalize_embedding_fields(fields)
    if selected_fields == list(DEFAULT_EMBEDDING_FIELDS):
        return "stage1"
    return "-".join(selected_fields)


def voyage_embed(
    texts: list[str],
    api_key: str,
    model: str = DEFAULT_VOYAGE_MODEL,
    batch_size: int = 64,
) -> list[list[float]]:
    endpoint = "https://api.voyageai.com/v1/embeddings"
    vectors: list[list[float]] = []
    for text_batch in chunked(list(range(len(texts))), batch_size):
        batch_inputs = [texts[index] for index in text_batch]
        payload = json.dumps(
            {"input": batch_inputs, "model": model, "input_type": "document"}
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=600) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise NeuroScapeError(f"Voyage embeddings failed with HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise NeuroScapeError(f"Voyage embeddings failed: {exc.reason}") from exc
        vectors.extend(item["embedding"] for item in parsed.get("data", []))
    return vectors


def minilm_embed(texts: list[str], model_name: str = DEFAULT_MINILM_MODEL) -> list[list[float]]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )
    return embeddings.tolist()


def write_embedding_bundle(
    output_dir: Path,
    embedding_name: str,
    model_name: str,
    abstracts: list[dict[str, Any]],
    vectors: list[list[float]],
    embedding_fields: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    import numpy as np

    output_dir.mkdir(parents=True, exist_ok=True)
    matrix = np.asarray(vectors, dtype=np.float32)
    ids = [abstract["id"] for abstract in abstracts]
    metadata = [
        {"id": abstract["id"], "title": abstract.get("title"), "accepted_for": abstract.get("accepted_for")}
        for abstract in abstracts
    ]
    np.save(output_dir / "vectors.npy", matrix)
    write_json(
        output_dir / "metadata.json",
        {
            "embedding_name": embedding_name,
            "model_name": model_name,
            "embedding_fields": normalize_embedding_fields(embedding_fields),
            "count": len(metadata),
            "metadata": metadata,
            "ids": ids,
        },
    )
    return {"ids": ids, "matrix": matrix, "metadata": metadata}


def compute_neighbors(ids: list[int], matrix: Any, top_k: int = 10) -> dict[str, Any]:
    import numpy as np

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = matrix / norms
    similarities = normalized @ normalized.T
    neighbors: dict[str, list[dict[str, float]]] = {}
    for index, abstract_id in enumerate(ids):
        row = similarities[index].copy()
        row[index] = -1.0
        neighbor_indices = np.argsort(row)[-top_k:][::-1]
        neighbors[str(abstract_id)] = [
            {"id": int(ids[neighbor_index]), "score": float(row[neighbor_index])}
            for neighbor_index in neighbor_indices
        ]
    return {"top_k": top_k, "neighbors": neighbors}


def write_neuroscape_manifest(output_path: Path) -> None:
    write_json(
        output_path,
        {
            "status": "stage1_ready_stage2_pending_validation",
            "base_embedding_model": DEFAULT_VOYAGE_MODEL,
            "local_stage1_model": DEFAULT_MINILM_MODEL,
            "zenodo_record": "https://zenodo.org/records/14865161",
            "repository": "https://github.com/ccnmaastricht/NeuroScape",
            "note": (
                "The published NeuroScape domain model depends on Voyage stage-one embeddings "
                "and still requires the Zenodo artifact download before stage-two projection can run. "
                "A local-retraining path using a local stage-one model should be treated as a separate "
                "track until validated against the NeuroScape training workflow."
            ),
        },
    )


def load_embedding_inputs(path: Path) -> list[dict[str, Any]]:
    database = json.loads(path.read_text(encoding="utf-8"))
    return database.get("abstracts", [])


def normalize_hidden_dimensions(values: list[int] | tuple[int, ...]) -> tuple[int, int, int]:
    dimensions = tuple(int(value) for value in values)
    if len(dimensions) != 3 or any(value <= 0 for value in dimensions):
        raise NeuroScapeError("Stage-2 hidden dimensions must contain exactly three positive integers")
    return dimensions


def choose_torch_device(requested: str | None = None) -> str:
    import torch

    if requested:
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_stage1_bundle(bundle_dir: Path) -> dict[str, Any]:
    import numpy as np

    metadata_path = bundle_dir / "metadata.json"
    vectors_path = bundle_dir / "vectors.npy"
    if not metadata_path.exists() or not vectors_path.exists():
        raise NeuroScapeError(f"Stage-1 bundle is incomplete: {bundle_dir}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    matrix = np.load(vectors_path)
    ids = metadata.get("ids", [])
    rows = metadata.get("metadata", [])
    if len(ids) != len(rows) or len(ids) != int(matrix.shape[0]):
        raise NeuroScapeError("Stage-1 bundle metadata does not match vectors.npy")
    return {"ids": ids, "metadata": rows, "matrix": matrix, "source_metadata": metadata}


def load_embedding_bundle(bundle_dir: Path) -> dict[str, Any]:
    return load_stage1_bundle(bundle_dir)


def compute_umap_projection(
    matrix: Any,
    n_neighbors: int = DEFAULT_UMAP_NEIGHBORS,
    min_dist: float = DEFAULT_UMAP_MIN_DIST,
    metric: str = "cosine",
    random_state: int = 42,
) -> Any:
    import umap

    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric=metric,
        random_state=random_state,
    )
    return reducer.fit_transform(matrix)


def write_umap_outputs(
    output_html: Path,
    output_json: Path,
    coordinates: Any,
    records: list[dict[str, Any]],
    title: str = "OHBM 2026 Abstract Embeddings UMAP",
) -> None:
    import numpy as np
    import plotly.graph_objects as go

    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    coords = np.asarray(coordinates)
    grouped_indices: dict[str, list[int]] = {}
    for index, record in enumerate(records):
        grouped_indices.setdefault(str(record.get("accepted_for") or "Unknown"), []).append(index)

    figure = go.Figure()
    for group_name in sorted(grouped_indices):
        indices = grouped_indices[group_name]
        customdata = [
            [
                records[index]["id"],
                records[index]["title"],
                group_name,
                ", ".join(records[index]["keywords"]),
            ]
            for index in indices
        ]
        figure.add_trace(
            go.Scattergl(
                x=coords[indices, 0],
                y=coords[indices, 1],
                mode="markers",
                name=group_name,
                marker={"size": 7, "opacity": 0.8},
                customdata=customdata,
                hovertemplate=(
                    "id=%{customdata[0]}<br>"
                    "title=%{customdata[1]}<br>"
                    "accepted_for=%{customdata[2]}<br>"
                    "keywords=%{customdata[3]}<extra></extra>"
                ),
            )
        )
    figure.update_layout(
        title=title,
        xaxis_title="UMAP-1",
        yaxis_title="UMAP-2",
        template="plotly_white",
        legend_title="Accepted For",
    )
    figure.write_html(str(output_html), include_plotlyjs="cdn")

    write_json(
        output_json,
        {
            "title": title,
            "count": len(records),
            "points": [
                {
                    "id": record["id"],
                    "title": record["title"],
                    "accepted_for": record["accepted_for"],
                    "keywords": record["keywords"],
                    "x": float(coords[index, 0]),
                    "y": float(coords[index, 1]),
                }
                for index, record in enumerate(records)
            ],
        },
    )


def split_stage2_matrix(
    matrix: Any, validation_size: float = 0.05, seed: int = 42
) -> tuple[Any, Any]:
    import numpy as np

    if not 0 < validation_size < 1:
        raise NeuroScapeError("validation_size must be between 0 and 1")
    if matrix.shape[0] < 20:
        raise NeuroScapeError("Stage-2 training requires at least 20 stage-1 vectors")

    indices = np.arange(matrix.shape[0])
    rng = np.random.default_rng(seed)
    rng.shuffle(indices)

    validation_count = max(1, int(round(matrix.shape[0] * validation_size)))
    train_indices = indices[validation_count:]
    validation_indices = indices[:validation_count]
    return matrix[train_indices].copy(), matrix[validation_indices].copy()


def build_stage2_network(
    input_dimension: int,
    hidden_dimensions: tuple[int, int, int] = DEFAULT_STAGE2_HIDDEN_DIMENSIONS,
    output_dimension: int = DEFAULT_STAGE2_OUTPUT_DIMENSION,
    dropout: float = 0.1,
) -> Any:
    import torch.nn as nn
    import torch.nn.functional as F

    class Network(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.first_stage = nn.Sequential(
                nn.Linear(input_dimension, hidden_dimensions[0]),
                nn.BatchNorm1d(hidden_dimensions[0]),
                nn.ELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dimensions[0], hidden_dimensions[1]),
                nn.ELU(),
            )
            self.second_stage = nn.Sequential(
                nn.Linear(hidden_dimensions[1], hidden_dimensions[2]),
                nn.BatchNorm1d(hidden_dimensions[2]),
                nn.ELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dimensions[2], output_dimension),
            )

        def forward(self, x: Any) -> Any:
            first_state = self.first_stage(x)
            second_state = self.second_stage(first_state)
            return F.normalize(second_state, p=2, dim=1)

    return Network()


def dimension_correlation(projected: Any) -> Any:
    import torch

    if projected.shape[0] < 2 or projected.shape[1] < 2:
        return torch.zeros((), dtype=projected.dtype, device=projected.device)
    corr_matrix = torch.corrcoef(projected.T)
    return torch.mean(torch.abs(torch.triu(corr_matrix, diagonal=1)))


def compute_stage2_losses(
    model: Any,
    batch: Any,
    temperature: float,
    cutoff_values: tuple[float, float],
    correlation_weight: float = 0.0,
) -> tuple[Any, Any, Any]:
    import torch

    positive_cutoff, negative_cutoff = cutoff_values
    projected = model(batch)
    source_similarity = torch.matmul(batch, batch.T)
    target_similarity = torch.matmul(projected, projected.T)
    positives_mask = source_similarity >= positive_cutoff
    positives_mask = positives_mask & ~torch.eye(batch.shape[0], dtype=torch.bool, device=batch.device)
    negatives_mask = source_similarity <= negative_cutoff

    positive_logsum = torch.logsumexp(target_similarity * positives_mask.float() / temperature, dim=1)
    negative_logsum = torch.logsumexp(target_similarity * negatives_mask.float() / temperature, dim=1)
    info_nce_loss = (-positive_logsum + negative_logsum).mean()
    correlation_loss = correlation_weight * dimension_correlation(projected)
    return info_nce_loss + correlation_loss, info_nce_loss, correlation_loss


def evaluate_stage2_model(
    model: Any,
    validation_tensor: Any,
    temperature: float,
    cutoff_values: tuple[float, float],
) -> float:
    import torch

    with torch.no_grad():
        _, info_nce_loss, _ = compute_stage2_losses(
            model,
            validation_tensor,
            temperature=temperature,
            cutoff_values=cutoff_values,
            correlation_weight=0.0,
        )
    return float(info_nce_loss.item())


def train_stage2_model(
    matrix: Any,
    hidden_dimensions: tuple[int, int, int] = DEFAULT_STAGE2_HIDDEN_DIMENSIONS,
    output_dimension: int = DEFAULT_STAGE2_OUTPUT_DIMENSION,
    dropout: float = 0.1,
    epochs: int = 120,
    batch_size: int = 256,
    validation_size: float = 0.05,
    initial_learning_rate: float = 1e-4,
    minimum_learning_rate: float = 1e-5,
    temperature: float = 0.1,
    cutoff_values: tuple[float, float] = (0.85, 0.75),
    correlation_weight: float = 0.1,
    seed: int = 42,
    device: str | None = None,
    report_every: int = 10,
) -> tuple[Any, dict[str, Any]]:
    import numpy as np
    import torch

    if epochs <= 0:
        raise NeuroScapeError("epochs must be positive")
    if batch_size <= 1:
        raise NeuroScapeError("batch_size must be greater than 1")

    torch.manual_seed(seed)
    np.random.seed(seed)

    train_matrix, validation_matrix = split_stage2_matrix(matrix, validation_size=validation_size, seed=seed)
    torch_device = choose_torch_device(device)
    model = build_stage2_network(
        int(matrix.shape[1]),
        hidden_dimensions=hidden_dimensions,
        output_dimension=output_dimension,
        dropout=dropout,
    ).to(torch_device)

    optimizer = torch.optim.Adam(model.parameters(), lr=initial_learning_rate, weight_decay=0.01)
    gamma = (minimum_learning_rate / initial_learning_rate) ** (1 / max(epochs, 1))
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=1, gamma=gamma)

    validation_tensor = torch.tensor(validation_matrix, dtype=torch.float32, device=torch_device)
    best_validation_loss = float("inf")
    best_state = copy.deepcopy(model.state_dict())
    train_history: list[dict[str, float]] = []

    for epoch in range(epochs):
        model.train()
        permutation = np.random.permutation(train_matrix.shape[0])
        shuffled = train_matrix[permutation]
        batch_losses: list[float] = []
        batch_info_losses: list[float] = []
        batch_correlation_losses: list[float] = []

        for start in range(0, shuffled.shape[0], batch_size):
            stop = min(start + batch_size, shuffled.shape[0])
            current_batch = shuffled[start:stop]
            if current_batch.shape[0] < 2:
                continue
            batch_tensor = torch.tensor(current_batch, dtype=torch.float32, device=torch_device)
            optimizer.zero_grad()
            total_loss, info_nce_loss, correlation_loss = compute_stage2_losses(
                model,
                batch_tensor,
                temperature=temperature,
                cutoff_values=cutoff_values,
                correlation_weight=correlation_weight,
            )
            total_loss.backward()
            optimizer.step()
            batch_losses.append(float(total_loss.item()))
            batch_info_losses.append(float(info_nce_loss.item()))
            batch_correlation_losses.append(float(correlation_loss.item()))

        scheduler.step()
        validation_loss = evaluate_stage2_model(
            model,
            validation_tensor,
            temperature=temperature,
            cutoff_values=cutoff_values,
        )
        if validation_loss < best_validation_loss:
            best_validation_loss = validation_loss
            best_state = copy.deepcopy(model.state_dict())

        epoch_record = {
            "epoch": float(epoch + 1),
            "training_loss": float(sum(batch_losses) / max(len(batch_losses), 1)),
            "training_info_nce_loss": float(sum(batch_info_losses) / max(len(batch_info_losses), 1)),
            "training_correlation_loss": float(sum(batch_correlation_losses) / max(len(batch_correlation_losses), 1)),
            "validation_loss": float(validation_loss),
        }
        train_history.append(epoch_record)
        if epoch == 0 or (epoch + 1) % report_every == 0 or epoch + 1 == epochs:
            print(json.dumps(epoch_record, sort_keys=True))

    model.load_state_dict(best_state)
    return model, {
        "device": torch_device,
        "epochs": epochs,
        "batch_size": batch_size,
        "validation_size": validation_size,
        "temperature": temperature,
        "cutoff_values": list(cutoff_values),
        "correlation_weight": correlation_weight,
        "best_validation_loss": best_validation_loss,
        "history": train_history,
    }


def apply_stage2_model(model: Any, matrix: Any, batch_size: int = 256, device: str | None = None) -> Any:
    import numpy as np
    import torch

    torch_device = choose_torch_device(device)
    model = model.to(torch_device)
    model.eval()
    projected_batches: list[Any] = []
    with torch.no_grad():
        for start in range(0, matrix.shape[0], batch_size):
            stop = min(start + batch_size, matrix.shape[0])
            batch_tensor = torch.tensor(matrix[start:stop], dtype=torch.float32, device=torch_device)
            projected_batches.append(model(batch_tensor).cpu().numpy())
    return np.concatenate(projected_batches, axis=0)


def write_stage2_bundle(
    output_dir: Path,
    stage1_bundle: dict[str, Any],
    projected_matrix: Any,
    model: Any,
    training_summary: dict[str, Any],
    hidden_dimensions: tuple[int, int, int],
    output_dimension: int,
    dropout: float,
) -> None:
    import numpy as np
    import torch

    output_dir.mkdir(parents=True, exist_ok=True)
    np.save(output_dir / "vectors.npy", np.asarray(projected_matrix, dtype=np.float32))
    torch.save(model.state_dict(), output_dir / "domain_embedding_model_best.pth")
    write_json(output_dir / "neighbors.json", compute_neighbors(stage1_bundle["ids"], projected_matrix))
    write_json(output_dir / "training.json", training_summary)
    write_json(
        output_dir / "metadata.json",
        {
            "embedding_name": output_dir.name,
            "model_name": "neuroscape-stage2-local",
            "count": len(stage1_bundle["ids"]),
            "ids": stage1_bundle["ids"],
            "metadata": stage1_bundle["metadata"],
            "source_embedding_name": stage1_bundle["source_metadata"].get("embedding_name"),
            "source_model_name": stage1_bundle["source_metadata"].get("model_name"),
            "embedding_fields": stage1_bundle["source_metadata"].get("embedding_fields"),
            "stage2_config": {
                "hidden_dimensions": list(hidden_dimensions),
                "output_dimension": output_dimension,
                "dropout": dropout,
            },
            "training_summary": {
                "device": training_summary["device"],
                "epochs": training_summary["epochs"],
                "batch_size": training_summary["batch_size"],
                "best_validation_loss": training_summary["best_validation_loss"],
            },
        },
    )


def load_enriched_lookup(path: Path) -> dict[int, dict[str, Any]]:
    return {
        abstract["id"]: abstract
        for abstract in load_embedding_inputs(path)
        if isinstance(abstract.get("id"), int)
    }


def align_semantic_records(
    ids: list[int],
    enriched_lookup: dict[int, dict[str, Any]],
    title_lookup: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for abstract_id in ids:
        abstract = enriched_lookup.get(abstract_id, {"id": abstract_id})
        record = dict(abstract)
        record["id"] = abstract_id
        record["title"] = (
            (title_lookup or {}).get(abstract_id)
            or abstract.get("title")
            or ""
        )
        record["cluster_document"] = build_embedding_text(
            record,
            DEFAULT_EMBEDDING_FIELDS,
            title_lookup=title_lookup,
        )
        records.append(record)
    return records


def align_cluster_records(
    ids: list[int],
    enriched_lookup: dict[int, dict[str, Any]],
    title_lookup: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    return align_semantic_records(ids, enriched_lookup, title_lookup=title_lookup)


def build_knn_graph(ids: list[int], matrix: Any, num_neighbors: int = 50) -> Any:
    import networkx as nx
    from sklearn.neighbors import NearestNeighbors

    if num_neighbors <= 0:
        raise NeuroScapeError("num_neighbors must be positive")
    if len(ids) != int(matrix.shape[0]):
        raise NeuroScapeError("IDs and matrix row count do not match")

    graph = nx.Graph()
    graph.add_nodes_from(int(abstract_id) for abstract_id in ids)
    neighbor_count = min(num_neighbors + 1, int(matrix.shape[0]))
    search = NearestNeighbors(n_neighbors=neighbor_count, metric="cosine", algorithm="brute")
    search.fit(matrix)
    distances, indices = search.kneighbors(matrix)

    for row_index, abstract_id in enumerate(ids):
        for neighbor_index, distance in zip(indices[row_index][1:], distances[row_index][1:]):
            neighbor_id = int(ids[int(neighbor_index)])
            similarity = max(0.0, 1.0 - float(distance))
            if similarity <= 0.0:
                continue
            if graph.has_edge(int(abstract_id), neighbor_id):
                graph[int(abstract_id)][neighbor_id]["weight"] = max(
                    float(graph[int(abstract_id)][neighbor_id]["weight"]),
                    similarity,
                )
            else:
                graph.add_edge(int(abstract_id), neighbor_id, weight=similarity)
    return graph


def detect_semantic_communities(
    graph: Any,
    num_resolution_parameter: int = 20,
    max_resolution_parameter: float = 1.0,
) -> dict[str, Any]:
    import numpy as np
    from networkx.algorithms.community import greedy_modularity_communities, modularity

    if num_resolution_parameter <= 0:
        raise NeuroScapeError("num_resolution_parameter must be positive")
    resolution_values = np.linspace(
        max_resolution_parameter / num_resolution_parameter,
        max_resolution_parameter,
        num_resolution_parameter,
    )
    history: list[dict[str, Any]] = []
    best_modularity = float("-inf")
    best_resolution = float(resolution_values[0])
    best_communities: list[set[int]] = []

    for resolution in resolution_values:
        try:
            communities = list(
                greedy_modularity_communities(
                    graph,
                    weight="weight",
                    resolution=float(resolution),
                )
            )
            modularity_value = float(
                modularity(graph, communities, weight="weight", resolution=float(resolution))
            )
        except TypeError:
            communities = list(greedy_modularity_communities(graph, weight="weight"))
            modularity_value = float(modularity(graph, communities, weight="weight"))
        history.append(
            {
                "resolution": float(resolution),
                "modularity": modularity_value,
                "community_count": len(communities),
            }
        )
        if modularity_value > best_modularity:
            best_modularity = modularity_value
            best_resolution = float(resolution)
            best_communities = [set(community) for community in communities]

    ordered_communities = sorted(best_communities, key=lambda community: (-len(community), min(community)))
    assignments: dict[int, int] = {}
    for cluster_id, community in enumerate(ordered_communities):
        for abstract_id in community:
            assignments[int(abstract_id)] = cluster_id

    return {
        "best_resolution": best_resolution,
        "best_modularity": best_modularity,
        "history": history,
        "communities": ordered_communities,
        "assignments": assignments,
    }


def detect_stage2_communities(
    graph: Any,
    num_resolution_parameter: int = 20,
    max_resolution_parameter: float = 1.0,
) -> dict[str, Any]:
    return detect_semantic_communities(
        graph,
        num_resolution_parameter=num_resolution_parameter,
        max_resolution_parameter=max_resolution_parameter,
    )


def extract_cluster_keywords(documents: list[str], max_keywords: int = 8) -> list[str]:
    from sklearn.feature_extraction.text import TfidfVectorizer

    filtered_documents = [document for document in documents if document.strip()]
    if not filtered_documents:
        return []
    try:
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=5000)
        matrix = vectorizer.fit_transform(filtered_documents)
    except ValueError:
        return []
    scores = matrix.sum(axis=0).A1
    feature_names = vectorizer.get_feature_names_out()
    ranked_indices = scores.argsort()[::-1]
    keywords = [feature_names[index] for index in ranked_indices if scores[index] > 0]
    return keywords[:max_keywords]


def summarize_semantic_clusters(
    ids: list[int],
    matrix: Any,
    records: list[dict[str, Any]],
    assignments: dict[int, int],
    max_keywords: int = 8,
    max_representatives: int = 5,
) -> list[dict[str, Any]]:
    import numpy as np

    index_by_id = {int(abstract_id): position for position, abstract_id in enumerate(ids)}
    cluster_members: dict[int, list[int]] = {}
    for abstract_id, cluster_id in assignments.items():
        cluster_members.setdefault(int(cluster_id), []).append(int(abstract_id))

    centroids: dict[int, Any] = {}
    for cluster_id, member_ids in cluster_members.items():
        cluster_matrix = matrix[[index_by_id[member_id] for member_id in member_ids]]
        centroid = cluster_matrix.mean(axis=0)
        centroid_norm = np.linalg.norm(centroid)
        if centroid_norm:
            centroid = centroid / centroid_norm
        centroids[cluster_id] = centroid

    cluster_ids = sorted(cluster_members)
    centroid_matrix = np.vstack([centroids[cluster_id] for cluster_id in cluster_ids])
    centroid_similarities = centroid_matrix @ centroid_matrix.T
    record_by_id = {int(record["id"]): record for record in records}

    summaries: list[dict[str, Any]] = []
    for cluster_position, cluster_id in enumerate(cluster_ids):
        member_ids = sorted(cluster_members[cluster_id])
        member_indices = [index_by_id[member_id] for member_id in member_ids]
        member_matrix = matrix[member_indices]
        centroid = centroids[cluster_id]
        scores = member_matrix @ centroid
        representative_order = np.argsort(scores)[::-1][:max_representatives]
        representative_ids = [member_ids[index] for index in representative_order]
        documents = [record_by_id[member_id].get("cluster_document", "") for member_id in member_ids]
        keywords = extract_cluster_keywords(documents, max_keywords=max_keywords)
        accepted_for_counts: dict[str, int] = {}
        for member_id in member_ids:
            accepted_for = record_by_id[member_id].get("accepted_for") or "Unknown"
            accepted_for_counts[str(accepted_for)] = accepted_for_counts.get(str(accepted_for), 0) + 1
        similarity_row = centroid_similarities[cluster_position].copy()
        similarity_row[cluster_position] = -1.0
        nearest_cluster_position = int(np.argmax(similarity_row))
        nearest_cluster_id = cluster_ids[nearest_cluster_position]

        summaries.append(
            {
                "cluster_id": cluster_id,
                "size": len(member_ids),
                "label": ", ".join(keywords[:3]) if keywords else f"Cluster {cluster_id}",
                "keywords": keywords,
                "accepted_for_counts": accepted_for_counts,
                "representative_abstracts": [
                    {
                        "id": member_id,
                        "title": record_by_id[member_id].get("title") or "",
                    }
                    for member_id in representative_ids
                ],
                "most_similar_cluster_id": nearest_cluster_id,
                "most_similar_cluster_score": float(similarity_row[nearest_cluster_position]),
            }
        )
    return summaries


def summarize_stage2_clusters(
    ids: list[int],
    matrix: Any,
    records: list[dict[str, Any]],
    assignments: dict[int, int],
    max_keywords: int = 8,
    max_representatives: int = 5,
) -> list[dict[str, Any]]:
    return summarize_semantic_clusters(
        ids,
        matrix,
        records,
        assignments,
        max_keywords=max_keywords,
        max_representatives=max_representatives,
    )


def write_semantic_analysis(
    output_dir: Path,
    graph: Any,
    community_result: dict[str, Any],
    cluster_summaries: list[dict[str, Any]],
) -> None:
    import networkx as nx

    output_dir.mkdir(parents=True, exist_ok=True)
    graphml_graph = nx.relabel_nodes(graph, lambda node: str(node))
    nx.write_graphml(graphml_graph, output_dir / "article_similarity.graphml")
    write_json(
        output_dir / "community_detection.json",
        {
            "best_resolution": community_result["best_resolution"],
            "best_modularity": community_result["best_modularity"],
            "history": community_result["history"],
        },
    )
    write_json(
        output_dir / "cluster_assignments.json",
        {
            "assignments": {
                str(abstract_id): cluster_id
                for abstract_id, cluster_id in sorted(community_result["assignments"].items())
            }
        },
    )
    write_json(output_dir / "cluster_summaries.json", {"clusters": cluster_summaries})


def write_stage2_analysis(
    output_dir: Path,
    graph: Any,
    community_result: dict[str, Any],
    cluster_summaries: list[dict[str, Any]],
) -> None:
    write_semantic_analysis(output_dir, graph, community_result, cluster_summaries)


def build_minilm_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate local MiniLM embeddings for OHBM 2026 abstracts")
    parser.add_argument("--input", default="data/abstracts_enriched.json")
    parser.add_argument("--title-input", default="data/abstracts.json")
    parser.add_argument("--embeddings-dir", default="data/embeddings")
    parser.add_argument("--minilm-model", default=DEFAULT_MINILM_MODEL)
    parser.add_argument("--fields", nargs="+", default=list(DEFAULT_EMBEDDING_FIELDS))
    return parser


def minilm_main(argv: list[str] | None = None) -> int:
    args = build_minilm_parser().parse_args(argv)
    abstracts = load_embedding_inputs(Path(args.input))
    embedding_fields = normalize_embedding_fields(args.fields)
    title_lookup = load_title_lookup(Path(args.title_input)) if "title" in embedding_fields else None
    embedding_texts = build_embedding_texts(abstracts, embedding_fields, title_lookup=title_lookup)
    output_dir = Path(args.embeddings_dir) / f"minilm_{embedding_variant_name(embedding_fields)}"
    vectors = minilm_embed(embedding_texts, model_name=args.minilm_model)
    bundle = write_embedding_bundle(
        output_dir,
        output_dir.name,
        args.minilm_model,
        abstracts,
        vectors,
        embedding_fields=embedding_fields,
    )
    write_json(output_dir / "neighbors.json", compute_neighbors(bundle["ids"], bundle["matrix"]))
    print(
        json.dumps(
            {
                "input": args.input,
                "title_input": args.title_input,
                "embeddings_dir": str(output_dir),
                "model_name": args.minilm_model,
                "embedding_fields": embedding_fields,
                "abstract_count": len(abstracts),
            },
            indent=2,
        )
    )
    return 0


def build_voyage_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Voyage embeddings for OHBM 2026 abstracts")
    parser.add_argument("--input", default="data/abstracts_enriched.json")
    parser.add_argument("--title-input", default="data/abstracts.json")
    parser.add_argument("--embeddings-dir", default="data/embeddings")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--voyage-api-var", default="VOYAGE_API")
    parser.add_argument("--voyage-model", default=DEFAULT_VOYAGE_MODEL)
    parser.add_argument("--fields", nargs="+", default=list(DEFAULT_EMBEDDING_FIELDS))
    return parser


def voyage_main(argv: list[str] | None = None) -> int:
    from ohbm2026.graphql_api import get_api_key

    args = build_voyage_parser().parse_args(argv)
    abstracts = load_embedding_inputs(Path(args.input))
    embedding_fields = normalize_embedding_fields(args.fields)
    title_lookup = load_title_lookup(Path(args.title_input)) if "title" in embedding_fields else None
    embedding_texts = build_embedding_texts(abstracts, embedding_fields, title_lookup=title_lookup)
    output_dir = Path(args.embeddings_dir) / f"voyage_{embedding_variant_name(embedding_fields)}"
    vectors = voyage_embed(
        embedding_texts,
        get_api_key(Path(args.env_file), args.voyage_api_var),
        model=args.voyage_model,
    )
    bundle = write_embedding_bundle(
        output_dir,
        output_dir.name,
        args.voyage_model,
        abstracts,
        vectors,
        embedding_fields=embedding_fields,
    )
    write_json(output_dir / "neighbors.json", compute_neighbors(bundle["ids"], bundle["matrix"]))
    print(
        json.dumps(
            {
                "input": args.input,
                "title_input": args.title_input,
                "embeddings_dir": str(output_dir),
                "model_name": args.voyage_model,
                "embedding_fields": embedding_fields,
                "abstract_count": len(abstracts),
            },
            indent=2,
        )
    )
    return 0


def build_stage2_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train and apply a local NeuroScape stage-2 model from an existing stage-1 embedding bundle"
    )
    parser.add_argument("--stage1-dir", default="data/embeddings/minilm_stage1")
    parser.add_argument("--output-dir", default="data/embeddings/neuroscape_stage2_local")
    parser.add_argument("--device")
    parser.add_argument("--hidden-dimensions", nargs="+", type=int, default=list(DEFAULT_STAGE2_HIDDEN_DIMENSIONS))
    parser.add_argument("--output-dimension", type=int, default=DEFAULT_STAGE2_OUTPUT_DIMENSION)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--validation-size", type=float, default=0.05)
    parser.add_argument("--initial-learning-rate", type=float, default=1e-4)
    parser.add_argument("--minimum-learning-rate", type=float, default=1e-5)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--positive-cutoff", type=float, default=0.85)
    parser.add_argument("--negative-cutoff", type=float, default=0.75)
    parser.add_argument("--correlation-weight", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--report-every", type=int, default=10)
    return parser


def stage2_main(argv: list[str] | None = None) -> int:
    args = build_stage2_parser().parse_args(argv)
    stage1_bundle = load_stage1_bundle(Path(args.stage1_dir))
    hidden_dimensions = normalize_hidden_dimensions(args.hidden_dimensions)
    model, training_summary = train_stage2_model(
        stage1_bundle["matrix"],
        hidden_dimensions=hidden_dimensions,
        output_dimension=args.output_dimension,
        dropout=args.dropout,
        epochs=args.epochs,
        batch_size=args.batch_size,
        validation_size=args.validation_size,
        initial_learning_rate=args.initial_learning_rate,
        minimum_learning_rate=args.minimum_learning_rate,
        temperature=args.temperature,
        cutoff_values=(args.positive_cutoff, args.negative_cutoff),
        correlation_weight=args.correlation_weight,
        seed=args.seed,
        device=args.device,
        report_every=args.report_every,
    )
    projected_matrix = apply_stage2_model(
        model,
        stage1_bundle["matrix"],
        batch_size=args.batch_size,
        device=training_summary["device"],
    )
    write_stage2_bundle(
        Path(args.output_dir),
        stage1_bundle,
        projected_matrix,
        model,
        training_summary,
        hidden_dimensions=hidden_dimensions,
        output_dimension=args.output_dimension,
        dropout=args.dropout,
    )
    print(
        json.dumps(
            {
                "stage1_dir": args.stage1_dir,
                "output_dir": args.output_dir,
                "count": len(stage1_bundle["ids"]),
                "device": training_summary["device"],
                "best_validation_loss": training_summary["best_validation_loss"],
                "epochs": args.epochs,
            },
            indent=2,
        )
    )
    return 0


def build_semantic_analysis_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a semantic graph, detect communities, and summarize clusters from a local embedding bundle"
    )
    parser.add_argument("--embeddings-dir", default="data/embeddings/minilm_stage1")
    parser.add_argument("--input", default="data/abstracts_enriched.json")
    parser.add_argument("--title-input", default="data/abstracts.json")
    parser.add_argument("--output-dir", default="data/embeddings/minilm_stage1/semantic_analysis")
    parser.add_argument("--num-neighbors", type=int, default=50)
    parser.add_argument("--num-resolution-parameter", type=int, default=20)
    parser.add_argument("--max-resolution-parameter", type=float, default=1.0)
    parser.add_argument("--max-keywords", type=int, default=8)
    parser.add_argument("--max-representatives", type=int, default=5)
    return parser


def semantic_analysis_main(argv: list[str] | None = None) -> int:
    args = build_semantic_analysis_parser().parse_args(argv)
    bundle = load_embedding_bundle(Path(args.embeddings_dir))
    title_lookup = load_title_lookup(Path(args.title_input))
    enriched_lookup = load_enriched_lookup(Path(args.input))
    records = align_semantic_records(bundle["ids"], enriched_lookup, title_lookup=title_lookup)
    graph = build_knn_graph(bundle["ids"], bundle["matrix"], num_neighbors=args.num_neighbors)
    community_result = detect_semantic_communities(
        graph,
        num_resolution_parameter=args.num_resolution_parameter,
        max_resolution_parameter=args.max_resolution_parameter,
    )
    cluster_summaries = summarize_semantic_clusters(
        bundle["ids"],
        bundle["matrix"],
        records,
        community_result["assignments"],
        max_keywords=args.max_keywords,
        max_representatives=args.max_representatives,
    )
    write_semantic_analysis(Path(args.output_dir), graph, community_result, cluster_summaries)
    print(
        json.dumps(
            {
                "embeddings_dir": args.embeddings_dir,
                "output_dir": args.output_dir,
                "node_count": len(bundle["ids"]),
                "edge_count": int(graph.number_of_edges()),
                "cluster_count": len(cluster_summaries),
                "best_resolution": community_result["best_resolution"],
                "best_modularity": community_result["best_modularity"],
            },
            indent=2,
        )
    )
    return 0


def build_stage2_analysis_parser() -> argparse.ArgumentParser:
    parser = build_semantic_analysis_parser()
    parser.description = (
        "Compatibility alias for semantic analysis from a local embedding bundle"
    )
    return parser


def stage2_analysis_main(argv: list[str] | None = None) -> int:
    argv = list(argv or [])
    translated_argv: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--stage2-dir":
            translated_argv.append("--embeddings-dir")
        else:
            translated_argv.append(token)
        index += 1
    return semantic_analysis_main(translated_argv)


def build_umap_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Project a local embedding bundle to 2D with UMAP and write an interactive Plotly HTML"
    )
    parser.add_argument("--embeddings-dir", default="data/embeddings/minilm_stage1")
    parser.add_argument("--raw-input", default="data/abstracts.json")
    parser.add_argument("--enriched-input", default="data/abstracts_enriched.json")
    parser.add_argument("--output-html", default="data/embeddings/minilm_stage1/umap_2d.html")
    parser.add_argument("--output-json", default="data/embeddings/minilm_stage1/umap_2d.json")
    parser.add_argument("--n-neighbors", type=int, default=DEFAULT_UMAP_NEIGHBORS)
    parser.add_argument("--min-dist", type=float, default=DEFAULT_UMAP_MIN_DIST)
    parser.add_argument("--metric", default="cosine")
    parser.add_argument("--random-state", type=int, default=42)
    return parser


def umap_main(argv: list[str] | None = None) -> int:
    args = build_umap_parser().parse_args(argv)
    bundle = load_embedding_bundle(Path(args.embeddings_dir))
    annotations = load_annotation_lookup(Path(args.raw_input), Path(args.enriched_input))
    records = build_visualization_records(bundle["ids"], annotations)
    coordinates = compute_umap_projection(
        bundle["matrix"],
        n_neighbors=args.n_neighbors,
        min_dist=args.min_dist,
        metric=args.metric,
        random_state=args.random_state,
    )
    write_umap_outputs(
        Path(args.output_html),
        Path(args.output_json),
        coordinates,
        records,
        title="OHBM 2026 Abstract Embeddings UMAP",
    )
    print(
        json.dumps(
            {
                "embeddings_dir": args.embeddings_dir,
                "raw_input": args.raw_input,
                "enriched_input": args.enriched_input,
                "output_html": args.output_html,
                "output_json": args.output_json,
                "count": len(records),
                "n_neighbors": args.n_neighbors,
                "min_dist": args.min_dist,
                "metric": args.metric,
            },
            indent=2,
        )
    )
    return 0


def build_manifest_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write the NeuroScape handoff manifest for OHBM 2026 embeddings")
    parser.add_argument("--output", default="data/embeddings/neuroscape_stage2_manifest.json")
    return parser


def manifest_main(argv: list[str] | None = None) -> int:
    args = build_manifest_parser().parse_args(argv)
    write_neuroscape_manifest(Path(args.output))
    print(json.dumps({"output": args.output}, indent=2))
    return 0
