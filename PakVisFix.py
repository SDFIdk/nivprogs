from distutils.core import setup
import py2exe
import shutil
import os
import sys
import glob
newname="R:\\Simon\\NySoftware\\VisFix_basic.exe"
#sys.path.insert(0,"./gdal-16/pymod")
os.environ["PATH"] += ";C:\\gdalwin32-1.6\\bin"
sys.argv.append("py2exe")
datafiles=glob.glob("./mcontent/*")
#gdalfiles=glob.glob("./gdal-16/share/gdal/*")
#gdalfiles.extend(glob.glob("./gdal-16/lib/*"))
#gdalfiles=glob.glob("C:\\gdalwin32-1.6\\bin\*.dll")
#data2=["./data/MTL.ref","./data/MTL.bsk","./data/Bsk.ind","./data/dk.bmp"]
#Husk pythonw.exe.manifest!!!
#sys.path.insert(0,"ProgramFiles")
#setup(windows=['MTL2.pyw'])
mfcdir="C:\\Python26\\Lib\\site-packages\\pythonwin"
mfc_files= [os.path.join(mfcdir, i) for i in ["mfc90.dll" ,"mfc90u.dll" ,"mfcm90.dll" ,"mfcm90u.dll" ,"Microsoft.VC90.MFC.manifest"]]
crt_files=glob.glob(".\\crt\\*")
print mfc_files
extra_files=["C:\\Python26\\DLLs\\libgeos-3-0-4.dll","C:\\Python26\\DLLs\\geos.dll"]
excludes=["Tkconstants","Tkinter","tcl","matplotlib","pylab","javaxx"]
setup(   options = {'py2exe': {'excludes': excludes, 'includes':['encodings','osgeo','osgeo.gdal','osgeo.osr']}},
windows=["VisFix.py"],
data_files=[("",extra_files),("mcontent",datafiles),("Microsoft.VC90.MFC", mfc_files),("Microsoft.VC90.CRT",crt_files)])
#shutil.copy("C:\\Python26\\pythonw.exe.manifest","./dist/VisFix.exe.manifest")
os.system("C:\\Programmer\NSIS\makensis.exe setup_VisFix.nsi")
try:
	os.remove(newname)
except:
	print("Could not delete %s" %newname)
try:
	shutil.copy("./VisFix.exe",newname)
except:
	pass
sys.exit()
#data_files=[("mcontent",datafiles),("gdal-16/data",gdalfiles),("gdal-16/bin",glob.glob("./gdal-16/bin/*.dll")))])