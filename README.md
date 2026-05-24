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
- `inspect_symbol`: inspect a symbol's resolved pins

Use the discovery tools before drafting a connection spec. The agent should choose real `lib_id` and `footprint` values from the KiCad application bundle, then validate the resulting spec before generation.

## Current Boundary

The code validates and normalizes a well-formed prompt output. It does not yet emit `.kicad_sch`. That is a deliberate boundary from `SPEC.md`: keep the agent-facing IR stable, prove symbol and pin resolution first, then add emitters behind the same graph.
