from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    ComponentSpec,
    ConnectionSpec,
    NetSpec,
    PinRef,
    PlacementHint,
    ProjectSpec,
    SheetInterface,
    SheetSpec,
)

PIN_SHAPES = {"input", "output", "bidirectional", "tri_state", "passive"}
NET_SCOPES = {"local", "global", "hierarchical"}


def load_spec(path: Path) -> ConnectionSpec:
    return parse_spec(json.loads(path.read_text(encoding="utf-8")))


def parse_spec(data: dict[str, Any]) -> ConnectionSpec:
    project = data.get("project", {})
    return ConnectionSpec(
        version=data.get("version", ""),
        project=ProjectSpec(
            name=project.get("name", ""),
            target_kicad_version=project.get("target_kicad_version"),
            root_sheet=project.get("root_sheet", "root"),
            library_policy=project.get("library_policy", "project-local"),
        ),
        components=[_component(c) for c in data.get("components", [])],
        nets=[_net(n) for n in data.get("nets", [])],
        sheets=[_sheet(s) for s in data.get("sheets", [])],
    )


def validate_shape(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != "0.1":
        errors.append("version must be '0.1'")
    project = data.get("project")
    if not isinstance(project, dict) or not project.get("name"):
        errors.append("project.name is required")
    components = data.get("components")
    if not isinstance(components, list) or not components:
        errors.append("components must be a non-empty array")
    else:
        for i, component in enumerate(components):
            _validate_component_shape(component, i, errors)
    nets = data.get("nets")
    if not isinstance(nets, list) or not nets:
        errors.append("nets must be a non-empty array")
    else:
        for i, net in enumerate(nets):
            _validate_net_shape(net, i, errors)
    return errors


def _validate_component_shape(component: Any, i: int, errors: list[str]) -> None:
    if not isinstance(component, dict):
        errors.append(f"components[{i}] must be an object")
        return
    if not component.get("id"):
        errors.append(f"components[{i}].id is required")
    lib_id = component.get("lib_id")
    if not isinstance(lib_id, str) or ":" not in lib_id:
        errors.append(f"components[{i}].lib_id must be a KiCad lib_id like 'Device:R'")
    if "unit" in component and (
        not isinstance(component["unit"], int) or component["unit"] < 1
    ):
        errors.append(f"components[{i}].unit must be a positive integer")


def _validate_net_shape(net: Any, i: int, errors: list[str]) -> None:
    if not isinstance(net, dict):
        errors.append(f"nets[{i}] must be an object")
        return
    if not net.get("name"):
        errors.append(f"nets[{i}].name is required")
    scope = net.get("scope", "local")
    if scope not in NET_SCOPES:
        errors.append(f"nets[{i}].scope must be one of {sorted(NET_SCOPES)}")
    label_shape = net.get("label_shape", "passive")
    if label_shape not in PIN_SHAPES:
        errors.append(f"nets[{i}].label_shape must be one of {sorted(PIN_SHAPES)}")
    connections = net.get("connections")
    if not isinstance(connections, list) or len(connections) < 2:
        errors.append(f"nets[{i}].connections must contain at least two pins")
        return
    for j, conn in enumerate(connections):
        if not isinstance(conn, dict):
            errors.append(f"nets[{i}].connections[{j}] must be an object")
            continue
        if not conn.get("component"):
            errors.append(f"nets[{i}].connections[{j}].component is required")
        if not conn.get("pin_number") and not conn.get("pin_name"):
            errors.append(f"nets[{i}].connections[{j}] requires pin_number or pin_name")


def _component(data: dict[str, Any]) -> ComponentSpec:
    placement = data.get("placement_hint")
    return ComponentSpec(
        id=data["id"],
        lib_id=data["lib_id"],
        value=data.get("value"),
        footprint=data.get("footprint"),
        unit=data.get("unit", 1),
        sheet=data.get("sheet", "root"),
        in_bom=data.get("in_bom", True),
        on_board=data.get("on_board", True),
        fields=data.get("fields", {}),
        pin_aliases=data.get("pin_aliases", {}),
        placement_hint=PlacementHint(**placement)
        if isinstance(placement, dict)
        else None,
    )


def _net(data: dict[str, Any]) -> NetSpec:
    return NetSpec(
        name=data["name"],
        scope=data.get("scope", "local"),
        power=data.get("power", False),
        label_shape=data.get("label_shape", "passive"),
        sheet=data.get("sheet", "root"),
        connections=[PinRef(**pin) for pin in data["connections"]],
    )


def _sheet(data: dict[str, Any]) -> SheetSpec:
    return SheetSpec(
        id=data["id"],
        name=data["name"],
        parent=data.get("parent"),
        filename=data.get("filename"),
        interfaces=[
            SheetInterface(name=i["name"], shape=i.get("shape", "passive"))
            for i in data.get("interfaces", [])
        ],
    )
