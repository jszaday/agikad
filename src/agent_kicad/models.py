from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

PinShape = Literal["input", "output", "bidirectional", "tri_state", "passive"]
NetScope = Literal["local", "global", "hierarchical"]


@dataclass(frozen=True)
class PlacementHint:
    x: float | None = None
    y: float | None = None
    rotation: float | None = None


@dataclass(frozen=True)
class ComponentSpec:
    id: str
    lib_id: str
    value: str | None = None
    footprint: str | None = None
    unit: int = 1
    sheet: str = "root"
    in_bom: bool = True
    on_board: bool = True
    fields: dict[str, str] = field(default_factory=dict)
    pin_aliases: dict[str, str] = field(default_factory=dict)
    placement_hint: PlacementHint | None = None


@dataclass(frozen=True)
class PinRef:
    component: str
    pin_number: str | None = None
    pin_name: str | None = None
    unit: int | None = None


@dataclass(frozen=True)
class NetSpec:
    name: str
    connections: list[PinRef]
    scope: NetScope = "local"
    power: bool = False
    label_shape: PinShape = "passive"
    sheet: str = "root"


@dataclass(frozen=True)
class SheetInterface:
    name: str
    shape: PinShape = "passive"


@dataclass(frozen=True)
class SheetSpec:
    id: str
    name: str
    parent: str | None = None
    filename: str | None = None
    interfaces: list[SheetInterface] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectSpec:
    name: str
    target_kicad_version: str | None = None
    root_sheet: str = "root"
    library_policy: Literal["project-local", "global-ok"] = "project-local"


@dataclass(frozen=True)
class ConnectionSpec:
    version: str
    project: ProjectSpec
    components: list[ComponentSpec]
    nets: list[NetSpec]
    sheets: list[SheetSpec] = field(default_factory=list)
    no_connects: list[PinRef] = field(default_factory=list)


@dataclass(frozen=True)
class SymbolPin:
    number: str
    name: str
    type: str
    unit: int


@dataclass(frozen=True)
class SymbolInfo:
    lib_id: str
    library: str
    name: str
    path: str
    reference_prefix: str | None
    pins: list[SymbolPin]


@dataclass(frozen=True)
class ResolvedPin:
    component: str
    lib_id: str
    unit: int
    pin_number: str
    pin_name: str
    pin_type: str


@dataclass(frozen=True)
class ResolvedNet:
    name: str
    scope: NetScope
    power: bool
    label_shape: PinShape
    sheet: str
    connections: list[ResolvedPin]


@dataclass(frozen=True)
class CircuitGraph:
    project: ProjectSpec
    components: list[ComponentSpec]
    nets: list[ResolvedNet]
    sheets: list[SheetSpec]
    no_connects: list[ResolvedPin] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
