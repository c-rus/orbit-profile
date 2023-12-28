# Project: orbit-profile
# Protocol: zipp
#
# A quick-and-dirty script to download packages from the internet for 
# integration with orbit.

import sys
import requests, zipfile, io

if len(sys.argv) < 2:
    print('error: Script requires URL as command-line argument')
    exit(101)
if len(sys.argv) < 3:
    print('error: Script requires queue as command-line argument')
    exit(101)

# get the url
URL = sys.argv[1]
# get the destination directory
ORBIT_QUEUE = sys.argv[2]

r = requests.get(URL)
if r.ok == False:
    print('error:', str(r), str(r.reason))
    exit(101)
z = zipfile.ZipFile(io.BytesIO(r.content))
z.extractall(ORBIT_QUEUE)
