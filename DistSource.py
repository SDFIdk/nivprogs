#Make a source distribution of the "niv-prog suite"
import sys,os,time,shutil
SUITE="NivProgs"
SCRIPTS=["VisFix.py","VisFix_main.py","MGL.py","MTL.py","ImportTest.py"]
VER_INFO=os.path.join(SUITE,"version.txt")
if os.path.exists(SUITE):
	shutil.rmtree(SUITE)
os.mkdir(SUITE)
shutil.copytree("MyModules",os.path.join(SUITE,"MyModules"))
for script in SCRIPTS:
	shutil.copy(script,os.path.join(SUITE,os.path.splitext(script)[0]+".pyw"))
os.system("hg identify > %s" %(VER_INFO))
f=open(VER_INFO,"a")
f.write("\nGenerated at %s\n" %time.asctime())
f.close()
