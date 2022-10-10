# ------------------------------------------------------------------------------
# Script   : modelsim.py
# Author   : Chase Ruskin
# Modified : 2022-09-05
# Created  : 2021-08-29
# Details  :
#   Use batch mode to run simulation in ModelSim.
#
# To unleash full capability, visit the modelsim reference guide: 
# https://www.microsemi.com/document-portal/doc_view/131617-modelsim-reference-manual
# ------------------------------------------------------------------------------
import os,sys,shutil
from typing import List

# --- constants ----------------------------------------------------------------

SIM_DIR = "msim"
# define python path
PYTHON_PATH = os.path.basename(sys.executable)

# temporarily append modelsim installation path to PATH env variable
MODELSIM_PATH = os.environ.get("ORBIT_ENV_MODELSIM_PATH")
if(MODELSIM_PATH != None and os.path.exists(MODELSIM_PATH) == True and MODELSIM_PATH not in os.getenv('PATH')):
    os.environ['PATH'] = MODELSIM_PATH + ';' + os.getenv('PATH')

DO_FILE = 'orbit.do'
WAVEFORM_FILE = 'vsim.wlf'

# --- classes and functions ----------------------------------------------------

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
    code_line = command + ' '
    for c in args:
        code_line = code_line + quote_str(c) + ' '
    rc = os.system(code_line)
    if verbose == True:
        print(code_line)
    #immediately stop script upon a bad return code
    if(rc != 0 and exit_on_err == True):
        exit('ERROR: plugin exited with error code: '+str(rc))


# --- Handle command-line arguments --------------------------------------------

generics = []
prev_arg = ''

# testbench's VHDL configuration unit
top_level_config = None

REVIEW = False
OPEN_GUI = False
INIT_ONLY = False
LINT_ONLY = False
CLEAN = False
# handle options
for cur_arg in sys.argv[1:]:
    if cur_arg == "--gui":
        OPEN_GUI = True
    elif cur_arg == '--review':
        REVIEW = True
    elif cur_arg == '--init':
        INIT_ONLY = True
    elif cur_arg == '--lint':
        LINT_ONLY = True
    elif cur_arg == '--clean':
        CLEAN = True
    elif prev_arg == '--generic' or prev_arg == '-g':
        gen = Generic.from_str(cur_arg)
        if gen != None:
            generics += [gen]
        else:
            exit('ERROR: Invalid generic entered as ' + cur_arg)
        pass
    elif prev_arg == '--config':
        top_level_config = cur_arg
        pass
    prev_arg = cur_arg
    pass

# open an existing waveform result
if REVIEW == True:
    if os.path.exists(WAVEFORM_FILE) == True:
        invoke('vsim', ['-view', WAVEFORM_FILE, '-do "add wave *;"'])
    else:
        exit("ERROR: No .wlf exists to review")

# --- process blueprint --------------------------------------------------------

# change directory to build
os.chdir(os.getenv("ORBIT_BUILD_DIR"))

#track what libraries we have seen
libraries = []

py_model = None
tb_do_file = None
# open the blueprint file
with open(os.getenv("ORBIT_BLUEPRINT"), 'r') as blueprint:
    # force remove directory if clean is enabled
    if CLEAN == True and os.path.exists(SIM_DIR) == True:
        shutil.rmtree(SIM_DIR)
    # enter modelsim directory
    os.makedirs(SIM_DIR, exist_ok=True)
    os.chdir(SIM_DIR)

    for rule in blueprint.readlines():
        #split the rule by the spaces
        fileset, library, path = rule.strip('\n').split('\t', maxsplit=3)
        #compile external custom libraries
        if(fileset == "VHDL-RTL" or fileset == "VHDL-SIM"):
            #create new modelsim library folder and mapping
            if(library not in libraries):
                invoke('vlib', [library])
                invoke('vmap', [library, library])
                libraries.append(library)
            # compile vhdl
            invoke('vcom', ['-work', library, path])
            pass
        #compile verilog source files
        elif(fileset == "VLOG-RTL" or fileset == "VLOG-SIM"):
            #create new modelsim library folder and mapping
            if(library not in libraries):
                invoke('vlib', [library])
                invoke('vmap', [library, library])
                libraries.append(library)
            # compile verilog
            invoke('vlog', ['-work', library, path])
            pass
        #see if there is a python model script to run before running testbench
        elif(fileset == "PY-MODEL"):
            py_model = path
            pass
        #see if there is a do file to run for opening modelsim
        elif(fileset == "DO-FILE"):
            tb_do_file = path
            pass
    pass

if LINT_ONLY == True:
    print("INFO: Static analysis complete")
    exit()

BENCH = os.getenv("ORBIT_BENCH")

if BENCH == None or len(BENCH) == 0:
    exit("ERROR: No testbench set with $ORBIT_BENCH")

# 1. pre-simulation hook: generate test vectors
if py_model != None:
    print("INFO: Running python software model ...")
    # format generics for SW MODEL
    py_generics = []
    for item in generics:
        py_generics += ['-g=' + item.to_str()]
    invoke(PYTHON_PATH, [py_model] + py_generics)

# 2. create a .do file to automate modelsim actions
print("INFO: Generating .do file ...")
with open(DO_FILE, 'w') as file:
    # prepend .do file data
    if OPEN_GUI == True:
        # add custom waveform/vsim commands
        if(tb_do_file != None):
            with open(tb_do_file, 'r') as do:
                for line in do.readlines():
                    # add all non-blank lines
                    if(len(line.strip())):
                        file.write(line)
                pass
        # write default to include all signals into waveform
        else:
            file.write('add wave *\n')
            pass
    if INIT_ONLY == False:
        file.write('run -all\n')
    if OPEN_GUI == False:
        file.write('quit\n')
    pass

# run simulation with this top-level testbench

# determine to run as script or as gui
mode = "-batch"
if OPEN_GUI == True:
    mode = "-gui"

# format any generics for vsim command-line
for i in range(len(generics)):
    generics[i] = '-g'+generics[i].to_str()

# override bench with top-level config
if top_level_config != None:
    BENCH = top_level_config

# 3. run vsim
print("INFO: Invoking modelsim ...")
invoke('vsim', [mode, '-onfinish', 'stop', '-do', DO_FILE, '-wlf', WAVEFORM_FILE, BENCH] + generics)