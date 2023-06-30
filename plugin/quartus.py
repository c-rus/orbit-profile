##! File        : quartus.py
##! Engineer    : Chase Ruskin
##!
##! Modified    : 2023-06-30
##! Created     : 2021-08-30
##!
##! Details     :
##!   Creates a Quartus project to execute any stage of the FPGA toolchain
##!   workflow. This script has the ability to override the top-level generics
##!   through the writing of a TCL script to eventually get called by Quartus.
##!
##!   The script can auto-detect an Intel FPGA connected to the PC to program
##!   with a .pof or .sof bitstream file.
##!   
##! References  :
##!   [1] https://www.intel.co.jp/content/dam/altera-www/global/ja_JP/pdfs/literature/an/an312.pdf
##!   [2] https://community.intel.com/t5/Intel-Quartus-Prime-Software/Passing-parameter-generic-to-the-top-level-in-Quartus-tcl/td-p/239039

import os
from typing import List
import argparse

import toml

from mod import Command, Env, Generic, Blueprint, Hdl

# --- Constants ----------------------------------------------------------------

# read environment variable from orbit config.toml
QUARTUS_PATH = Env.read("ORBIT_ENV_QUARTUS_PATH", missing_ok=True)
# temporarily appends quartus installation path to PATH env variable
Env.add_path(QUARTUS_PATH)

# device selected here is read from .board file
FAMILY = None
DEVICE = None

# the quartus project will reside in a folder the same name as the IP
PROJECT = Env.read("ORBIT_IP_NAME", default="untitled")

# the directory to hold all plugin-related files
PROJECT_DIR = 'quartus'

# the script that is made within this file and then executed by quartus
TCL_SCRIPT = "orbit.tcl"

# will be overridden when programming to board with auto-detection by quartus
CABLE = "USB-Blaster"

# --- Classes/Functions --------------------------------------------------------

class Tcl:
    def __init__(self, path: str):
        self._file = path
        self._contents = ''
        pass


    def append(self, code: str, end='\n'):
        self._contents += code + end


    def save(self):
        with open(self._file, 'w') as f:
            f.write(self._contents)


    def get_script(self) -> str:
        return self._file
    
    pass

# --- Handle command-line arguments --------------------------------------------

parser = argparse.ArgumentParser(allow_abbrev=False)

parser.add_argument("--pgm-soft", action="store_true", default=False, help="program with temporary bitfile")
parser.add_argument("--pgm-hard", action="store_true", default=False, help="program with permanent bitfile")
parser.add_argument("--open", action="store_true", default=False, help="open quartus project in gui")
parser.add_argument("--include-sim", action="store_true", default=False, help="add simulation files to project")
parser.add_argument("--compile", action="store_true", default=False, help="full toolflow")
parser.add_argument("--synth", action="store_true", default=False, help="execute analysize and synthesis")
parser.add_argument("--route", action="store_true", default=False, help="execute place and route")
parser.add_argument("--bit", action="store_true", default=False, help="generate bitstream file")
parser.add_argument("--sta", action="store_true", default=False, help="execute static timing analysis")
parser.add_argument("--board", action="store", default=None, type=str, help="board configuration file name")
parser.add_argument("--eda-netlist", action="store_true", default=False, help="generate eda timing netlist")
parser.add_argument('--generic', '-g', action='append', type=Generic.from_arg, default=[], metavar='key=value', help='override top-level VHDL generics')

args = parser.parse_args()

generics: List[Generic] = args.generic

# determine if to program the FPGA board
pgm_temporary = args.pgm_soft
pgm_permanent = args.pgm_hard

# determine if to open the quartus project in GUI
open_project = args.open

# don't add simulation files to project
ignore_sim = args.include_sim == False

# default flow is none (won't execute any flow)
flow = None
synth = impl = asm = sta = eda_netlist = False
if args.compile == True:
    flow = '-compile'
else:
    # run up through synthesis
    if args.synth == True:
        synth = True
    # run up through fitting
    if args.route == True:
        synth = impl = True
    # run up through static timing analysis
    if args.sta == True:
        synth = impl = sta = True
    # run up through assembly
    if args.bit == True:
        synth = impl = sta = asm = True
    # run up through generating eda timing netlist
    if args.eda_netlist == True:
        synth = impl = sta = asm = eda_netlist = True
    # use a supported device to generate .SDO and .VHO files for timing simulation
    if eda_netlist == True:
        FAMILY = "MAXII"
        DEVICE = "EPM2210F324I5"
    pass

# --- Collect data from the blueprint ------------------------------------------

# enter the build directory
BUILD_DIR = Env.read("ORBIT_BUILD_DIR", missing_ok=False)
os.chdir(BUILD_DIR)

# list of (lib, path)
vhdl_files = []
vlog_files = []
# list of paths to board design files
bdf_files = []
# list of tuples (pin, port)
pin_assignments = []

board_config = None

for rule in Blueprint().parse():
    if rule.fileset == 'VHDL-RTL':
        vhdl_files += [Hdl(rule.identifier, rule.path)]
    elif rule.fileset == 'VHDL-SIM' and ignore_sim == False:
        vhdl_files += [Hdl(rule.identifier, rule.path)]
    elif rule.fileset == 'VLOG-RTL':
        vlog_files += [Hdl(rule.identifier, rule.path)]
    elif rule.fileset == 'VLOG-SIM' and ignore_sim == False:
        vlog_files += [Hdl(rule.identifier, rule.path)]
    elif rule.fileset == "BDF-FILE":
        bdf_files += [rule.path]
    elif rule.fileset == 'BOARD-CF':
        if args.board is None:
            board_config = toml.load(rule.path)
        elif rule.identifier == args.board:
            board_config = toml.load(rule.path)
        pass
    pass

# verify we got a matching board file if specified from the command-line
if board_config is None and args.board is not None:
    exit("error: Board file "+Env.quote_str(args.board)+" is not found in blueprint")

if board_config is not None:
    FAMILY = board_config["part"]["FAMILY"]
    DEVICE = board_config["part"]["DEVICE"]

top_unit = Env.read("ORBIT_TOP", missing_ok=False)

if FAMILY == None:
    exit("error: FPGA 'FAMILY' must be specified in .board file")
if DEVICE == None:
    exit("error: FPGA 'DEVICE' must be specified in .board file")

# --- Process data -------------------------------------------------------------

# Define initial project settings
PROJECT_SETTINGS = """\
# Quartus project TCL script automatically generated by Orbit. DO NOT EDIT.
load_package flow

#### General project settings ####

# Create the project and overwrite any settings or files that exist
project_new """ + Env.quote_str(PROJECT) + """ -revision """ + Env.quote_str(PROJECT) + """ -overwrite
# Set default configurations and device
set_global_assignment -name VHDL_INPUT_VERSION VHDL_1993
set_global_assignment -name EDA_SIMULATION_TOOL "ModelSim-Altera (VHDL)"
set_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VHDL" -section_id EDA_SIMULATION
set_global_assignment -name EDA_GENERATE_FUNCTIONAL_NETLIST OFF -section_id EDA_SIMULATION
set_global_assignment -name FAMILY """ + Env.quote_str(FAMILY) + """
set_global_assignment -name DEVICE """ + Env.quote_str(DEVICE) + """
# Use single uncompressed image with memory initialization file
set_global_assignment -name EXTERNAL_FLASH_FALLBACK_ADDRESS 00000000
set_global_assignment -name USE_CONFIGURATION_DEVICE OFF
set_global_assignment -name INTERNAL_FLASH_UPDATE_MODE "SINGLE IMAGE WITH ERAM" 
# Configure tri-state for unused pins     
set_global_assignment -name RESERVE_ALL_UNUSED_PINS_WEAK_PULLUP "AS INPUT TRI-STATED"
"""

# 1. write TCL file for quartus project

tcl = Tcl(TCL_SCRIPT)

tcl.append(PROJECT_SETTINGS)

tcl.append('#### Application-specific settings ####', end='\n\n')

tcl.append('# Add source code files to the project')

# generate the required tcl text for adding source files (vhdl, verilog, bdf)
tcl_src_files = ""
for vhd in vhdl_files:
    tcl.append("set_global_assignment -name VHDL_FILE "+Env.quote_str(vhd.path)+" -library "+Env.quote_str(vhd.lib))

for vlg in vlog_files:
    tcl.append("set_global_assignment -name VHDL_FILE "+Env.quote_str(vlg.path)+" -library "+Env.quote_str(vlg.lib))

for bdf in bdf_files:
    tcl.append("set_global_assignment -name BDF_FILE "+Env.quote_str(bdf))

# set the top level entity
tcl.append('# Set the top level entity')
tcl.append("set_global_assignment -name TOP_LEVEL_ENTITY "+Env.quote_str(top_unit))

# set generics for top level entity
if len(generics) > 0:
    tcl.append('# Set generics for top level entity')
generic: Generic
for generic in generics:
    tcl.append("set_parameter -name "+Env.quote_str(generic.key)+" "+Env.quote_str(str(generic.val)))

# set the pin assignments
tcl.append('# Set the pin assignments')
for (pin, port) in board_config['pins'].items():
    tcl.append("set_location_assignment "+Env.quote_str(pin)+" -to "+Env.quote_str(port))

# run a preset workflow
if flow is not None:
    tcl.append('# Execute a workflow')
    tcl.append('execute_flow '+flow)
    pass

# close the newly created project
tcl.append('# Close the project')
tcl.append('project_close')

# create and enter the quartus project directory
os.makedirs(PROJECT_DIR, exist_ok=True)
os.chdir(PROJECT_DIR)

# finish writing the TCL script and save it to disk
tcl.save()

# 2. run quartus with TCL script

# execute quartus using the generated tcl script
Command("quartus_sh").args(['-t', tcl.get_script()]).spawn().unwrap()

# 3. perform a specified toolflow

# synthesize design
if synth == True:
    Command("quartus_map").arg(PROJECT).spawn().unwrap()
# route design to board
if impl == True:
    Command("quartus_fit").arg(PROJECT).spawn().unwrap()
# perform static timing analysis
if sta == True:
    Command("quartus_sta").arg(PROJECT).spawn().unwrap()
# generate bitstream
if asm == True:
    Command("quartus_asm").arg(PROJECT).spawn().unwrap()
# generate necessary files for timing simulation
if eda_netlist == True:
    Command("quartus_eda").args([PROJECT, '--simulation']).spawn().unwrap()

# 4. program the FPGA board

# auto-detect the FPGA programming cable
if pgm_temporary == True or pgm_permanent == True:
    out, status = Command("quartus_pgm").arg('-a').output()
    status.unwrap()
    if out.startswith('Error ') == True:
        print(out, end='')
        exit(101)
    tokens = out.split()
    # grab the second token (cable name)
    CABLE = tokens[1]
    pass

prog_args = ['-c', CABLE, '-m', 'jtag', '-o']
# program the FPGA board with temporary SRAM file
if pgm_temporary == True:
    if os.path.exists(PROJECT+'.sof') == True:
        Command('quartus_pgm').args(prog_args).args(['p'+';'+PROJECT+'.sof']).spawn().unwrap()
    else:
        exit('error: Bitstream .sof file not found')
    pass
# program the FPGA board with permanent program file
elif pgm_permanent == True:
    if os.path.exists(PROJECT+'.pof') == True:
        Command('quartus_pgm').args(prog_args).args(['bpv'+';'+PROJECT+'.pof']).spawn().unwrap()
    else:
        exit('error: Bitstream .pof file not found')
    pass

# 5. open the quartus project

# open the project using quartus GUI
if open_project == True:
    Command('quartus').arg(PROJECT+'.qpf').spawn().unwrap()
    pass