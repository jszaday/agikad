from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

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
