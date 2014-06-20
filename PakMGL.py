import sys
from MGL import PROGRAM
from CommonBuild import build
build("MGL.py","setup_MGL.nsi",PROGRAM.exename)
sys.exit()

