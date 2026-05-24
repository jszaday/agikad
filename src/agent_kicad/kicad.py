from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_KICAD_APP = Path("/Applications/KiCad/KiCad.app")


@dataclass(frozen=True)
class KiCadEnvironment:
    cli: Path | None
    python: Path | None
    version: str | None
    shared_support: Path | None
    symbols_dir: Path | None
    footprints_dir: Path | None


def discover_kicad(app_path: Path = DEFAULT_KICAD_APP) -> KiCadEnvironment:
    cli = _find_cli(app_path)
    python = _find_python(app_path)
    version = _run_version(cli) if cli else None
    shared = app_path / "Contents" / "SharedSupport"
    if not shared.exists():
        shared = None
    symbols = shared / "symbols" if shared else None
    footprints = shared / "footprints" if shared else None
    return KiCadEnvironment(
        cli=cli,
        python=python,
        version=version,
        shared_support=shared,
        symbols_dir=symbols if symbols and symbols.exists() else None,
        footprints_dir=footprints if footprints and footprints.exists() else None,
    )


def run_kicad_cli(
    args: list[str], env: KiCadEnvironment | None = None
) -> subprocess.CompletedProcess[str]:
    env = env or discover_kicad()
    if env.cli is None:
        raise FileNotFoundError("kicad-cli was not found")
    return subprocess.run(
        [str(env.cli), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "KICAD_RUN_FROM_BUILD_DIR": "0"},
    )


def _find_cli(app_path: Path) -> Path | None:
    bundled = app_path / "Contents" / "MacOS" / "kicad-cli"
    if bundled.exists():
        return bundled
    found = shutil.which("kicad-cli")
    return Path(found) if found else None


def _find_python(app_path: Path) -> Path | None:
    bundled = (
        app_path
        / "Contents"
        / "Frameworks"
        / "Python.framework"
        / "Versions"
        / "3.9"
        / "bin"
        / "python3"
    )
    return bundled if bundled.exists() else None


def _run_version(cli: Path) -> str | None:
    proc = subprocess.run(
        [str(cli), "--version"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None
