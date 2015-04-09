#GUI-less stuff here...
import FileOps
import numpy as np
import math
import MTLsetup

def MTLPlotData(fname):
	data=GetTransferSetupData(fname)
	dists=[]
	temps=[]
	r_errs=[]
	ind1=[]
	ind2=[]
	for setup in data:
		for sats in setup:
			#slow...
			n_opst,d,i1,i2,r_err=sats[0:5]
			t=sats[10]
			dists.append((n_opst,d))
			temps.append((n_opst,t))
			r_errs.append((n_opst,r_err))
			ind1.append((n_opst,i1))
			ind2.append((n_opst,i2))
	return dists,temps,r_errs,ind1,ind2				


def rad_to_sec(val):
	return math.degrees(val)*3600

def GetTransferSetupData(fname):
	#extract all relevant data from 'transfer setup' - similar to above
	#extract each setup and return data...
	f=open(fname)
	#start by extracting position data and temp.
	current_temp=None
	current_date=None
	current_time=None
	is_transfer_setup=False
	nopst=0
	for line in f:
		sline=line.split()
		if len(sline)>3 and sline[0]=="#":
			current_temp=float(sline[-2])
			current_date=sline[3]
			current_time=sline[4]
			break
	f.close()
	f=open(fname)
	line="X"
	all_data=[]
	while len(line)>0:  #loeb igennem filen nu
		line=f.readline()
		sline=line.split()
		if len(sline)==0:
			continue
		if "Satser" in sline and "Afstand" in sline and line.strip()[0]!=";":
			setup_data=[] #data for this setup
			nopst+=1
			is_transfer_setup=True
			#we have a setup - now read 'satser'
			line=f.readline().split()
			N=int(line[2])
			d=float(line[3].replace("m",""))
			for i in range(N):
				line1=f.readline().split()
				line2=f.readline().split()
				r_err_term=line2[-2]
				#from the r_error term we can (also) read what unit is used...
				try:
					translator,unit,fconv=MTLsetup.Unit2Translator(r_err_term)
					r_err=float(r_err_term.replace(unit,""))*fconv*180/math.pi*3600 #in seconds
					ok,z11=translator(line1[-3])
					assert(ok)
					ok,z12=translator(line1[-2])
					assert(ok)
					ok,z21=translator(line2[-4])
					assert(ok)
					ok,z22=translator(line2[-3])
					assert(ok)
					is_buggy=abs(z11+z12-2*math.pi)>math.pi*0.5#stupid bug
					if is_buggy:
						zz=z12
						z12=z21
						z21=zz
					h1=float(line1[-1].replace("m",""))
					h2=float(line2[-1].replace("m",""))
				except Exception,e:
					print("Exception: %s\nSpringer denne sats over.."%str(e))
					continue
				ind1=((z11+z12)-2*math.pi)*0.5
				ind2=((z21+z22)-2*math.pi)*0.5
				#calculate adjusted angles
				z1c=z11-ind1
				z2c=z21-ind2
				#print z1c+z2c
				r_err_raw=(z1c+z2c)-math.pi
				setup_data.append([nopst,d,rad_to_sec(ind1),rad_to_sec(ind2),r_err,rad_to_sec(r_err_raw),h1,h2,current_date,current_time,current_temp,-9999,-9999])
			if len(setup_data)>0:
				#read until the sats has endend - and dont read too far!
				n_read=0
				while len(sline)>0:
					line=f.readline()
					sline=line.split()
					if len(sline)>2 and sline[0]=="*" and sline[1]=="II":
						break
					n_read+=1
				#sats endend
				line=f.readline()
				sline=line.split()
				if len(sline)>0 and sline[0]=="GPS:": #may go wrong for basis setup
					current_x=float(sline[2])
					current_y=float(sline[1])
					for sats in setup_data:
						sats[-1]=current_y
						sats[-2]=current_x
				all_data.append(setup_data)
				if len(sline)==0:
					continue
		if sline[0]=="#":
			current_temp=float(sline[-2])
			current_date=sline[3]
			current_time=sline[4]
					
	f.close()
	return all_data			

def GetSummaRho(fil,include=None,exclude=None,f_out=None):
	nerrors=0
	msg=""
	heads=FileOps.Hoveder(fil)
	jsides={}
	if len(heads)==0:
		return False,"Ingen hoveder fundet i filen."
	for head in heads:
		jside=head[6]
		fra=head[0]
		til=head[1]
		skipthis=False
		if include is not None:
			if not (til in include or fra in include): #if til or fra in include continue
				skipthis=True
		if (not skipthis) and exclude is not None:
			if til in exclude or fra in exclude:
				skipthis=True
		if skipthis:
			continue
		dist=float(head[4])
		hdiff=float(head[5])
		err=False
		spl=jside.split(".")
		if len(spl)!=2:
			err=True
		else:
			try:
				jside=int(spl[0])
				ext=int(spl[1])
			except:
				err=True
			if err:
				nerrors+=1
				msg+=u"Ukurankt journalside: %s, str\u00E6kning: %s til %s, fil: %s\n" %(jside,fra,til,os.path.basename(file))
			else:
				if jside in jsides:
					jsides[jside].append((fra,til,ext,dist,hdiff))
				else:
					jsides[jside]=[(fra,til,ext,dist,hdiff)]
	summa_rho=0.0
	total_dist=0
	n_used=0
	max_used=0
	for jside in jsides:
		items=jsides[jside]
		if len(items)>1:
			item=items[0]
			h_forward=item[-1]
			dists=[item[-2]]
			h_back=0.0
			fra=item[0]
			til=item[1]
			org_ext=item[2]
			n_forward=1
			n_back=0
			ok=True
			for item in items[1:]:
				if item[0]==fra and item[1]==til:
					n_forward+=1
					h_forward+=item[-1]
				elif item[1]==fra and item[0]==til:
					n_back+=1
					h_back+=item[-1]
				else:
					msg+="Fejl i journalside %d.%d, punkter stemmer ikke med journalside nummer %d.%d:\n" %(jside,item[2],jside,org_ext)
					msg+="Fra: %s, til: %s, for denne jside: %s, %s\n" %(fra,til,item[0],item[1])
					ok=False
					break
				dists.append(item[-2])
			if ok:
				n_used+=1
				d1=min(dists)
				d2=max(dists)
				if (d2-d1)>50:
					msg+="Journalside: %d, stor forskel i afstande: %.2f m, max %.2f m, min: %.2f m\n" %(jside,d2-d1,d2,d1)
				max_used=max((max_used,n_forward,n_back))
				h_forward=h_forward/n_forward
				h_back=h_back/n_back
				h_all=h_forward+h_back
				d=np.mean(dists)
				summa_rho+=h_all
				total_dist+=d
				if f_out is not None:
					f_out.write("'%d';'%s';'%s';%d;%d;%s;%s\n" %(jside,fra,til,n_forward,n_back,("%.2f"%d).replace(".",","),("%.6f"%h_all).replace(".",",")))
					
				
	if n_used>0:
		summa_rho_norm=abs(summa_rho)/np.sqrt(total_dist/1e3)
		msg+="Summa rho:                                            %.3f cm\n" %(summa_rho*100.0)
		msg+="Normaliseret summa rho (mm/sqrt(d_km)):               %.2f ne\n" %(summa_rho_norm*1e3)
		msg+="Samlet afstand:                                       %.2f m\n"  %(total_dist)
		msg+="Brugte journalsidenumre:                              %d\n"  %n_used
		msg+="Max. antal maalinger af samme straek i samme retning: %d\n" %max_used
	else:
		return True,"Fandt ingen relevante/korrekte data..." 
	return True,msg