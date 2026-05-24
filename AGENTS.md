# AGENTS.md

This repository is building an agent-friendly KiCad schematic workflow. The core contract is a strict JSON connection spec that is normalized into a circuit graph, then emitted through deterministic backends and validated with KiCad itself.

## Environment

- Project root: `/Users/szaday2/workspace/agent-kicad`
- KiCad application bundle: `/Applications/KiCad/KiCad.app`
- KiCad version used during development: `10.0.1`
- KiCad CLI path on this machine: `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`
- Bundled symbols: `/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols`
- Bundled footprints: `/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints`
- Use the repo `.venv` Python from `PATH`.

## Common Commands

Run formatting and linting:

```sh
ruff format --check .
ruff check .
```

Validate a connection spec:

```sh
agent-kicad validate examples/divider_demo.json
agent-kicad validate examples/dual_p3_thermal_controller.json
```

Emit a direct KiCad schematic project:

```sh
agent-kicad emit-kicad-schematic examples/dual_p3_thermal_controller.json --out-dir build/dual_p3_direct
```

Run KiCad ERC:

```sh
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc --exit-code-violations build/dual_p3_direct/dual_p3_thermal_controller.kicad_sch
```

Export a KiCad netlist:

```sh
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch export netlist build/dual_p3_direct/dual_p3_thermal_controller.kicad_sch --output build/dual_p3_direct/dual_p3_thermal_controller.net
```

Compile-check changed Python modules:

```sh
python -m py_compile src/agent_kicad/emitters/kicad_sch.py src/agent_kicad/graph.py src/agent_kicad/models.py src/agent_kicad/spec.py src/agent_kicad/symbols.py
```

## CLI Capabilities

Useful implemented commands:

- `agent-kicad doctor`
- `agent-kicad validate <spec.json>`
- `agent-kicad normalize <spec.json>`
- `agent-kicad emit-skidl <spec.json> --out <file.py>`
- `agent-kicad emit-skidl-schematic <spec.json> --out-dir <dir>`
- `agent-kicad emit-kicad-schematic <spec.json> --out-dir <dir>`
- `agent-kicad inspect-symbol <Lib:Symbol>`
- `agent-kicad list-symbol-libraries`
- `agent-kicad search-symbols --query <text> [--library <Lib>]`
- `agent-kicad list-footprint-libraries`
- `agent-kicad search-footprints --query <text>`

The MCP server mirrors the important discovery, validation, normalization, and emitter operations. Prefer the CLI for local debugging and exact output.

## Design Contract

The agent-facing input is `schemas/connection-spec.schema.json`.

Important model concepts:

- `components`: KiCad `lib_id`, optional `value`, optional `footprint`, BOM/board flags, fields, pin aliases, placement hints.
- `nets`: named electrical connectivity, with pin references by number or name.
- `no_connects`: explicit unconnected pins; use this for unused MCU pins, unused IC channels, fan tach pins intentionally left open, and connector pins that are intentionally NC.
- `sheets`: planned hierarchical support; current direct emitter is essentially flat.

Canonical pin identity should be treated as `(component, unit, pin_number)`. Pin names are useful for prompting and discovery but are not stable enough as a primary key.

## Direct KiCad Emitter Notes

The direct `.kicad_sch` emitter is in `src/agent_kicad/emitters/kicad_sch.py`.

Current behavior:

- Emits sparse `.kicad_pro` plus `.kicad_sch`.
- Uses deterministic UUIDs.
- Embeds `lib_symbols` from the installed KiCad bundle.
- Places symbols on a simple grid unless `placement_hint` is supplied.
- Connects nets with `global_label` objects placed at pin terminals.
- Emits explicit `no_connect` markers for graph `no_connects`.

Important KiCad coordinate finding:

- Symbol pin coordinates are symbol-local.
- For unrotated symbol instances, sheet-space pin coordinates are `(symbol_x + pin_x, symbol_y - pin_y)`.
- Getting the Y sign wrong causes dangling labels and dangling no-connect markers in ERC.

Important inherited-symbol finding:

- KiCad libraries use `(extends "...")` aliases heavily.
- The symbol discovery layer resolves inherited symbols so aliases such as `MCU_Microchip_ATmega:ATmega328P-P`, `Interface_UART:MAX3232`, and `Transistor_FET:IRLZ44N` expose inherited pins correctly.
- KiCad ERC is strict about schematic cache symbols matching the installed library. Flattening inherited alias symbols into cached `lib_symbols` can produce `lib_symbol_mismatch` warnings even when connectivity is correct.
- The emitter now correctly handles inherited symbols (`extends`): it flattens the base geometry but merges the child symbol's property values (Value, Datasheet, Description, etc.) on top. Inherited alias `lib_id`s such as `Interface_UART:MAX3232` and `Transistor_FET:IRLZ44N` can now be used directly without ERC `lib_symbol_mismatch` warnings.

## KiCad ERC Expectations

ERC should be part of every non-trivial change to the emitter or examples.

Power nets from connectors and fuses usually need `power:PWR_FLAG` components. Without these, KiCad reports `power_pin_not_driven` for MCU/IC power pins even when the logical net is connected.

The dual PIII example should currently be ERC-clean:

```sh
agent-kicad emit-kicad-schematic examples/dual_p3_thermal_controller.json --out-dir build/dual_p3_direct
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli sch erc --exit-code-violations build/dual_p3_direct/dual_p3_thermal_controller.kicad_sch
```

Expected result:

```text
Found 0 violations
```

## Known Good Symbols And Footprints

Symbols verified or used:

- `Interface_UART:MAX3232` — use directly; emitter handles inherited symbol correctly.
- `Interface_UART:MAX232` — base symbol for MAX3232; no longer needed as a workaround.
- `MCU_Microchip_ATmega:ATmega328P-P` — inherited; use directly for ATmega328P-PU DIP-28. Pin numbers confirmed: 1=RESET, 2=PD0/RX, 3=PD1/TX, 7=VCC, 8=GND, 9=XTAL1, 10=XTAL2, 15=PB1/OC1A, 16=PB2/OC1B, 17=PB3/MOSI, 18=PB4/MISO, 19=PB5/SCK, 20=AVCC, 21=AREF, 22=GND, 23=PC0/ADC0, 24=PC1/ADC1.
- `MCU_Microchip_ATmega:ATmega48PV-10P` — non-inherited base; no longer needed as ATmega328P-P workaround.
- `Transistor_FET:IRLZ44N` — inherited; can now be used directly.
- `Transistor_FET:BUZ11` — base symbol for IRLZ44N; no longer needed as a workaround.
- `Device:Thermistor_NTC`
- `Device:Polyfuse`
- `Device:Crystal`
- `Device:FerriteBead`
- `Device:D_Schottky`
- `Device:D_TVS`
- `Device:LED`, pins `1=K`, `2=A`
- `Device:R`
- `Device:C`
- `Device:C_Polarized`; KiCad 10 here does not expose `Device:CP`
- `Connector_Generic:Conn_01x02`
- `Connector_Generic:Conn_01x03`
- `Connector_Generic:Conn_01x04`
- `Connector_Generic:Conn_01x06`
- `Connector_Generic:Conn_02x03_Odd_Even`
- `power:PWR_FLAG`, virtual `power_out` pin `1`

Footprints verified or used:

- `Package_DIP:DIP-28_W7.62mm_Socket`
- `Package_DIP:DIP-16_W7.62mm_Socket`
- `Package_TO_SOT_THT:TO-220-3_Vertical`
- `Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical`
- `Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical`
- `Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical`
- `Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical`
- `Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical`
- `Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal`
- `Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm`
- `Capacitor_THT:CP_Radial_D5.0mm_P2.50mm`
- `Crystal:Crystal_HC49-4H_Vertical`
- `Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal`
- `LED_THT:LED_D5.0mm`

Molex note:

- `Connector_Molex:Molex_KK-254_AE-6410-04A_1x04_P2.54mm_Vertical` — confirmed present; Berg/floppy-style 4-pin power connector, 2.54mm pitch. Used for the power inlet in the dual P3 example (low current budget fits easily within floppy connector ratings).
- `Connector_Molex:Molex_KK-396_5273-04A_1x04_P3.96mm_Vertical` — confirmed present; 3.96mm pitch 1x4, classic large peripheral Molex (HDD/optical drive power).
- `Connector_Molex:Molex_Mini-Fit_Jr_5566-04A_2x02_P4.20mm_Vertical` — confirmed present; ATX 4-pin CPU power connector (2x2, 4.20mm pitch). Not a peripheral power connector.

## Dual PIII Example

The current high-complexity example is `examples/dual_p3_thermal_controller.json`.

It models:

- PC peripheral-style power input with separate fused `+12V` and `+5V` rails.
- TVS protection, bulk capacitance, MCU/IC decoupling, and power flags.
- ATmega328P-PU intent on a DIP-28 footprint.
- 16 MHz crystal and load capacitors.
- Two thermistor divider/filter channels.
- Two low-side MOSFET 3-pin fan channels with default-on gate pullups.
- MAX3232-style RS232 telemetry.
- AVR ISP header.
- FTDI header with VCC and CTS intentionally NC.
- Explicit no-connects for unused MCU pins, spare MAX232/MAX3232 channel pins, fan tach pins, and FTDI NC pins.

## Development Rules

- Do not hand-edit generated files in `build/`; change specs or emitters instead.
- Keep root KiCad report/log artifacts ignored. `.gitignore` already ignores `build/`, `/*.erc`, `/*.log`, and `/*.rpt`.
- Run `ruff format --check .`, `ruff check .`, spec validation, direct schematic emission, KiCad ERC, and netlist export before committing emitter or example changes.
- Use `rg` and `rg --files` for searching.
- Use `apply_patch` for source edits.
- Do not use destructive git commands unless explicitly requested.

## Near-Term TODOs

- Add automated tests around inherited symbol resolution and KiCad pin-coordinate transforms.
- Add a test fixture that emits `examples/dual_p3_thermal_controller.json` and asserts ERC has zero violations when KiCad CLI is available.
- Improve direct emitter layout; current grid plus global labels is electrically valid but not human-optimized.
- Support drawn wires or grouped local labels for more readable schematics.
- Add hierarchy-aware emission for sheets and sheet pins.
- Add semantic lint rules on top of KiCad ERC, such as requiring `PWR_FLAG` on connector-fed power rails and checking no pin is both connected and no-connected.
