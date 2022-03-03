###########
## Simply exctract transfer setup data from file and write to Excel-friendly format...
##############
import os,sys
from MyModules import Analysis

def usage():
	print(("Kald: %s <res_filnavn> <udfil_excel> <udfil_gis>" %os.path.basename(sys.argv[0])))
	sys.exit()
	
def float2excel(val,prc): #stupid...
	fmt="{0:."+str(int(prc))+"f}"
	return fmt.format(val).replace(".",",")

def main(args):
	if len(args)<4:
		usage()
	print(("Reading %s, writing %s ('Excellish') and %s (standard csv for GIS)." %(args[1],args[2],args[3])))
	data=Analysis.GetTransferSetupData(args[1])
	print(("Opstillinger fundet: %d" %len(data)))
	f_excel=open(args[2],"w")
	f_gis=open(args[3],"w")
	f_excel.write("nopst;dist;ind1;ind2;rerr;rerr_raw;h1;h2;date;time;temp\n")
	f_gis.write("nopst,dist,ind1,ind2,rerr,rerr_raw,h1,h2,date,time,temp,X,Y\n")
	fmt_gis="{0:d};{1:.2f};{2:.2f};{3:.2f};{4:.2f};{5:.2f};{6:.4f};{7:.4f};{8:s};{9:s};{10:.1f};{11:.1f};{12:.1f}"
	fmt_excel="{0:d};{1:s};{2:s};{3:s};{4:s};{5:s};{6:s};{7:s};{8:s};{9:s};{10:s}"
	for setup in data:
		for sats in setup:
			f_gis.write(fmt_gis.format(*sats)+"\n")
			for i in range(1,6):
				sats[i]=float2excel(sats[i],2)
			sats[6]=float2excel(sats[6],4)
			sats[7]=float2excel(sats[7],4)
			sats[10]=float2excel(sats[10],1)
			f_excel.write(fmt_excel.format(*sats[:-2])+"\n")
			
	f_excel.close()
	f_gis.close()

if __name__=="__main__":
	main(sys.argv)
