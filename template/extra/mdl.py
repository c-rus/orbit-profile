# ------------------------------------------------------------------------------
# Project: {{ orbit.ip }}
# Engineer: {{ orbit.user }}
# Created: {{ orbit.date }}
# Script: {{ orbit.filename }}
# Details:
#   Implements behavioral software model for HDL testbench {{ orbit.filename }}.
#
#   Writes files to be used as input data and expected output data during the
#   HDL simulation.
# ------------------------------------------------------------------------------

# @note: uncomment the following lines to use custom python module for testbenches
# --- BEGIN IMPORT TOOLBOX ---
# import subprocess, sys
# # grab the profile's installed path which should be starting from ORBIT_HOME
# try:
#     ORBIT_HOME = subprocess.check_output(['orbit', 'env', 'ORBIT_HOME']).decode('utf-8').strip()
# except:
#     exit('error: Failed to access Orbit home path')
# # append to the system path to look for toolbox package
# sys.path.append(ORBIT_HOME+'/profile/c-rus')
# # @note: the module is viewable: "$(orbit env ORBIT_HOME)"/profile/c-rus/toolbox
# from toolbox import toolbox as tb
# --- END IMPORT TOOLBOX ---

# --- Constants ----------------------------------------------------------------

IN_FILE_NAME  = 'inputs.dat'
OUT_FILE_NAME = 'outputs.dat'

# --- Classes and Functions ----------------------------------------------------


# --- Logic --------------------------------------------------------------------

# collect generics from HDL testbench file and command-line
# generics = tb.get_generics()

# input_file = open(IN_FILE_NAME, 'w')
# output_file = open(OUT_FILE_NAME, 'w')



# # close files
# input_file.close()
# output_file.close()