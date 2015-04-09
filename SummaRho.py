import os,sys
from MyModules.Analysis import GetSummaRho

def usage():
	print("Call: %s <datafile> <outputfile> [<inc_points_file>] [<exclude_points_file>]" %os.path.basename(sys.argv[0]))
	print("If include file is not present, all points will be used")
	print("Last argument (exclude file) is optional")
	print("Include and exclude files should contain one point per line:")
	print("12123232\n121214334\n.....")
	print("Lines can be commented out with a #")
	sys.exit()
	

def read_pts(f):
	pts=[]
	for line in f:
		line=line.strip()
		if len(line)>0 and line[0]!="#":
			pts.append(line)
	return pts

def main(args):
	if len(args)<3:
		usage()
	resfile=args[1]
	outfile=args[2]
	if len(args)>3:
		inc_pts_file=args[3]
	else:
		inc_pts_file=None
	if len(args)>4:
		exc_pts_file=args[4]
	else:
		exc_pts_file=None
	for name in [resfile,inc_pts_file,exc_pts_file]:
		if(name is not None) and (not os.path.exists(name)):
			print("%s does not exist" %name)
			usage()
	if inc_pts_file is not None:
		f=open(inc_pts_file)
		inc_pts=read_pts(f)
		f.close()
		if len(inc_pts)==0:
			print("No points specified in include file.")
			usage()
		print("Including %d points" %len(inc_pts))
	else:
		inc_pts=None
	if exc_pts_file is not None:
		f=open(exc_pts_file)
		exc_pts=read_pts(f)
		f.close()
		if len(exc_pts)==0:
			print("No points specified in include file.")
			usage()
		print("Excluding %d points" %len(exc_pts))
	else:
		exc_pts=None
	print("Reading %s, writing %s...\n" %(resfile,outfile))
	f_out=open(outfile,"w")
	f_out.write("jside;p1;p2;n_frem;n_tilbage;dist;rho\n")
	ok,msg=GetSummaRho(resfile,inc_pts,exc_pts,f_out)
	if not ok:
		print("Something wrong::")
	print(msg)
	f_out.close()


if __name__=="__main__":
	main(sys.argv)
		
	
	

