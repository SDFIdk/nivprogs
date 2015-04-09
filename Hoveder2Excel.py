###########
## Simply exctract 'heads' and write to a ; separeted file...
##############
import os,sys
from MyModules import FileOps

def usage():
	print("Kald: %s <res_filnavn> <udfil>" %os.path.basename(sys.argv[0]))
	sys.exit()



def main(args):
	if len(args)<3:
		usage()
	print("Reading %s, writing %s." %(args[1],args[2]))
	heads=FileOps.Hoveder(args[1])
	f=open(args[2],"w")
	f.write("fra;til;dato;tid;dist;hdiff;jside;temp;nopst\n")
	fmt="'{0:s}';'{1:s}';{2:s};{3:s};{4:s};{5:s};{6:s};{7:s};{8:s}"
	for head in heads:
		print head
		head[4]=head[4].replace(".",",")
		head[5]=head[5].replace(".",",")
		head[7]=head[7].replace(".",",")
		f.write(fmt.format(*head)+"\n")
	f.close()

if __name__=="__main__":
	main(sys.argv)
