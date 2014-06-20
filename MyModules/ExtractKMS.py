import glob
import os
from PIL import Image
#Dette modul haandterer laesning af KMS-filformater genereret ved udtraek fra refgeo
#update 12-04-10 simlk, kan nu laese vandstandsnavne fra skitser....
#uodate 14-04-10 simlk, Pointname2Numformat fikset - kunne ikke oversaette G.I./G.M. navne ordenligt
def GetPointName(line):
	line=line.split()
	if len(line)<2 or not line[0][0].isalnum():
		return -1
	name=line[0]
	while line[0][-1] in ["K","-"] and len(line)>1:
		name+=line[1]
		line=line[1:]
	return name
	

def GetBsk(ind):
	Stations={} # dictionary med punkter og beskrivelser...
	Nd=0
	Nempty=0
	Bsk=[] #til beskrivelser...
	bsk=[]
	foundpoint=False #til at skippe tomme linier mellem punktbeskrivelser.
	bsknospace=0 #til at taelle ikke tomme linier
	line=ind.readline()
	while len(line)>0 and line.strip()!="quit!":
		if (not foundpoint) and not line.isspace() and line.strip()[-1]==":": #finder kun punkter hvis de slutter med ':'
			foundpoint=True
		if foundpoint:
			if bsknospace==1 and (not line.isspace()) and line.strip()[-1]==":": #Til tomme beskrivelser uden @= i enden
				bsk=[]
				bsknospace=0   #vi har fundet et punkt... 
			if not line.isspace():
				bsk.append(line.strip())  #kun ikke spaces!
				bsknospace+=1
		if line.find("@=")!=-1: #En beskrivelse SKAL slutte med @= ellers findes naeste beskrivelse ikke
			if bsknospace>1:
				Bsk.append(bsk)
			bsk=[]
			foundpoint=False
			bsknospace=0
		line=ind.readline()
	for bsk in Bsk:
		if len(bsk)>1:
			navn=bsk[0].strip().replace(":","")
			navn=navn.replace(" ","")  #slet mellemrum
			if len(navn)>4: #maaske bedre validering?
				if Stations.has_key(navn):
					Nd+=1
				else:
					bsk=bsk[1:]
					text=""
					for line in bsk:
						if line!="@=":
							text+=line+"\n"
					text=unicode(text.decode("latin1"))
					if len(text)>0:
						Stations[navn]=text
					else:
						Nempty+=1
	return Stations, Nd,Nempty
	
def GetCrd(ind): #deprecated
	Stations={}
	Nd=0
	line=ind.readline()
	type="N" #default, means 'normal'
	while len(line)>0 and line.strip()!="quit!":
		line=line.split()
		if len(line)>4:
			try:
				N=float(line[1])
				E=float(line[2])
				Z=float(line[3])
			except:
				pass
			else:
				if N>1000000 and E>99999 and Z>-1: #this should ensure right format, I hope!
					navn=line[0]
					if Stations.has_key(navn):
						Nd+=1
					else:
						if line[-2].upper()=="TRANSFORMEREDE":
							savetype="T"
						else:
							savetype=type
						t=(N,E,Z,type)
						Stations[navn]=t
		elif len(line)==2 and line[1][0]=="#":
			if line[1].lower().find("msl")!=-1: #MSL-system
				type="M"
			elif line[1].lower().find("lrl")!=-1: #lokalt system
				type="L"
		line=ind.readline()
	return Stations,Nd

def GetZs(ind):
	Stations={} 
	Nd=0
	type="N" #default, means 'normal'
	line=ind.readline()
	while len(line)>0 and line.strip()!="quit!":
		sline=line.split()
		if len(sline)>2 and "m" in sline: #saa har vi nok en kote
			navn=GetPointName(line)
			if navn!=-1:
				if navn in Stations:
						Nd+=1
				else:
					i=sline.index("m")
					Z=float(sline[i-1])
					if line.upper().find("TRANSFORMEREDE")!=-1:
						savetype="T"
					else:
						savetype=type
					Stations[navn]=(Z,savetype)
		elif len(sline)>0 and sline[0][0]=="#":
			if sline[0].lower().find("msl")!=-1: #MSL-system
				type="M"
			elif sline[0].lower().find("lrl")!=-1: #lokalt system
				type="L"
		line=ind.readline()
	return Stations,Nd


def GetIDs(ind):
	Stations={} 
	Nd=0
	Ngmgi=0
	Ngps=0
	line=ind.readline()
	while len(line)>0 and line.strip()!="quit!":
		hsnavn=GetPointName(line)
		if hsnavn!=-1:
			if Stations.has_key(hsnavn):
				Nd+=1
				print hsnavn
			else:
				gpsnavn=None
				gmginavn=None
				sline=line.split()
				for word in sline[1:]:
					if len(word)==4 and word.isalnum() and (not word.isdigit()): #then gpsnavn
						gpsnavn=word
						Ngps+=1
					elif word.find("G.M.")!=-1 or word.find("G.I.")!=-1:
						gmginavn=word
						Ngmgi+=1
				Stations[hsnavn]=[gmginavn,gpsnavn]
		line=ind.readline()
	return Stations,Nd,Ngmgi,Ngps
					
def GetLoc(ind):#tidligere GetKanKoLoc
	Stations={} 
	Nd=0
	line=ind.readline()
	while len(line)>0 and line.strip()!="quit!":
		line=line.strip()
		sline=line.split()
		if len(sline)>0 and "m" in sline:
			navn=GetPointName(line)
			if navn!=-1:
				if  Stations.has_key(navn):
						Nd+=1
				else:
					i=line.find("m")
					if i!=-1:
						nline=line[0:i].split()
						eline=line[i+1:].split()
						N=nline[-3]+nline[-2]+nline[-1]
						E=eline[0]+eline[1]
						try:
							N=float(N)
							E=float(E)
						except:
							pass
						else:
							t=(N,E)
							Stations[navn]=t
		line=ind.readline()
	return Stations,Nd

def GetSkitser(dir):
	if dir[-1] not in ["\\","/"]:
		dir+="/"
	files=glob.glob(dir+"*")
	Stations={}
	Nd=0
	for file in files:
		try:
			im=Image.open(file)
		except:
			pass
		else:
			name=os.path.basename(file)
			name=os.path.splitext(name)[0]
			if name[0:3]=="000":
				name="K"+name[3:]
			while name[0]=="0":
				name=name[1:]
			if Stations.has_key(name):
				Nd+=1
			else:
				Stations[name]=file
	return Stations,Nd
	
############################
## Translation Routiones                   
#############################

#valideringsfkt. til punktnavne - tjek med maalere o.a...
def ValidatePointName(name): 
	if len(name)<3: #at least 3 chars
		return False
	if len(name.split())>1: #No spaces
		return False
	return True

def IdenticalTranslation(name):
	return name

def Pointname2Numformat(name):
	if name.isdigit(): #then we are OK
		return name
	#name=name.replace(".","").replace("-","") #delete . and -
	name=name.upper()
	SIGN=""
	if  name.find("G.M.")!=-1 or name.find("G.I.")!=-1:
		sname=name.split(".")
		if len(sname)>3:
			try:
				int(sname[-1])
			except:
				 print "Error:",name
			else:
				SNR=sname[-1]
				if len(SNR)==1:
					SNR="0"+SNR
		else:
			SNR="00"
		i=name.find("/")
		if i!=-1:
			HNR="510"
		else:
			HNR="500"
		LBN=""
		i=0
		while 4+i<len(name):
			digit=name[4+i]
			if digit.isdigit():
				LBN+=digit
				i+=1
			else:
				break
		if len(LBN)<4:
			LBN="0"+LBN
		return HNR+SNR+LBN
	parts=name.split("-")
	if len(parts)<3: #then we dont know what to do....
		return name.replace("-","")
	if parts[0]=="K":
		HNR="200"
	else:
		HNR=parts[0]
	SNR=parts[1]
	if parts[2][0]=="V": #vandstand
		LBN="2200"
		i=parts[2].find(".")
		if i!=-1:
			vs=parts[2][i+1:]
			if len(vs)==1:
				vs="0"+vs
			LBN="22"+vs
		SIGN="-"
	elif parts[2][0]!="0": #saa hjaelpepunkt
		return parts[2]
	else:
		LBN=parts[2][1:] #slet foerste nul
	return SIGN+HNR+SNR+LBN
		
def Numformat2Pointname(navn): #meget kluntet skrevet....
	navn=navn.strip()
	if len(navn)<2:
		return ""
	try: 
		test=int(navn)
	except:
		return ""
	if navn[0]!="-":  #hvis ikke vandstandsbraet (- foran for vandstandsbraedder)
		nr=int(navn)
		HNR = int(nr/1000000)  #foerste cifre  (som regel 3)
		SNR = int(nr/10000) - HNR*100 #mellemste  (som regel 2)
		LBN = nr%10000  #sidste (som regel 4)
		if ( HNR == 200 ):
			HNR = "K"
		if ( nr < 100000):
			LNSNR = navn
		elif (nr < 300000000): 
			LNSNR = "%3s-%02d-0%04d" %(HNR,SNR,LBN) #vi indsaetter et ekstra 0 foran!
		else:  #Saa er HNR mindst 300 og dermed ikke oversat til K. Vi gaar til G.I, G.M-afdelingen...
			if (HNR<510): 
				if (SNR<1): #prik..??
					if (LBN<1600):
						LNSNR = "G.M.%s" %LBN
					else:
						LNSNR = "G.I.%s" %LBN
				else: #naa, ellers skal vi ha' en prik for et revideret punkt.
					if (LBN<1600):
						LNSNR = "G.M.%s.%s" %(LBN,SNR)
					else:
						LNSNR = "G.I.%s.%s" %(LBN,SNR)
	
			elif (HNR<520): #Ellers med skraastreg, for HNR stoerre end 500 
				if (SNR<1): #skal vi ha' prik?
					if (LBN<1600):
						LNSNR = "G.M.%s/%s" %(LBN,LBN+1)
					else:
						LNSNR = "G.I.%s/%s" %(LBN,LBN+1) #slut SNR=0
				else:  #ok, saa saetter vi en prik....
					if (LBN<1600):
						LNSNR = "G.M.%s/%s.%s" %(LBN,LBN+1,SNR)
					else:
						LNSNR = "G.I.%s/%s.%s"%(LBN,LBN+1,SNR) #slut SNR=1
			else:
				LNSNR=""
	else:  #ellers har vi fundet et minus...
		navn=int(navn[1:]) #vend fortegn/fjern minus
		HNR = int(navn/1000000)
		SNR = int(navn/10000) - HNR*100
		LBN = navn%100 #kun sidste 2 cifre for vandstandsbraedder...
		if ( HNR == 200 ):
			HNR = "K"
		
		LNSNR = "%3s-%02d-V.%s" %(HNR, SNR, LBN)
		#slut vandstandsbraet
	return LNSNR.strip()
