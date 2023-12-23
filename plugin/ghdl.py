# Project: orbit-profile
# Script: ghdl.py
#
# Defines a common workflow for working with the GHDL simulator and software
# models written in Python used for generating test vector I/O. Generics
# are passed to the software script as well as the VHDL testbench for
# synchronization across code
#
# The script is written to be used as the entry-point to an Orbit plugin.
#
# [1] https://github.com/ghdl/ghdl

import os, sys
import argparse, random
from typing import List

from mod import Command, Status, Env, Generic, Blueprint, Hdl

# directory to store artifacts within build directory
SIM_DIR = 'gsim'

# define ghdl path
GHDL_PATH: str = Env.read("ORBIT_ENV_GHDL_PATH", default='ghdl')
# define a vcd viewer
VCD_VIEWER: str = Env.read("ORBIT_ENV_VCD_VIEWER")

## Handle command-line arguments

parser = argparse.ArgumentParser(allow_abbrev=False)

parser.add_argument('--view', action='store_true', default=False, help='open the vcd file in a waveform viewer')
parser.add_argument('--lint', action='store_true', default=False, help='run static analysis and exit')
parser.add_argument('--seed', action='store', type=int, nargs='?', default=None, const=random.randrange(sys.maxsize), metavar='NUM', help='set the randomness seed')
parser.add_argument('--generic', '-g', action='append', type=Generic.from_arg, default=[], metavar='KEY=VALUE', help='override top-level VHDL generics')
parser.add_argument('--std', action='store', default='93', metavar='EDITION', help="specify the VHDL edition (87, 93, 02, 08, 19)")
parser.add_argument('--enable-veriti', default=1, metavar='BIT', help="toggle the usage of veriti verification library")
parser.add_argument('--run-model', default=1, metavar='BIT', help="toggle the generation of test vectors")

args = parser.parse_args()

USE_VERITI = int(args.enable_veriti) != 0
RUN_MODEL = int(args.run_model) != 0

# import and use the veriti library
if USE_VERITI == True:
    import veriti

generics: List[Generic] = args.generic

## Read blueprint

# enter the build directory for the rest of the workflow
BUILD_DIR = Env.read("ORBIT_BUILD_DIR", missing_ok=False)
os.chdir(BUILD_DIR)

py_model: str = None
rtl_order: List[Hdl] = []
# collect data from the blueprint
for rule in Blueprint().parse():
    if rule.fileset == 'VHDL-RTL' or rule.fileset == 'VHDL-SIM':
        rtl_order += [Hdl(rule.identifier, rule.path)]
    elif rule.fileset == 'PY-MODEL':
        py_model = rule.path
    pass

## Run backend workflow

# enter GHDL simulation working directory
os.makedirs(SIM_DIR, exist_ok=True)
os.chdir(SIM_DIR)

# analyze units
print("info: Analyzing HDL source code ...")
item: Hdl
for item in rtl_order:
    print('  -', Env.quote_str(item.path))
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
if USE_VERITI == True and py_model != None:
    import veriti

    ORBIT_BENCH = Env.read("ORBIT_BENCH", missing_ok=False)
    ORBIT_TOP = Env.read("ORBIT_TOP", missing_ok=False)

    # export the interfaces using orbit to get the json data format
    design_if = Command("orbit").arg("get").arg(ORBIT_TOP).arg("--json").output()[0]
    bench_if = Command("orbit").arg("get").arg(ORBIT_BENCH).arg("--json").output()[0]
    
    print("info: Running Python software model ...")
    
    # prepare the proper context
    veriti.config.set(design_if=design_if, bench_if=bench_if, work_dir='.', generics=generics, seed=args.seed)
    pass

if RUN_MODEL == True and py_model != None:
    import runpy, sys, os
    # switch the sys.path[0] from this script's path to the model's path
    this_script_path = sys.path[0]
    sys.path[0] = os.path.dirname(py_model)
    # run the python model script in its own namespace
    runpy.run_path(py_model, init_globals={})
    sys.path[0] = this_script_path
    pass

BYPASS_FAILURE = VCD_VIEWER is not None

# determine level of severity to exit
severity_arg = '--assert-level=' + ('none' if BYPASS_FAILURE == True else 'failure')

BENCH = Env.read("ORBIT_BENCH", missing_ok=True)

if BENCH is None:
    exit('error: No testbench to simulate\n\nUse \"--lint\" to only compile the HDL code or set a testbench to simulate')

VCD_FILE = str(BENCH)+'.vcd'

# run simulation
print("info: Starting VHDL simulation for testbench", Env.quote_str(BENCH), "...")
status: Status = Command(GHDL_PATH) \
    .args(['-r', '--ieee=synopsys', BENCH, '--vcd='+VCD_FILE, severity_arg]) \
    .args(['-g' + item.to_str() for item in generics]) \
    .spawn(verbose=False)

if BYPASS_FAILURE == False:
    status.unwrap()

# post-simulation hook: analyze outcomes
if USE_VERITI == True:
    print("info: Computing results ...")
    print()
    rc = 0 if veriti.log.check('events.log', None) == True else 101
    exit(rc)
else:
    print('info: Simulation complete')

# open the vcd file
if(VCD_VIEWER != None and args.view == True):
    Command(VCD_VIEWER).arg(VCD_FILE).spawn().unwrap()
    pass