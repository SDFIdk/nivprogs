import os
import win32ui
import win32con
import time
def TjekMTLFil(filename,directory,Inst1,Inst2):
	fullfilename=os.path.join(directory,filename)
	D=0
	N=0
	Nopst=0
	d=0
	nopst=0
	hdiff=0
	f=open(fullfilename,"rb")
	Nline=0
	OK=True
	Slut=None
	Start=None
	#Hlines=[]
	POS=f.tell()
	line="X"
	lastpos=POS
	analysis=False  #only analysis mode
	test=TjekHeader(fullfilename,Inst1,Inst2) #nej tjek header skal ikke vaere her, sandt nok - hvis ikke ini-fil
	if not test:
		analysis=True
	while len(line)>0:
		line=f.readline()
		pos=f.tell()
		if not line.isspace() and len(line)>1:
			lastpos=pos  #sidste ikke tomme line
			line=line.split()
			tegn=line[0]
			if tegn=="#":
				POS=pos #Gem position lige efter hoved
				#Hlines.append[Nline]
				D+=float(line[5])
				Nopst+=int(line[-1])
				N+=1
				Slut=line[2]   #Seneste punkt
	if lastpos!=POS: #hvis der er ikke tomme liner efter sidste hovede, saa skal vi goere noget specielt senere...
		dofile=True
	else:
		dofile=False
	f.seek(POS)  #Saet efter sidste hoved eller i starten, hvis ingen hoveder....
	line="X"
	lastpos=POS
	while len(line)>0:
		line=f.readline()
		pos=f.tell()
		if not line.isspace() and len(line)>0:
			lastpos=f.tell() #gem sidste ikke tomme position
			saveline=line
			line=line.split()
			tegn=line[0]
			if tegn=="*" and line[1]!="B2":  #Hvis B2, saa er sidste hoved ikke skrevet, derfor fejl.
				POS=pos #Gem position lige efter maaling
				#print line
				if line[1] in ["II","B1"]:  #Saa taelles headerslut ikke med!
					d+=float(line[-2])
					hdiff+=float(line[-1])
					nopst+=1
					if line[1]=="B1":
						Start=line[2]
					if saveline.find(Inst1.navn)!=-1: #Hvem baerer hoejden?
						Inst1.hstate=1
						Inst2.hstate=0
					else:
						Inst1.hstate=0
						Inst2.hstate=1
		
	
	f.close()  #Luk fil nu.
	msg=u"Filen er tilsyneladende afsluttet korrekt med et hoved."
	
	if (nopst>0 or lastpos!=POS) and not analysis: #ikke i analyse-mode
		OK=-1   #saerlig situation, kraever et aktivt valg!
		msg=u"Filen blev ikke afsluttet med et hoved!\nM\u00E5ske blev programmet lukket ved en fejl ved seneste k\u00F8rsel.\n"
		if lastpos!=POS and nopst==0:
			msg+=u"Filen indeholder linier, men ingen aflsuttede m\u00E5linger, efter seneste hoved.\n"
			if Slut!=None:
				msg+="Seneste basis: "+Slut+"\n"
		else:
			OK=-2
		#print pos,POS,OK	
		if dofile and OK: #hvis der har vaeret fejlnedlukning til slut
			copy=os.path.join(directory,"kopi.res")
			g=open(copy,"w")
			f=open(fullfilename,"r")
			save=""
			savelast=""
			while f.tell()!=POS:
				line=f.readline()
				g.write(line)
				if len(line)>0 and not line.isspace():
					if line.split()[0]=="*":
							savelast=save
							save=""
					else:
						save+=line
			while len(line)>0:
				line=f.readline()#gem ikke tomme linier, eller tomme kommentarer!
				if len(line.strip())>0:
					if line.strip()[0]!=";":
						g.write("; "+line) #der gemmes en udkommenteret linie!
					elif line.find("Tilslutter til fil")==-1:
						g.write(line)
			g.write("\n;Tilslutter til fil...\n")
			g.close()
			f.close()
			if OK==-2:
				msg=savelast
			
	if Nopst+nopst==0:
		msg=u"Filen indeholder ingen korrekte m\u00E5linger!"
		OK=0
	elif analysis:
		OK=-3 #analysis signal til MTL-prog
		msg=u"Header i fil passer ikke med data i ini-fil. Der kan ikke gemmes nye m\u00E5linger i filen!\n" 
	
	return OK, msg, hdiff, d, nopst, D, Nopst, N, Start, Slut


def TilslutTilMGLFil(resfile,statusdata): #returnerer ErDetEnMGLfil,ErDerFejliFilen,besked - aendrer input status-klasse
	OK=TjekHeader(resfile,"MGL")
	if not OK:
		return False,False,"Tilsyneladende ikke en MGL-datafil."
	nheads=0
	projekt="Ikke fundet."
	f=open(resfile,"r")
	line=f.readline()
	while len(line)>0: #find slut paa header
		line=f.readline()
		if line.lower().find("dato")!=-1:
			sline=line.split()
			statusdata.SetDate(sline[-2])
			t,m=sline[-1].split(".")
			tid=int(t)+int(m)/60.0
			statusdata.SetStartTime(tid)
		if line.lower().find("projektbeskrivelse")!=-1:
			projekt=line.split(":")[1].strip()
		sline=line.split()
		if len(sline)>0 and sline[0]=="*": #slut paa header her!
			break
	statusdata.SetProject(projekt)
	line=f.readline()
	while len(line)>0:
		sline=line.split()
		if len(sline)>0 and sline[0]=="#": 
			nheads+=1
			temp=float(sline[8]) 
			t,m=sline[4].split(".")
			tid=int(t)+int(m)/60.0
			dato=sline[3]
			if dato!=statusdata.GetDate():
				statusdata.SetDate(dato)
				statusdata.SetStartTime(tid)
			statusdata.AddTemperature(temp,tid)
		elif len(sline)>0 and sline[0]=="*": #kodelinie
			code=sline[1]
			dist=float(sline[2])
			ddist=float(sline[3])
			hdiff=float(sline[4])
			statusdata.AddSetup(hdiff,dist,ddist)
			if code=="B1":
				statusdata.SetStart(sline[-1])
			elif code=="B2":
				statusdata.SetEnd(sline[-1])
				statusdata.StartNewStretch()
		line=f.readline()
	f.close()
	nerrors=0
	msg=""
	if nheads!=statusdata.GetStretches():
		nerrors+=1
		msg+="Antallet af hoveder i filen stemmer ikke med data.\n"
	if statusdata.GetStretchData()[2]>0:
		nerrors+=1
		msg+=u"Filen indeholder tilsyneladende en uafsluttet str\u00E6kning."
	if nerrors==0:
		return True, True,"Filen er tilsyneladende OK."
	else:
		return True, False, msg
				
				
def TjekHeader(resfile,program="MGL"):
	f=open(resfile,"r")
	line=f.readline().upper()
	if line.find("PROGRAM")!=-1 and line.find(program)!=-1:
		OK=True
	else:
		OK=False
	f.close()
	#print "header", OK
	return OK
def TjekMTLHeader(fullfilename,Inst1,Inst2):
	f=open(fullfilename,"r")
	line=f.readline()
	while len(line)>0 and line.find("Instrumenter")==-1:
		line=f.readline()
	if len(line)<2:
		f.close()
		return False
	try:
		line1=f.readline()  #Instrumentlinier
		line1s=line1.split()
		line2=f.readline()
		line2s=line2.split()
	except:
		f.close()
		return False
	if len(line1s)<5 or len(line2s)<5:
		f.close()
		return False
	if line1.find(Inst1.navn)==-1: 
		f.close()
		return False
	if line2.find(Inst2.navn)==-1:
		f.close()
		return False
	f.close()
	return True
def SletTilSenesteHoved(filnavn,directory):
	resfilnavn=os.path.join(directory,filnavn)
	copy=os.path.join(directory,"copy.res")
	f=open(resfilnavn,"r") #virker vist her med 'r'-mode selvom f.seek() bruges...
	tegn="X"
	pos=f.tell()
	line="X"
	Nh=0
	while len(line)>0:
		line=f.readline()
		if (not line.isspace()) and len(line)>0:
			tegn=line.split()[0]
			if tegn=="#":
				pos=f.tell()
				Nh+=1
	f.close()
	if Nh>0: #hvis vi fandt ikke slettede hoveder, det burde status-tjek inden kald dog altid soerge for
		g=open(copy,"w")
		f=open(resfilnavn)
		while f.tell()!=pos:
			line=f.readline()
			g.write(line)
		for line in f: #skriv nu resten af linierne med ; foran!
			docomment=True
			if line.isspace():
				docomment=False
			elif line.strip()[0]==";":
				docomment=False
			if docomment:
				g.write(";"+line)
			else:
				g.write(line)
	
		g.close()
		f.close()
		os.remove(resfilnavn)
		os.rename(copy,resfilnavn)
	
def Hoveder(fullfile):
	f=open(fullfile,"r")
	heads=[]
	for line in f:
		if len(line.strip())>2:
			#line=line.split()
			if line.strip()[0]=="#":
				line=line.strip()[1:].split()
				heads.append(line)
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

	
		
def SletSenesteHandling(filnavn,directory,Inst1,Inst2):
	resfilnavn=os.path.join(directory,filnavn)
	copy=os.path.join(directory,"kopi.res")
	f=open(resfilnavn,"r") #virker med 'r'-mode? tilsyneladende!
	pos=f.tell()
	lastpos=pos
	N=0
	d=0
	h=0
	D=0
	H=0
	nopst=0
	punkt="NA"
	type="NA"
	line="X"
	Nh=0 #antal hoveder
	while len(line)>0:    #Skanner hele filen, men den er heldigvis ikke stor :-)#Blot lettere fra et programmerings-synspunkt
		line=f.readline()	  
		if len(line)>0 and not line.isspace():
			if line.split()[0]=="*":
				#print line
				gem=line
				if N==0:
					lastpos=f.tell() #skulle tage vare paa situationen hvor * er slut paa headeren...
				else:
					lastpos=pos
				pos=f.tell()
				
				N+=1
			elif line.split()[0]=="#":
				Nh+=1
				lasthead=f.tell()
	#print f.tell(),"pos slut"	
	#Laes sidste maaling:
	if N>1:  #saa er der flere end bare header slut *-en. Det ordnes nu ogsaa af status-tjek inden kald.
		
		line=gem
		#print pos, lastpos
		saveline=line
		#print saveline
		line=line.split()
		d=float(line[-2])
		h=float(line[-1])
		type=line[1]
		if type=="II":
			if saveline.find(Inst1.navn)!=-1: #navnet paa det instrument, der IKKE skal vaere hoejdebaerende skrives. Hmmm...
				Inst1.hstate=0
				Inst2.hstate=1
			else:
				Inst1.hstate=1
				Inst2.hstate=0
					
		elif type=="B1":
			Inst1.hstate=0
			Inst2.hstate=0
			if Nh>0:
				lastpos=lasthead #da det er en B1'er skal hovedet med, hvis det findes!
		else:
			
			punkt=line[2]
			D=float(line[-5]) #bedre at taelle bagfra, da det ikke vides hvor mange led der er i instrumentnavnet!
			H=float(line[-4])
			nopst=int(line[-3])
			if saveline.find(Inst1.navn)!=-1: #navnet paa det instrument, der skal vaere hoejdebaerende skrives!!
				Inst1.hstate=1
				Inst2.hstate=0
			else:
				Inst1.hstate=0
				Inst2.hstate=1
			
	f.close()
	if N>1:
		f=open(resfilnavn,"r")
		g=open(copy,"w")
		while f.tell()!=lastpos:
			line=f.readline()
			g.write(line)
		for line in f: #skriv nu resten af linierne med ; foran!
			docomment=True
			if line.isspace():
				docomment=False
			elif line.strip()[0]==";":
				docomment=False
			if docomment:
				g.write(";"+line)
			else:
				g.write(line)
		f.close()
		g.close()
		os.remove(resfilnavn)
		os.rename(copy,resfilnavn)
	
	return d,h,type,D,H,nopst,punkt

def Jside(resfile,mode=1,JS="XXX",program="MTL"): #mode 1: normal, mode 2: soegemode, mode3: test
	f=open(resfile,"rb") #'rb' fordi f.tell() i SaetEfterHoved ellers screwer up!
	f.readline() #foerste linie er program version
	filnavn=f.readline().split()[1] #anden linie indeholder filnavn
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
				pline=pline.replace("oe",u"\u00F8")
				pline=pline.replace("ae",u"\u00E6")
				pline=pline.replace("aa",u"\u00E5")
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
			print pline
	
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
	dc.TextOut(scale_factor * 40,-i * scale_factor * ls,(u"H\u00F8jdeforskel: %.5f m" %(float(gem[6]))).encode('L6'))
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
			print lastpos, gnl2-gnl1
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
		msg=u"%*i dobbeltm\u00E5linger (frem + tilbage)\n%*i enkeltm\u00E5linger.\n"%(-3,Nd,-3,Ns)
		if 2*Nd+Ns!=len(heads):
			msg+=u"Dette giver en fejl p\u00E5 %i i forhold til antal hoveder.\n" %(len(heads)-2*Nd+Ns)
		return msg

