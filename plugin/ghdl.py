# ------------------------------------------------------------------------------
# Script   : ghdl.py
# Engineer : Chase Ruskin
# Modified : 2022/09/03
# Created  : 2022/08/20
# Details  :
#   @todo
# ------------------------------------------------------------------------------
import os, sys
from typing import List

# --- constants ----------------------------------------------------------------

BYPASS_FAILURE = False
SIM_DIR = 'ghdl-sim'

OPEN_VCD_VIEWER = False

# define python path
PYTHON_PATH = os.path.basename(sys.executable)

# define ghdl path
GHDL_PATH = os.environ.get("ORBIT_ENV_GHDL_PATH")
if GHDL_PATH == None:
    GHDL_PATH = 'ghdl'

# define a vcd viewer
VCD_VIEWER = os.environ.get("ORBIT_ENV_VCD_VIEWER")

# --- classes and functions ----------------------------------------------------

class Vhdl:
    def __init__(self, lib: str, path: str):
        self.lib = lib
        self.path = path
        pass
    pass


class Generic:
    def __init__(self, key: str, val: str):
        self.key = key
        self.val = val
        pass
    pass


    @classmethod
    def from_str(self, s: str):
        # split on equal sign
        words = s.split('=', 1)
        if len(words) != 2:
            return None
        return Generic(words[0], words[1])


    def to_str(self) -> str:
        return self.key+'='+self.val
    pass


def quote_str(s: str) -> str:
    '''Wraps the string `s` around double quotes `\"` characters.'''
    return '\"' + s + '\"'


def invoke(command: str, args: List[str], verbose: bool=False, exit_on_err: bool=True):
    '''
    Runs a subprocess calling `command` with a series of `args`.

    Prints the command if `verbose` is `True`.
    '''
    code_line = quote_str(command) + ' '
    for c in args:
        code_line = code_line + quote_str(c) + ' '
    rc = os.system(code_line)
    if verbose == True:
        print(code_line)
    #immediately stop script upon a bad return code
    if(rc != 0 and exit_on_err == True):
        exit('ERROR: plugin exited with error code: '+str(rc))


# --- process command-line inputs ----------------------------------------------

generics = []
prev_arg = ''
# handle options
for cur_arg in sys.argv:
    if cur_arg == '--view':
        OPEN_VCD_VIEWER = True
    elif prev_arg == '--generic' or prev_arg == '-g':
        gen = Generic.from_str(cur_arg)
        if gen != None:
            generics += [gen]
        else:
            exit('invalid generic entered as ' + cur_arg)
        pass
    prev_arg = cur_arg
    pass

# --- verify the planning phase was previously ran -----------------------------

# verify the build directory exists
BUILD_DIR = os.environ.get("ORBIT_BUILD_DIR")
try:
    os.chdir(BUILD_DIR)
except:
    exit("build directory '"+str(BUILD_DIR)+"' does not exist")

# verify a blueprint exists
BLUEPRINT = os.environ.get("ORBIT_BLUEPRINT")
if os.path.exists(BLUEPRINT) == False:
    exit("blueprint file does not exist in build directory '"+BUILD_DIR+"'")

# --- collect data from the blueprint ------------------------------------------

rtl_order = []
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

# enter GHDL simulation working directory
os.makedirs(SIM_DIR, exist_ok=True)
os.chdir(SIM_DIR)

# analyze units
print("INFO: analyzing source code ...")
for item in rtl_order:
    print('   analyzing '+quote_str(item.path))
    invoke(GHDL_PATH, ['-a', '--ieee=synopsys', '--std=93', '--work='+str(item.lib), item.path])
    pass

# pre-simulation hook: generate test vectors
if py_model != None:
    print("INFO: running python software model ...")
    # format generics for SW MODEL
    py_generics = []
    for item in generics:
        py_generics += ['-g=' + item.to_str()]
    invoke(PYTHON_PATH, [py_model] + py_generics)

BYPASS_FAILURE = VCD_VIEWER != None

# determine level of severity to exit
severity_arg = '--assert-level='
if BYPASS_FAILURE == True:
    severity_arg += 'none'
else:
    severity_arg += 'failure'

BENCH = os.environ.get("ORBIT_BENCH")

# run simulation
if(BENCH != None):
    VCD_FILE = str(BENCH)+'.vcd'
    print("INFO: simulating vhdl testbench "+BENCH+" ...")
    # format generics for GHDL
    ghdl_generics = []
    for item in generics:
        ghdl_generics += ['-g'+item.to_str()]
        pass
    invoke(GHDL_PATH, ['-r', '--ieee=synopsys', BENCH, '--vcd='+VCD_FILE, severity_arg] + ghdl_generics, exit_on_err=not BYPASS_FAILURE)

    # open the vcd file
    if(VCD_VIEWER != None and OPEN_VCD_VIEWER == True):
        invoke(VCD_VIEWER, [VCD_FILE])
        pass
else:
    print('WARNING: no testbench entity detected')