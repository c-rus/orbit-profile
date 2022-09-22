# ------------------------------------------------------------------------------
# Script   : zipr.py
# Author   : Chase Ruskin
# Modified : 2022-09-22
# Created  : 2022-09-22
# Details  :
#   Compresses a list of files into a zip file.
#
#   The order of search:
#       1. Try to find file in blueprint
#       2. Try to find file in IP directory
#       3. (if --inc-build) is true -> try to find file in build directory
# ------------------------------------------------------------------------------
import argparse, os
from typing import List
from glob import glob
from zipfile import ZipFile

# --- classes and functions ----------------------------------------------------
# ------------------------------------------------------------------------------

def extract_search_list(filepath: str) -> List[str]:
    '''Loads the list of files separated by newlines from `filepath`.'''
    result = []
    with open(filepath, 'r') as zfile:
        for file in zfile.readlines():
            line = file.strip()
            # skip blank lines
            if len(line) == 0:
                continue
            # skip commented lines
            if line.startswith(';') == True:
                continue
            result += [file.strip()]
            pass
    return result


def search(target: str, space: List[str]):
    '''Searches for an ending-match of `target` within `space`.
    
    Returns `None` if no item was found.'''
    for item in space:
        if item.endswith(target):
            return item
    return None


def normalize(path: str) -> str:
    '''Transforms the `path` into a normalized path with forward slashes (`/`).'''
    return os.path.normpath(path).replace('\\', '/')


def report_search(target: str, match: str, loc: str):
    print('INFO: Found "'+match+'" for "'+target+'" in '+loc)


# --- Handle command-line arguments --------------------------------------------
# ------------------------------------------------------------------------------

# initialize parser
parser = argparse.ArgumentParser()
 
# adding arguments
parser.add_argument("-o", "--output", type=str, help="compressed filename", default=str(os.getenv("ORBIT_IP_NAME")))
parser.add_argument("--flat", help="remove directories from compression", action="store_true", default=False)
parser.add_argument("--force", help="create archive even if not all files were found", action="store_true", default=False)
# read arguments from command line
args = parser.parse_args()

# --- verify the planning phase was previously ran -----------------------------
# ------------------------------------------------------------------------------

# verify the build directory exists
BUILD_DIR = os.environ.get("ORBIT_BUILD_DIR")
try:
    os.chdir(BUILD_DIR)
except:
    exit("ERROR: build directory '"+str(BUILD_DIR)+"' does not exist")

# verify a blueprint exists
BLUEPRINT = os.environ.get("ORBIT_BLUEPRINT")
if os.path.exists(BLUEPRINT) == False:
    exit("ERROR: blueprint file does not exist in build directory '"+BUILD_DIR+"'")


# --- collect data from the blueprint ------------------------------------------
# ------------------------------------------------------------------------------

# store blueprint files
blueprint_files = []
search_list = None
with open(BLUEPRINT, 'r') as blueprint:
    for rule in blueprint.readlines():
        # remove newline and split into three components
        fileset, identifier, path = rule.strip().split('\t')
        # add filepath to list of blueprint files
        blueprint_files += [path]

        if fileset == 'ZIP-LIST':
            search_list = extract_search_list(path)
        pass
    pass

# check if a bench was defined or a top
ORBIT_BENCH = os.getenv("ORBIT_BENCH")
ORBIT_TOP = os.getenv("ORBIT_TOP")

# verify a submission file was found
if search_list == None:
    extra_args = ''
    if ORBIT_TOP != None:
        extra_args += ' --top '+ORBIT_TOP
    if ORBIT_BENCH != None:
        extra_args += ' --bench '+ORBIT_BENCH
    extra_args += '`'
    exit('ERROR: ZIP-LIST file (submission.txt) was not collected in the blueprint\n\nTry running `orbit plan --plugin zipr '+extra_args.strip())


# --- perform zip logic --------------------------------------------------------
# ------------------------------------------------------------------------------

# collect build directory files
all_files = glob(os.getcwd()+'/**/*', recursive=True)
build_files = []
for f in all_files:
    norm = normalize(f)
    # include only files from build directory
    if os.path.isfile(norm) == True:
        build_files += [norm]
    pass

# collect all project files
all_files = glob(os.getenv("ORBIT_IP_PATH")+'/**/*', recursive=True)
project_files = []
for f in all_files:
    norm = normalize(f)
    # skip file if it was in build directory
    if norm.startswith(os.getenv("ORBIT_BUILD_DIR")+'\\') or norm.startswith(os.getenv("ORBIT_BUILD_DIR")+'/'):
        continue

    if os.path.isfile(norm) == True:
        project_files += [norm]
    pass

# search for the target files
found_files = []
total_count = len(search_list)
if total_count == 0:
    print('WARNING: No files to find in submission.txt')
for f in search_list:
    result = search(f, blueprint_files)
    if result != None:
        report_search(f, result, 'blueprint')
        found_files += [result]
    else:
        result = search(f, project_files)
        if result != None:
            report_search(f, result, 'project')
            found_files += [result]
        else:
            result = search(f, build_files)
            if result != None:
                report_search(f, result, 'build directory')
                found_files += [result]
            else:
                print('WARNING: Could not find match for '+f)

# report to user number of successful searches
print('INFO: '+str(len(found_files))+'/'+str(total_count)+' files successfully found')

# produce an error if there was not all the files found and we aren't forced to make the zip
if len(found_files) < total_count and args.force == False:
    exit('ERROR: Missing '+str(total_count-len(found_files))+' files to archive\n\nTry including \'--force\' to proceed anyway')

# write the zip file
OUTPUT_FILE = args.output+'.zip'

with ZipFile(OUTPUT_FILE, 'w') as zip:
    for f in found_files:
        # determine archive name
        arcname: str = f
        if args.flat == True:
            arcname = os.path.basename(f)
        else:
            basepath = os.path.commonprefix((f, normalize(os.getcwd())))
            arcname = arcname.removeprefix(basepath)
            pass
        zip.write(f, arcname)
        pass
    pass

print('INFO: Zip file written to: '+str(normalize(os.getcwd()+'/'+OUTPUT_FILE)))