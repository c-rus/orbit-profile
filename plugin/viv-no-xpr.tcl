# ------------------------------------------------------------------------------
# Script   : viv-no-xpr.tcl
# Author   : Chase Ruskin
# Modified : 2022-09-04
# Created  : 2022-09-04
# Details  :
#   Complete toolchain for Vivado in non-project mode.
#   
#   Referenced from:
#       https://grittyengineer.com/vivado-non-project-mode-releasing-vivados-true-potential/
# ------------------------------------------------------------------------------

# try to disable webtalk (may have no affect if using WEBPACK license)
config_webtalk -user "off"

# --- Constants ----------------------------------------------------------------
# ------------------------------------------------------------------------------

set SYNTH_FLOW 1
set IMPL_FLOW  2
set ROUTE_FLOW 3
set BIT_FLOW   4

set DEFAULT_FLOW 0

set ON  1
set OFF 0

set ERR_CODE 1
set OK_CODE  0

# --- Procedures ---------------------------------------------------------------
# ------------------------------------------------------------------------------

proc program_device {bit_file} {
    # connect to the digilent cable on localhost
    open_hw_manager
    connect_hw_server -allow_non_jtag
    open_hw_target

    # find the Xilinx FPGA device connected to the local machine
    set DEVICE [lindex [get_hw_devices "xc*"] 0]
    puts "INFO: Detected device $DEVICE ..."
    current_hw_device $DEVICE
    refresh_hw_device -update_hw_probes false $DEVICE
    set_property PROBES.FILE {} $DEVICE
    set_property FULL_PROBES.FILE {} $DEVICE
    set_property PROGRAM.FILE $bit_file $DEVICE
    # program and refresh the fpga device
    program_hw_devices $DEVICE
    refresh_hw_device $DEVICE 
}

# --- Handle command-line inputs -----------------------------------------------
# ------------------------------------------------------------------------------

# values set by command-line
set PART ""
set FLOW $DEFAULT_FLOW
set CLEAN $OFF
set PROGRAM_BOARD $OFF

set prev_arg ""
for {set i 0 } { $i < $argc } { incr i } {
    # set the current argument to handle
    set cur_arg [lindex $argv $i]

    # check for single flags
    switch $cur_arg {
        "--synth" {
            set FLOW $SYNTH_FLOW
        }
        "--impl" {
            set FLOW $IMPL_FLOW
        }
        "--route" {
            set FLOW $ROUTE_FLOW
        }
        "--bit" {
            set FLOW $BIT_FLOW
        }
        "--clean" {
            set CLEAN $ON
        }
        "--pgm" {
            set PROGRAM_BOARD $ON
        }
        default {
           # check for optional values 
            switch $prev_arg {
                "--part" {
                    set PART $cur_arg
                }
            }
        }
    }
    # update previous argument to remember for next state
    set prev_arg $cur_arg
}

# --- Initialize setup ---------------------------------------------------------
# ------------------------------------------------------------------------------

# verify the output directory exists
if { [file exists $env(ORBIT_BUILD_DIR)] == 0 } {
    puts "ERROR: Orbit build directory does not exist"
    exit $ERR_CODE
}
# enter the build directory
cd $env(ORBIT_BUILD_DIR)

# verify the blueprint exists
if { [file exists $env(ORBIT_BLUEPRINT)] == 0 } {
    puts "ERROR: Orbit blueprint file does not exist in current build directory"
    exit $ERR_CODE
}

# verify a toplevel is set
if { $env(ORBIT_TOP) == "" } {
    puts "ERROR: No toplevel set by Orbit through environment variable ORBIT_TOP"
    exit $ERR_CODE
}
# store the target bitfile filename
set BIT_FILE "$env(ORBIT_TOP).bit"

# create output directory
set OUTPUT_DIR $env(ORBIT_IP_NAME)
file mkdir $OUTPUT_DIR
set files [glob -nocomplain "$OUTPUT_DIR/*"]
if { $CLEAN == $ON && [llength $files] != 0 } {
    # clear folder contents
    puts "INFO: Deleting contents of $OUTPUT_DIR/"
    file delete -force {*}[glob -directory $OUTPUT_DIR *]; 
}

# access the blueprint's data
set blueprint_file $env(ORBIT_BLUEPRINT)
set blueprint_data [read [open $env(ORBIT_BLUEPRINT) r]]

# enter the output directory
cd $OUTPUT_DIR

# just program device if there is a bitstream file and no flow was specified
if { $FLOW == $DEFAULT_FLOW && $PROGRAM_BOARD == $ON } {
    program_device $BIT_FILE
    exit $OK_CODE
}

# --- Process data in blueprint ------------------------------------------------
# ------------------------------------------------------------------------------

foreach rule [split $blueprint_data "\n"] {
    # break rule into the 3 main components
    lassign [split $rule "\t"] fileset library path
    # branch to action according to rule's fileset
    switch $fileset {
        # synthesizable vhdl files
        "VHDL-RTL" {
            read_vhdl -library $library $path
        }
        # synthesizable verilog files
        "VLOG-RTL" {
            read_verilog -library $library $path
        }
        # Xilinx design constraints
        "XIL-XDC" {
            read_xdc $path
        }
    }
}

# --- Execute toolchain --------------------------------------------------------
# ------------------------------------------------------------------------------

# 1. run synthesis
if { $FLOW >= $DEFAULT_FLOW } {
    synth_design -top $env(ORBIT_TOP) -part $PART
    write_checkpoint -force "post_synth.dcp"
    report_timing_summary -file "post_synth_timing_summary.rpt"
    report_utilization -file "post_synth_util.rpt"
}

# 2. run implementation
if { $FLOW >= $IMPL_FLOW } {
    opt_design
    place_design
    report_clock_utilization -file "clock_util.rpt"
    #get timing violations and run optimizations if needed
    if {[get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]] < 0} {
        puts "INFO: Found setup timing violations => running physical optimization"
        phys_opt_design
    }
    write_checkpoint -force "post_place.dcp"
    report_utilization -file "post_place_util.rpt"
    report_timing_summary -file "post_place_timing_summary.rpt"
}

# 3. route design
if { $FLOW >= $ROUTE_FLOW } {
    route_design -directive Explore
    write_checkpoint -force "post_route.dcp"
    report_route_status -file "post_route_status.rpt"
    report_timing_summary -file "post_route_timing_summary.rpt"
    report_power -file "post_route_power.rpt"
    report_drc -file "post_imp_drc.rpt"
}

# 4. generate bitstream
if { $FLOW >= $BIT_FLOW } {
    write_verilog -force "cpu_impl_netlist_$env(ORBIT_TOP).v" -mode timesim -sdf_anno true
    write_bitstream -force $BIT_FILE

    # 4a. program to the connected device
    if { $PROGRAM_BOARD == $ON } {
        program_device $BIT_FILE
    }
}

exit 0