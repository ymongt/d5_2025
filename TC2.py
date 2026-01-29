import os
import subprocess
import platform
import csv

# -------------------------------
# UAD class to interface with IP
# -------------------------------
class Uad():
    def __init__(self):
        self.inst = None
        self.is_windows = platform.system() == "Windows"

    # --- Common Channel ---
    def reset(self):
        cmd = f'{self.inst}.exe com --action reset' if self.is_windows else f'./{self.inst} com --action reset'
        return os.system(cmd)

    def enable(self):
        cmd = f'{self.inst}.exe com --action enable' if self.is_windows else f'./{self.inst} com --action enable'
        return os.system(cmd)

    def disable(self):
        cmd = f'{self.inst}.exe com --action disable' if self.is_windows else f'./{self.inst} com --action disable'
        return os.system(cmd)

    # --- Configuration Channel ---
    def read_CSR(self, address=0x0):
        cmd = f'{self.inst}.exe cfg --address {hex(address)}' if self.is_windows else f'./{self.inst} cfg --address {hex(address)}'
        try:
            csr_bytes = subprocess.check_output(cmd, shell=True)
            return int(csr_bytes.strip(), 16)
        except (subprocess.CalledProcessError, ValueError):
            return None

    def write_CSR(self, value, address=0x0):
        cmd = f'{self.inst}.exe cfg --address {hex(address)} --data {hex(value)}' if self.is_windows else f'./{self.inst} cfg --address {hex(address)} --data {hex(value)}'
        return os.system(cmd)

    # --- Signal Channel ---
    def drive_signal(self, value):
        cmd = f'{self.inst}.exe sig --data {hex(value)}' if self.is_windows else f'./{self.inst} sig --data {hex(value)}'
        try:
            output = subprocess.check_output(cmd, shell=True)
            output = output.strip()
            if not output:
                return None
            return int(output, 16)
        except (subprocess.CalledProcessError, ValueError):
            return None

# -------------------------------
# Read POR.csv as reference
# -------------------------------
def read_por_csv(file):
    por = {}
    with open(file, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            reg = row['register']
            val = int(row['value'], 16)
            por[reg] = val
    return por

# -------------------------------
# Testcase 1: Enable/Disable + Signal
# -------------------------------
def run_tc1(uad, test_signal=0x55, enable_bit=4):
    results = {}
    print("=== Enable/Disable Test ===")

    uad.reset()
    uad.enable()

    csr = uad.read_CSR()
    if csr is not None:
        print(f"Raw CSR after enable: 0x{csr:08X}")
        results['enabled_fen'] = (csr >> enable_bit) & 1
        print(f"Filter enabled (bit {enable_bit}): {results['enabled_fen']}")
    else:
        results['enabled_fen'] = None
        print("error: interface unavailable after enable")
        print("Filter enabled: Interface unavailable")

    uad.disable()
    csr = uad.read_CSR()
    if csr is not None:
        print(f"Raw CSR after disable: 0x{csr:08X}")
        results['disabled_fen'] = (csr >> enable_bit) & 1
        print(f"Filter enabled (bit {enable_bit}): {results['disabled_fen']}")
    else:
        results['disabled_fen'] = None
        print("error: interface unavailable after disable")
        print("CSR after disable: Interface unavailable")
        print("Filter enabled: Interface unavailable")

    output = uad.drive_signal(test_signal)
    if output is not None:
        results['signal_bypass'] = output
        print(f"Test signal 0x{test_signal:02X} → Output 0x{output:02X}")
    else:
        results['signal_bypass'] = None
        print(f"Test signal 0x{test_signal:02X} → Output: Interface unavailable")

    return results

def compare_tc1(spec_results, impl_results, impl_name="impl"):
    passed = True
    print(f"\n--- Comparing {impl_name} with specification ---")
    for key in spec_results:
        g_val = spec_results[key]
        i_val = impl_results[key]
        if g_val != i_val:
            print(f"[FAIL] {key}: Spec={g_val} Impl={i_val}")
            passed = False
        else:
            print(f"[PASS] {key}: Value={i_val}")
    print(f"TC1 Enable/Disable for {impl_name}: {'PASS' if passed else 'FAIL'}")
    return passed

# -------------------------------
# Testcase 2: POR Register Check
# -------------------------------
def run_tc2(uad, por_spec):
    results = {}
    print("=== POR Register Values Test ===")
    uad.reset()

    for reg_str, expected in por_spec.items():
        # convert reg_str like 'CSR' to address (example: CSR->0x00)
        addr = {'CSR':0x00, 'COEF':0x04, 'OUTCAP':0x08}.get(reg_str, None)
        if addr is None:
            continue
        val = uad.read_CSR(addr)
        if val is not None:
            print(f"Register 0x{addr:02X} after POR: 0x{val:08X}")
            results[reg_str] = val
        else:
            results[reg_str] = None
            print(f"Register 0x{addr:02X} after POR: Interface unavailable")
    return results

def compare_tc2(spec_por, impl_por, impl_name="impl"):
    passed = True
    print(f"\n--- Comparing {impl_name} with POR specification ---")
    for reg in spec_por:
        spec_val = spec_por[reg]
        impl_val = impl_por.get(reg, None)
        if spec_val != impl_val:
            print(f"[FAIL] Register {reg}: Spec=0x{spec_val:X} Impl={impl_val if impl_val is None else hex(impl_val)}")
            print(f"Analysis: Register {reg} does not match POR specification.")
            passed = False
        else:
            print(f"[PASS] Register {reg}: Value=0x{impl_val:X}")
            print(f"Analysis: Register {reg} correctly reset to POR value.")
    print(f"TC2 POR Check for {impl_name}: {'PASS' if passed else 'FAIL'}")
    return passed

# -------------------------------
# Main execution
# -------------------------------
if __name__ == "__main__":
    instances = ["impl0", "impl1", "impl2", "impl3", "impl4", "impl5"]
    por_spec = read_por_csv("POR.csv")  # your POR.csv file

    # Run TC1 and TC2 for all instances
    for impl in instances:
        print(f"\n\n======= Testing {impl} =======\n")
        uad = Uad()
        uad.inst = impl

        # --- TC1 ---
        tc1_results = run_tc1(uad)
        compare_tc1({'enabled_fen':0,'disabled_fen':0,'signal_bypass':None}, tc1_results, impl_name=impl)

        # --- TC2 ---
        tc2_results = run_tc2(uad, por_spec)
        compare_tc2(por_spec, tc2_results, impl_name=impl)
