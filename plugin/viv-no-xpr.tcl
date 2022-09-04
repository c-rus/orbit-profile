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
config_webtalk -user off

# constants
set SYNTH_FLOW 1
set IMPL_FLOW  2
set ROUTE_FLOW 3
set BIT_FLOW   4

set DEFAULT_FLOW 0


set ON 1
set OFF 0

# values set by command-line
set PART ""
set FLOW $DEFAULT_FLOW
set CLEAN $OFF
set PROGRAM_BOARD $OFF

# --- handle command-line inputs -----------------------------------------------
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

# verify the output directory exists
if { [file exists $env(ORBIT_BUILD_DIR)] == 0 } {
    puts "ERROR: Orbit build directory does not exist"
    exit 1
}
# enter the build directory
cd $env(ORBIT_BUILD_DIR)

# verify the blueprint exists
if { [file exists $env(ORBIT_BLUEPRINT)] == 0 } {
    puts "ERROR: Orbit blueprint file does not exist in current build directory"
    exit 1
}

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

set BIT_FILE "$env(ORBIT_TOP).bit"

proc program_device {bit_file} {
   # Connect to the Digilent Cable on localhost:3121
    open_hw_manager
    connect_hw_server -allow_non_jtag
    # connect_hw_server -url localhost:3121

    # current_hw_target [get_hw_targets "*/xilinx_tcf/Digilent/12345"]
    open_hw_target

    # Program and Refresh the XC7K325T Device
    set DEVICE [lindex [get_hw_devices] 0]
    current_hw_device $DEVICE
    refresh_hw_device -update_hw_probes false $DEVICE
    set_property PROBES.FILE {} $DEVICE
    set_property FULL_PROBES.FILE {} $DEVICE
    set_property PROGRAM.FILE $bit_file $DEVICE

    program_hw_devices $DEVICE
    refresh_hw_device $DEVICE 
}

# check if there is a bitstream file and no flow was specified
if { $FLOW == $DEFAULT_FLOW && $PROGRAM_BOARD == $ON } {
    program_device $BIT_FILE
    exit
}

# --- process data in blueprint ------------------------------------------------
foreach rule [split $blueprint_data "\n"] {
    # break rule into the 3 main components
    lassign [split $rule "\t"] fileset library path
    switch $fileset {
        "VHDL-RTL" {
            read_vhdl -library $library $path
        }
        "VLOG-RTL" {
            read_verilog -library $library $path
        }
        "XIL-XDC" {
            read_xdc $path
        }
    }
}

# --- execute toolchain --------------------------------------------------------

# run synthesis
if { $FLOW >= $DEFAULT_FLOW } {
    synth_design -top $env(ORBIT_TOP) -part $PART
    write_checkpoint -force "post_synth.dcp"
    report_timing_summary -file "post_synth_timing_summary.rpt"
    report_utilization -file "post_synth_util.rpt"
}

# run implementation
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

# route design
if { $FLOW >= $ROUTE_FLOW } {
    route_design -directive Explore
    write_checkpoint -force "post_route.dcp"
    report_route_status -file "post_route_status.rpt"
    report_timing_summary -file "post_route_timing_summary.rpt"
    report_power -file "post_route_power.rpt"
    report_drc -file "post_imp_drc.rpt"
}

# generate bitstream
if { $FLOW >= $BIT_FLOW } {
    write_verilog -force "cpu_impl_netlist_$env(ORBIT_TOP).v" -mode timesim -sdf_anno true
    write_bitstream -force "$env(ORBIT_TOP).bit"
}

exit