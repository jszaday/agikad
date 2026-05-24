from __future__ import annotations

from pathlib import Path


def index_footprints(footprints_dir: Path | None) -> set[str]:
    if footprints_dir is None:
        return set()
    footprints: set[str] = set()
    for pretty in sorted(footprints_dir.glob("*.pretty")):
        library = pretty.stem
        for mod in pretty.glob("*.kicad_mod"):
            footprints.add(f"{library}:{mod.stem}")
    return footprints


def list_footprint_libraries(footprints_dir: Path) -> list[str]:
    return [path.stem for path in sorted(footprints_dir.glob("*.pretty"))]


def search_footprints(
    footprints_dir: Path,
    query: str | None = None,
    library: str | None = None,
    limit: int = 50,
) -> list[dict[str, str]]:
    query_norm = query.casefold() if query else None
    paths = (
        [footprints_dir / f"{library}.pretty"]
        if library
        else sorted(footprints_dir.glob("*.pretty"))
    )
    results: list[dict[str, str]] = []
    for path in paths:
        if not path.exists():
            continue
        for mod in sorted(path.glob("*.kicad_mod")):
            footprint_id = f"{path.stem}:{mod.stem}"
            if query_norm and query_norm not in footprint_id.casefold():
                continue
            results.append(
                {
                    "footprint": footprint_id,
                    "library": path.stem,
                    "name": mod.stem,
                    "path": str(mod),
                }
            )
            if len(results) >= limit:
                return results
    return results
