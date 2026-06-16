# LTspice-automation

A Python automation script for running LTspice simulations in batch, swapping op-amp models dynamically, executing multiple testbenches, and extracting measurement results into structured outputs.

This tool removes repetitive manual work in LTspice-based op-amp benchmarking workflows.

---

## Features

- Automatically detects LTspice installation (Windows)
- GUI-based selection of:
  - Op-amp model file (`.lib`, `.cir`, `.sub`)
  - Master testbench folder (`.asc`)
- Automatically rewrites LTspice testbenches:
  - Injects selected op-amp model name
  - Ensures `.lib` directive is included
- Supports:
  - Automatic batch execution (`-b -run`)
  - Optional manual LTspice run mode
- Extracts and parses `.log` measurement results
- Supports multiple LTspice output formats
- Converts numeric values into engineering notation
- Organizes outputs into structured folders
- Prints full simulation results in terminal

---

## Requirements

- Python 3.8+
- Windows OS
- LTspice XVII or LTspice (Analog Devices version)

### Python Standard Libraries Used

No external dependencies required:


os
re
shutil
subprocess
time
tkinter


---

## How It Works

### 1. Input Selection

The script prompts the user to select:

- LTspice executable (auto-detected if possible)
- Op-amp model file (`.lib`, `.cir`, `.sub`)
- Master `.asc` testbench folder

---

### 2. Output Directories

Automatically created:


generated_runs_<OPAMP_NAME>/
extracted_logs_<OPAMP_NAME>/


---

### 3. Testbench Processing

For each `.asc` file:

- Copies master testbench
- Replaces op-amp instance value with selected model
- Adds `.lib "model_path"` if missing

---

### 4. Simulation Execution

#### Automatic Mode (Default)

Runs LTspice in batch mode:


LTspice.exe -b -run file.asc


Waits for `.log` output automatically.

#### Manual Mode (Optional)

Opens LTspice GUI for manual execution.

---

### 5. Log Processing

Each `.log` file is:

- Cleaned (removes boilerplate lines)
- Saved as `.txt`
- Parsed for:
  - `name = value`
  - `Measurement: name`
  - `name: value`

---

### 6. Engineering Notation Formatting

Example conversions:


3.2e-9 → 3.2000 n
1.5e6 → 1.5000 M
0.00012 → 120.0000 µ


---

### 7. Final Output

At the end, the script displays:

- Parsed measurement results per testbench
- Full formatted logs
- File locations of:
  - Generated `.asc` files
  - Extracted `.txt` logs

---

## Output Structure


generated_runs_<OPAMP_NAME>/
<opamp>_<bench>.asc

extracted_logs_<OPAMP_NAME>/
<opamp>_<bench>_data.txt


---

## Key Functions

| Function | Description |
|----------|-------------|
| `find_ltspice()` | Auto-locates LTspice executable |
| `rewrite_testbench()` | Injects op-amp model into `.asc` |
| `run_simulation_auto()` | Runs LTspice in batch mode |
| `extract_data_from_log()` | Extracts useful log content |
| `parse_all_from_text()` | Parses measurement results |
| `format_numbers_in_text()` | Converts numbers to engineering format |
| `display_all_results()` | Prints final consolidated report |

---

## Notes

- LTspice must be installed and working properly
- Testbenches must include identifiable op-amp instances (`U1`, `U2`, etc.)
- Batch mode requires LTspice CLI support
- GUI mode requires manual Run execution

---

## Use Cases

- Op-amp benchmarking and comparison
- Analog circuit validation workflows
- Academic simulations and research
- Multi-model performance testing

---

## Future Improvements

- Parallel simulation execution
- CSV / Excel export of results
- GUI dashboard for results visualization
- Cross-platform support (Wine/Linux)
- Automatic measurement detection from schematics

---
