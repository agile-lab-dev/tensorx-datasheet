#!/usr/bin/env -S uv run
# Install uv: https://docs.astral.sh/uv/getting-started/installation/
# Manage dependencies with: uv add --script tensorx-datasheet.py <package>
#                            uv remove --script tensorx-datasheet.py <package>
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",
#     "typer>=0.12",
#     "rich>=13",
# ]
# ///
"""tensorx-datasheet.py — Build a Bifrost pricing datasheet from TensorX + Bifrost.

Fetches the live model catalogue from ``https://sys.tensorx.ai/api/models``,
rewrites each entry into the schema used by ``https://getbifrost.ai/datasheet``
(a flat JSON object keyed by model id, with numeric token costs, ``mode``,
``provider``, ``base_model``, token limits, capability flags, and metadata
notes), then concats it on top of the official Bifrost datasheet: all Bifrost
models are kept, and for models present in both the TensorX entry wins (fields
are merged per-model, with TensorX values taking precedence).

Usage:
    uv run tensorx-datasheet.py --output data.json --provider tensorx
    uv run tensorx-datasheet.py --output data.json --provider none --verbose
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, TypedDict

import httpx
import typer
from rich import print as rprint

logger = logging.getLogger(__name__)

MODELS_URL = "https://sys.tensorx.ai/api/models"
BIFROST_DATASHEET_URL = "https://getbifrost.ai/datasheet"

# ---------------------------------------------------------------------------
# Typed models (external payloads → TypedDict; internal data → dataclass)
# ---------------------------------------------------------------------------


class TensorXModel(TypedDict):
    """A single entry from the TensorX models API."""

    id: str
    model_id: str
    model_name: str
    provider: str
    input_cost_per_token: str | None
    output_cost_per_token: str | None
    cache_read_input_token_cost: str | None
    max_tokens: int | None
    max_input_tokens: int | None
    max_output_tokens: int | None
    supports_vision: bool
    supports_function_calling: bool
    supports_tool_choice: bool
    supports_reasoning: bool
    description: str | None
    icon_url: str | None
    featured: bool


class TensorXPayload(TypedDict):
    """Top-level response envelope of the models API."""

    data: list[TensorXModel]


@dataclass(frozen=True)
class NormalizedModel:
    """Internal, validated representation of a TensorX model."""

    model_id: str
    provider: str
    input_cost_per_token: float | None
    output_cost_per_token: float | None
    cache_read_input_token_cost: float | None
    max_tokens: int | None
    max_input_tokens: int | None
    max_output_tokens: int | None
    supports_vision: bool
    supports_function_calling: bool
    supports_tool_choice: bool
    supports_reasoning: bool
    description: str | None


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------


def fetch_models(client: httpx.Client) -> list[TensorXModel]:
    """Fetch and return the raw model list from the TensorX API."""
    response = client.get(MODELS_URL)
    response.raise_for_status()
    payload: TensorXPayload = response.json()
    return payload["data"]


def fetch_bifrost_datasheet(client: httpx.Client) -> dict[str, dict[str, Any]]:
    """Fetch the Bifrost datasheet: a map of model id -> entry."""
    response = client.get(BIFROST_DATASHEET_URL)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Transformation
# ---------------------------------------------------------------------------


def parse_cost(value: str | None) -> float | None:
    """Parse a decimal-string cost from the API into a float, or None."""
    return float(value) if value is not None else None


def normalize_model(raw: TensorXModel) -> NormalizedModel:
    """Validate and normalize a raw TensorX model entry."""
    return NormalizedModel(
        model_id=raw["model_id"],
        provider=raw["provider"],
        input_cost_per_token=parse_cost(raw["input_cost_per_token"]),
        output_cost_per_token=parse_cost(raw["output_cost_per_token"]),
        cache_read_input_token_cost=parse_cost(raw["cache_read_input_token_cost"]),
        max_tokens=raw["max_tokens"],
        max_input_tokens=raw["max_input_tokens"],
        max_output_tokens=raw["max_output_tokens"],
        supports_vision=raw["supports_vision"],
        supports_function_calling=raw["supports_function_calling"],
        supports_tool_choice=raw["supports_tool_choice"],
        supports_reasoning=raw["supports_reasoning"],
        description=raw["description"],
    )


def base_model_of(model_id: str) -> str:
    """Strip the provider prefix from a ``provider/name`` model id."""
    return model_id.split("/", 1)[1] if "/" in model_id else model_id


def to_datasheet_entry(
    model: NormalizedModel, provider: str = "tensorx"
) -> dict[str, Any]:
    """Map a normalized model into a Bifrost datasheet entry.

    ``provider`` overrides the API-provided provider unless it is exactly
    ``"none"``, in which case the fetched provider is kept.
    """
    entry: dict[str, Any] = {
        "mode": "chat",
        "provider": model.provider if provider == "none" else provider,
        "base_model": base_model_of(model.model_id),
    }
    if model.max_input_tokens is not None:
        entry["max_input_tokens"] = model.max_input_tokens
    if model.max_output_tokens is not None:
        entry["max_output_tokens"] = model.max_output_tokens
    if model.max_tokens is not None:
        entry["max_tokens"] = model.max_tokens
    if model.input_cost_per_token is not None:
        entry["input_cost_per_token"] = model.input_cost_per_token
    if model.output_cost_per_token is not None:
        entry["output_cost_per_token"] = model.output_cost_per_token
    if model.cache_read_input_token_cost is not None:
        entry["cache_read_input_token_cost"] = model.cache_read_input_token_cost
    if model.supports_vision:
        entry["supports_vision"] = True
    if model.supports_function_calling:
        entry["supports_function_calling"] = True
    if model.supports_tool_choice:
        entry["supports_tool_choice"] = True
    if model.supports_reasoning:
        entry["supports_reasoning"] = True
    if model.description:
        entry["metadata"] = {"notes": model.description}
    return entry


def build_datasheet(
    raw_models: list[TensorXModel],
    prefix: str = "tensorx",
    provider: str = "tensorx",
) -> dict[str, dict[str, Any]]:
    """Build the Bifrost datasheet map from raw TensorX models.

    Each model id is namespaced with ``prefix`` (e.g. ``tensorx/gpt-4o``);
    an empty prefix keeps the raw model id. ``provider`` overrides each
    entry's provider unless it is exactly ``"none"``.
    """
    prefix = prefix.strip("/")
    return {
        f"{prefix}/{model['model_id']}" if prefix else model["model_id"]: to_datasheet_entry(
            normalize_model(model), provider
        )
        for model in raw_models
    }


def merge_datasheets(
    bifrost: dict[str, dict[str, Any]], tensorx: dict[str, dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Merge the Bifrost datasheet with the TensorX one; on clashing keys TensorX wins.

    Returns the merged datasheet and the list of clashing model ids (in
    definition order), i.e. the models where a TensorX entry won over a
    Bifrost one.
    """
    merged = dict(bifrost)
    clashed: list[str] = []
    for model_id, tx_entry in tensorx.items():
        if model_id not in merged:
            merged[model_id] = tx_entry
            continue
        clashed.append(model_id)
        entry = {**merged[model_id], **tx_entry}
        metadata = {**merged[model_id].get("metadata", {}), **tx_entry.get("metadata", {})}
        if metadata:
            entry["metadata"] = metadata
        else:
            entry.pop("metadata", None)
        for field in tx_entry:
            old = merged[model_id].get(field)
            new = entry[field]
            if old != new:
                logger.debug("%s: TensorX wins %s: %r -> %r", model_id, field, old, new)
        merged[model_id] = entry
    return merged, clashed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Path of the JSON datasheet file to write.",
        ),
    ],
    prefix: Annotated[
        str,
        typer.Option(
            "--prefix",
            "-p",
            help="Prefix added to TensorX model ids, e.g. PREFIX/<model-id>. "
            "Pass an empty string to disable prefixing.",
        ),
    ] = "tensorx",
    provider: Annotated[
        str,
        typer.Option(
            "--provider",
            help='Provider written into TensorX entries; pass exactly "none" '
            "to keep the provider from the TensorX API.",
        ),
    ] = "tensorx",
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging."),
    ] = False,
) -> None:
    """Fetch TensorX + Bifrost data and write the merged datasheet to OUTPUT."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    rprint(f"[bold cyan]Fetching[/] models from {MODELS_URL}")
    try:
        with httpx.Client(timeout=30.0) as client:
            raw_models = fetch_models(client)
            rprint(f"[bold cyan]Fetching[/] datasheet from {BIFROST_DATASHEET_URL}")
            bifrost = fetch_bifrost_datasheet(client)
    except httpx.HTTPError as exc:
        rprint(f"[bold red]Error:[/] failed to fetch: {exc}")
        raise typer.Exit(code=1) from exc

    tensorx_sheet = build_datasheet(raw_models, prefix=prefix, provider=provider)
    datasheet, clashed = merge_datasheets(bifrost, tensorx_sheet)
    rprint(
        f"[bold green]Converted[/] {len(tensorx_sheet)} TensorX models, "
        f"merged with {len(bifrost)} Bifrost entries -> {len(datasheet)} models"
    )
    if clashed:
        rprint(
            f"[bold yellow]Overridden[/] {len(clashed)} Bifrost entries "
            "(TensorX wins): " + ", ".join(clashed)
        )

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(datasheet, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        rprint(f"[bold red]Error:[/] failed to write {output}: {exc}")
        raise typer.Exit(code=1) from exc

    rprint(f"[bold green]Wrote[/] {output}")


if __name__ == "__main__":
    typer.run(main)