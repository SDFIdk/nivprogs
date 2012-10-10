from distutils.core import setup
import py2exe
import shutil
import os
import sys
import glob
from MGL import PROGRAM
nsi_name="MGL.exe"
#os.environ["PATH"] += ";C:\\gdalwin32-1.6\\bin"
sys.argv.append("py2exe")
media_files=glob.glob("./mcontent/*")
mfcdir="C:\\Python27\\Lib\\site-packages\\pythonwin"
mfc_files= [os.path.join(mfcdir, i) for i in ["mfc90.dll" ,"mfc90u.dll" ,"mfcm90.dll" ,"mfcm90u.dll" ,"Microsoft.VC90.MFC.manifest"]]
crt_files=glob.glob(".\\crt\\*")
extra_files=["C:\\Python27\\DLLs\\geos_c.dll","C:\\Python27\\DLLs\\geos.dll"]
extra_files.extend(glob.glob("Microsoft.VC100.CRT/*.dll"))
print mfc_files
#Husk pythonw.exe.manifest!!! -not needed in python2.6
excludes=["Tkconstants","Tkinter","tcl","matplotlib","pylab","javaxx"]
setup(   options = {'py2exe': {'excludes': excludes, 'includes':['encodings','osgeo','osgeo.gdal','osgeo.osr']}},
console=[{"script" : "MGL.py"}],
data_files=[("",extra_files),("mcontent",media_files),("Microsoft.VC90.MFC", mfc_files),("Microsoft.VC90.CRT",crt_files),])
#shutil.copy("C:\\Python25\\pythonw.exe.manifest","./dist/MGL.exe.manifest") #not needed in python2.6
os.system("C:\\Programmer\NSIS\makensis.exe setup_MGL.nsi")
ver_name=PROGRAM.exename
os.rename(nsi_name,ver_name)
sys.exit()
