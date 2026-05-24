from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CircuitGraph


def load_pcb_constraints(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_pcb_constraint_shape(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != "0.1":
        errors.append("pcb constraints version must be '0.1'")
    pcb = data.get("pcb")
    if not isinstance(pcb, dict):
        return [*errors, "pcb must be an object"]
    board = pcb.get("board")
    if not isinstance(board, dict):
        errors.append("pcb.board must be an object")
    else:
        _validate_positive_number(board, "width_mm", "pcb.board", errors)
        _validate_positive_number(board, "height_mm", "pcb.board", errors)
        layers = board.get("layers", 2)
        if not isinstance(layers, int) or layers not in {2, 4, 6, 8}:
            errors.append("pcb.board.layers must be one of [2, 4, 6, 8]")
    for i, item in enumerate(pcb.get("placements", [])):
        path = f"pcb.placements[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{path} must be an object")
            continue
        _validate_required_string(item, "component", path, errors)
        _validate_number(item, "x_mm", path, errors)
        _validate_number(item, "y_mm", path, errors)
    for i, item in enumerate(pcb.get("net_classes", [])):
        path = f"pcb.net_classes[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{path} must be an object")
            continue
        _validate_required_string(item, "name", path, errors)
        for key in ("track_width_mm", "via_diameter_mm", "via_drill_mm"):
            if key in item:
                _validate_positive_number(item, key, path, errors)
        if "clearance_mm" in item:
            _validate_nonnegative_number(item, "clearance_mm", path, errors)
    for section in (
        "decoupling",
        "oscillators",
        "differential_pairs",
        "silkscreen_labels",
    ):
        items = pcb.get(section, [])
        if not isinstance(items, list):
            errors.append(f"pcb.{section} must be an array")
    return errors


def validate_pcb_constraint_semantics(
    constraints: dict[str, Any], graph: CircuitGraph
) -> list[str]:
    errors: list[str] = []
    pcb = constraints.get("pcb", {})
    board = pcb.get("board", {})
    layers = board.get("layers", 2) if isinstance(board, dict) else 2
    components = {component.id: component for component in graph.components}
    on_board_components = {
        component.id: component for component in graph.components if component.on_board
    }
    nets = {net.name for net in graph.nets}

    for component in on_board_components.values():
        if not component.footprint:
            errors.append(f"{component.id}: on-board component has no footprint")

    placed: set[str] = set()
    occupied: dict[tuple[float, float], str] = {}
    for i, item in enumerate(pcb.get("placements", [])):
        path = f"pcb.placements[{i}]"
        component_id = item.get("component")
        if component_id not in components:
            errors.append(
                f"{path}.component references unknown component: {component_id}"
            )
            continue
        if component_id in placed:
            errors.append(f"{path}.component duplicates placement for {component_id}")
        placed.add(component_id)
        xy = (float(item.get("x_mm", 0)), float(item.get("y_mm", 0)))
        if xy in occupied:
            errors.append(
                f"{path} conflicts with {occupied[xy]} at x={xy[0]} mm, y={xy[1]} mm"
            )
        occupied[xy] = component_id

    for i, item in enumerate(pcb.get("net_classes", [])):
        for net_name in item.get("nets", []):
            if net_name not in nets:
                errors.append(
                    f"pcb.net_classes[{i}].nets references unknown net: {net_name}"
                )

    for i, item in enumerate(pcb.get("decoupling", [])):
        _validate_component_ref(
            item, "capacitor", f"pcb.decoupling[{i}]", components, errors
        )
        _validate_component_ref(
            item, "parent", f"pcb.decoupling[{i}]", components, errors
        )

    for i, item in enumerate(pcb.get("oscillators", [])):
        _validate_component_ref(
            item, "component", f"pcb.oscillators[{i}]", components, errors
        )
        _validate_component_ref(
            item, "parent", f"pcb.oscillators[{i}]", components, errors
        )

    for i, item in enumerate(pcb.get("differential_pairs", [])):
        path = f"pcb.differential_pairs[{i}]"
        pair_nets = item.get("nets", [])
        if len(pair_nets) != 2:
            errors.append(f"{path}.nets must contain exactly two nets")
        for net_name in pair_nets:
            if net_name not in nets:
                errors.append(f"{path}.nets references unknown net: {net_name}")
        if item.get("target_impedance_ohm") is not None and layers < 4:
            errors.append(f"{path} requires a 4+ layer stackup for impedance control")
    return errors


def _validate_component_ref(
    item: dict[str, Any],
    key: str,
    path: str,
    components: dict[str, object],
    errors: list[str],
) -> None:
    component_id = item.get(key)
    if not isinstance(component_id, str) or not component_id:
        errors.append(f"{path}.{key} is required")
    elif component_id not in components:
        errors.append(f"{path}.{key} references unknown component: {component_id}")


def _validate_required_string(
    item: dict[str, Any], key: str, path: str, errors: list[str]
) -> None:
    if not isinstance(item.get(key), str) or not item[key]:
        errors.append(f"{path}.{key} is required")


def _validate_number(
    item: dict[str, Any], key: str, path: str, errors: list[str]
) -> None:
    if not isinstance(item.get(key), int | float):
        errors.append(f"{path}.{key} must be a number")


def _validate_positive_number(
    item: dict[str, Any], key: str, path: str, errors: list[str]
) -> None:
    if not isinstance(item.get(key), int | float) or item[key] <= 0:
        errors.append(f"{path}.{key} must be a positive number")


def _validate_nonnegative_number(
    item: dict[str, Any], key: str, path: str, errors: list[str]
) -> None:
    if not isinstance(item.get(key), int | float) or item[key] < 0:
        errors.append(f"{path}.{key} must be a nonnegative number")
