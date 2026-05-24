from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from agent_kicad.models import CircuitGraph


def emit_kicad_pcb_project(
    graph: CircuitGraph,
    constraints_path: Path,
    out_dir: Path,
    footprints_dir: Path,
    kicad_python: Path,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    project_name = graph.project.name
    project_path = out_dir / f"{project_name}.kicad_pro"
    board_path = out_dir / f"{project_name}.kicad_pcb"
    if not project_path.exists():
        project_path.write_text(_render_project(project_name), encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="agent-kicad-pcb-") as tmp:
        graph_path = Path(tmp) / "graph.json"
        graph_path.write_text(json.dumps(graph.to_dict()), encoding="utf-8")
        worker = Path(__file__).with_name("kicad_pcb_worker.py")
        proc = subprocess.run(
            [
                str(kicad_python),
                str(worker),
                str(graph_path),
                str(constraints_path),
                str(footprints_dir),
                str(board_path),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip()
        raise RuntimeError(message or "KiCad PCB emitter failed")
    return project_path, board_path


def _render_project(project_name: str) -> str:
    return (
        json.dumps(
            {
                "meta": {"filename": f"{project_name}.kicad_pro", "version": 1},
                "board": {},
                "schematic": {},
            },
            indent=2,
        )
        + "\n"
    )
