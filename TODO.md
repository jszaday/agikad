# TODO

## Direct KiCad schematic emitter

Status: initial labels-only single-sheet backend exists. Keep hardening it.

Build a production `.kicad_sch` backend from `CircuitGraph`.

Initial scope:

- [x] Emit KiCad 10-compatible `.kicad_pro` and `.kicad_sch`.
- [x] Use deterministic UUIDs derived from project/component/net identities.
- [x] Place symbols on a simple grid using `placement_hint` when present.
- [x] Prefer net labels for the first version; routed wires can come later.
- [x] Preserve `in_bom`, `on_board`, footprints, and fields.
- [x] Validate generated schematics with `kicad-cli sch erc` and `sch export netlist`.
- [ ] Preserve and emit sheet intent/hierarchy.
- [ ] Add routed-wire output for simple two-pin and low-fanout nets.
- [ ] Add richer `.kicad_pro` defaults instead of a sparse project file.
- [ ] Add golden connectivity tests comparing source graph to KiCad-exported netlist.

The SKiDL schematic emitter is a quick prototype path. This direct backend should become the durable editable-KiCad output path.

## Direct KiCad PCB emitter

Status: initial placed, net-aware `.kicad_pcb` backend exists. It emits board outline, footprints, component placement, pad net assignment, no-connect parity nets, and net classes, but does not route copper yet.

Physical constraint scope:

- [x] Add a formal PCB constraint schema for board outline, stackup, net classes, placement regions, keepouts, and routing intent.
- [x] Add semantic validation for PCB constraints, including unknown component ids, unknown net names, invalid layer counts, missing footprints, and duplicate/conflicting placements.
- [ ] Add a compact placement mode that reduces empty board space while preserving probe access and hand-assembly clearance.
- [ ] Make oscillator placement footprint-aware enough to keep crystals physically tight to MCU XTAL pins without courtyard or silkscreen violations.
- [x] Add constraint-driven silkscreen labels for connector pinouts, warnings, and design intent notes such as fail-safe fan behavior and high-current regions.
- [ ] Add generated default silkscreen labels derived from connector pin metadata and high-level design intent.
- [ ] Support decoupling-capacitor constraints that assign each capacitor to a parent component power pin and ground pin.
- [ ] Place assigned capacitors as close as possible to the assigned pin to minimize impedance between the capacitor and pin.
- [ ] Sort same-parent decoupling capacitors from smallest to largest capacitance before placement.
- [ ] Parse common capacitance units (`uF`, `µF`, `nF`, `pF`, etc.) and normalize to nF for placement calculations.
- [ ] Prefer capacitor connections with as few vias as possible, ideally no vias on the capacitor-to-pin current loop.
- [ ] Support oscillator/crystal placement constraints tied to parent component pins.
- [ ] Place oscillators/crystals as close as possible to their parent pins and avoid vias where practical.
- [ ] Support differential-pair constraints with matched length, controlled spacing, and target impedance metadata.
- [ ] Treat impedance-controlled differential pairs as requiring 4+ layer stackups so the router can assume an uninterrupted ground-plane return path.
- [ ] Run impedance calculations at 1 GHz for constraints that request controlled impedance.
- [ ] Add router integration or a deterministic routing stage after placement; current DRC unconnected-items reports are expected until this exists.
- [ ] Add a generated-board fixture for `examples/dual_p3_thermal_controller.json` that asserts zero schematic parity issues and zero non-routing DRC violations when KiCad CLI is available.
