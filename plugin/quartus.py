# ------------------------------------------------------------------------------
# Script   : quartus.py
# Author   : Chase Ruskin
# Modified : 2022/09/03
# Created  : 2021/08/30
# Details  :
#   By default creates a Quartus project.
#
#   Quartus TCL Reference Guide:
#   https://www.intel.co.jp/content/dam/altera-www/global/ja_JP/pdfs/literature/an/an312.pdf
#
# Todo:
#   - [ ] override top-level generics 
#   https://community.intel.com/t5/Intel-Quartus-Prime-Software/Passing-parameter-generic-to-the-top-level-in-Quartus-tcl/td-p/239039
# ------------------------------------------------------------------------------
import os,sys,subprocess
from typing import List
import argparse

# --- Constants ----------------------------------------------------------------

# read environment variable from orbit config.toml
QUARTUS_PATH = os.environ.get("ORBIT_ENV_QUARTUS_PATH")
# temporarily appends quartus installation path to PATH env variable
if(QUARTUS_PATH != None and os.path.exists(QUARTUS_PATH) and QUARTUS_PATH not in os.getenv('PATH')):
    os.environ['PATH'] = QUARTUS_PATH + ';' + os.getenv('PATH')

# device selected here is read from .board file
FAMILY = None
DEVICE = None

# the quartus project will reside in a folder the same name as the IP
PROJECT = os.path.basename(os.environ.get("ORBIT_IP_NAME"))

# the script that is made within this file and then executed by quartus
TCL_SCRIPT = "orbit.tcl"

# will be overridden when programming to board with auto-detection by quartus
CABLE = "USB-Blaster"

# --- Classes and Functions ----------------------------------------------------

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

generics = {}
# adding arguments
parser = argparse.ArgumentParser()
parser.add_argument("--pgm-soft", help="program with temporary bitfile", action="store_true", default=False)
parser.add_argument("--pgm-hard", help="program with permanent bitfile", action="store_true", default=False)
parser.add_argument("--open", help="open quartus project in gui", action="store_true", default=False)
parser.add_argument("--include-sim", help="add simulation files to project", action="store_true", default=False)
parser.add_argument("--compile", help="full toolflow", action="store_true", default=False)
parser.add_argument("--synth", help="execute analysize and synthesis", action="store_true", default=False)
parser.add_argument("--route", help="execute place and route", action="store_true", default=False)
parser.add_argument("--bit", help="generate bitstream file", action="store_true", default=False)
parser.add_argument("--sta", help="execute static timing analysis", action="store_true", default=False)
parser.add_argument("--eda-netlist", help="generate eda timing netlist", action="store_true", default=False)
parser.add_argument('-g', '--generic', action='append', nargs='*', type=str)
args = parser.parse_args()
if args.generic != None:
    for arg in args.generic:
        value = None
        name = arg[0]
        if arg[0].count('=') > 0:
            name, value = arg[0].split('=', maxsplit=1)
        generics[name] = value

# determine if to program the FPGA board
pgm_temporary = args.pgm_soft
pgm_permanent = args.pgm_hard

# determine if to open the quartus project in GUI
open_project = args.open

# don't add simulation files to project
ignore_sim = args.include_sim

# default flow is none (won't execute any flow)
flow = None
synth = impl = asm = sta = eda_netlist = False
if(args.compile):
    flow = '-compile'
else:
    # run up through synthesis
    if(args.synth):
        synth = True
    # run up through fitting
    if(args.route):
        synth = impl = True
    # run up through assembly
    if(args.bit):
        synth = impl = asm = True
    # run up through static timing analysis
    if(args.sta):
        synth = impl = asm = sta = True
    # run up through generating eda timing netlist
    if(args.eda_netlist):
        synth = impl = asm = sta = eda_netlist = True
    # use a supported device to generate .SDO and .VHO files for timing simulation
    if(eda_netlist):
        FAMILY = "MAXII"
        DEVICE = "EPM2210F324I5"

# --- Verify the planning phase and setup --------------------------------------

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

# --- Collect data from the blueprint ------------------------------------------

# list of (lib, path)
vhdl_files = []
vlog_files = []
# list of paths to board design files
bdf_files = []
# list of tuples (pin, port)
pin_assignments = []

# open the blueprint file
with open(BLUEPRINT, 'r') as blueprint:
    for rule in blueprint.readlines():
        fileset, name, path = rule.strip('\n').split('\t', maxsplit=3)
        # add VHDL source files
        if fileset == "VHDL-RTL":
            vhdl_files.append((name, path))
            pass
        # add VHDL simulation files if explicitly requested
        elif fileset == "VHDL-SIM" and ignore_sim == False:
            vhdl_files.append((name, path))
            pass
        # add Verilog source files
        elif fileset == "VLOG-RTL":
            vlog_files.append((name, path))
            pass
        # add Verilog simulation files if explicitly requested
        elif fileset == "VLOG-SIM" and ignore_sim == False:
            vlog_files.append((name, path))
            pass
        # custom fileset: add board design files
        elif fileset == "BDF-FILE":
            bdf_files.append(path)
            pass
        # custom fileset: capture information regarding pin planning
        elif fileset == "PIN-PLAN":
            # custom parsing of file to get necessary pin->port data
            with open(path) as pin_file:
                placements = pin_file.readlines()
                for assignment in placements:
                    assignment = assignment.strip()
                    # skip any comment lines indicated by '#' or ';'
                    ending = len(assignment)
                    ci = assignment.find('#')
                    if ci > -1:
                        ending = ci
                    ci = assignment.find(';')
                    if ci > -1 and ci < ending:
                        ending = ci
                    # trim to before the comment
                    if(ci > -1):
                        assignment = assignment[:ci]
                    # separate by the equal sign '='
                    if(assignment.count('=') != 1):
                        continue
                    pin,name = assignment.split('=')
                    pin = pin.strip().upper()
                    name = name.strip()
                    # configures the device and family if set in .PAF file
                    if(pin == "DEVICE" or pin == "FAMILY"):
                        # do not override device if writing a eda netlist
                        if(eda_netlist == False):
                            FAMILY = name if(pin == "FAMILY") else FAMILY
                            DEVICE = name if(pin == "DEVICE") else DEVICE
                    # configures the pin mappings
                    else:
                        pin_assignments.append((pin,name))
                    pass
                pass
            pass
    pass

top_unit = os.environ.get("ORBIT_TOP")

if top_unit == None:
    exit("ERROR: No top-level set in $ORBIT_TOP")

if FAMILY == None:
    exit("ERROR: FPGA 'FAMILY' must be specified in .board file")
if DEVICE == None:
    exit("ERROR: FPGA 'DEVICE' must be specified in .board file")

# --- Process data -------------------------------------------------------------

# 1. write TCL file for quartus project

# generate the required tcl text for adding source files (vhdl, verilog, bdf)
tcl_src_files = ""
for vhd in vhdl_files:
    tcl_src_files = tcl_src_files+"set_global_assignment -name VHDL_FILE "+vhd[1]+" -library "+vhd[0]+"\n"

for vlg in vlog_files:
    tcl_src_files = tcl_src_files+"set_global_assignment -name VERILOG_FILE "+vlg[1]+" -library "+vlg[0]+"\n"

for bdf in bdf_files:
    tcl_src_files = tcl_src_files+"set_global_assignment -name BDF_FILE "+bdf+"\n"

# generate the required tcl text for placing pins
tcl_pin_assigments = ""
for pin in pin_assignments:
    tcl_pin_assigments = tcl_pin_assigments+"set_location_assignment "+pin[0]+" -to "+pin[1]+"\n"

# generate the required tcl text for setting the top level design entity
tcl_top_level = ""
if(top_unit != None):
    tcl_top_level = "set_global_assignment -name TOP_LEVEL_ENTITY "+top_unit+"\n"

# set top-level generics
tcl_top_generics = ""
for (key, val) in generics.items():
    tcl_top_generics = tcl_top_generics+"set_parameter -name "+key+" "+str(val)+"\n"


tcl_flow = ""
if(flow != None):
    tcl_flow = "execute_flow "+flow

# contents of the tcl script
tcl_contents = """load_package flow
# create the project and overwrite any settings or files that exist
project_new """ + PROJECT + """ -revision """ + PROJECT + """ -overwrite
# set default configurations and device
set_global_assignment -name VHDL_INPUT_VERSION VHDL_1993
set_global_assignment -name EDA_SIMULATION_TOOL "ModelSim-Altera (VHDL)"
set_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VHDL" -section_id EDA_SIMULATION
set_global_assignment -name EDA_GENERATE_FUNCTIONAL_NETLIST OFF -section_id EDA_SIMULATION
set_global_assignment -name FAMILY """ + FAMILY + """
set_global_assignment -name DEVICE """ + DEVICE + """
# use single uncompressed image with memory initialization file
set_global_assignment -name EXTERNAL_FLASH_FALLBACK_ADDRESS 00000000
set_global_assignment -name USE_CONFIGURATION_DEVICE OFF
set_global_assignment -name INTERNAL_FLASH_UPDATE_MODE "SINGLE IMAGE WITH ERAM" 
# configure tri-state for unused pins     
set_global_assignment -name RESERVE_ALL_UNUSED_PINS_WEAK_PULLUP "AS INPUT TRI-STATED"
# add source code files to the project
""" + tcl_src_files + """
# set the top level entity
""" + tcl_top_level + """
# set generics for top level entity
""" + tcl_top_generics + """
# add pin assignments
""" + tcl_pin_assigments + """
# execute a flow
""" + tcl_flow + """
# load_rtl_netlist
project_close
"""

# create and enter the quartus project directory
os.makedirs(PROJECT, exist_ok=True)
os.chdir(PROJECT)

# write the contents of the tcl script
with open(TCL_SCRIPT, 'w') as f:
    f.write(tcl_contents)

# 2. run quartus with TCL script

# execute quartus using the generated tcl script
invoke('quartus_sh', ['-t', TCL_SCRIPT])

# 3. perform a specified toolflow

# synthesize design
if(synth):
    invoke("quartus_map", [PROJECT])
# route design to board
if(impl):
    invoke("quartus_fit", [PROJECT])
# generate bitstream
if(asm):
     invoke("quartus_asm", [PROJECT])
# perform static timing analysis
if(sta):
    invoke("quartus_sta", [PROJECT])
# generate necessary files for timing simulation
if(eda_netlist):
    invoke('quartus_eda', [PROJECT, '--simulation'])

# 4. program the FPGA board

# auto-detect the FPGA programming cable
if pgm_temporary == True or pgm_permanent == True:
    output = subprocess.Popen(['quartus_pgm', '-a'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = output.communicate()
    if(out != None):
        out = out.decode('utf-8')
        print(out, end='')
        if(out.startswith('Error ')):
            exit(1)
        tokens = out.split()
        # grab the second token (cable name)
        CABLE = tokens[1]
    pass

prog_args = ['-c', CABLE, '-m', 'jtag', '-o']
# program the FPGA board with temporary SRAM file
if pgm_temporary == True:
    if os.path.exists(PROJECT+'.sof') == True:
        invoke('quartus_pgm', prog_args + ['p'+';'+PROJECT+'.sof'])
    else:
        exit('ERROR: Bitstream .sof file not found')
# program the FPGA board with permanent program file
elif pgm_permanent == True:
    if os.path.exists(PROJECT+'.pof') == True:
        invoke('quartus_pgm', prog_args + ['bpv'+';'+PROJECT+'.pof'])
    else:
        exit('ERROR: Bitstream .pof file not found')

# 5. open the quartus project

# open the project using quartus GUI
if open_project == True:
    invoke('quartus', [PROJECT+'.qpf'])