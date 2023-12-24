# File: zip-op.py
# Author: Chase Ruskin
# Revised: 2023-05-12
# Details:
#   A quick-and-dirty script to download packages
#   from the internet for integration with Orbit.
#
import sys, os
import subprocess
import random

if len(sys.argv) < 2:
    print('error: Script requires URL as command-line argument')
    exit(101)

# get the url
URL = sys.argv[1]

print("info: Identifying download destination ...")
# determine the destination to place downloads for future installing
ORBIT_QUEUE = os.getenv("ORBIT_QUEUE")
print("info: Download directory:", ORBIT_QUEUE)
os.chdir(ORBIT_QUEUE)

dest = ORBIT_QUEUE+'/'+str(random.randint(0, 999999))+'.zip'
# download zip files using curl
subprocess.run(["curl", "-L", URL, "-o", dest])
# unzip contents
subprocess.run(["unzip", "-qo", dest])
# remove zip file
subprocess.run(["rm", dest])

exit(0)
