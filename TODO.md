# TODO

## Direct KiCad schematic emitter

Build a production `.kicad_sch` backend from `CircuitGraph`.

Initial scope:

- Emit KiCad 10-compatible `.kicad_pro` and `.kicad_sch`.
- Use deterministic UUIDs derived from project/component/net identities.
- Place symbols on a simple grid using `placement_hint` when present.
- Prefer net labels for the first version; routed wires can come later.
- Preserve `in_bom`, `on_board`, footprints, fields, and sheet intent.
- Validate generated schematics with `kicad-cli sch erc` and `sch export netlist`.

The SKiDL schematic emitter is a quick prototype path. This direct backend should become the durable editable-KiCad output path.
