import os
import re
import shutil
import subprocess
import time
import math
from tkinter import Tk, filedialog

# ==========================================
# 🛠️ AUTOMATIC LTSPICE PATH FINDER
# ==========================================
def find_ltspice():
    """Attempts to auto-locate LTspice.exe on Windows, falls back to file picker."""
    standard_paths = [
        r"C:\Program Files\ADI\LTspice\LTspice.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\ADI\LTspice\LTspice.exe"),
        r"C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe",
        r"C:\Program Files\LTC\LTspiceXVII\ltsvc.exe",
    ]
    for path in standard_paths:
        if os.path.exists(path):
            print(f"✅ Auto-located LTspice: {path}")
            return path

    print("🔍 Could not auto-locate LTspice.exe.")
    print("📂 Please select your 'LTspice.exe' file in the popup...")
    exe_path = filedialog.askopenfilename(
        title="Locate LTspice.exe",
        filetypes=[("Executable Files", "*.exe")],
    )
    return exe_path


# ==========================================
# 📥 INITIALISE TKINTER (hidden window)
# ==========================================
root = Tk()
root.withdraw()
root.attributes("-topmost", True)

LTSPICE_EXE = find_ltspice()
if not LTSPICE_EXE or not os.path.exists(LTSPICE_EXE):
    print("❌ Valid LTspice.exe not found. Exiting.")
    raise SystemExit(1)


# ==========================================
# 📥 USER INTERACTIVE FLOW INPUTS
# ==========================================
print("\n📂 Please select your target Op-Amp library file (.cir / .lib / .sub)...")
selected_lib_path = filedialog.askopenfilename(
    title="Select Op-Amp Library File",
    filetypes=[("SPICE Models", "*.cir *.lib *.sub"), ("All Files", "*.*")],
)
if not selected_lib_path:
    print("❌ No library file selected. Exiting.")
    raise SystemExit(1)

OPAMP_NAME = os.path.splitext(os.path.basename(selected_lib_path))[0]
OPAMP_CIR_PATH = selected_lib_path

print("\n📂 Please select the folder containing your master .asc testbenches...")
master_bench_dir = filedialog.askdirectory(title="Select Master Testbenches Folder")
if not master_bench_dir:
    print("❌ No testbench folder selected. Exiting.")
    raise SystemExit(1)

parent_dir = os.path.dirname(master_bench_dir)
generated_bench_dir = os.path.join(parent_dir, f"generated_runs_{OPAMP_NAME}")
extracted_logs_dir = os.path.join(parent_dir, f"extracted_logs_{OPAMP_NAME}")
combined_data_path = os.path.join(parent_dir, "extracted_data.txt")

# Create directories if they don't exist
os.makedirs(generated_bench_dir, exist_ok=True)
os.makedirs(extracted_logs_dir, exist_ok=True)

# ==========================================
# 🧹 CLEANUP STALE DATA FROM PREVIOUS RUNS
# ==========================================
print("🧹 Cleaning up old simulation runs and logs to prevent stale results...")
for folder in [generated_bench_dir, extracted_logs_dir]:
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"⚠️  Could not delete {file_path}: {e}")

try:
    if os.path.exists(combined_data_path):
        os.unlink(combined_data_path)
except Exception as e:
    print(f"⚠️  Could not delete {combined_data_path}: {e}")

print(f"\n{'='*60}")
print(f"  Target Op-Amp   : {OPAMP_NAME}")
print(f"  Library Path    : {OPAMP_CIR_PATH}")
print(f"  Master Folder   : {master_bench_dir}")
print(f"  Simulated ASCs  : {generated_bench_dir}")
print(f"  Extracted Logs  : {extracted_logs_dir}")
print(f"{'='*60}\n")


# ==========================================
# ⚙️ CORE REWRITE ENGINE
# ==========================================
def rewrite_testbench(master_asc_path, dest_asc_path):
    """
    Copies a master testbench and makes two targeted changes:

      1) Rewrites the op-amp instance Value line to the selected model name.
      2) Appends a .lib include directive if one is not already present.

    Returns True on success, False on failure.
    """
    try:
        if os.path.exists(dest_asc_path):
            os.remove(dest_asc_path)
        shutil.copy2(master_asc_path, dest_asc_path)
    except PermissionError:
        print(f"\n⚠️  '{os.path.basename(dest_asc_path)}' is locked by LTspice.")
        print("👉 Close all LTspice windows, then press Enter to retry...")
        input()
        try:
            shutil.copy2(master_asc_path, dest_asc_path)
        except Exception as e:
            print(f"❌ Still cannot write: {e}. Skipping.")
            return False

    with open(dest_asc_path, "r", encoding="latin-1", errors="ignore") as fh:
        lines = fh.readlines()

    out_lines = []
    i = 0
    lib_already_present = False

    while i < len(lines):
        line = lines[i]

        if re.search(r"\.lib\b", line, re.IGNORECASE):
            lib_already_present = True

        # Rewrite only the value line immediately following an op-amp instance name.
        if re.match(r"SYMATTR\s+InstName\s+U\d+", line.rstrip(), re.IGNORECASE):
            out_lines.append(line)
            i += 1
            if i < len(lines):
                value_line = lines[i]
                if re.match(r"SYMATTR\s+Value\s+", value_line, re.IGNORECASE):
                    value_line = re.sub(
                        r"(SYMATTR\s+Value\s+)\S+",
                        rf"\g<1>{OPAMP_NAME}",
                        value_line,
                        flags=re.IGNORECASE,
                    )
                out_lines.append(value_line)
                i += 1
            continue

        out_lines.append(line)
        i += 1

    if not lib_already_present:
        if out_lines and not out_lines[-1].endswith("\n"):
            out_lines[-1] += "\n"
        lib_line = f'TEXT 0 -200 Left 2 !.lib "{OPAMP_CIR_PATH}"\n'
        out_lines.append(lib_line)

    with open(dest_asc_path, "w", encoding="latin-1", newline="\n") as fh:
        fh.writelines(out_lines)

    return True


# ==========================================
# 🎬 SIMULATION RUNNER (MANUAL)
# ==========================================
def run_simulation(dest_asc_path):
    """
    Launches LTspice for the given .asc (manual Run click required).
    Returns the path to the generated .log file, or None if not found.
    """
    print(f"\n🎬  Launching LTspice → {os.path.basename(dest_asc_path)}")
    print("    ▶  Run the simulation inside LTspice, then close the window.")
    subprocess.run([LTSPICE_EXE, dest_asc_path])

    log_path = os.path.splitext(dest_asc_path)[0] + ".log"
    if os.path.exists(log_path):
        return log_path

    print(f"⚠️   No .log found for {os.path.basename(dest_asc_path)}.")
    print("    (Did you click Run ▶ before closing LTspice?)")
    return None


# ==========================================
# 🎬 SIMULATION RUNNER (AUTOMATIC)
# ==========================================
def run_simulation_auto(dest_asc_path, timeout_sec=120):
    """
    Launches LTspice in headless batch mode (-b flag).
    Blocks until LTspice exits, then returns the .log path.
    """
    bench_name = os.path.basename(dest_asc_path)
    print(f"\n🎬  Auto-running → {bench_name}")

    try:
        subprocess.run(
            [LTSPICE_EXE, "-b", dest_asc_path],
            cwd=os.path.dirname(dest_asc_path),
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        print(f"⚠️   LTspice timed out after {timeout_sec}s for {bench_name}")
    except Exception as e:
        print(f"❌  LTspice failed for {bench_name}: {e}")
        return None

    log_path = os.path.splitext(dest_asc_path)[0] + ".log"
    if os.path.exists(log_path):
        return log_path

    print(f"⚠️   No .log found for {bench_name} after batch run.")
    return None


def run_simulation_fourier(dest_asc_path, timeout_sec=120):
    """
    Runs a .four/.tran bench in batch mode with -ascii flag.
    LTspice 26+ writes Fourier results into the .log in batch+ascii mode.
    Falls back to interactive if log doesn't contain Fourier results.
    """
    bench_name = os.path.basename(dest_asc_path)
    print(f"\n🎬  Auto-running (Fourier) → {bench_name}")

    log_path = os.path.splitext(dest_asc_path)[0] + ".log"

    # Remove stale log so we can detect fresh output
    if os.path.exists(log_path):
        os.remove(log_path)

    try:
        subprocess.run(
            [LTSPICE_EXE, "-b", "-ascii", dest_asc_path],
            cwd=os.path.dirname(dest_asc_path),
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        print(f"⚠️   LTspice timed out after {timeout_sec}s")
    except Exception as e:
        print(f"❌  LTspice failed: {e}")
        return None

    if os.path.exists(log_path):
        content = open(log_path, "r", encoding="utf-8", errors="ignore").read()
        if "Fourier components" in content or "Total Harmonic Distortion" in content:
            print("    ✅ Fourier results found in log")
            return log_path
        else:
            print("    ⚠️  Batch ran but no Fourier output in log")
            print("    Falling back to interactive mode...")

    # Fallback: open interactively, user runs it manually
    print("    📌 Click Run ▶ in LTspice, then close the window when done.")
    subprocess.run([LTSPICE_EXE, dest_asc_path])

    if os.path.exists(log_path):
        return log_path

    print(f"⚠️   No .log found for {bench_name}.")
    return None


# ==========================================
# 📄 LOG DATA EXTRACTOR
# ==========================================
def extract_data_from_log(log_path):
    """
    Reads a LTspice .log and returns the measurement/log contents,
    stripping only the Circuit boilerplate if present.
    """
    with open(log_path, "r", encoding="utf-8", errors="ignore") as fh:
        lines = fh.readlines()

    # Keep everything except the "Circuit:" boilerplate line.
    data_lines = [l for l in lines if not re.match(r"^Circuit:", l.strip(), re.IGNORECASE)]
    return "".join(data_lines).strip()


def save_extracted_log(data_text, bench_name):
    """Saves extracted measurement data as a .txt in extracted_logs_dir."""
    stem = os.path.splitext(bench_name)[0]
    out_name = f"{OPAMP_NAME}_{stem}_data.txt"
    out_path = os.path.join(extracted_logs_dir, out_name)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(data_text)
    print(f"💾  Saved → {out_path}")
    return out_path



def append_combined_extracted_data(data_text, bench_name):
    """Appends extracted measurement data to one combined summary file."""
    stem = os.path.splitext(bench_name)[0]
    with open(combined_data_path, "a", encoding="utf-8") as fh:
        fh.write(f"\n{'='*80}\n")
        fh.write(f"{OPAMP_NAME} — {stem}\n")
        fh.write(f"{'='*80}\n")
        fh.write(data_text)
        if not data_text.endswith("\n"):
            fh.write("\n")

# ==========================================
# 🔢 NUMBER FORMATTING
# ==========================================
def _engineering_string(value, digits=4):
    """
    Convert a float to a readable engineering string with SI prefixes.
    Examples:
      3.99955108095e-11 -> 39.9955 p
      1.54518245423e-07 -> 154.5182 n
      4.69344034942e+07 -> 46.9344 M
    """
    try:
        v = float(value)
    except Exception:
        return str(value)

    if v == 0:
        return "0"

    sign = "-" if v < 0 else ""
    v = abs(v)

    prefixes = [
        (1e12, "T"),
        (1e9, "G"),
        (1e6, "M"),
        (1e3, "k"),
        (1, ""),
        (1e-3, "m"),
        (1e-6, "u"),
        (1e-9, "n"),
        (1e-12, "p"),
        (1e-15, "f"),
        (1e-18, "a"),
    ]

    for scale, prefix in prefixes:
        if v >= scale:
            scaled = v / scale
            if scaled >= 100:
                fmt = f"{scaled:.2f}"
            elif scaled >= 10:
                fmt = f"{scaled:.3f}"
            else:
                fmt = f"{scaled:.4f}"
            return f"{sign}{fmt} {prefix}".rstrip()

    # Smaller than atto
    return f"{sign}{v:.4e}"


def format_numbers_in_text(text):
    """
    Replace standalone numeric literals in a block of text with engineering format.
    This preserves measurement names like bw_3db because the numeric part is embedded
    inside a word and will not be touched.
    """
    num_pattern = re.compile(
        r"(?<![\w.])([+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?)(?![\w.])"
    )

    def repl(match):
        token = match.group(1)
        # Leave very small integers like line numbers alone only if you prefer;
        # here we format everything numeric for readability.
        try:
            return _engineering_string(float(token))
        except Exception:
            return token

    return num_pattern.sub(repl, text)


# ==========================================
# 📊 THD EXTRACTOR
# ==========================================
def extract_thd(text):
    """
    Extract Total Harmonic Distortion (%) from LTspice .four output.
    Returns (thd_percent, thd_db) or (None, None) if missing/unparseable.
    """
    m = re.search(
        r"Total Harmonic Distortion:\s*([0-9.+\-eE]+)\s*%",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None, None

    try:
        thd_percent = float(m.group(1))
    except (TypeError, ValueError):
        return None, None

    if thd_percent <= 0:
        return thd_percent, None

    try:
        thd_db = 20 * math.log10(thd_percent / 100.0)
    except (ValueError, OverflowError):
        thd_db = None

    return thd_percent, thd_db


# ==========================================
# 📊 LOG READER
# ==========================================
def parse_all_from_text(text):
    """
    Extracts every named measurement result from a saved log .txt file.
    Handles all LTspice output formats:
      - "name=value"
      - "name: ... = value"
      - "Measurement: name" header blocks followed by a numeric result
    Returns a list of (name, value_string) tuples in file order.
    """
    results = []
    seen = set()
    lines = text.splitlines()

    def add_result(name, value):
        key = name.lower()
        if key not in seen:
            results.append((name, value))
            seen.add(key)

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # THD line: "Total Harmonic Distortion: 0.002406%"
        thd_m = re.match(
            r"^Total Harmonic Distortion[:\s]+"
            r"([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*%",
            line, re.IGNORECASE
        )
        if thd_m:
            thd_pct = float(thd_m.group(1))
            add_result("THD_%", str(thd_pct))
            if thd_pct > 0:
                thd_db = 20 * math.log10(thd_pct / 100.0)
                add_result("THD_dB", f"{thd_db:.4f}")
            i += 1
            continue
        m = re.match(r"^Measurement:\s*(\S+)", line, re.IGNORECASE)
        if m:
            meas_name = m.group(1)

            # Search ahead for the first numeric value.
            found = False
            for j in range(i + 1, min(i + 15, len(lines))):
                candidate = lines[j].strip()

                # Common LTspice result line with "value" somewhere on the line
                num = re.search(
                    r"([+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?)",
                    candidate,
                )
                if num:
                    add_result(meas_name, num.group(1))
                    found = True
                    break

            if not found:
                add_result(meas_name, "N/A")

            i += 1
            continue

        # Format 2: name = value
        m = re.match(
            r"^([\w_]+)\s*=\s*([+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?)",
            line,
            re.IGNORECASE,
        )
        if m:
            add_result(m.group(1), m.group(2))
            i += 1
            continue

        # Format 3: name: ... = value
        m = re.match(
            r"^([\w_]+)\s*:.*?=\s*([+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?)",
            line,
            re.IGNORECASE,
        )
        if m:
            add_result(m.group(1), m.group(2))
            i += 1
            continue

        # Format 4: name: value
        m = re.match(
            r"^([\w_]+)\s*:\s*([+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?)",
            line,
            re.IGNORECASE,
        )
        if m:
            add_result(m.group(1), m.group(2))
            i += 1
            continue

        i += 1

    return results


def display_all_results():
    """
    After all simulations finish, reads every *_data.txt in extracted_logs_dir
    and prints every single measurement found, grouped by testbench.
    Also prints the full saved text in a number-friendly engineering format so
    the command terminal shows the whole log content, not just parsed pairs.
    """
    txt_files = sorted(f for f in os.listdir(extracted_logs_dir) if f.endswith("_data.txt"))

    if not txt_files:
        print("  ⚠️   No extracted log files found.")
        return

    print(f"\n{'='*60}")
    print(f"  📊  DATA EXTRACTED — {OPAMP_NAME}")
    print(f"{'='*60}")

    for txt_file in txt_files:
        bench_label = txt_file
        if bench_label.startswith(OPAMP_NAME + "_"):
            bench_label = bench_label[len(OPAMP_NAME) + 1 :]
        if bench_label.endswith("_data.txt"):
            bench_label = bench_label[:-len("_data.txt")]

        txt_path = os.path.join(extracted_logs_dir, txt_file)
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()

        measurements = parse_all_from_text(text)
        thd_percent, thd_db = extract_thd(text)
        formatted_text = format_numbers_in_text(text)

        print(f"\n  ┌─ {bench_label}")
        if measurements:
            print("  │   Parsed measurements:")
            for name, val in measurements:
                print(f"  │   {name:<30} = {_engineering_string(val)}")
        else:
            print("  │   (no parsed measurement pairs found)")

        if thd_percent is not None:
            print(f"  │   {'THD (%)':<30} = {thd_percent:.6f}")
            if thd_db is not None:
                print(f"  │   {'THD (dB)':<30} = {thd_db:.2f}")

        print("  │")
        print("  │   Full log text:")
        for raw_line in formatted_text.splitlines():
            print(f"  │   {raw_line}")

        print(f"  └{'─'*50}")

    print(f"\n📁  Simulated ASCs  : {generated_bench_dir}")
    print(f"📁  Extracted logs  : {extracted_logs_dir}")
    print("✅  Done.")


# ==========================================
# 🚀 MAIN RUNNER
# ==========================================
if __name__ == "__main__":
    all_benches = sorted(
        f for f in os.listdir(master_bench_dir) if f.lower().endswith(".asc")
    )

    if not all_benches:
        print("❌ No .asc files found in the master folder. Exiting.")
        raise SystemExit(1)

    print(f"🔎 Found {len(all_benches)} testbench(es): {', '.join(all_benches)}\n")

    for bench_file in all_benches:
      

        print(f"\n{'─'*60}")
        print(f"📋  Processing: {bench_file}")

        master_path = os.path.join(master_bench_dir, bench_file)
        dest_name = f"{OPAMP_NAME}_{bench_file}"
        dest_path = os.path.join(generated_bench_dir, dest_name)

        if not rewrite_testbench(master_path, dest_path):
            print(f"⏩  Skipping {bench_file} (write error).")
            continue

        # THD/Fourier bench: try batch+ascii first, fall back to interactive
        is_thd = "harmonic" in bench_file.lower() or "thd" in bench_file.lower()

        if is_thd:
            log_path = run_simulation_fourier(dest_path)
        else:
            log_path = run_simulation_auto(dest_path)
        if not log_path:
            continue

        data_text = extract_data_from_log(log_path)
        if not data_text:
            print("⚠️   Log exists but no measurement data found.")
            continue

        save_extracted_log(data_text, bench_file)
        append_combined_extracted_data(data_text, bench_file)

    display_all_results()
