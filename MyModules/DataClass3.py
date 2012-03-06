import numpy as np
import sqlite3
from PIL import Image,ImageDraw
import zlib
import os
#last update 26.03.2010 simlk - fixed GetCoordinates 
#no threads here- runs relatively fast, even when fetching 100k+ points.
class PointData(object):
	def __init__(self,datafile=None):
		self.INITIALIZED=False
		self.dtype=np.dtype([('id',np.int64),('label','<S16'),('x',np.float64),('y',np.float64),('q',np.uint8)])
		self.located=np.array([],dtype=self.dtype)
		self.located_np=0
		self.lx1,self.lx2,self.ly1,self.ly2=-1,-1,-1,-1 #bounding box for located points
		self.lastfetch=None #container to determine whteher we already have point data available in memory
		self.maxedout=False
		self.selected=None   #attributte for drawing a selected point in a certain way
		if datafile is not None:
			try:
				self.con=sqlite3.connect(datafile)
			except:
				pass
			else:
				self.cur=self.con.cursor()
				try:
					self.cur.execute("select min(easting),max(easting),min(northing),max(northing) from main")
					data=self.cur.fetchone()
					self.x1,self.x2,self.y1,self.y2=data
				except Exception,msg:
					f=open("data_error.log","w")
					f.write(repr(msg))
					f.close()
				else:
					self.INITIALIZED=True
	def IsInitialized(self):
		return self.INITIALIZED
	def GetMaxBounds(self):
		return self.x1,self.x2,self.y1,self.y2
	def GetLocatedBounds(self):
		return self.lx1,self.lx2,self.ly1,self.ly2
	def GetMaxedOut(self):
		return self.maxedout
	def GetNameType(self,id):
		if id==0:
			return "herred/sogne"
		elif id==1:
			return "G.M./G.I."
		elif id==2:
			return "GPS"
		else:
			return ""
	def GetID(self,label):
		#this is too slow:
		#self.cur.execute("select id from main where (hsnavn = ? or gpsnavn = ? or gmginavn = ?)",(label,label,label))
		nametype=self._GetNameType(label)
		if nametype==0:
			self.cur.execute("select id from main where (hsnavn = ?)",(label,))
		elif nametype==1:
			self.cur.execute("select id from main where (gmginavn = ?)",(label,))
		else:
			self.cur.execute("select id from main where (gpsnavn = ?)",(label,))
		id=self.cur.fetchone()
		if id is None:
			return None
		else:
			return id[0]
	def _GetNameType(self,label): 
		nametype=0 #hsnavn
		if label.find("G.M.")!=-1 or label.find("G.I.")!=-1:
			nametype=1 #gmginavn
		elif len(label)==4 and label.isalnum() and (not label.isdigit()): 
			nametype=2 #then gpsnavn:
		return nametype
	def GetNewID(self):
		self.cur.execute("select max(id) from main")
		id=self.cur.fetchone()[0]
		try:
			id=int(id)+1
		except:
			id=1
		return id
	def GetInfo(self,id):
		if id is None:
			return "Beskrivelse ikke fundet...",False
		self.cur.execute("select bsk from beskrivelse where id = ?",(id,))
		bsk=self.cur.fetchone()
		if bsk is not None and len(bsk)>0:
			return bsk[0],True
		else:
			return "Beskrivelse ikke fundet...", False
	def ReturnNoSkitse(self):
		im=Image.new("RGB",(200,200),"white")
		draw=ImageDraw.Draw(im)
		draw.text((30,90),"Skitse ikke fundet.","red")
		del draw
		return im.tostring(),200,200
	def GetSkitse(self,id):
		found=False
		if id is None:
			im,w,h=self.ReturnNoSkitse()
		else:
			try:
				self.cur.execute("select img,mode,width,height from skitse where id = ?",(id,))
			except:
				im,w,h=self.ReturnNoSkitse()
			else:
				data=self.cur.fetchone()
				if data is not None and len(data)>0:
					im=zlib.decompress(str(data[0]))
					mode=data[1]
					w=data[2]
					h=data[3]
					im=Image.fromstring(mode,(w,h),im)
					if mode!="RGB":
						im=im.convert("RGB")
					im=im.tostring()
					found=True
				else:
					im,w,h=self.ReturnNoSkitse()
		return im,w,h,found
	def GetSkitseAndBsk(self,label):
		id=self.GetID(label)
		if id is not None:
			im,w,h,found1=self.GetSkitse(id)
			bsk,found2=self.GetInfo(id)
			foundsome=found1 or found2
			return bsk,im,w,h,foundsome
		else:
			return None,None,None,None,False
	def GetInfoNamesLike(self,prefix):
		pattern="%s%s%s" %("%",prefix,"%")
		self.cur.execute("select id,hsnavn from main where (hsnavn like ? or gpsnavn like ? or gmginavn like ?)  and (id in (select id from beskrivelse) or id in (select id from skitse))",(pattern,pattern,pattern))
		ids=self.cur.fetchall()
		if ids is not None and len(ids)>0: #hmm, got to know return type, when "error"
			ids=map(lambda x: x[1],ids)
		else:
			ids=None
		return ids
	def GetHeights(self,names):
		heights=[]
		for name in names:
			z=None
			id=self.GetID(name)
			if id is not None:
				self.cur.execute("select z from kote where id = ?",(id,)) #apperently this is the way to do it with only 1 input...
				data=self.cur.fetchone()
				if data is not None and len(data)>0:
					z=data[0]
			heights.append(z)
		return heights
	def GetCoordinates(self,name):
		nametype=self._GetNameType(name)
		if nametype==0:
			self.cur.execute("select easting,northing from main where hsnavn = ?",(name,))
		elif nametype==1:
			self.cur.execute("select easting,northing from main where gmginavn = ?",(name,))
		else:
			self.cur.execute("select easting,northing from main where gpsnavn = ?",(name,))
		data=self.cur.fetchone()
		if (data is not None) and len(data)>0:
			x,y=data
		else:
			x,y=None,None
		return x,y
	def GetManyCoordinates(self,names): #hs-names by default
		#nametype=self._GetNameType(names[0])
		sql_list="("
		for name in names[:-1]:
			sql_list+='"%s",' %name
		sql_list+='"%s")' %names[-1]
		self.cur.execute("select hsnavn,easting,northing from main where hsnavn in %s"%sql_list)
		data=self.cur.fetchall()
		return data
		
	def Locate(self,x1,x2,y1,y2,lost=0,nametype=0):
		self.selected=None #always unselect the special point here
		if not self.INITIALIZED:
			return
		if (x1,x2,y1,y2,lost,nametype)==self.lastfetch and self.located_np>0: #then we already have data
			return
		self.lastfetch=(x1,x2,y1,y2,lost,nametype)
		if not TestOverlap(x1,x2,y1,y2,self.x1,self.x2,self.y1,self.y2):
			self.Clear()
		self.located=np.array([],dtype=self.dtype)
		self.located_np=0
		if nametype==0:
			self.cur.execute("select id,hsnavn,easting,northing,kvalitet from main where easting<? and easting>? and northing<? and northing>? and tabtgaaet=?",(x2,x1,y2,y1,lost))
		elif nametype==1:
			self.cur.execute("select id,gmginavn,easting,northing,kvalitet from main where easting<? and easting>? and northing<? and northing>? and gmginavn is not NULL and tabtgaaet=?",(x2,x1,y2,y1,lost))
		elif nametype==2:
			self.cur.execute("select id,gpsnavn,easting,northing,kvalitet from main where easting<? and easting>? and northing<? and northing>? and gpsnavn is not NULL and tabtgaaet=?",(x2,x1,y2,y1,lost))
		data=self.cur.fetchall()
		self.located=np.array(data,dtype=self.dtype)
		self.located_np=np.size(self.located,0)
		if self.located_np>0:
			self.lx1=np.min(self.located['x'])
			self.lx2=np.max(self.located['x'])
			self.ly1=np.min(self.located['y'])
			self.ly2=np.max(self.located['y'])
			self.maxedout=x1<self.x1 and x2>self.x2 and y1<self.y1 and y2>self.y2
		else:
			self.Clear()
	def GetSelectedXY(self):
		if self.selected is not None and self.selected<self.located_np:
			return np.array([[self.located['x'][self.selected],self.located['y'][self.selected]]])
		return None
	def GetSelectedQuality(self):
		if self.selected is not None and self.selected<self.located_np:
			return self.located['q'][self.selected]
		return None
	def GetSelectedLabel(self):
		if self.selected is not None and self.selected<self.located_np:
			return self.located['label'][self.selected]
		else:
			return None
	def GetSelectedZ(self):
		z=None
		type=None
		if self.selected is not None and self.located_np>self.selected:
			id=int(self.located['id'][self.selected])
			self.cur.execute("select z,type from kote where id = ?",(id,))
			data=self.cur.fetchone()
			if data is not None:
				z,t=data
				if t=="T":
					type="(Transformeret)."
				elif t=="L":
					type="(Lokalt system)."
				elif t=="M":
					type="(MSL system)."
		return z,type
	def GetSelectedSkitse(self):
		if self.selected is not None:
			id=int(self.located['id'][self.selected])
			im,w,h,found=self.GetSkitse(id)
			return im,w,h,found
		else:
			return None,None,None,False
	def GetSelectedInfo(self):
		if self.selected is not None:
			id=int(self.located['id'][self.selected])
			info,found=self.GetInfo(id)
			return info,found
		else:
			return None
	def Select(self,j):
		if j<self.located_np:
			self.selected=j
		else:
			self.selected=None
	def UnSelect(self):
		self.selected=None
	def GetSelected(self):
		return self.selected
	def GetLocatedQuality(self):
		return self.located['q']
	def GetLocatedXY(self,j=-999):
		if self.located_np>j and j!=-999:
			return np.array([[self.located['x'][j],self.located['y'][j]]])
		elif j==-999:
			return np.array([self.located['x'],self.located['y']]).transpose()
		else:
			return None
	def GetLocatedLabels(self):
		return self.located['label'].tolist()
	def ClosestLocatedPoint(self,x,y):
		if self.located_np>0:
			xp,yp=self.located['x'],self.located['y']
			d=np.sqrt((x-xp)**2+(y-yp)**2)
			j=np.argmin(d)
			D=np.min(d)
		else:
			D=10000
			j=-1
		return D,j
	def Clear(self):
		self.located=np.array([],dtype=self.dtype)
		self.located_np=0
		self.selected=None
		self.lastfetch=None
		self.lx1,self.lx2,self.ly1,self.ly2=-1,-1,-1,-1
		self.maxedout=False
	def Disconnect(self):
		try:
			self.cur.close()
			self.con.close()
		except:
			pass
	def NumbersLocated(self):
		return self.located_np
	def NumbersAll(self): #check up
		return 0,0
	def GetNChanged(self):
		self.cur.execute("select total_changes()")
		ntc=self.cur.fetchall()[0][0]
		return ntc
	def GetStats(self):
		self.cur.execute("select count(*) from (select * from main where (easting >0 and northing >0))")
		ng=self.cur.fetchall()[0][0]
		self.cur.execute("select count(*) from kote")
		nz=self.cur.fetchall()[0][0]
		self.cur.execute("select count(*) from main where tabtgaaet = 1")
		nt=self.cur.fetchall()[0][0]
		self.cur.execute("select count(*) from beskrivelse")
		nb=self.cur.fetchall()[0][0]
		self.cur.execute("select count(*) from skitse")
		ns=self.cur.fetchall()[0][0]
		#self.cur.execute("select count(*) from (select navn from geo intersect select navn from beskrivelse)")
		#ng_b=self.cur.fetchall()[0][0]
		#self.cur.execute("select count(*) from (select navn from geo intersect select navn from skitse)")
		#ng_s=self.cur.fetchall()[0][0]
		#self.cur.execute("select count(*) from (select navn from beskrivelse union select navn from skitse except select navn from geo)")
		#nng_bs=self.cur.fetchall()[0][0]
		self.cur.execute("select total_changes()")
		ntc=self.cur.fetchall()[0][0]
		msg="%*s %i\n" %(-40,"# punkter med (x,y)-koordinater:",ng)
		msg+="%*s %i\n"%(-40,u"# punkter markeret som tabtg\u00E5et:",nt)
		msg+="%*s %i\n" %(-40,"# punkter med kote:",nz)
		msg+="%*s %i\n" %(-40,"# beskrivelser:",nb)
		msg+="%*s %i\n" %(-40,"# skitser:",ns)
		#msg+="# punkter med koordinater og beskrivelser: %i\n" %ng_b
		#msg+="# punkter med koordinater og skitser     : %i\n" %ng_s
		#msg+="# punkter med beskrivelse eller skitse men uden lokation: %i\n" %nng_bs
		msg+="%*s %i\n" %(-40,u"# totale \u00E6ndringer i datafilen:",ntc)
		return msg
	#STUFF FOR UPDATING THE FILE
	def GetNotFoundFile(self):
		i=0
		name="notfound.txt"
		while os.path.exists(name):
			name="notfound_%i.txt" %i
			i+=1
		f=open(name,"w")
		f.write("#DK_idt\n\n")
		return f
	def StationDoesNotExist(self,station):
		#perhaps write to some other error log....
		print("%s kunne ikke findes i alias-tabellen." %station)
	def MarkAsLost(self,stations):
		notfound=[]
		for station in stations:
			id=self.GetID(station)
			if id is not None:
				self.cur.execute("update main set tabtgaaet = 1 where id = ?",(id,))
			else:
				notfound.append(station)
		self.con.commit()
		return notfound
	def MarkAsGeo(self,stations):
		notfound=[]
		for station in stations:
			id=self.GetID(station)
			if id is not None:
				self.cur.execute("update main set kvalitet = 1 where id = ?",(id,))
			else:
				notfound.append(station)
		self.con.commit()
		return notfound
	def CreateNewPoints(self,stations,tabt=False):
		nd=0
		for station in stations.keys():
			gmginavn,gpsnavn=stations[station]
			try:
				self.cur.execute("insert into main(hsnavn,gmginavn,gpsnavn,tabtgaaet) values(?,?,?,?)",(station,gmginavn,gpsnavn,tabt))
			except sqlite3.IntegrityError:
				nd+=1 #then point already exists since names are unique
		self.con.commit()
		return nd
	def UpdateDsc(self,BSK): #we assume stations are labelled using hs-navn
		notfound=0
		done=0
		f=self.GetNotFoundFile()
		for station in BSK.keys():
			bsk=BSK[station] 
			id=self.GetID(station)
			if id is not None:
				self.cur.execute("insert or replace into beskrivelse values(?,?)",(id,bsk)) 
				done+=1
			else:
				notfound+=1
				f.write("%s\n" %station)
			if done%500==0:
				print done,notfound
		f.write("-1z")
		f.close()
		if notfound>0:
			print("#Stations not found: %i\nSee names in file." %notfound)
		self.con.commit()
	def UpdateCoords(self,coords): #accepts a dictionary with tuples as values
		f=self.GetNotFoundFile()
		notfound=0
		done=0
		for station in coords.keys():
			crd=coords[station]
			N,E=crd
			id=self.GetID(station)
			if id is not None:
				self.cur.execute("update main set easting = ?, northing = ? where id = ?",(E,N,id))
				#self.cur.execute("insert or replace into loc(id,northing,easting) values(?,?,?)",(id,N,E))
				done+=1
			else:
				f.write("%s\n" %station)
				notfound+=1
			if done%500==0:
				print done,notfound
		f.write("-1z")
		f.close()
		if notfound>0:
			print("#Stations not found: %i\nSee names in file." %notfound)
		self.con.commit()
	def UpdateZs(self,coords): #accepts a dictionary with tuples as values
		f=self.GetNotFoundFile()
		notfound=0
		done=0
		for station in coords.keys():
			crd=coords[station]
			#if station exists a replace will happen since name was set to unique in the create cmd
			Z,T=crd
			id=self.GetID(station)
			if id is not None:
				self.cur.execute("insert or replace into kote values(?,?,?)",(id,Z,T)) 
				done+=1
			else:
				f.write("%s\n" %station)
				notfound+=1
			if done%500==0:
				print done,notfound	
		f.write("-1z")
		f.close()
		if notfound>0:
			print("#Stations not found: %i\nSee names in file." %notfound)
		self.con.commit()
	def UpdateSkitser(self,skitser): #a dictionary of station names and file names
		notfound=0
		done=0
		f=self.GetNotFoundFile()
		for station in skitser.keys():
			file=skitser[station]
			try:
				im=Image.open(file)
			except:
				pass
			else:
				id=self.GetID(station)
				if id is not None:
					mode=im.mode
					if mode in ["RGB","RGBA"]:
						im=im.convert("L") #to black and white
					mode="L"
					width=im.size[0]
					height=im.size[1]
					im=buffer(zlib.compress(im.tostring())) #kun fordi sqlite gerne vil ha' det!
					t=(id,im,mode,width,height)
					try:
						self.cur.execute("insert or replace into skitse values (?,?,?,?,?)",t)
					except:
						pass
					else:
						done+=1
				else:
					f.write("%s\n" %station)
					notfound+=1
				if done%100==0:
					print done,notfound
		f.write("-1z")
		f.close()
		if notfound>0:
			print("#Stations not found: %i\nSee names in file." %notfound)
		self.con.commit()


def MakeDatabase_manytables(filename):
	if os.path.exists(filename):
		try:
			os.remove(filename)
		except:
			return False
	koder=["N","T","L","M"]
	oversaet=["DVR90","Transformeret","Lokalt system","MSL"]
	con=sqlite3.connect(filename)
	cur=con.cursor()
	cur.execute("CREATE TABLE alias(id INTEGER PRIMARY KEY, hsnavn TEXT unique,gmginavn TEXT unique,gpsnavn TEXT unique,tabtgaaet INTEGER)")
	cur.execute("CREATE TABLE loc (id INTEGER unique, northing REAL, easting REAL, tabtgaaet INTEGER)")
	cur.execute("CREATE TABLE kote (id INTEGER unique, z REAL, type TEXT)")
	cur.execute("CREATE TABLE skitse (id INTEGER unique, img BLOB, mode TEXT, width INTEGER, height INTEGER)")
	cur.execute("CREATE TABLE beskrivelse (id INTEGER unique, bsk TEXT)")
	cur.execute("CREATE TABLE typeinfo (kode TEXT, vaerdi TEXT)")
	for k,v in zip(koder,oversaet):
		cur.execute("INSERT INTO typeinfo VALUES (?,?)",(k,v))
	con.commit()
	cur.close()
	con.close()
	return True


def MakeDatabase(filename):
	if os.path.exists(filename):
		try:
			os.remove(filename)
		except:
			return False
	koder=["N","T","L","M"]
	oversaet=["DVR90","Transformeret","Lokalt system","MSL"]
	con=sqlite3.connect(filename)
	cur=con.cursor()
	cur.execute("CREATE TABLE main (id INTEGER PRIMARY KEY, hsnavn TEXT unique,gmginavn TEXT unique,gpsnavn TEXT unique, easting REAL, northing real, tabtgaaet INTEGER, kvalitet INTEGER)")
	cur.execute("CREATE TABLE kote (id INTEGER unique, z REAL, type TEXT)")
	cur.execute("CREATE TABLE skitse (id INTEGER unique, img BLOB, mode TEXT, width INTEGER, height INTEGER)")
	cur.execute("CREATE TABLE beskrivelse (id INTEGER unique, bsk TEXT)")
	cur.execute("CREATE TABLE typeinfo (kode TEXT, vaerdi TEXT)")
	for k,v in zip(koder,oversaet):
		cur.execute("INSERT INTO typeinfo VALUES (?,?)",(k,v))
	con.commit()
	cur.close()
	con.close()
	return True

def TestOverlap(x11,x12,y11,y12,x21,x22,y21,y22): #test for overlap of rectangles...
	xhit=False
	yhit=False
	if x11<=x21<=x12 or x11<=x22<=x12:
		xhit=True
	if x21<=x11<=x22 or x21<=x12<=x22:
		xhit=True
	if y11<=y21<=y12 or y11<=y22<=y12:
		yhit=True
	if y21<=y11<=y22 or y21<=y12<=y22:
		yhit=True
	return int(xhit & yhit) 
def Contains(x11,x12,y11,y12,x21,x22,y21,y22): #first contains second?
	xtest=(x11<=x21) & (x12>=x22)
	ytest=(y11<=y21) & (y12>=y22)
	return xtest & ytest