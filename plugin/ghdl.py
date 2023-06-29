# ------------------------------------------------------------------------------
# Script   : ghdl.py
# Engineer : Chase Ruskin
# Modified : 2023/06/29
# Created  : 2022/08/20
# Details  :
#   @todo
# ------------------------------------------------------------------------------
import os, sys
import argparse
from typing import List

from mod import Command, Status, Env, Generic, quote_str

# --- Constants ----------------------------------------------------------------

BYPASS_FAILURE = False
SIM_DIR = 'sim-ghdl'

OPEN_VCD_VIEWER = False

# define python path
PYTHON_PATH = os.path.basename(sys.executable)

# define ghdl path
GHDL_PATH: str = Env.read("ORBIT_ENV_GHDL_PATH", default='ghdl')
# define a vcd viewer
VCD_VIEWER: str = Env.read("ORBIT_ENV_VCD_VIEWER")

# --- Classes and functions ----------------------------------------------------

class Vhdl:
    def __init__(self, lib: str, path: str):
        self.lib = lib
        self.path = path
        pass
    pass

# --- Process command-line inputs ----------------------------------------------

# arguments
GLUE_LOGIC = '--code'
RAND_SEED = '--seed'

parser = argparse.ArgumentParser()

parser.add_argument('--view', action='store_true', default=False, help='open the vcd file in a waveform viewer')
parser.add_argument('--lint', action='store_true', default=False, help='run static analysis and exit')
parser.add_argument(GLUE_LOGIC, action='store_true', default=False, help='print VHDL glue logic code for Python model')
parser.add_argument(RAND_SEED, action='store', type=int, nargs='?', default=None, const=None, metavar='num', help='set the randomness seed')
parser.add_argument('--generic', '-g', action='append', type=Generic.from_arg, default=[], metavar='key=value', help='override top-level VHDL generics')
parser.add_argument('--std', action='store', default='93', metavar='edition', help="specify the VHDL edition (87, 93, 02, 08, 19)")

args = parser.parse_args()

set_seed: bool = sys.argv.count(RAND_SEED) > 0
generics: List[Generic] = args.generic

# --- Collect data from the blueprint ------------------------------------------

# enter the build directory for the rest of the workflow
BUILD_DIR = Env.read("ORBIT_BUILD_DIR", missing_ok=False)
os.chdir(BUILD_DIR)

BLUEPRINT = Env.read("ORBIT_BLUEPRINT", missing_ok=False)

# @todo: create abstract blueprint class
rtl_order: List[Vhdl] = []
py_model = None
with open(BLUEPRINT, 'r') as blueprint:
    for rule in blueprint.readlines():
        # remove newline and split into three components
        fileset, identifier, path = rule.strip().split('\t')
        # conditionally handle different supported filesets
        if fileset == 'VHDL-RTL' or fileset == 'VHDL-SIM':
            rtl_order += [Vhdl(identifier, path)]
        elif fileset == 'PY-MODEL':
            py_model = path
        pass
    pass

# --- Perform workflow ---------------------------------------------------------

# enter GHDL simulation working directory
os.makedirs(SIM_DIR, exist_ok=True)
os.chdir(SIM_DIR)

# only display glue logic code if requested and exit
if py_model is not None and args.code == True:
    print("info: Writing Python software model glue logic for VHDL testbench ...")

    Command(PYTHON_PATH) \
        .arg(py_model) \
        .args(['-g=' + item.to_str() for item in generics]) \
        .arg(GLUE_LOGIC if args.code == True else None) \
        .arg(RAND_SEED if set_seed == True else None) \
        .arg(args.seed) \
        .spawn() \
        .unwrap()
    exit(0)

# analyze units
print("info: Analyzing HDL source code ...")
item: Vhdl
for item in rtl_order:
    print('   * Analyzing', quote_str(item.path))
    Command(GHDL_PATH) \
        .args(['-a', '--ieee=synopsys', '--std='+args.std, '--work='+str(item.lib), item.path]) \
        .spawn() \
        .unwrap()
    pass

# halt workflow here when only providing lint
if args.lint == True:
    print("info: Static analysis complete")
    exit(0)

# pre-simulation hook: generate test vectors
if py_model != None:
    print("info: Running Python software model ...")

    Command(PYTHON_PATH) \
        .arg(py_model) \
        .args(['-g=' + item.to_str() for item in generics]) \
        .arg(GLUE_LOGIC if args.code == True else None) \
        .arg(RAND_SEED if set_seed == True else None) \
        .arg(args.seed) \
        .spawn() \
        .unwrap()
    pass

BYPASS_FAILURE = VCD_VIEWER is not None

# determine level of severity to exit
severity_arg = '--assert-level=' + ('none' if BYPASS_FAILURE == True else 'failure')

BENCH = Env.read("ORBIT_BENCH", missing_ok=True)

if BENCH is None:
    exit('error: No testbench to simulate\n\nUse \"--lint\" to only compile the HDL code or set a testbench to simulate')

VCD_FILE = str(BENCH)+'.vcd'

# run simulation
print("info: Starting VHDL simulation for testbench", quote_str(BENCH), "...")
status: Status = Command(GHDL_PATH) \
    .args(['-r', '--ieee=synopsys', BENCH, '--vcd='+VCD_FILE, severity_arg]) \
    .args(['-g' + item.to_str() for item in generics]) \
    .spawn()

if BYPASS_FAILURE == False:
    status.unwrap()

# open the vcd file
if(VCD_VIEWER != None and args.view == True):
    Command(VCD_VIEWER).arg(VCD_FILE).spawn().unwrap()
    pass