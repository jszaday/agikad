from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .emitters.kicad_pcb import emit_kicad_pcb_project
from .emitters.kicad_sch import emit_kicad_schematic_project
from .emitters.skidl import emit_skidl_script, run_skidl_script
from .footprints import index_footprints, list_footprint_libraries, search_footprints
from .graph import build_graph, validate_semantics
from .kicad import discover_kicad
from .spec import load_spec, validate_shape
from .symbols import (
    index_symbols_for_lib_ids,
    list_symbol_libraries,
    read_symbol_library,
    search_symbols,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-kicad")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")

    validate = sub.add_parser("validate")
    validate.add_argument("spec", type=Path)

    normalize = sub.add_parser("normalize")
    normalize.add_argument("spec", type=Path)
    normalize.add_argument("--output", "-o", type=Path)

    emit_skidl = sub.add_parser("emit-skidl")
    emit_skidl.add_argument("spec", type=Path)
    emit_skidl.add_argument("--output", "-o", type=Path, required=True)
    emit_skidl.add_argument("--netlist-output", type=Path)
    emit_skidl.add_argument("--run", action="store_true")

    emit_schematic = sub.add_parser("emit-skidl-schematic")
    emit_schematic.add_argument("spec", type=Path)
    emit_schematic.add_argument("--output", "-o", type=Path, required=True)
    emit_schematic.add_argument("--schematic-dir", type=Path, required=True)
    emit_schematic.add_argument("--top-name")
    emit_schematic.add_argument("--run", action="store_true")

    emit_kicad = sub.add_parser("emit-kicad-schematic")
    emit_kicad.add_argument("spec", type=Path)
    emit_kicad.add_argument("--out-dir", type=Path, required=True)

    emit_pcb = sub.add_parser("emit-kicad-pcb")
    emit_pcb.add_argument("spec", type=Path)
    emit_pcb.add_argument("--constraints", type=Path, required=True)
    emit_pcb.add_argument("--out-dir", type=Path, required=True)

    inspect = sub.add_parser("inspect-symbol")
    inspect.add_argument("lib_id")

    symbol_libs = sub.add_parser("list-symbol-libraries")
    symbol_libs.add_argument("--query")
    symbol_libs.add_argument("--limit", type=int, default=200)

    symbols = sub.add_parser("search-symbols")
    symbols.add_argument("--query")
    symbols.add_argument("--library")
    symbols.add_argument("--limit", type=int, default=50)

    footprint_libs = sub.add_parser("list-footprint-libraries")
    footprint_libs.add_argument("--query")
    footprint_libs.add_argument("--limit", type=int, default=200)

    footprints = sub.add_parser("search-footprints")
    footprints.add_argument("--query")
    footprints.add_argument("--library")
    footprints.add_argument("--limit", type=int, default=50)

    args = parser.parse_args(argv)
    if args.command == "doctor":
        return _doctor()
    if args.command == "validate":
        return _validate(args.spec)
    if args.command == "normalize":
        return _normalize(args.spec, args.output)
    if args.command == "emit-skidl":
        return _emit_skidl(args.spec, args.output, args.netlist_output, args.run)
    if args.command == "emit-skidl-schematic":
        return _emit_skidl_schematic(
            args.spec, args.output, args.schematic_dir, args.top_name, args.run
        )
    if args.command == "emit-kicad-schematic":
        return _emit_kicad_schematic(args.spec, args.out_dir)
    if args.command == "emit-kicad-pcb":
        return _emit_kicad_pcb(args.spec, args.constraints, args.out_dir)
    if args.command == "inspect-symbol":
        return _inspect_symbol(args.lib_id)
    if args.command == "list-symbol-libraries":
        return _list_symbol_libraries(args.query, args.limit)
    if args.command == "search-symbols":
        return _search_symbols(args.query, args.library, args.limit)
    if args.command == "list-footprint-libraries":
        return _list_footprint_libraries(args.query, args.limit)
    if args.command == "search-footprints":
        return _search_footprints(args.query, args.library, args.limit)
    return 2


def _doctor() -> int:
    env = discover_kicad()
    print(json.dumps(asdict(env), indent=2, default=str))
    return 0 if env.cli and env.symbols_dir and env.footprints_dir else 1


def _validate(path: Path) -> int:
    errors, _graph = _validate_and_graph(path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"{path}: ok")
    return 0


def _normalize(path: Path, output: Path | None) -> int:
    errors, graph = _validate_and_graph(path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    assert graph is not None
    payload = json.dumps(graph.to_dict(), indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
        print(str(output))
    else:
        print(payload)
    return 0


def _emit_skidl(
    path: Path, output: Path, netlist_output: Path | None, run: bool
) -> int:
    errors, graph = _validate_and_graph(path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    assert graph is not None
    env = discover_kicad()
    emit_skidl_script(
        graph,
        output,
        netlist_output=netlist_output,
        symbols_dir=env.symbols_dir,
        footprints_dir=env.footprints_dir,
    )
    print(str(output))
    if not run:
        return 0
    proc = run_skidl_script(output)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    return proc.returncode


def _emit_skidl_schematic(
    path: Path,
    output: Path,
    schematic_dir: Path,
    top_name: str | None,
    run: bool,
) -> int:
    errors, graph = _validate_and_graph(path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    assert graph is not None
    env = discover_kicad()
    emit_skidl_script(
        graph,
        output,
        schematic_dir=schematic_dir,
        schematic_top_name=top_name or graph.project.name,
        symbols_dir=env.symbols_dir,
        footprints_dir=env.footprints_dir,
    )
    print(str(output))
    if not run:
        return 0
    proc = run_skidl_script(output)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")
    return proc.returncode


def _emit_kicad_schematic(path: Path, out_dir: Path) -> int:
    errors, graph = _validate_and_graph(path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    assert graph is not None
    env = discover_kicad()
    if env.symbols_dir is None:
        print("KiCad symbol directory was not found", file=sys.stderr)
        return 1
    project_path, schematic_path = emit_kicad_schematic_project(
        graph, out_dir=out_dir, symbols_dir=env.symbols_dir
    )
    print(str(project_path))
    print(str(schematic_path))
    return 0


def _emit_kicad_pcb(path: Path, constraints: Path, out_dir: Path) -> int:
    errors, graph = _validate_and_graph(path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    assert graph is not None
    env = discover_kicad()
    if env.footprints_dir is None:
        print("KiCad footprint directory was not found", file=sys.stderr)
        return 1
    if env.python is None:
        print("KiCad Python with pcbnew was not found", file=sys.stderr)
        return 1
    try:
        project_path, board_path = emit_kicad_pcb_project(
            graph,
            constraints_path=constraints,
            out_dir=out_dir,
            footprints_dir=env.footprints_dir,
            kicad_python=env.python,
        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(str(project_path))
    print(str(board_path))
    return 0


def _inspect_symbol(lib_id: str) -> int:
    env = discover_kicad()
    if env.symbols_dir is None:
        print("KiCad symbol directory was not found", file=sys.stderr)
        return 1
    library, _, name = lib_id.partition(":")
    if not library or not name:
        print("lib_id must look like 'Device:R'", file=sys.stderr)
        return 1
    path = env.symbols_dir / f"{library}.kicad_sym"
    if not path.exists():
        print(f"library not found: {library}", file=sys.stderr)
        return 1
    symbols = {symbol.lib_id: symbol for symbol in read_symbol_library(path)}
    symbol = symbols.get(lib_id)
    if symbol is None:
        print(f"symbol not found: {lib_id}", file=sys.stderr)
        return 1
    print(json.dumps(asdict(symbol), indent=2))
    return 0


def _list_symbol_libraries(query: str | None, limit: int) -> int:
    env = discover_kicad()
    if env.symbols_dir is None:
        print("KiCad symbol directory was not found", file=sys.stderr)
        return 1
    query_norm = query.casefold() if query else None
    libraries = [
        library
        for library in list_symbol_libraries(env.symbols_dir)
        if query_norm is None or query_norm in library.casefold()
    ][:limit]
    print(json.dumps(libraries, indent=2))
    return 0


def _search_symbols(query: str | None, library: str | None, limit: int) -> int:
    env = discover_kicad()
    if env.symbols_dir is None:
        print("KiCad symbol directory was not found", file=sys.stderr)
        return 1
    symbols = search_symbols(env.symbols_dir, query=query, library=library, limit=limit)
    print(json.dumps([asdict(symbol) for symbol in symbols], indent=2))
    return 0


def _list_footprint_libraries(query: str | None, limit: int) -> int:
    env = discover_kicad()
    if env.footprints_dir is None:
        print("KiCad footprint directory was not found", file=sys.stderr)
        return 1
    query_norm = query.casefold() if query else None
    libraries = [
        library
        for library in list_footprint_libraries(env.footprints_dir)
        if query_norm is None or query_norm in library.casefold()
    ][:limit]
    print(json.dumps(libraries, indent=2))
    return 0


def _search_footprints(query: str | None, library: str | None, limit: int) -> int:
    env = discover_kicad()
    if env.footprints_dir is None:
        print("KiCad footprint directory was not found", file=sys.stderr)
        return 1
    print(
        json.dumps(
            search_footprints(
                env.footprints_dir, query=query, library=library, limit=limit
            ),
            indent=2,
        )
    )
    return 0


def _validate_and_graph(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_shape(raw)
    if errors:
        return errors, None
    spec = load_spec(path)
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
    raise SystemExit(main())
