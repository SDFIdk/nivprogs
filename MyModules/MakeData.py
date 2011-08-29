import sqlite3
import os
from PIL import Image
import glob
import zlib
import sys
#BUG: I beskrivelser kommer nogle tomme beskrivelser med....
koder=["N","T","L","M"]
oversaet=["DVR90","Transformeret","Lokalt system","MSL"]
fixopl="R:\\Fixopl2009\\"
kotefiles=["Fyn\\koterfyn","Jylland\\koterjyl",u"Sj\u00E6lland\\kotersjl",u"Sj\u00E6lland\\koterkbf","Bornholm\\koterbor"]
lockanko="DK\\lockanko" #skal behandels specielt
#og heraf afledes lrl og msl-filer
bskfiles=["Fyn\\bskphfyn","Jylland\\bskphjyl",u"Sj\u00E6lland\\bskphsjl","Bornholm\\bskphbor","DK\\bsk_kanko"]
skitsedirs=["Fyn\\skitse\\","Jylland\\skitse\\",u"Sj\u00E6lland\\skitse\\","Bornholm\\skitse\\"]
def MakeTables(database):
	con=sqlite3.connect("C:\Data\mtl.sqlite")
	cur=con.cursor()
	cur.execute("CREATE TABLE geo (navn TEXT unique, northing REAL, easting REAL, z REAL, type TEXT)")
	cur.execute("CREATE TABLE skitse (navn TEXT unique, img BLOB, mode TEXT, width INTEGER, height INTEGER)")
	cur.execute("CREATE TABLE beskrivelse (navn TEXT unique, bsk TEXT)")
	cur.execute("CREATE TABLE typeinfo (kode TEXT, vaerdi TEXT)")
	for k,v in zip(koder,oversaet):
		cur.execute("INSERT INTO typeinfo VALUES (?,?)",(k,v))
	conn.commit()
	cur.close()
	con.close()
	return
def MakeTypeInfo(database):
	con=sqlite3.connect(database)
	cur=con.cursor()
	for k,v in zip(koder,oversaet):
		cur.execute("INSERT INTO typeinfo VALUES (?,?)",(k,v))
	con.commit()
	cur.close()
	con.close()
	return
def MakeGeo(database):
	Stations=[]
	Nd=0
	con=sqlite3.connect(database)
	cur=con.cursor()
	for file in kotefiles:
		for ext in ["",".lrl",".msl"]:
			filename=fixopl+file+ext
			if os.path.exists(filename):
				print filename
				f=open(filename)
				for line in f:
					line=line.split()
					if len(line)>4:
						try:
							N=float(line[1])
							E=float(line[2])
							Z=float(line[3])
						except:
							pass
						else:
							navn=line[0]
							if navn in Stations:
								Nd+=1
							else:
								Stations.append(navn)
								if ext==".lrl":
									type="L"
								elif ext==".msl":
									type="M"
								elif line[-2]=="TRANSFORMEREDE":
									type="T"
								else:
									type="N"
								t=(navn,N,E,Z,type)
								try:
									cur.execute("INSERT INTO geo VALUES (?,?,?,?,?)",t)
								except:
									pass
				f.close()
				con.commit()
	f=open(fixopl+lockanko)  #kan koteres, behandles specielt.
	for line in f:
		line=line.strip()
		if len(line)>0 and line[-1]=="*":
			sline=line.split()
			if line[0]=="K":
				navn="K"+sline[1]
			else:
				navn=sline[0]
			if navn in Stations:
					Nd+=1
			else:
				Stations.append(navn)
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
						t=(navn,N,E,-999,'N')
						cur.execute("INSERT INTO geo VALUES (?,?,?,?,?)",t)
	con.commit()
	cur.close()
	con.close()
	print "Dubletter: ",Nd
	
def MakeBsk(database):
	con=sqlite3.connect(database)
	cur=con.cursor()
	try:
		cur.execute("delete * from beskrivelse")
	except:
		pass
	else:
		cur.execute("vacuum")
		con.commit()
	Stations=[]
	Nd=0
	for file in bskfiles:
		filename=fixopl+file
		print filename
		Bsk=[] #til beskrivelser...
		ind=open(filename)
		Lines=ind.readlines()
		bsk=[]
		foundpoint=False #til at skippe tomme linier mellem punktbeskrivelser.
		bsknospace=0 #til at taelle ikke tomme linier
		for i in range(0,len(Lines)):
			line=Lines[i]
			if (not foundpoint) and not line.isspace():
				foundpoint=True
				
			if foundpoint:
				if bsknospace==1 and (not line.isspace()) and line.strip()[-1]==":": #Til tomme beskrivelser...
					#Bsk.append(bsk) #gem ikke
					bsk=[]
					bsknospace=0   #vi har fundet et punkt... 
				if not line.isspace():
					bsk.append(line.strip())  #kun ikke spaces!
					bsknospace+=1
			if line.find("@=")!=-1: 
				if bsknospace>1:
					Bsk.append(bsk)
				bsk=[]
				foundpoint=False
				bsknospace=0
		for bsk in Bsk:
			if len(bsk)>1:
				navn=bsk[0].strip().replace(":","")
				navn=navn.replace(" ","")  #slet mellemrum
				if navn in Stations:
					Nd+=1
				else:
					Stations.append(navn)
					bsk=bsk[1:]
					text=""
					for line in bsk:
						if line!="@=":
							text+=line+"\n"
					text=text.decode("latin1").encode("utf-8")
					try:
						cur.execute("INSERT INTO beskrivelse VALUES (?,?)",(navn,text))
					except:
						pass
		ind.close()
		con.commit()
	cur.close()
	con.close()
	print "Dubletter: ",Nd
	return
	
def MakeSkitse(database):
	Stations=[]
	Nd=0
	con=sqlite3.connect(database)
	cur=con.cursor()
	for dir in skitsedirs:
		sdir=fixopl+dir
		files=glob.glob(sdir+"*")
		for file in files:
			
			try:
				im=Image.open(file)
			except:
				pass
			else:
				print file
				mode=im.mode
				width=im.size[0]
				height=im.size[1]
				name=(file.split("\\")[-1]).split(".")[0]
				if name[0:3]=="000":
					name="K"+name[3:]
				while name[0]=="0":
					name=name[1:]
				if name in Stations:
					Nd+=1
				else:
					Stations.append(name)
					im=buffer(zlib.compress(im.tostring())) #kun fordi sqlite gerne vil ha' det!
					t=(name,im,mode,width,height)
					try:
						cur.execute("INSERT INTO skitse VALUES (?,?,?,?,?)",t)
					except:
						pass
					else:
						con.commit()
	cur.close()
	con.close()
	print "Dubletter: ",Nd
	return 
def DoAll(database):
	MakeTables(database)
	MakeTypeInfo(database)
	MakeGeo(database)
	MakeSkitse(database)
	return
	