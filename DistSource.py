#Make a source distribution of the "niv-prog suite"
import sys,os,time,shutil,glob
SUITE="NivProgs"
WSCRIPTS=["VisFix.py","MGL.py","MTL.py","ImportTest.py"] #gui apps
SCRIPTS=["SummaRho.py","VisFix_main.py"]  #console scripts
VER_INFO=os.path.join(SUITE,"version.txt")
if os.path.exists(SUITE):
	shutil.rmtree(SUITE)
os.makedirs(os.path.join(SUITE,"MyModules"))
module_files=glob.glob(os.path.join("MyModules","*.py"))
for name in module_files:
	shutil.copy(name,os.path.join(SUITE,"MyModules",os.path.basename(name)))
#shutil.copytree("MyModules",os.path.join(SUITE,"MyModules"))
shutil.copytree("mcontent",os.path.join(SUITE,"mcontent"))
for script in WSCRIPTS:
	shutil.copy(script,os.path.join(SUITE,os.path.splitext(os.path.basename(script))[0]+".pyw"))
for script in SCRIPTS:
	shutil.copy(script,os.path.join(SUITE,os.path.basename(script)))
os.system("hg identify > %s" %(VER_INFO))
f=open(VER_INFO,"a")
f.write("\nGenerated at %s\n" %time.asctime())
f.close()
