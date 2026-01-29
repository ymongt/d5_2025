import subprocess, argparse, shlex, csv, os
import numpy as np
import matplotlib.pyplot as plt

CSR_ADDR = 0x0
UAD_PATH = '...'

class Csr():
    def __init__(self, csr_bin):
        self.fen = (csr_bin >> 0) & 0x1
        self.c0en = (csr_bin >> 1) & 0x1
        self.c1en = (csr_bin >> 2) & 0x1
        self.c2en = (csr_bin >> 3) & 0x1
        self.c3en = (csr_bin >> 4) & 0x1
        self.halt = (csr_bin >> 5) & 0x1
        self.sts = (csr_bin >> 6) & 0x3
        self.ibcnt = (csr_bin >> 8) & 0xff
        self.ibovf = (csr_bin >> 16) & 0x1
        self.ibclr = (csr_bin >> 17) & 0x1
        self.tclr = (csr_bin >> 18) & 0x1
        self.rnd = (csr_bin >> 19) & 0x3
        self.icoef = (csr_bin >> 21) & 0x1
        self.icap = (csr_bin >> 22) & 0x1
        self.rsvd = (csr_bin >> 23) & 0xffff

    def encode(self):
        return (
            ((self.fen & 0x1) << 0) |
            ((self.c0en & 0x1) << 1) |
            ((self.c1en & 0x1) << 2) |
            ((self.c2en & 0x1) << 3) |
            ((self.c3en & 0x1) << 4) |
            ((self.halt & 0x1) << 5) |
            ((self.sts & 0x3) << 6) |
            ((self.ibcnt & 0xff) << 8) |
            ((self.ibovf & 0x1) << 16) |
            ((self.ibclr & 0x1) << 17) |
            ((self.tclr & 0x1) << 18) |
            ((self.rnd & 0x3) << 19) |
            ((self.icoef & 0x1) << 21) |
            ((self.icap & 0x1) << 22) |
            ((self.rsvd & 0x3ff) << 23)
        )
    
    def __str__(self):
        str_rep = "CSR Register Content\n"
        str_rep += f"fen   : {hex(self.fen)}\n"
        str_rep += f"c0en  : {hex(self.c0en)}\n"
        str_rep += f"c1en  : {hex(self.c1en)}\n"
        str_rep += f"c2en  : {hex(self.c2en)}\n"
        str_rep += f"c3en  : {hex(self.c3en)}\n"
        str_rep += f"halt  : {hex(self.halt)}\n"
        str_rep += f"sts   : {hex(self.sts)}\n"
        str_rep += f"ibcnt : {hex(self.ibcnt)}\n"
        str_rep += f"ibovf : {hex(self.ibovf)}\n"
        str_rep += f"ibclr : {hex(self.ibclr)}\n"
        str_rep += f"tclr  : {hex(self.tclr)}\n"
        str_rep += f"rnd   : {hex(self.rnd)}\n"
        str_rep += f"icoef : {hex(self.icoef)}\n"
        str_rep += f"icap  : {hex(self.icap)}\n"
        str_rep += f"rsvd  : {hex(self.rsvd)}"
        return str_rep

class Uad():
    def __init__(self):
        self.csr = None

    def reset(self):
        return os.system(f'{UAD_PATH} com --action reset')
    
    def drive_signal(self, sig_in):
        sig_out = subprocess.check_output(shlex.split(f'{UAD_PATH} sig --data {hex(sig_in)}')).decode()
        return int(sig_out, 0)

    def get_csr(self):
        csr_bin = subprocess.check_output(shlex.split(f'{UAD_PATH} cfg --address {CSR_ADDR}')).decode()
        csr_bin = int(csr_bin, 0)
        self.csr = Csr(csr_bin)
        return self.csr

    def set_csr(self):
        exit_code = os.system(f'{UAD_PATH} cfg --address {CSR_ADDR} --data {hex(self.csr.encode())}')
        self.get_csr()
        return exit_code
    
    def get_reg(self, reg_name):
        if reg_name == 'csr':
            return self.get_csr()
        
def twos_comp(num):
    return ((num & 0x7F) + (-128 if num >> 7 == 0x1 else 0)) / 64
    
def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-u', '--unit', choices=['golden', 'impl0', 'impl1', 'impl2', 'impl3', 'impl4'])
    parser.add_argument('-t', '--test', choices=['drive'], help='the tests that can be run with this script')
    parser.add_argument('-f', '--file', help='path to file required for a test')
    args = parser.parse_args()

    UAD_PATH = f'./insts/{args.unit}'
    uad = Uad()

    if args.test == 'drive':
        csr = uad.get_csr()
        csr.fen=1
        csr.tclr=1
        csr.ibclr=1
        uad.set_csr()

        sig_in = []
        sig_out = []
      
        with open(args.file, 'r') as f:
            for line in f.readlines():
                sig_in.append(int(line, 0))
        
        for samp_in in sig_in:
            sig_out.append(uad.drive_signal(samp_in))

        with open('output.vec', 'w') as f:
            for samp_out in sig_out:
                f.write(f'{twos_comp(samp_out)}\n')

        if args.plot:
            plt.plot([i for i in range(len(sig_in))], [twos_comp(samp) for samp in sig_in], label='Input', drawstyle='steps-post')
            plt.plot([i for i in range(len(sig_in))], [twos_comp(samp) for samp in sig_out], label='Output', drawstyle='steps-post')
            plt.xlabel('Sample')
            plt.ylabel('Value')
            plt.title('Signal Input and Output')
            plt.legend()
            plt.show()

if __name__ == '__main__':
    main()
