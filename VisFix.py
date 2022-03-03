#Wrapper of VisFix.py - mainly to be able to handle errors on import
#simlk, 3-11-09
import sys
import time
try:
	sys.frozen
except:
	pass
else:
	sys.stderr=open("VF.log","w")
	sys.stdout=sys.stderr
import VisFix_main
def main():
	print(("Running %s on %s." %(sys.argv[0],time.asctime())))
	VisFix_main.main()
	sys.exit()
if __name__=='__main__':
	main()
