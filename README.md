# agent-kicad

Agent-oriented scaffolding for turning a structured connection prompt into KiCad artifacts.

The repository currently implements the first deterministic layer recommended by `SPEC.md`:

- a lean connection-spec contract for prompts to target
- KiCad 10 CLI discovery
- KiCad library indexing for bundled `.kicad_sym` files
- semantic validation of components, footprints, nets, and pins
- normalized graph output suitable for later SKiDL or `.kicad_sch` backends
- an optional MCP server exposing the same operations as tools

Routing is intentionally out of scope. The next generation step should emit either SKiDL netlists for a fast MVP or modern `.kicad_sch` files for the long-term editable schematic path.

## Quick Start

```sh
python -m agent_kicad.cli doctor
python -m agent_kicad.cli search-symbols --query Conn_01x03 --library Connector_Generic
python -m agent_kicad.cli search-footprints --query PinHeader_1x03 --library Connector_PinHeader_2.54mm
python -m agent_kicad.cli validate examples/divider_demo.json
python -m agent_kicad.cli normalize examples/divider_demo.json --output build/divider_demo.graph.json
python -m agent_kicad.cli emit-skidl examples/divider_demo.json --output build/divider_demo.py --netlist-output divider_demo.net --run
python -m agent_kicad.cli emit-skidl-schematic examples/divider_demo.json --output build/divider_demo_schematic.py --schematic-dir build/schematic --run
```

If running from a fresh checkout without installing the package:

```sh
PYTHONPATH=src python -m agent_kicad.cli validate examples/divider_demo.json
```

## MCP Server

Install the optional MCP dependency, then run:

```sh
pip install -e '.[mcp]'
agent-kicad-mcp
```

Available tools:

- `kicad_doctor`: report KiCad CLI/library discovery
- `list_symbol_libraries`: list installed KiCad symbol libraries
- `search_available_symbols`: search installed symbols and return pin metadata
- `list_footprint_libraries`: list installed KiCad footprint libraries
- `search_available_footprints`: search installed footprints
- `validate_connection_spec`: validate JSON against the contract and installed KiCad libraries
- `normalize_connection_spec`: return the canonical graph as JSON
- `emit_skidl_script`: render a SKiDL Python script from a validated connection spec
- `emit_skidl_schematic_script`: render a SKiDL Python script that generates `.kicad_sch`
- `write_skidl_script`: write a SKiDL Python script to a local path
- `inspect_symbol`: inspect a symbol's resolved pins

Use the discovery tools before drafting a connection spec. The agent should choose real `lib_id` and `footprint` values from the KiCad application bundle, then validate the resulting spec before generation.

## SKiDL Emitter

The first emitter targets SKiDL because it gives a fast netlist-first path. It writes a deterministic Python script from the normalized graph and can optionally execute it if `skidl` is installed:

```sh
pip install -e '.[skidl]'
agent-kicad emit-skidl examples/divider_demo.json --output build/divider_demo.py --netlist-output divider_demo.net --run
agent-kicad emit-skidl-schematic examples/divider_demo.json --output build/divider_demo_schematic.py --schematic-dir build/schematic --run
```

The generated script points SKiDL at the KiCad app bundle's symbol and footprint libraries and keeps SKiDL cache/config files under the output directory.

The schematic command is a prototype bridge, not the final editable-schematic backend. It uses SKiDL's `generate_schematic(auto_stub=True)` path, so KiCad can load/export the result, but ERC may still report layout-generator artifacts such as dangling labels, power-driver warnings, or library-copy mismatch warnings.

## Current Boundary

The code validates and normalizes a well-formed prompt output and can emit SKiDL scripts for netlist and prototype schematic generation. The durable direct `.kicad_sch` backend is tracked in `TODO.md`.
