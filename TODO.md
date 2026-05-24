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
