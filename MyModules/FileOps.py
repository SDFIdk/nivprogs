import os,sys
try:
	import win32ui
	import win32con
except:
	HAS_WIN32=False
else:
	HAS_WIN32=True
import time
from . import Funktioner
import shutil

ATTACH_MSG=";Tilslutter til fil..."
DEBUG="debug" in sys.argv
#En faelles funktion til laesning af MTL/MGL resultatfiler....
#Returnerer ErDetEnResFil, ErDenOK, msg			
def ReadResultFile(resfile,statusdata,instruments,program="MGL"): #TODO: check at vi kan tilslutte til baade en ny og en gammel MTL-fil....
	projekt="Ikke fundet."
	msg=""
	f=open(resfile,"r")
	line=f.readline()
	today1=Funktioner.Dato()
	today2=Funktioner.Dato2()
	has_started=False
	header_ended=False
	header_pos=0 #position efter header
	head_pos=0  #position efter sidste hoved
	last_pos=0  #position efter sidste ikke tomme linie
	nheads=0
	if not(line.upper().find("PROGRAM")!=-1 and line.find(program)!=-1):
		f.close()
		return False,False,"Tilsyneladende ikke en %s-resultatfil." %program
	lines=[line]+f.readlines()
	f.close()
	#Tjek MTL header here#
	if program=="MTL":
		instrument_names=[inst.GetName() for inst in instruments]
		if not TjekMTLHeader(lines,instruments):
			msg+="Instrumenter defineret i resultatfilen er IKKE kompatible med instrumenter i ini-filen!\n"
	#loop igennem linier for at laese header og hoveder#
	for linenumber in range(1,len(lines)):
		line=lines[linenumber]
		sline=line.split()
		if len(sline)>0:
			if not (ATTACH_MSG in line):
				last_pos=linenumber+1
				last_line=line
			if sline[0]=="#": 
				temp=float(sline[8]) 
				t,m=sline[4].split(".")
				tid=int(t)+int(m)/60.0
				dato=sline[3]
				D=float(sline[5])
				try: #gamle MGL-filer har ikke logget antal opst....
					Nopst=int(sline[9])
				except:
					Nopst=0
				Slut=sline[2]   #Seneste punkt
				if dato==today1 or dato==today2:
					if not has_started:
						statusdata.SetDate(today1)
						statusdata.SetStartTime(tid)
						has_started=True
					else:
						statusdata.AddTemperature(temp,tid)
				statusdata.AddStretch(Slut,D,Nopst)
				head_pos=linenumber+1
				nheads+=1
			elif sline[0]=="*" and not header_ended:
					header_ended=True  #marker at headeren er slut
					header_pos=linenumber+1
			if "projektbeskrivelse" in line.lower():
				projekt=line.split(":")[1].strip()
	statusdata.SetProject(projekt)
	has_extra_lines=False
	if nheads>0 and last_pos>head_pos:
		msg+="Der er linier efter sidste hoved.\nM\u00E5ske blev programmet lukket ved en fejl."
		msg+="\nSidste linie: %s" %last_line
		start_pos=head_pos
		has_extra_lines=True
	elif nheads==0 and last_pos>header_pos:
		msg+="Filen indeholder ingen hoveder, men linier efter headeren.\nM\u00E5ske blev programmet lukket ved en fejl."
		msg+="\nSidste linie: %s" %last_line
		start_pos=header_pos
		has_extra_lines=True
	elif nheads==0:
		msg+="Filen indeholder ingen m\u00E5linger."
		return True, False, msg
	else:
		msg="Filen er tilsyneladende OK."
	#Hvis der er linier efter sidste hoved: forsoeg at laese maalinger og saette status#
	if has_extra_lines:
		mtl_have_warned=False
		for i in range(start_pos,len(lines)):
			line=lines[i]
			sline=line.split()
			if len(sline)>1 and sline[0]=="*":
				code=sline[1]
				if program=="MGL" and code in ["B1","N","B2"]:
					dist=float(sline[2])
					ddist=float(sline[3])
					hdiff=float(sline[4])
					if code=="B1":
						Start=sline[-1]
					elif code=="B2":
						Slut=sline[-1]
					statusdata.AddSetup(hdiff,dist,ddist)
				elif program=="MTL" and code in ["II","B1","B2"]:
					dist=float(sline[-2])
					hdiff=float(sline[-1])
					if code=="B1":
						Start=sline[2]
						check_line=i-4
					elif code=="II":
						check_line=i
					elif code=="B2":
						check_line=i-4
						Slut=None   #In prev. versions EndPoint was not stored here... It's not really a big deal...
					if DEBUG:
						print(instrument_names,len(lines),check_line,code)
					if instrument_names[0] in lines[check_line]:
						statusdata.SetInstrumentState(0) #foerste inst. baerer hoejden
					else:
						statusdata.SetInstrumentState(1) #andet inst baerer hoejden
						if (not (instrument_names[1] in lines[i-4])) and (not mtl_have_warned):
							msg+="\nKan ikke finde aktuelle instrumentnavne i resultatfilen.\n"
							msg+="H\u00F8jdeb\u00E6rende instrument m\u00E5ske ikke sat OK."
							mtl_have_warned=True
					statusdata.AddSetup(hdiff,dist)
				if code=="B1":
					statusdata.SetStart(Start)
				elif code=="B2": #Dette betyder at sidste hoved ikke naaede at blive skrevet da programmet crashede....
					msg+="\nProgrammet er tilsyneladende afsluttet f\u00F8r sidste hoved blev skrevet.\n"
					msg+="Ingen data er dog g\u00E5et tabt! Skriv det manglende hoved ind i resultatfilen."
					statusdata.SetEnd(Slut)
					f=open(resfile,"a")
					f.write("; manglende hoved skrives ind her...\n")
					f.close()
					statusdata.StartNewStretch()
		if statusdata.GetStretches()+statusdata.GetSetups()==0:
			msg+="\nFilen indeholder ingen m\\u00E5linger."
			return True,False,msg
	if not (ATTACH_MSG in lines[-1]):
		f=open(resfile,"a")
		f.write("\n%s\n" %ATTACH_MSG)
		f.close()
	return True,(not has_extra_lines),msg
			


# This is only essential in case someone tries to attach to a resfile with instruments defined in a different way than the current instruments!
def TjekMTLHeader(lines,instruments):
	nfound=0
	for line in lines:
		if "Instrument:" in line:
			i=line.find("konstanter:")
			if i==-1:
				return False
			else:
				sline=line[i:].split()
				try:
					addconst=float(sline[1])
					axisconst=float(sline[3])
				except:
					if DEBUG:
						print(sline)
					return False
				else:
					if instruments[nfound].addconst==addconst and instruments[nfound].axisconst==axisconst:
						nfound+=1
		if "* Slut paa header" in line:
			break
		if nfound==2:
			break
	return (nfound==2)

def GetInstrumentNames(fname,program="MTL"):
	f=open(fname,"r")
	program=program.lower()
	names=[]
	line=f.readline()
	fprogram=False
	nread=1
	while len(line)>0:
		if not fprogram and program in line.lower():
			fprogram=True
		if not fprogram:
			if nread>500:
				break
			else:
				line=f.readline()
				nread+=1
				continue
		if "Instrumenter:" in line:
			line=f.readline()
			names.append(line.split(":")[0].strip())
			line=f.readline()
			names.append(line.split(":")[0].strip())
		elif "Instrument:" in line:
			names.append(line.split()[1].split(",")[0].strip())
		if len(names)>1 or (len(names)==1 and program=="mgl"):
			break
		line=f.readline()
	
	f.close()
	return names

def TjekHeader(fname,program_name): #majet, majet simpel funktion, som bare ser efter programnavn i foerste linie af en fil....
	try:
		f=open(fname,"r")
	except:
		return False
	line=f.readline()
	f.close()
	if program_name.lower() in line.lower():
		return True
	return False
#We waste memory here - gives less code and a res-file is usually a lot smaller than 1MB	
def DeleteToLastHead(resfilnavn):
	copy=os.path.splitext(resfilnavn)[0]+"_backup.res"
	if os.path.exists(copy):
		os.remove(copy)
	shutil.copy(resfilnavn,copy)
	f=open(resfilnavn,"r") #virker vist her med 'r'-mode selvom f.seek() bruges...
	lines=f.readlines()
	f.close()
	for i in range(1,len(lines)+1):
		sline=lines[len(lines)-i].split()
		if len(sline)>0 and sline[0]=="#":
			break
	keep=len(lines)-i+1
	f=open(resfilnavn,"w")
	for i in range(len(lines)):
		line=lines[i]
		if i<keep or line.isspace():
			f.write(line)
		else:
			f.write(";"+line)
	f.close()

def DeleteLastAction(resfilnavn):
	copy=os.path.splitext(resfilnavn)[0]+"_backup.res"
	if os.path.exists(copy):
		os.remove(copy)
	shutil.copy(resfilnavn,copy)
	f=open(resfilnavn,"r") #virker vist her med 'r'-mode selvom f.seek() bruges...
	lines=f.readlines()
	f.close()
	nactions=0
	i=1
	while i<len(lines) and nactions<2:
		sline=lines[len(lines)-i].split()
		if len(sline)>0 and sline[0]=="*":
			nactions+=1
		i+=1
	keep=len(lines)-i+2
	f=open(resfilnavn,"w")
	for j in range(len(lines)):
		line=lines[j]
		if j<keep or line.isspace():
			f.write(line)
		else:
			f.write(";"+line)
	f.close()
			
def EditHead(resfilnavn,head_nr,newhead):
	copy=os.path.splitext(resfilnavn)[0]+"_backup.res"
	if os.path.exists(copy):
		os.remove(copy)
	shutil.copy(resfilnavn,copy)
	f=open(resfilnavn,"r") #virker vist her med 'r'-mode selvom f.seek() bruges...
	lines=f.readlines()
	f.close()
	newline=FormatHead(newhead)
	found=0
	linenr=None
	for i in range(len(lines)):
		line=lines[i]
		sline=line.split()
		if len(sline)>0 and sline[0]=="#":
			if found==head_nr:
				linenr=i
				break
			found+=1
	if linenr is not None:
		keep=lines[linenr]
		lines[linenr]=newline
		lines=lines[:linenr]+[";"+keep]+lines[linenr:]
		f=open(resfilnavn,"w")
		for line in lines:
			f.write(line)
		f.close()
	elif DEBUG:
		print("edit_head",found,linenr,newline)
			

def FormatHead(data):
	return "# %s %s %s %s %.2f %.6f %s %.1f %d\n\n" %tuple(data)
	
def Hoveder(fullfile):
	f=open(fullfile,"r")
	heads=[]
	for line in f:
		sline=line.split()
		if len(sline)>3 and sline[0]=="#":
			heads.append(sline[1:])
	return heads
	
def LaesSidsteHoved(fullfile):
	f=open(fullfile,"r")
	tegn="X"
	off=0
	while tegn!="#":
		off-=1
		f.seek(off,os.SEEK_END)
		tegn=f.read(1)
	line=f.readline()
	f.close()
	#print line,"hoved"
	return line

	
		

	
	

def Jside(resfile,mode=1,JS="XXX",program="MTL"): #mode 1: normal, mode 2: soegemode, mode3: test
	if (not HAS_WIN32):
		raise Warning("Udprint kraever win32-moduler, som ikke er loadet korrekt")
		return False
	f=open(resfile,"rb") #'rb' fordi f.tell() i SaetEfterHoved ellers screwer up!
	f.readline() #foerste linie er program version
	#filnavn=f.readline().split()[1] #anden linie indeholder filnavn
	filnavn=resfile
	pos, nl=SaetEfterHoved(f,mode,JS) #egentlig er nl overfloedig her nu....
	if mode==2 and nl==0:
		return False #betyder at JS ikke blev fundet (udskriv enkeltsidemode=2)
	f.seek(pos)
	line="X"
	tegn="X"
	gem=["Fejl","Fejl","Fejl","Fejl","Fejl","Fejl","Fejl","Fejl","Fejl","Fejl"]
	Plines=[]
	while len(line)>0 and tegn!="#":
		line=f.readline()
		#print line
		if (not line.isspace()) and len(line)>1:
			#print line
			tegn=line.split()[0]
			if tegn=="#":
				gem=line.split()
				#print gem
		if len(line.strip())>2 and line.find("Tilslutter til fil")==-1: #saa er det ikke space... 
			pline=line.strip()
			if pline.find("*")==-1 and pline[0]!=";": #vi udskriver saa ikke slettede ting
				pline=pline.replace(";","")
				pline=pline.replace("\n","")
				pline=pline.replace("oe","\u00F8")
				pline=pline.replace("ae","\u00E6")
				pline=pline.replace("aa","\u00E5")
				pline=pline.encode('L6')
				Plines.append(pline)
	if mode!=3: #testmode er 3
		nl=len(Plines)
		fs=10  #Fontsize
		ls=14  #"linesize"
		pb=48  #pagebrak ca 57 liner her...
		if nl>48 and nl<71:  #Saa proever vi at presse det ind paa een side!!! 
			fs=8
			ls=10        #giver 81 linier
			pb=72
		scale_factor = 20 # dvs. 20 twips til punkt ???
		dc = win32ui.CreateDC()
		dc.CreatePrinterDC()
		dc.SetMapMode(win32con.MM_TWIPS) # 1440 pr. tomme
		dc.StartDoc("ml-journalside")
		font = win32ui.CreateFont({"name": "Courier New","height": int(scale_factor * fs),"weight": 400,})
		dc.SelectObject(font)  #nb. med disse indstillinger ca. 57 linier pr. a4-side!
		i=1
		for pline in Plines:
			dc.TextOut(scale_factor * 40,-i * scale_factor * ls,pline)
			i+=1
			if i==pb:
				dc.EndPage()
				i=1
	else:
		for pline in Plines:
			print(pline)
	
	f.close()
	if mode==3: #testmode
		return True 
	i=pb #Skulle saette hovedet forneden!
	dc.TextOut(scale_factor * 40,-i * scale_factor * ls,"Startpunkt: "+gem[1])
	i+=1
	dc.TextOut(scale_factor * 40,-i * scale_factor * ls,"Slutpunkt : "+gem[2])
	i+=1
	dc.TextOut(scale_factor * 40,-i * scale_factor * ls,"Dato og tid: "+gem[3]+" "+gem[4])
	i+=1
	dc.TextOut(scale_factor * 40,-i * scale_factor * ls,"Temperatur: "+gem[8])
	i+=1
	dc.TextOut(scale_factor * 40,-i * scale_factor * ls,"Afstand: %s m"%gem[5])
	i+=1
	if len(gem)==10:
		dc.TextOut(scale_factor * 40,-i * scale_factor * ls,"Opstillinger: "+gem[-1])
		i+=1
	dc.TextOut(scale_factor * 40,-i * scale_factor * ls,("H\u00F8jdeforskel: %.5f m" %(float(gem[6]))).encode('L6'))
	i+=1
	dc.TextOut(scale_factor * 40,-i * scale_factor * ls,"Datafil: "+filnavn)
	i+=1
	dc.TextOut(scale_factor * 40,-i * scale_factor * ls,"Journalside: "+gem[7])
	dc.EndDoc()
	return True
				
	
def SaetEfterHoved(filepointer,mode=1,JS="XXX"):
	f=filepointer
	pos=f.tell()
	lastpos=pos
	nh=0 #antal hoveder fundet/scannet
	ns=0 #antal *-koder fundet/scannet
	nl=0
	gnl1=0
	gnl2=0
	line="X"
	found=False
	while len(line)>0:
		line=f.readline()
		nl+=1
		if len(line)>2 and not line.isspace():
			line=line.split()
			if line[0]=="#" or line[0]=="*":
				#print line,lastpos,pos
				if nh==0 and ns==0:
					lastpos=f.tell()
					gnl1=gnl2
				elif line[0]=="#" and nh>0:
					lastpos=pos
					gnl1=gnl2
				if line[0]=="#": 
					pos=f.tell() #gem nuvaerende position
					gem=line
					nh+=1
					gnl2=nl
					if mode!=1 and JS in line: #hop ud naar JS findes
						found=True
						break
						
				else:
					ns+=1
					nl-=1
	if mode==1 or found:
		return lastpos,gnl2-gnl1
	else:
		if mode==3: #testmode
			print(lastpos, gnl2-gnl1)
		return lastpos,0
		

def FindFrem(fil,P1,P2):
	OK=False
	foundfrem=False
	alreadythere=False
	hfrem=0
	Nfound=0
	try:
		f=open(fil,"r")
	except:
		return OK,foundfrem,alreadythere,hfrem,Nfound
	OK=True
	lines=f.readlines()   #daarligt ved stor fil
	for line in lines:
		line=line.split()
		if len(line)>2:
			St=line[0]
			Sl=line[1]
			if St==P2 and Sl==P1:
				foundfrem=True
				Nfound+=1
				hfrem+=float(line[2]) #lav gennemsnit
			if St==P1 and Sl==P2:
				alreadythere=True
	f.close()
	if foundfrem:
		hfrem=hfrem/float(Nfound)
	return OK,foundfrem,alreadythere,hfrem,Nfound
				
	
def FilStatus(fil): #an slags analyse...
		heads=Hoveder(fil)
		edges=[]
		nodes=[]
		doubles=[]
		singles=[]
		#if len(heads)==0:
		#return
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
		msg="%*i dobbeltm\u00E5linger (frem + tilbage)\n%*i enkeltm\u00E5linger.\n"%(-3,Nd,-3,Ns)
		if 2*Nd+Ns!=len(heads):
			msg+="Dette giver en fejl p\u00E5 %i i forhold til antal hoveder.\n" %(len(heads)-2*Nd+Ns)
		return msg

