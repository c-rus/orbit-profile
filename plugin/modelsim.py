# Project: orbit-profile
# Script: modelsim.py
# 
# Runs ModelSim in batch mode to perform HDL simulations.
# 
# [1] https://www.microsemi.com/document-portal/doc_view/131617-modelsim-reference-manual

import os, sys, shutil, argparse, random
from typing import List

from mod import Env, Generic, Command, Hdl, Blueprint

SIM_DIR = "msim"

# temporarily append modelsim installation path to PATH env variable
MODELSIM_PATH = Env.read("ORBIT_ENV_MODELSIM_PATH", missing_ok=True)
Env.add_path(MODELSIM_PATH)

DO_FILE = 'orbit.do'
WAVEFORM_FILE = 'vsim.wlf'

## Handle command-line arguments

parser = argparse.ArgumentParser(prog='msim', allow_abbrev=False)

parser.add_argument('--enable-veriti', default=0, metavar='BIT', help="toggle the usage of veriti verification library")

parser.add_argument('--lint', action='store_true', default=False, help='perform static code analysis and exit')
parser.add_argument('--run-model', default=1, metavar='BIT', help="run the pre-simulation script")
parser.add_argument('--run-sim', default=1, metavar='BIT', help='start process to run through simulation')

parser.add_argument('--gui', action='store_true', default=False, help='open the gui')
parser.add_argument('--review', action='store_true', default=False, help='review the previous simulation')
parser.add_argument('--clean', action='store_true', default=False, help='remove previous simulation artifacts')
parser.add_argument('--generic', '-g', action='append', type=Generic.from_arg, default=[], metavar='KEY=VALUE', help='override top-level VHDL generics')
parser.add_argument('--seed', action='store', type=int, nargs='?', default=None, const=random.randrange(sys.maxsize), metavar='NUM', help='set the randomness seed')

parser.add_argument('--top-config', default=None, help='define the top-level configuration unit')

args = parser.parse_args()

USE_VERITI = int(args.enable_veriti) != 0
RUN_MODEL = int(args.run_model) != 0

# import and use the veriti library
if USE_VERITI == True:
    import veriti

generics: List[Generic] = args.generic

# testbench's VHDL configuration unit
top_level_config = args.top_config

REVIEW = args.review
OPEN_GUI = args.gui
SETUP_SIM_ONLY = int(args.run_sim) == 0
LINT_ONLY = args.lint
CLEAN = args.clean

# open an existing waveform result
if REVIEW == True:
    if os.path.exists(WAVEFORM_FILE) == True:
        rc = Command('vsim').arg('-view').arg(WAVEFORM_FILE).arg('-do').arg("add wave *;").spawn()
        rc.unwrap()
    else:
        exit("error: No .wlf exists to review")

## Process blueprint

# enter the build directory for the rest of the workflow
BUILD_DIR = Env.read("ORBIT_BUILD_DIR", missing_ok=False)
os.chdir(BUILD_DIR)

tb_do_file: str = None
py_model: str = None
compile_order: List[Hdl] = []
# collect data from the blueprint
for rule in Blueprint().parse():
    if rule.fileset == 'VHDL-RTL' or rule.fileset == 'VHDL-SIM':
        compile_order += [Hdl(rule.identifier, rule.path)]
    elif rule.fileset == 'PY-MODEL':
        py_model = rule.path
    # see if there is a do file to run for opening modelsim
    elif rule.fileset == 'DO-FILE':
        tb_do_file = rule.path
        pass
    pass

# force remove directory if clean is enabled
if CLEAN == True and os.path.exists(SIM_DIR) == True:
    shutil.rmtree(SIM_DIR)

# enter modelsim directory
os.makedirs(SIM_DIR, exist_ok=True)
os.chdir(SIM_DIR)

# track what libraries we have seen
libraries = []

print("info: Compiling HDL source code ...")
item: Hdl
for item in compile_order:
    print('  -', Env.quote_str(item.path))
    # create new libraries and their mappings
    if item.lib not in libraries:
        Command('vlib').arg(item.lib).spawn().unwrap()
        Command('vmap').arg(item.lib).arg(item.lib).spawn().unwrap()
        libraries.append(item.lib)
    # compile VHDL
    Command('vcom').arg('-work').arg(item.lib).arg(item.path).spawn().unwrap()
    pass

if LINT_ONLY == True:
    print("info: Static analysis complete")
    exit(0)

# pre-simulation hook: generate test vectors
if USE_VERITI == True and py_model != None:
    import veriti

    ORBIT_BENCH = Env.read("ORBIT_BENCH", missing_ok=False)
    ORBIT_TOP = Env.read("ORBIT_TOP", missing_ok=False)

    # export the interfaces using orbit to get the json data format
    design_if = Command("orbit").arg("get").arg(ORBIT_TOP).arg("--json").output()[0]
    bench_if = Command("orbit").arg("get").arg(ORBIT_BENCH).arg("--json").output()[0]
    
    # prepare the proper context
    veriti.config.set(design_if=design_if, bench_if=bench_if, work_dir='.', generics=generics, seed=args.seed)
    pass

if RUN_MODEL == True and py_model != None:
    import runpy, sys, os
    # switch the sys.path[0] from this script's path to the model's path
    this_script_path = sys.path[0]
    sys.path[0] = os.path.dirname(py_model)
    print("info: Running Python software model ...")
    # run the python model script in its own namespace
    runpy.run_path(py_model, init_globals={})
    sys.path[0] = this_script_path
    pass

BENCH = Env.read("ORBIT_BENCH", missing_ok=True)

if BENCH is None:
    exit('error: No testbench to simulate\n\nUse \"--lint\" to only compile the HDL code or set a testbench to simulate')

# 2. create a .do file to automate modelsim actions
print("info: Generating .do file ...")
with open(DO_FILE, 'w') as file:
    # prepend .do file data
    if OPEN_GUI == True:
        # add custom waveform/vsim commands
        if tb_do_file != None and os.path.exists(tb_do_file) == True:
            print("info: Importing commands from .do file:", tb_do_file)
            with open(tb_do_file, 'r') as do:
                for line in do.readlines():
                    # add all non-blank lines
                    if len(line.strip()) > 0:
                        file.write(line)
                pass
        # write default to include all signals into waveform
        else:
            file.write('add wave *\n')
            pass
    if SETUP_SIM_ONLY == False:
        file.write('run -all\n')
    if OPEN_GUI == False:
        file.write('quit\n')
    pass

## Run simulation with top-level testbench

# determine to run as script or as gui
mode = "-batch" if OPEN_GUI == False else "-gui"

# override bench with top-level config
BENCH = top_level_config if top_level_config != None else BENCH

# run simulation with vsim
print("info: Starting VHDL simulation for testbench", Env.quote_str(BENCH), "...")
Command('vsim') \
    .arg(mode) \
    .arg('-onfinish').arg('stop') \
    .arg('-do').arg(DO_FILE) \
    .arg('-wlf').arg(WAVEFORM_FILE) \
    .arg(BENCH) \
    .args(['-g' + item.to_str() for item in generics]) \
    .spawn().unwrap()

# post-simulation hook: analyze outcomes
if USE_VERITI == True:
    log_file = veriti.log.get_name()
    print("info: Simulation history saved at:", veriti.log.get_event_log_path(log_file))
    print("info: Computing results ...")
    print("info: Simulation score:", veriti.log.report_score(log_file))
    rc = 0 if veriti.log.check(log_file, None) == True else 101
    exit(rc)
else:
    print('info: Simulation complete')