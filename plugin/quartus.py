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
# ------------------------------------------------------------------------------
import os,sys,subprocess

# === Define constants, important variables, helper methods ====================
#   Identify any variables necessary for this script to work. Some examples
#   include tool path, device name, project name, device family name. 
# ==============================================================================

# read environment variable from orbit config.toml
QUARTUS_PATH = os.environ.get("ORBIT_ENV_QUARTUS_PATH")

# temporarily appends quartus installation path to PATH env variable
if(QUARTUS_PATH != None and os.path.exists(QUARTUS_PATH) and QUARTUS_PATH not in os.getenv('PATH')):
    os.environ['PATH'] = os.getenv('PATH') + ';' + QUARTUS_PATH


def execute(*code, subproc=False):
    '''Prints the space-separated command and runs it as a subprocess.'''
    code_line = ''
    for c in code:
        code_line = code_line + c + ' '
    print(code_line)
    if(subproc):
        rc = subprocess.Popen(code_line.split()).returncode
    else:
        rc = os.system(code_line)
    # immediately stop script upon a bad return code
    if(rc):
        exit('error: command exited with code: '+str(rc))
    pass


# device selected here is the DE10-Lite FPGA (overridden)
FAMILY = None
DEVICE = None

# the quartus project will reside in a folder the same name as this block's folder
PROJECT = os.path.basename(os.getcwd())

# the script that is made within this file and then executed by quartus
TCL_SCRIPT = "project.tcl"

# will be overridden when programming to board with auto-detection by quartus
CABLE = "USB-Blaster"

# === Handle command-line arguments ============================================
#   Create custom command-line arguments to handle specific workflows and common
#   usage cases.
# ==============================================================================

# skip over the first argument (this script's filepath)
args = sys.argv[1:]

# determine if to program the FPGA board
pgm_temporary = args.count('--pgm-soft')
pgm_permanent = args.count('--pgm-hard')

# determine if to open the quartus project in GUI
open_project = args.count('--open')

# don't add simulation files to project
ignore_sim = args.count('--include-sim') == 0

# default flow is none (won't execute any flow)
flow = None
synth = impl = asm = sta = eda_netlist = False
if(args.count('--compile')):
    flow = '-compile'
else:
    # run up through synthesis
    if(args.count('--synth')):
        synth = True
    # run up through fitting
    if(args.count('--route')):
        synth = impl = True
    # run up through assembly
    if(args.count('--bitstream')):
        synth = impl = asm = True
    # run up through static timing analysis
    if(args.count('--sta')):
        synth = impl = asm = sta = True
    # run up through generating eda timing netlist
    if(args.count('--eda-netlist')):
        synth = impl = asm = sta = eda_netlist = True
    # use a supported device to generate .SDO and .VHO files for timing simulation
    if(eda_netlist):
        FAMILY = "MAXII"
        DEVICE = "EPM2210F324I5"

# === Collect data from the blueprint file =====================================
#   This part will gather the necessary data we want for our workflow so that
#   we can act accordingly on that data to get the ouptut we want.
# ==============================================================================

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

# change directory to build
os.chdir(BUILD_DIR)

# --- collect data from the blueprint ------------------------------------------

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
        fileset, name, path = rule.strip().split('\t')
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
    blueprint.close()
    pass

top_unit = os.environ.get("ORBIT_TOP")

if FAMILY == None:
    exit("error: FPGA 'FAMILY' must be specified in .board file")
if DEVICE == None:
    exit("error: FPGA 'DEVICE' must be specified in .board file")

# === Act on the collected data ================================================
#   Now that we have the 'ingredients', write some logic to call your tool
#   based on the data we collected. One example could be to use the collected
#   data to write a TCL script, and then call your EDA tool to use that TCL
#   script.
# ==============================================================================

# ---[1] Write TCL file for quartus project

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

tcl_flow = ""
if(flow != None):
    tcl_flow = "execute_flow "+flow

# contents of the tcl script
tcl_contents = """load_package flow
# Create the project and overwrite any settings
# files that exist
project_new """ + PROJECT + """ -revision """ + PROJECT + """ -overwrite
# Set the device
set_global_assignment -name VHDL_INPUT_VERSION VHDL_1993
set_global_assignment -name EDA_SIMULATION_TOOL "ModelSim-Altera (VHDL)"
set_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VHDL" -section_id EDA_SIMULATION
set_global_assignment -name EDA_GENERATE_FUNCTIONAL_NETLIST OFF -section_id EDA_SIMULATION
set_global_assignment -name FAMILY """ + FAMILY + """
set_global_assignment -name DEVICE """ + DEVICE + """
# Use single uncompressed image with memory initialization file
set_global_assignment -name EXTERNAL_FLASH_FALLBACK_ADDRESS 00000000
set_global_assignment -name USE_CONFIGURATION_DEVICE OFF
set_global_assignment -name INTERNAL_FLASH_UPDATE_MODE "SINGLE IMAGE WITH ERAM" 
# Tri-state unused pins     
set_global_assignment -name RESERVE_ALL_UNUSED_PINS_WEAK_PULLUP "AS INPUT TRI-STATED"
# Add source code files to the project
""" + tcl_src_files + """
# Set the top level entity
""" + tcl_top_level + """
# Add pin assignments
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

# ---[2] Run quartus with TCL script

# execute quartus using the written tcl script
execute('quartus_sh','-t', TCL_SCRIPT)

# ---[3] Perform a specified toolflow

# synthesize design
if(synth):
    execute("quartus_map", PROJECT)
# route design to board
if(impl):
    execute("quartus_fit", PROJECT)
# generate bitstream
if(asm):
     execute("quartus_asm", PROJECT)
# perform static timing analysis
if(sta):
    execute("quartus_sta", PROJECT)
# generate necessary files for timing simulation
if(eda_netlist):
    execute('quartus_eda', PROJECT, '--simulation')

# ---[4] Program the FPGA board

# auto-detect the FPGA programming cable
if(pgm_temporary or pgm_permanent):
    output = subprocess.Popen(['quartus_pgm','-a'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = output.communicate()
    if(out != None):
        out = out.decode('utf-8')
        print(out,end='')
        if(out.startswith('Error ')):
            exit(1)
        tokens = out.split()
        # grab the second token (cable name)
        CABLE = tokens[1]

# program the FPGA board with temporary SRAM file
if(pgm_temporary):
    if(os.path.exists(PROJECT+'.sof')):
        execute('quartus_pgm','-c',CABLE,'-m','jtag','-o','p'+';'+PROJECT+'.sof')
    else:
        exit('error: bit stream not found')
# program the FPGA board with permanent program file
elif(pgm_permanent):
    if(os.path.exists(PROJECT+'.pof')):
        execute('quartus_pgm','-c',CABLE,'-m','jtag','-o','bpv'+';'+PROJECT+'.pof')
    else:
        exit('error: bitstream not found')

# ---[5] Open the quartus project

# open the project using quartus GUI
if open_project == True:
    execute('quartus', PROJECT+'.qpf', subproc=open_project)