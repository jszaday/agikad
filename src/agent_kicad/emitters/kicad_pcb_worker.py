from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pcbnew


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(
            "usage: kicad_pcb_worker.py <graph.json> <constraints.json> "
            "<footprints_dir> <board.kicad_pcb>",
            file=sys.stderr,
        )
        return 2
    graph = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    constraints = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    footprints_dir = Path(argv[3])
    board_path = Path(argv[4])
    try:
        _emit_board(graph, constraints, footprints_dir, board_path)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def _emit_board(
    graph: dict[str, Any],
    constraints: dict[str, Any],
    footprints_dir: Path,
    board_path: Path,
) -> None:
    board = pcbnew.BOARD()
    pcb = constraints.get("pcb", {})
    board_spec = pcb.get("board", {})
    width = float(board_spec.get("width_mm", 120))
    height = float(board_spec.get("height_mm", 80))
    margin = float(board_spec.get("margin_mm", 5))

    no_connect_net_names = _no_connect_net_names(graph)
    net_by_name = _create_nets(board, graph, no_connect_net_names)
    _apply_netclasses(board, pcb.get("net_classes", []))
    _draw_outline(board, width, height)

    placements = _placements_by_component(pcb.get("placements", []))
    auto_index = 0
    pin_nets = _pin_net_map(graph, no_connect_net_names)
    for component in graph["components"]:
        if not component.get("on_board", True):
            continue
        footprint_id = component.get("footprint")
        if not footprint_id:
            raise ValueError(f"{component['id']}: on-board component has no footprint")
        footprint = _load_footprint(footprints_dir, footprint_id)
        footprint.SetFPIDAsString(footprint_id)
        footprint.SetReference(component["id"])
        footprint.SetValue(component.get("value") or footprint_id.split(":", 1)[1])
        x, y, rotation = placements.get(component["id"], _auto_xy(auto_index, margin))
        auto_index += 1
        footprint.SetPosition(_v(x, y))
        footprint.SetOrientationDegrees(float(rotation))
        for pad in footprint.Pads():
            net_name = pin_nets.get((component["id"], pad.GetNumber()))
            if net_name is not None:
                pad.SetNet(net_by_name[net_name])
        board.Add(footprint)

    board_path.parent.mkdir(parents=True, exist_ok=True)
    pcbnew.SaveBoard(str(board_path), board)


def _create_nets(
    board: Any, graph: dict[str, Any], no_connect_net_names: dict[tuple[str, str], str]
) -> dict[str, Any]:
    nets: dict[str, Any] = {}
    for name in [
        *[net["name"] for net in graph["nets"]],
        *no_connect_net_names.values(),
    ]:
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        nets[name] = item
    return nets


def _apply_netclasses(board: Any, netclasses: list[dict[str, Any]]) -> None:
    settings = board.GetDesignSettings().m_NetSettings
    for spec in netclasses:
        name = spec["name"]
        netclass = pcbnew.NETCLASS(name)
        if "track_width_mm" in spec:
            netclass.SetTrackWidth(pcbnew.FromMM(float(spec["track_width_mm"])))
        if "clearance_mm" in spec:
            netclass.SetClearance(pcbnew.FromMM(float(spec["clearance_mm"])))
        if "via_diameter_mm" in spec:
            netclass.SetViaDiameter(pcbnew.FromMM(float(spec["via_diameter_mm"])))
        if "via_drill_mm" in spec:
            netclass.SetViaDrill(pcbnew.FromMM(float(spec["via_drill_mm"])))
        settings.SetNetclass(name, netclass)
        names = pcbnew.STRINGSET()
        names.add(name)
        for net_name in spec.get("nets", []):
            settings.SetNetclassLabelAssignment(net_name, names)


def _draw_outline(board: Any, width: float, height: float) -> None:
    points = [(0, 0), (width, 0), (width, height), (0, height)]
    for start, end in zip(points, [*points[1:], points[0]]):
        line = pcbnew.PCB_SHAPE(board)
        line.SetShape(pcbnew.SHAPE_T_SEGMENT)
        line.SetLayer(pcbnew.Edge_Cuts)
        line.SetStart(_v(*start))
        line.SetEnd(_v(*end))
        board.Add(line)


def _placements_by_component(
    placements: list[dict[str, Any]],
) -> dict[str, tuple[float, float, float]]:
    return {
        item["component"]: (
            float(item["x_mm"]),
            float(item["y_mm"]),
            float(item.get("rotation", 0)),
        )
        for item in placements
    }


def _pin_net_map(
    graph: dict[str, Any], no_connect_net_names: dict[tuple[str, str], str]
) -> dict[tuple[str, str], str]:
    mapping: dict[tuple[str, str], str] = {}
    for net in graph["nets"]:
        for pin in net["connections"]:
            mapping[(pin["component"], pin["pin_number"])] = net["name"]
    mapping.update(no_connect_net_names)
    return mapping


def _no_connect_net_names(graph: dict[str, Any]) -> dict[tuple[str, str], str]:
    return {
        (pin["component"], pin["pin_number"]): (
            f"unconnected-({pin['component']}-{pin['pin_name']}-Pad{pin['pin_number']})"
        )
        for pin in graph.get("no_connects", [])
    }


def _load_footprint(footprints_dir: Path, footprint_id: str) -> Any:
    library, name = footprint_id.split(":", 1)
    library_path = footprints_dir / f"{library}.pretty"
    if not library_path.exists():
        raise ValueError(f"footprint library not found: {library}")
    footprint = pcbnew.FootprintLoad(str(library_path), name)
    if footprint is None:
        raise ValueError(f"footprint not found: {footprint_id}")
    return footprint


def _auto_xy(index: int, margin: float) -> tuple[float, float, float]:
    col = index % 8
    row = index // 8
    return margin + col * 15, margin + row * 12, 0


def _v(x_mm: float, y_mm: float) -> Any:
    return pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
