from distutils.core import setup
import py2exe
import shutil
import os
import sys
import glob
os.environ["PATH"] += ";C:\\gdalwin32-1.6\\bin"
sys.argv.append("py2exe")
media_files=glob.glob("./mcontent/*")
mfcdir="C:\\Python26\\Lib\\site-packages\\pythonwin"
mfc_files= [os.path.join(mfcdir, i) for i in ["mfc90.dll" ,"mfc90u.dll" ,"mfcm90.dll" ,"mfcm90u.dll" ,"Microsoft.VC90.MFC.manifest"]]
print mfc_files
#Husk pythonw.exe.manifest!!! -not needed in python2.6
excludes=["Tkconstants","Tkinter","tcl","matplotlib","pylab","javaxx"]
setup(   options = {'py2exe': {'excludes': excludes, 'includes':['encodings','osgeo','osgeo.gdal','osgeo.osr']}},
console=[{"script" : "MGL.py"}],
data_files=[("mcontent",media_files),("Microsoft.VC90.MFC", mfc_files),])
#shutil.copy("C:\\Python25\\pythonw.exe.manifest","./dist/MGL.exe.manifest") #not needed in python2.6
os.system("C:\\Programmer\NSIS\makensis.exe setup_MGL.nsi")
sys.exit()
