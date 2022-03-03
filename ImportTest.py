import sys,os,time,platform,traceback
SL="*"*70
f=open("ImportLog.txt","w")
f.write("Import test of niv suite programs at: %s\n" %time.asctime())
f.write("Python version: %s\n" %sys.version)
f.write("System is: %s, architecture: %s\n" %(sys.platform,platform.architecture()))
f.write("%s\n" %SL)
try:
	import VisFix
except Exception as e:
	f.write("Import of VisFix failed with exception:\n")
	f.write("%s\n" %repr(e))
	f.write("%s\n"%traceback.format_exc())
else:
	f.write("Import of VisFix succeeded!\n")

f.write("%s\n" %SL)
try:
	import MGL
except Exception as e:
	f.write("Import of MGL failed with exception:\n")
	f.write("%s\n" %repr(e))
	f.write("%s\n"%traceback.format_exc())
else:
	f.write("Import of MGL succeeded!\n")

f.write("%s\n" %SL)
try:
	import MTL
except Exception as e:
	f.write("Import of MTL failed with exception:\n")
	f.write("%s\n" %repr(e))
	f.write("%s\n"%traceback.format_exc())
else:
	f.write("Import of MTL succeeded!\n")
f.close()