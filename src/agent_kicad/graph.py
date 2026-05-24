from __future__ import annotations

from .models import (
    CircuitGraph,
    ConnectionSpec,
    ResolvedNet,
    ResolvedPin,
    SymbolInfo,
    SymbolPin,
)


def validate_semantics(
    spec: ConnectionSpec, symbol_index: dict[str, SymbolInfo], footprints: set[str]
) -> list[str]:
    errors: list[str] = []
    component_ids = [component.id for component in spec.components]
    duplicates = sorted(
        {item for item in component_ids if component_ids.count(item) > 1}
    )
    for duplicate in duplicates:
        errors.append(f"duplicate component id: {duplicate}")
    components = {component.id: component for component in spec.components}
    for component in spec.components:
        if component.lib_id not in symbol_index:
            errors.append(f"{component.id}: symbol not found: {component.lib_id}")
        if component.footprint and footprints and component.footprint not in footprints:
            errors.append(f"{component.id}: footprint not found: {component.footprint}")
    for net in spec.nets:
        seen_on_net: set[tuple[str, str | None, str | None]] = set()
        for conn in net.connections:
            component = components.get(conn.component)
            if component is None:
                errors.append(f"{net.name}: unknown component {conn.component}")
                continue
            symbol = symbol_index.get(component.lib_id)
            if symbol is None:
                continue
            pin, pin_errors = resolve_pin(
                symbol, conn.pin_number, conn.pin_name, conn.unit or component.unit
            )
            errors.extend(f"{net.name}/{component.id}: {error}" for error in pin_errors)
            key = (
                conn.component,
                pin.number if pin else conn.pin_number,
                conn.pin_name,
            )
            if key in seen_on_net:
                errors.append(f"{net.name}: duplicate connection to {conn.component}")
            seen_on_net.add(key)
    for conn in spec.no_connects:
        component = components.get(conn.component)
        if component is None:
            errors.append(f"no_connects: unknown component {conn.component}")
            continue
        symbol = symbol_index.get(component.lib_id)
        if symbol is None:
            continue
        _pin, pin_errors = resolve_pin(
            symbol, conn.pin_number, conn.pin_name, conn.unit or component.unit
        )
        errors.extend(f"no_connects/{component.id}: {error}" for error in pin_errors)
    return errors


def build_graph(
    spec: ConnectionSpec, symbol_index: dict[str, SymbolInfo]
) -> CircuitGraph:
    components = {component.id: component for component in spec.components}
    nets: list[ResolvedNet] = []
    for net in spec.nets:
        resolved: list[ResolvedPin] = []
        for conn in net.connections:
            component = components[conn.component]
            symbol = symbol_index[component.lib_id]
            pin, errors = resolve_pin(
                symbol, conn.pin_number, conn.pin_name, conn.unit or component.unit
            )
            if pin is None:
                raise ValueError("; ".join(errors))
            resolved.append(
                ResolvedPin(
                    component=component.id,
                    lib_id=component.lib_id,
                    unit=pin.unit,
                    pin_number=pin.number,
                    pin_name=pin.name,
                    pin_type=pin.type,
                )
            )
        nets.append(
            ResolvedNet(
                name=net.name,
                scope=net.scope,
                power=net.power,
                label_shape=net.label_shape,
                sheet=net.sheet,
                connections=resolved,
            )
        )
    no_connects: list[ResolvedPin] = []
    for conn in spec.no_connects:
        component = components[conn.component]
        symbol = symbol_index[component.lib_id]
        pin, errors = resolve_pin(
            symbol, conn.pin_number, conn.pin_name, conn.unit or component.unit
        )
        if pin is None:
            raise ValueError("; ".join(errors))
        no_connects.append(
            ResolvedPin(
                component=component.id,
                lib_id=component.lib_id,
                unit=pin.unit,
                pin_number=pin.number,
                pin_name=pin.name,
                pin_type=pin.type,
            )
        )
    return CircuitGraph(
        project=spec.project,
        components=spec.components,
        nets=nets,
        sheets=spec.sheets,
        no_connects=no_connects,
    )


def resolve_pin(
    symbol: SymbolInfo,
    pin_number: str | None,
    pin_name: str | None,
    unit: int,
) -> tuple[SymbolPin | None, list[str]]:
    candidates = [pin for pin in symbol.pins if pin.unit in {unit, 0}]
    if pin_number:
        matches = [pin for pin in candidates if pin.number == pin_number]
    elif pin_name:
        matches = [pin for pin in candidates if pin.name == pin_name]
    else:
        return None, ["pin_number or pin_name is required"]
    if not matches:
        label = f"pin_number {pin_number}" if pin_number else f"pin_name {pin_name}"
        return None, [f"{label} not found on {symbol.lib_id} unit {unit}"]
    deduped = {(pin.unit, pin.number, pin.name, pin.type): pin for pin in matches}
    if len(deduped) > 1:
        return None, [
            f"pin reference is ambiguous on {symbol.lib_id}: {pin_name or pin_number}"
        ]
    return next(iter(deduped.values())), []
