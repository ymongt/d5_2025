import os
import subprocess
import shlex
import csv
import matplotlib.pyplot as plt

#----------------------------------
# Constants
#----------------------------------
CSR_ADDR = 0x0
COEF_ADDR = 0x4
OUTCAP_ADDR = 0x8
MAX_BUF = 255

UNITS = ["impl0", "impl1", "impl2", "impl3", "impl4", "impl5"]
GOLDEN = "golden"

UNIT_FOLDER = r"C:\Users\zhlee_t\Desktop\Git Project\day-5-final-project-LZH-Oppstar"
CONFIG_FILE = "filter.cfg"
VECTOR_FILE = "sqr.vec"
POR_FILE = "por.csv"

#----------------------------------
# Helpers
#----------------------------------

def get_unit_path(unit):
    """
    Returns the full path to the unit executable.
    Checks for .exe or .bat files.
    """
    exe_path = os.path.join(UNIT_FOLDER, unit + ".exe")
    bat_path = os.path.join(UNIT_FOLDER, unit + ".bat")
    if os.path.exists(exe_path):
        return exe_path
    elif os.path.exists(bat_path):
        return bat_path
    else:
        return None

def run_cmd(unit, command):
    """
    Run a command on the unit executable.
    """
    path = get_unit_path(unit)
    if not path:
        print(f"[ERROR] Unit executable not found: {unit}")
        return None

    full_cmd = [path] + shlex.split(command)
    print(f"[{unit}] Running: {' '.join(full_cmd)}")
    try:
        subprocess.run(full_cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {e}")
        return None

def read_reg(unit, addr):
    path = get_unit_path(unit)
    if not path:
        raise FileNotFoundError(f"Unit executable not found: {unit}")

    out = subprocess.check_output([path, "cfg", "--address", hex(addr)]).decode().strip()
    if out == '':
        raise ValueError(f"No output from unit {unit} at address {hex(addr)}")
    return int(out, 0)

def write_reg(unit, addr, data):
    return run_cmd(unit, f"cfg --address {hex(addr)} --data {hex(data)}")

def drive_signal(unit, sig_in):
    """
    Send a single input sample to the FIR filter and return output.
    """
    path = get_unit_path(unit)
    if not path:
        print(f"[ERROR] Unit executable missing: {unit}")
        return None

    try:
        out = subprocess.check_output([path, "sig", "--data", hex(sig_in)]).decode().strip()
        if out == '':
            print(f"[WARNING] No output from unit {unit} for input {sig_in}")
            return None
        return int(out, 0)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Signal command failed for input {sig_in}: {e}")
        return None

def load_coeffs(unit, cfg_file):
    """
    Load filter coefficients from CSV.
    CSV format: coef,value,en
    """
    cfg_path = os.path.join(UNIT_FOLDER, cfg_file)
    if not os.path.exists(cfg_path):
        print(f"[ERROR] Configuration file missing: {cfg_file}")
        return

    coefs = [0]*4
    enables = [0]*4

    with open(cfg_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = int(row["coef"])
            val = int(row["value"], 0) & 0xFF
            en  = int(row["en"])
            coefs[idx] = val
            enables[idx] = en

    # Pack coefficients into 32-bit register
    coef_reg = (coefs[3]<<24)|(coefs[2]<<16)|(coefs[1]<<8)|coefs[0]
    write_reg(unit, COEF_ADDR, coef_reg)

    # Enable coefficients in CSR
    csr = read_reg(unit, CSR_ADDR)
    csr &= ~(0xF << 1)  # Clear C0EN-C3EN
    csr |= (enables[0]<<1)|(enables[1]<<2)|(enables[2]<<3)|(enables[3]<<4)
    write_reg(unit, CSR_ADDR, csr)

#----------------------------------
# Testcases
#----------------------------------

def tc1_global_enable_disable(unit):
    print(f"\n[{unit}] TC1: Global enable/disable")
    run_cmd(unit, "com --action disable")
    try:
        read_reg(unit, CSR_ADDR)
        print("FAIL: CSR accessible when disabled")
    except Exception:
        print("PASS: CSR inaccessible when disabled")
    run_cmd(unit, "com --action enable")

def tc2_por(unit, por_values):
    print(f"\n[{unit}] TC2: POR register values")
    run_cmd(unit, "com --action reset")
    success = True
    for reg_name, expected in por_values.items():
        addr_map = {"CSR":CSR_ADDR,"COEF":COEF_ADDR,"OUTCAP":OUTCAP_ADDR}
        addr = addr_map.get(reg_name)
        if addr is None:
            continue
        try:
            val = read_reg(unit, addr)
            if val != expected:
                print(f"FAIL: {reg_name} expected {hex(expected)}, got {hex(val)}")
                success = False
        except Exception as e:
            print(f"FAIL: Cannot read {reg_name}: {e}")
            success = False
    if success:
        print("PASS: POR values match")

def tc3_input_buffer(unit):
    print(f"\n[{unit}] TC3: Input buffer overflow/clear")
    csr = read_reg(unit, CSR_ADDR)
    csr |= (1<<5)  # HALT
    write_reg(unit, CSR_ADDR, csr)

    overflow_triggered = False
    for i in range(MAX_BUF+5):
        drive_signal(unit, i)
        csr = read_reg(unit, CSR_ADDR)
        if csr & (1<<16):  # IBOVF
            overflow_triggered = True

    if overflow_triggered:
        print("PASS: Buffer overflow set")
    else:
        print("FAIL: Buffer overflow not triggered")

    # Clear buffer
    csr |= (1<<17)
    write_reg(unit, CSR_ADDR, csr)
    csr = read_reg(unit, CSR_ADDR)
    if (csr & 0xFF00)>>8 == 0:
        print("PASS: Buffer cleared")
    else:
        print("FAIL: Buffer not cleared")

def tc5_signal_processing(unit, cfg_file, vec_file):
    print(f"\n[{unit}] TC5: Signal processing")
    csr = read_reg(unit, CSR_ADDR)
    csr |= (1<<5)|(1<<17)|(1<<18)  # HALT + IBCLR + TCLR
    write_reg(unit, CSR_ADDR, csr)

    load_coeffs(unit, cfg_file)

    csr &= ~(1<<5)  # release HALT
    write_reg(unit, CSR_ADDR, csr)

    sig_in = []
    sig_out = []
    vec_path = os.path.join(UNIT_FOLDER, vec_file)
    if not os.path.exists(vec_path):
        print(f"[ERROR] Vector file missing: {vec_file}")
        return []

    with open(vec_path) as f:
        for line in f:
            val = int(line.strip(),0)
            sig_in.append(val)
            sig_out.append(drive_signal(unit, val))

    # Plot input vs output
    plt.figure()
    plt.plot(sig_in, label="Input", drawstyle="steps-post")
    plt.plot(sig_out, label="Output", drawstyle="steps-post")
    plt.xlabel("Sample")
    plt.ylabel("Value")
    plt.title(f"{unit} Filter Response")
    plt.legend()
    plt.grid(True)
    plt.show()

    return sig_out

#----------------------------------
# Main
#----------------------------------

def main():
    # Load POR reference
    por_path = os.path.join(UNIT_FOLDER, POR_FILE)
    por_values = {}
    if os.path.exists(por_path):
        with open(por_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                por_values[row["register"]] = int(row["value"],0)
    else:
        print(f"[WARNING] POR file missing: {POR_FILE}")

    # Golden output
    golden_output = tc5_signal_processing(GOLDEN, CONFIG_FILE, VECTOR_FILE)

    # Run all units
    for unit in UNITS:
        print(f"\n================= VALIDATING {unit} =================")
        tc1_global_enable_disable(unit)
        tc2_por(unit, por_values)
        tc3_input_buffer(unit)
        sig_out = tc5_signal_processing(unit, CONFIG_FILE, VECTOR_FILE)
        if sig_out == golden_output:
            print(f"[{unit}] TC5 PASS: Matches golden output")
        else:
            print(f"[{unit}] TC5 FAIL: Output differs from golden")

if __name__ == "__main__":
    main()
