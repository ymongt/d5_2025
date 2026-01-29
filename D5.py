import os
import subprocess
import platform

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
    def read_CSR(self):
        cmd = f'{self.inst}.exe cfg --address 0x0' if self.is_windows else f'./{self.inst} cfg --address 0x0'
        try:
            csr_bytes = subprocess.check_output(cmd, shell=True)
            return int(csr_bytes.strip(), 16)
        except subprocess.CalledProcessError:
            return None
        except ValueError:
            return None

    def write_CSR(self, value):
        cmd = f'{self.inst}.exe cfg --address 0x0 --data {hex(value)}' if self.is_windows else f'./{self.inst} cfg --address 0x0 --data {hex(value)}'
        return os.system(cmd)

    # --- HALT functions ---
    def halt(self):
        csr = self.read_CSR()
        if csr is not None:
            csr |= (1 << 5)
            self.write_CSR(csr)

    # --- Signal Channel ---
    def drive_signal(self, value):
        cmd = f'{self.inst}.exe sig --data {hex(value)}' if self.is_windows else f'./{self.inst} sig --data {hex(value)}'
        try:
            output = subprocess.check_output(cmd, shell=True)
            output = output.strip()
            if not output:
                return None
            return int(output, 16)
        except subprocess.CalledProcessError:
            return None
        except ValueError:
            return None

# -------------------------------
# Testcase 1: Enable/Disable
# -------------------------------
# -------------------------------
# Testcase 1: Enable/Disable (fixed)
# -------------------------------
def run_tc1_sequence(uad, test_signal=0x55, enable_bit=4):
    """
    Run enable/disable sequence on the given UAD instance.
    enable_bit: CSR bit position for global enable (default=4)
    Returns a dict with results for comparison.
    """
    results = {}
    print("=== Enable/Disable Test ===")

    # Reset and enable
    uad.reset()
    uad.enable()

    csr = uad.read_CSR()
    if csr is not None:
        print(f"Raw CSR after enable: 0x{csr:08X}")
        results['enabled_fen'] = (csr >> enable_bit) & 1
        print(f"Filter enabled (bit {enable_bit}):", results['enabled_fen'])
    else:
        print("error: interface unavailable after enable")
        results['enabled_fen'] = None
        print("Filter enabled: Interface unavailable")

    # Disable filter
    uad.disable()
    csr = uad.read_CSR()
    if csr is not None:
        print(f"Raw CSR after disable: 0x{csr:08X}")
        results['disabled_fen'] = (csr >> enable_bit) & 1
        print(f"Filter enabled (bit {enable_bit}):", results['disabled_fen'])
    else:
        print("error: interface unavailable after disable")
        print("CSR after disable: Interface unavailable")
        print("Filter enabled: Interface unavailable")
        results['disabled_fen'] = None

    # Drive a test signal while disabled
    output = uad.drive_signal(test_signal)
    if output is not None:
        results['signal_bypass'] = output
        print(f"Test signal 0x{test_signal:02X} → Output 0x{output:02X}")
    else:
        results['signal_bypass'] = None
        print(f"Test signal 0x{test_signal:02X} → Output: Interface unavailable")

    return results

def compare_tc1(golden_results, impl_results, impl_name="impl"):
    """
    Compare implementation results with golden and print detailed pass/fail.
    """
    passed = True
    print(f"\n--- Comparing {impl_name} with Golden ---")
    for key in golden_results:
        g_val = golden_results[key]
        i_val = impl_results[key]
        if g_val != i_val:
            print(f"[FAIL] {key}: Golden={g_val} Impl={i_val}")
            passed = False
        else:
            print(f"[PASS] {key}: Value={i_val}")
    if passed:
        print(f"TC1 Enable/Disable for {impl_name}: PASS")
    else:
        print(f"TC1 Enable/Disable for {impl_name}: FAIL")

# -------------------------------
# Main loop over all instances
# -------------------------------
instances = ["impl0", "impl1", "impl2", "impl3", "impl4", "impl5"]
golden_inst = "golden"

# Run golden first
golden_uad = Uad()
golden_uad.inst = golden_inst
golden_results = run_tc1_sequence(golden_uad)

# Run all other implementations
for impl in instances:
    print(f"\n\n======= Testing {impl} =======\n")
    uad = Uad()
    uad.inst = impl
    impl_results = run_tc1_sequence(uad)
    compare_tc1(golden_results, impl_results, impl_name=impl)





