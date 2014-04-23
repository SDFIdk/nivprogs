#GUI-less stuff here...
import FileOps
import numpy as np
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
			if not (til in include or fra in include):
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
					f_out.write("%d,%s,%s,%d,%d,%.2f,%.6f\n" %(jside,fra,til,n_forward,n_back,d,h_all))
					
				
	if n_used>0:
		summa_rho_norm=summa_rho/np.sqrt(total_dist/1e3)
		msg+="Summa rho:                                            %.3f cm\n" %(summa_rho*100.0)
		msg+="Normaliseret summa rho (mm/sqrt(d_km)):               %.2f ne\n" %(summa_rho_norm*1e3)
		msg+="Samlet afstand:                                       %.2f m\n"  %(total_dist)
		msg+="Brugte journalsidenumre:                              %d\n"  %n_used
		msg+="Max. antal maalinger af samme straek i samme retning: %d\n" %max_used
	else:
		return True,"Fandt ingen relevante/korrekte data..." 
	return True,msg