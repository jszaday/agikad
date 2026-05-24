from __future__ import annotations

from pathlib import Path

from .models import SymbolInfo, SymbolPin
from .sexpr import SExpr, children, first_child, head, parse_sexpr


def index_symbol_libraries(symbols_dir: Path) -> dict[str, SymbolInfo]:
    index: dict[str, SymbolInfo] = {}
    for path in sorted(symbols_dir.glob("*.kicad_sym")):
        for symbol in read_symbol_library(path):
            index[symbol.lib_id] = symbol
    return index


def index_symbols_for_lib_ids(
    symbols_dir: Path, lib_ids: set[str]
) -> dict[str, SymbolInfo]:
    libraries = {lib_id.split(":", 1)[0] for lib_id in lib_ids if ":" in lib_id}
    index: dict[str, SymbolInfo] = {}
    for library in sorted(libraries):
        path = symbols_dir / f"{library}.kicad_sym"
        if not path.exists():
            continue
        for symbol in read_symbol_library(path):
            if symbol.lib_id in lib_ids:
                index[symbol.lib_id] = symbol
    return index


def list_symbol_libraries(symbols_dir: Path) -> list[str]:
    return [path.stem for path in sorted(symbols_dir.glob("*.kicad_sym"))]


def search_symbols(
    symbols_dir: Path,
    query: str | None = None,
    library: str | None = None,
    limit: int = 50,
) -> list[SymbolInfo]:
    query_norm = query.casefold() if query else None
    paths = (
        [symbols_dir / f"{library}.kicad_sym"]
        if library
        else sorted(symbols_dir.glob("*.kicad_sym"))
    )
    results: list[SymbolInfo] = []
    for path in paths:
        if not path.exists():
            continue
        for symbol in read_symbol_library(path):
            haystack = f"{symbol.lib_id} {symbol.reference_prefix or ''}".casefold()
            if query_norm and query_norm not in haystack:
                continue
            results.append(symbol)
            if len(results) >= limit:
                return results
    return results


def read_symbol_library(path: Path) -> list[SymbolInfo]:
    parsed = parse_sexpr(path.read_text(encoding="utf-8"))
    if (
        not parsed
        or not isinstance(parsed[0], list)
        or head(parsed[0]) != "kicad_symbol_lib"
    ):
        raise ValueError(f"{path} is not a KiCad symbol library")
    library_name = path.stem
    symbols: list[SymbolInfo] = []
    for expr in children(parsed[0], "symbol"):
        if len(expr) < 2 or not isinstance(expr[1], str):
            continue
        name = expr[1]
        if "_" in name and name.rsplit("_", 2)[-1].isdigit():
            continue
        pins = _symbol_pins(expr)
        reference = _property_value(expr, "Reference")
        symbols.append(
            SymbolInfo(
                lib_id=f"{library_name}:{name}",
                library=library_name,
                name=name,
                path=str(path),
                reference_prefix=reference,
                pins=pins,
            )
        )
    return symbols


def _symbol_pins(symbol: list[SExpr]) -> list[SymbolPin]:
    pins: list[SymbolPin] = []
    for nested in children(symbol, "symbol"):
        nested_name = (
            nested[1] if len(nested) > 1 and isinstance(nested[1], str) else ""
        )
        unit = _unit_from_nested_name(nested_name)
        for pin in children(nested, "pin"):
            if len(pin) < 3:
                continue
            pin_type = pin[1] if isinstance(pin[1], str) else "unspecified"
            name = _pin_text(pin, "name")
            number = _pin_text(pin, "number")
            if number is None:
                continue
            pins.append(
                SymbolPin(number=number, name=name or "", type=pin_type, unit=unit)
            )
    return _dedupe_pins(pins)


def _pin_text(pin: list[SExpr], child_name: str) -> str | None:
    child = first_child(pin, child_name)
    if child and len(child) > 1 and isinstance(child[1], str):
        return child[1]
    return None


def _unit_from_nested_name(name: str) -> int:
    parts = name.rsplit("_", 2)
    if len(parts) == 3 and parts[1].isdigit():
        return int(parts[1])
    return 1


def _property_value(symbol: list[SExpr], property_name: str) -> str | None:
    for prop in children(symbol, "property"):
        if len(prop) > 2 and prop[1] == property_name and isinstance(prop[2], str):
            return prop[2]
    return None


def _dedupe_pins(pins: list[SymbolPin]) -> list[SymbolPin]:
    seen: set[tuple[int, str, str]] = set()
    out: list[SymbolPin] = []
    for pin in pins:
        key = (pin.unit, pin.number, pin.name)
        if key in seen:
            continue
        seen.add(key)
        out.append(pin)
    return out
