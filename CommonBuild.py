from distutils.core import setup
import py2exe
import shutil
import os
import sys
import glob
NSIS="C:\\Programmer\NSIS\makensis.exe"
sys.argv.append("py2exe")
media_files=glob.glob("./mcontent/*")
mfcdir="C:\\Python27\\Lib\\site-packages\\pythonwin"
mfc_files= [os.path.join(mfcdir, i) for i in ["mfc90.dll" ,"mfc90u.dll" ,"mfcm90.dll" ,"mfcm90u.dll" ,"Microsoft.VC90.MFC.manifest"]]
crt_files=glob.glob(".\\crt\\*")
extra_files=["C:\\Python27\\DLLs\\geos_c.dll","C:\\Python27\\DLLs\\geos.dll"]
extra_files.extend(glob.glob("Microsoft.VC100.CRT/*.dll"))
excludes=["Tkconstants","Tkinter","tcl","matplotlib","pylab","javaxx"]
print mfc_files
def build(script,nsi_script=None,exe_name=None):
	try:
		shutil.rmtree("dist")
	except Exception,msg:
		print msg
	setup(   options = {'py2exe': {'excludes': excludes, 'includes':['encodings','osgeo','osgeo.gdal','osgeo.osr']}},
	windows=[{"script" : script}],
	data_files=[("",extra_files),("mcontent",media_files),("Microsoft.VC90.MFC", mfc_files),("Microsoft.VC90.CRT",crt_files),])
	if nsi_script is not None:
		os.system(NSIS+" "+nsi_script)
		nsi_name=os.path.splitext(script)[0]+".exe"
		if exe_name is not None:
			try:
				os.remove(exe_name)
			except:
				pass
		os.rename(nsi_name,exe_name)
	