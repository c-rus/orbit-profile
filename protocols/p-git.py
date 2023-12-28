# Project: orbit-profile 
# Protocol: p-git.py
#
# Downloads packages that use git remote repositories.
import sys, os
import subprocess
import random

DELIMITER = '###'

if len(sys.argv) < 2:
    print('error: Script requires URL as command-line argument')
    exit(101)

source = sys.argv[1]

# access the url and tag
comps = source.split(DELIMITER, 1)

REPO = comps[0]
TAG = comps[1]

print("info: Identifying download destination ...")
# determine the destination to place downloads for future installing
ORBIT_QUEUE = os.getenv("ORBIT_QUEUE")
print("info: Download directory:", ORBIT_QUEUE)

dest = ORBIT_QUEUE+'/'+str(random.randint(0, 999999))+'/'
# clone to the specific tag using git
subprocess.run(["git", "clone", "-b", TAG, REPO, dest, "--quiet"])

exit(0)
