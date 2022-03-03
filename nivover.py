#!/usr/bin/python 
#MGL/MTL-oversaettelsesprogram, simlk juli 2014
#Til datafiler i NYT format - UDEN gammeldaws punktnumre!
#Oversaetter mgl/mtl-datafiler til kms-format.
#Kald nivover_ny.py indfil udfil
#Dataformat i indfil: Der soeges efter 'hoveder': # fra til dato tid afstand hdiff jside temp nopst

import sys
import os
PROGRAM=os.path.basename(sys.argv[0])
TMP_CORR=0.8*0.000001  #udvidelseskoefficient (reduceret til 20 grader C). Saettes her til 0.8 ppm (NEDO)
MGLP="#DK_ni_niv   1.5 ne   0.01 mm\n"
MTLP="#DK_ni_mtz   7.3 ppm   0.1 cm\n"

def Analyse(heads):
		edges=[]
		nodes=[]
		doubles=[]
		singles=[]
		for head in heads:
			edges.append([head[0],head[1]])
			nodes.extend(edges[-1])
		nodes=set(nodes)
		for e in edges:
			ec=e[:]
			ec.reverse()
			if ec in edges: 
				if ec not in doubles:
					doubles.append(e)
			else:
				singles.append(e)
		Nd=len(doubles)
		Ns=len(singles)
		msg="%*i dobbeltstraekninger (frem + tilbage).\n%*i enkeltstraekninger."%(-3,Nd,-3,Ns)
		if 2*Nd+Ns!=len(heads):
			msg+="Dette giver en fejl paa %i i forhold til antal hoveder.\n" %(len(heads)-2*Nd+Ns)
		return msg

def NytDatoFormat(dato): #oversaetter aarmddag til dag,md.aar f.eks. 091014 til 14.10.2009 Virker kun til 2099!! naa, der er jeg nok pensioneret...
	aar=dato[0:2]
	md=dato[2:4]
	dag=dato[4:]
	return "20%s%s%s" %(aar,md,dag)

def Usage():
	print("Oversaettelsesprogram til MGL (/MTL) datafiler.")
	print("INGEN oversaettelse af punktnavne - what you see is what you get!")
	print("Kald: %s indfil udfil (-tkorr)" %(PROGRAM))
	print("-tkorr slaar temperaturkorrektioner TIL - kun MGL.")
	print("Og KUN hvis du IKKE allerede har koert kalibreringsprogram!")
	sys.exit()

def main(args):
	if len(args)<3:
		Usage()
	try:
		ind=open(args[1],"r")
		ud=open(args[2],"w")
	except Exception as msg:
		print((str(msg)))
		Usage()
	tkorr="-tkorr" in args
	indfilnavn=os.path.basename(args[1])
	print("Koerer %s paa filen %s." %(PROGRAM,indfilnavn))
	hvd=[]
	nbad=0
	nbadnames=0
	firstline=ind.readline().upper()
	MGL=False
	MTL=False
	if firstline.find("MGL")!=-1:
		MGL=True
	elif firstline.find("MTL")!=-1:
		MTL=True
	if not (MTL or MGL): #saa tjek om det er output fra det gamle digniv.
		if firstline.find("FILNAVN")!=-1:
			print("Tilsyneladende er %s en MGL-datafil genereret med det gamle digniv-program." %indfilnavn)
		else: 
			print("Kunne ikke genkende header-formatet i datafilen.\nVi antager det er en MGL-datafil.")
		MGL=True  #well, saa antager vi bare at det er en MGL-fil og ser hvad der sker.
	else:
		print("Datafil genereret med: %s" %firstline.replace("PROGRAM:","").lower().strip())
	if MGL:
		if not tkorr:
			print("Bruger IKKE laegte-temperaturudvidelse for maalte hoejdeforskelle!")
			print("Koer istedet laegtekalibreringsprogram paa raadata!")
			print("(Hvis du IKKE allerede har gjort det :-) )")
		else:
			print("Temperaturudvidelseskorrektion (pyhhh) slaaet til!")
			print("ADVARSEL: GOER kun dette, hvis du IKKE allerede har koert kalibreringsprogram!!!!!") 
		ud.write(MGLP)  #skriv header preacisions-kommentar
	else:
		print("Bruger IKKE laegte-temperaturudvidelse for maalte hoejdeforskelle...")
		ud.write(MTLP)
	nopst=0 #kun noedv. ved mgl-filer i gammelt format
	line=ind.readline()
	while len(line)>0:
		sline=line.split()
		if len(sline)>=9 and sline[0]=="#":  #nyt format har 10 tegn, gammelt mgl-format kun 9
			if len(sline)==9:
				sline.append("%s" %nopst)
			hvd.append(sline[1:])
			nopst=0
		elif MGL and len(sline)>0 and sline[0].lower()=="tilbagesigte": #mulighed for fejl her, Hvis et hovede er slettet ved at fjerne #, saa vil der komme for mange opstillinger.
			nopst+=1
		elif len(sline)>=8 and line.find("#")!=-1:
			nbad+=1
			nopst=0
		line=ind.readline()
	ind.close()
	msg=Analyse(hvd)
	print("Antal hoveder: %i." %(len(hvd)))
	print(msg)
	for line in hvd:
		fra=line[0]
		til=line[1]
		dato=line[2]
		tid=line[3]
		afst=line[4]
		hdiff=line[5]
		jside=line[6]
		temp=line[7]
		nopst=line[8]
		try:
			if dato.find(".")==-1: #saa gammelt format
				dato=NytDatoFormat(dato)
			else:
				sdato=dato.split(".")
				dato=sdato[2]+sdato[1]+sdato[0] #aar md dag
			aar=dato[0:4]
			hdiff=float(hdiff)
			temp=float(temp)
			afst=round(float(afst)) 
			jside=float(jside)*10
		except Exception as msg:
			nbad+=1
			print(msg)
		else:#saa skriv til udfil...
			if MGL and tkorr: #ved MGL brug temp.-udvidelse - bruges ikke mere (koer istedet rod_calibration.py!)
				hdiff=hdiff*(1-(20-temp)*TMP_CORR)  #temperatur-udvidelse....
			ud.write("\n%12s a   %4s   1    %8.0lf" %(fra,aar,jside))
			ud.write("\n%12s   %8.5lf m   %4d m" %(til,hdiff,afst))
			ud.write("      %8s,%5s   %2s   \n" %(dato, tid, nopst))
	ud.write("\n\n-1a\n") #aflustningstegn
	ud.close()
	print("Antal ukurante eller slettede hoveder: %i." %nbad)
	print("Antal ukurante punktnavne: %i." %nbadnames)
	print("Genererede udfilen %s." %args[2])
	sys.exit()

if __name__=="__main__":
	main(sys.argv)
	
		