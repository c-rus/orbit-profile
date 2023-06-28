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

VHDL_EDITION = '93'

OPEN_VCD_VIEWER = False

# define python path
PYTHON_PATH = os.path.basename(sys.executable)

# define ghdl path
GHDL_PATH = os.environ.get("ORBIT_ENV_GHDL_PATH")
if GHDL_PATH == None:
    GHDL_PATH = 'ghdl'

# define a vcd viewer
VCD_VIEWER = os.environ.get("ORBIT_ENV_VCD_VIEWER")

# arguments
GLUE_LOGIC = '--code'
RAND_SEED = '--seed'

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
        exit('ERROR: Plugin exited with error code: '+str(rc))


# --- process command-line inputs ----------------------------------------------

generics = []
prev_arg = ''
disp_teskit_code = False
set_seed = False
rng_seed = None
# handle options
for cur_arg in sys.argv:
    if cur_arg == '--view':
        OPEN_VCD_VIEWER = True
    elif cur_arg == GLUE_LOGIC:
        disp_teskit_code = True
    elif cur_arg == RAND_SEED:
        set_seed = True
    elif prev_arg == RAND_SEED and cur_arg[0] != '-':
        rng_seed = int(cur_arg)
    elif (prev_arg == '--generic' or prev_arg == '-g') and cur_arg[0] != '-':
        gen = Generic.from_str(cur_arg)
        if gen != None:
            generics += [gen]
        else:
            exit('ERROR: Invalid generic entered as ' + cur_arg)
        pass
    prev_arg = cur_arg
    pass

# --- verify the planning phase was previously ran -----------------------------

# verify the build directory exists
BUILD_DIR = os.environ.get("ORBIT_BUILD_DIR")
try:
    os.chdir(BUILD_DIR)
except:
    exit("ERROR: Build directory '"+str(BUILD_DIR)+"' does not exist")

# verify a blueprint exists
BLUEPRINT = os.environ.get("ORBIT_BLUEPRINT")
if os.path.exists(BLUEPRINT) == False:
    exit("ERROR: Blueprint file does not exist in build directory '"+BUILD_DIR+"'")

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

# only display glue logic code if requested and exit
if py_model is not None and disp_teskit_code == True:
    print("INFO: Writing Python software model glue logic for VHDL testbench ...")
    # format generics for SW MODEL
    py_generics = []
    item: Generic
    for item in generics:
        py_generics += ['-g=' + item.to_str()]

    invoke(PYTHON_PATH, [py_model] 
           + py_generics 
           + ([GLUE_LOGIC] if disp_teskit_code == True else []) 
           + ([RAND_SEED] if set_seed == True else [])
           + ([str(rng_seed)] if rng_seed is not None else [])
        )
    
    exit(0)

# analyze units
print("INFO: Analyzing HDL source code ...")
item: Vhdl
for item in rtl_order:
    print('   * Analyzing '+quote_str(item.path))
    invoke(GHDL_PATH, ['-a', '--ieee=synopsys', '--std='+VHDL_EDITION, '--work='+str(item.lib), item.path])
    pass

# pre-simulation hook: generate test vectors
if py_model != None:
    print("INFO: Running Python software model ...")
    # format generics for SW MODEL
    py_generics = []
    item: Generic
    for item in generics:
        py_generics += ['-g=' + item.to_str()]

    invoke(PYTHON_PATH, [py_model] 
           + py_generics 
           + ([GLUE_LOGIC] if disp_teskit_code == True else []) 
           + ([RAND_SEED] if set_seed == True else [])
           + ([str(rng_seed)] if rng_seed is not None else [])
        )
    pass

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
    print("INFO: Starting VHDL simulation for testbench "+BENCH+" ...")
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
    print('WARNING: No testbench entity detected')