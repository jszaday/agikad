from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .emitters.kicad_sch import emit_kicad_schematic_project
from .emitters.skidl import emit_skidl_script as write_skidl_file
from .emitters.skidl import render_skidl_script
from .footprints import (
    index_footprints,
    list_footprint_libraries as available_footprint_libraries,
    search_footprints,
)
from .graph import build_graph, validate_semantics
from .kicad import discover_kicad
from .spec import parse_spec, validate_shape
from .symbols import (
    index_symbols_for_lib_ids,
    list_symbol_libraries as available_symbol_libraries,
    read_symbol_library,
    search_symbols,
)


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit("Install MCP support with: pip install -e '.[mcp]'") from exc

    mcp = FastMCP("agent-kicad")

    @mcp.tool()
    def kicad_doctor() -> dict[str, object]:
        """Report discovered KiCad CLI and library locations."""
        return asdict(discover_kicad())

    @mcp.tool()
    def validate_connection_spec(spec_json: str) -> dict[str, object]:
        """Validate a connection-spec JSON string against KiCad libraries."""
        errors, _graph = _validate_json(spec_json)
        return {"ok": not errors, "errors": errors}

    @mcp.tool()
    def normalize_connection_spec(spec_json: str) -> dict[str, object]:
        """Return the normalized circuit graph for a connection-spec JSON string."""
        errors, graph = _validate_json(spec_json)
        if errors:
            return {"ok": False, "errors": errors}
        assert graph is not None
        return {"ok": True, "graph": graph.to_dict()}

    @mcp.tool()
    def emit_skidl_script(spec_json: str) -> dict[str, object]:
        """Render a SKiDL Python script for a validated connection spec."""
        errors, graph = _validate_json(spec_json)
        if errors:
            return {"ok": False, "errors": errors}
        assert graph is not None
        env = discover_kicad()
        return {
            "ok": True,
            "script": render_skidl_script(
                graph, symbols_dir=env.symbols_dir, footprints_dir=env.footprints_dir
            ),
        }

    @mcp.tool()
    def emit_skidl_schematic_script(
        spec_json: str, schematic_dir: str, top_name: str = ""
    ) -> dict[str, object]:
        """Render a SKiDL Python script that generates a KiCad schematic."""
        errors, graph = _validate_json(spec_json)
        if errors:
            return {"ok": False, "errors": errors}
        assert graph is not None
        env = discover_kicad()
        return {
            "ok": True,
            "script": render_skidl_script(
                graph,
                schematic_dir=Path(schematic_dir),
                schematic_top_name=top_name or graph.project.name,
                symbols_dir=env.symbols_dir,
                footprints_dir=env.footprints_dir,
            ),
        }

    @mcp.tool()
    def write_skidl_script(spec_json: str, output_path: str) -> dict[str, object]:
        """Write a SKiDL Python script to a local path."""
        errors, graph = _validate_json(spec_json)
        if errors:
            return {"ok": False, "errors": errors}
        assert graph is not None
        env = discover_kicad()
        output = write_skidl_file(
            graph,
            Path(output_path),
            symbols_dir=env.symbols_dir,
            footprints_dir=env.footprints_dir,
        )
        return {"ok": True, "path": str(output)}

    @mcp.tool()
    def write_kicad_schematic_project(
        spec_json: str, out_dir: str
    ) -> dict[str, object]:
        """Write a direct KiCad .kicad_pro/.kicad_sch project."""
        errors, graph = _validate_json(spec_json)
        if errors:
            return {"ok": False, "errors": errors}
        assert graph is not None
        env = discover_kicad()
        if env.symbols_dir is None:
            return {"ok": False, "errors": ["KiCad symbol directory was not found"]}
        project_path, schematic_path = emit_kicad_schematic_project(
            graph, Path(out_dir), env.symbols_dir
        )
        return {
            "ok": True,
            "project_path": str(project_path),
            "schematic_path": str(schematic_path),
        }

    @mcp.tool()
    def inspect_symbol(lib_id: str) -> dict[str, object]:
        """Inspect a KiCad symbol and its resolved pin table."""
        env = discover_kicad()
        if env.symbols_dir is None:
            return {"ok": False, "errors": ["KiCad symbol directory was not found"]}
        library, _, name = lib_id.partition(":")
        if not library or not name:
            return {"ok": False, "errors": ["lib_id must look like 'Device:R'"]}
        path = env.symbols_dir / f"{library}.kicad_sym"
        if not path.exists():
            return {"ok": False, "errors": [f"library not found: {library}"]}
        symbols = {symbol.lib_id: symbol for symbol in read_symbol_library(path)}
        symbol = symbols.get(lib_id)
        if symbol is None:
            return {"ok": False, "errors": [f"symbol not found: {lib_id}"]}
        return {"ok": True, "symbol": asdict(symbol)}

    @mcp.tool()
    def list_symbol_libraries(query: str = "", limit: int = 200) -> dict[str, object]:
        """List KiCad symbol libraries available from the app bundle."""
        env = discover_kicad()
        if env.symbols_dir is None:
            return {"ok": False, "errors": ["KiCad symbol directory was not found"]}
        query_norm = query.casefold() if query else None
        libraries = [
            library
            for library in available_symbol_libraries(env.symbols_dir)
            if query_norm is None or query_norm in library.casefold()
        ][:limit]
        return {"ok": True, "libraries": libraries}

    @mcp.tool()
    def search_available_symbols(
        query: str = "", library: str = "", limit: int = 50
    ) -> dict[str, object]:
        """Search KiCad symbols available from the app bundle."""
        env = discover_kicad()
        if env.symbols_dir is None:
            return {"ok": False, "errors": ["KiCad symbol directory was not found"]}
        symbols = search_symbols(
            env.symbols_dir, query=query or None, library=library or None, limit=limit
        )
        return {"ok": True, "symbols": [asdict(symbol) for symbol in symbols]}

    @mcp.tool()
    def list_footprint_libraries(
        query: str = "", limit: int = 200
    ) -> dict[str, object]:
        """List KiCad footprint libraries available from the app bundle."""
        env = discover_kicad()
        if env.footprints_dir is None:
            return {"ok": False, "errors": ["KiCad footprint directory was not found"]}
        query_norm = query.casefold() if query else None
        libraries = [
            library
            for library in available_footprint_libraries(env.footprints_dir)
            if query_norm is None or query_norm in library.casefold()
        ][:limit]
        return {"ok": True, "libraries": libraries}

    @mcp.tool()
    def search_available_footprints(
        query: str = "", library: str = "", limit: int = 50
    ) -> dict[str, object]:
        """Search KiCad footprints available from the app bundle."""
        env = discover_kicad()
        if env.footprints_dir is None:
            return {"ok": False, "errors": ["KiCad footprint directory was not found"]}
        footprints = search_footprints(
            env.footprints_dir,
            query=query or None,
            library=library or None,
            limit=limit,
        )
        return {"ok": True, "footprints": footprints}

    mcp.run()


def _validate_json(spec_json: str):
    raw = json.loads(spec_json)
    errors = validate_shape(raw)
    if errors:
        return errors, None
    spec = parse_spec(raw)
    env = discover_kicad()
    if env.symbols_dir is None:
        return ["KiCad symbol directory was not found"], None
    symbols = index_symbols_for_lib_ids(
        env.symbols_dir, {component.lib_id for component in spec.components}
    )
    footprints = index_footprints(env.footprints_dir)
    errors = validate_semantics(spec, symbols, footprints)
    if errors:
        return errors, None
    return [], build_graph(spec, symbols)


if __name__ == "__main__":
    main()
