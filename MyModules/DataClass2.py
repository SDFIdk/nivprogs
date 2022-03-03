import numpy as np
import sqlite3
from PIL import Image,ImageDraw
import zlib
import os
#no threads here- runs relatively fast, even when fetching 100k+ points.
class PointData():
	def __init__(self,datafile):
		self.INITIALIZED=False
		try:
			self.con=sqlite3.connect(datafile)
		except:
			pass
		else:
			self.INITIALIZED=True
			self.cur=self.con.cursor()
			self.dtype=np.dtype([('label','<S16'),('x',np.float64),('y',np.float64),('z',np.float32),('type','S1')])
			self.located=np.array([],dtype=self.dtype)
			self.located_np=0
	def IsInitialized(self):
		return self.INITIALIZED
	def GetInfo(self,label):
		try:
			self.cur.execute("select bsk from beskrivelse where navn = ?",(label,))
		except:
			return "Beskrivelse ikke fundet...",False
		bsk=self.cur.fetchone()
		#print len(bsk)
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
	def GetSkitse(self,label):
		found=False
		try:
			self.cur.execute("select img,mode,width,height from skitse where navn = ?",(label,))
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
		im,w,h,found1=self.GetSkitse(label)
		bsk,found2=self.GetInfo(label)
		foundsome=found1 or found2
		return bsk,im,w,h,foundsome
	def GetInfoNamesLike(self,prefix):
		pattern="%s%s%s" %("%",prefix,"%")
		self.cur.execute("select navn from beskrivelse where navn like ? union select navn from skitse where navn like ?",(pattern,pattern))
		names=self.cur.fetchall()
		if names is not None and len(names)>0: #hmm, got to know return type, when "error"
			names=[x[0] for x in names]
		else:
			names=None
		return names
	def GetHeights(self,names):
		heights=[]
		for name in names:
			try:
				self.cur.execute("select z from geo where navn = ?",(name,)) #apperently this is the way to do it with only 1 input...
			except:
				z=None
			else:
				data=self.cur.fetchone()
				if data is not None and len(data)>0:
					z=data[0]
				else:
					z=None
			heights.append(z)
		return heights
	def GetCoordinates(self,name):
		try:
			self.cur.execute("select easting,northing,z from geo where navn = ?",(name,))
		except Exception as msg:
			print(repr(msg))
			x,y,z=None,None,None
		else:
			data=self.cur.fetchone()
			if (data is not None) and len(data)>0:
				x,y,z=data
			else:
				x,y,z=None,None,None
		return x,y,z
	def GetLocatedSkitse(self,j):
		label=self.located['label'][j]
		im,w,h,found=self.GetSkitse(label)
		return im,w,h,found
	def GetLocatedInfo(self,j):
		label=self.located['label'][j]
		info,found=self.GetInfo(label)
		return info,found
	def Locate(self,x1,x2,y1,y2):
		self.located=np.array([],dtype=self.dtype)
		self.located_np=0
		try:
			self.cur.execute("select navn,easting,northing,z,type from geo where easting<? and easting>? and northing<? and northing>?",(x2,x1,y2,y1))
		except:
			pass
		else:
			data=self.cur.fetchall()
			self.located=np.array(data,dtype=self.dtype)
		self.located_np=np.size(self.located,0)
	def GetLocatedType(self,j):
		if self.located_np>j:
			return self.located['type'][j]
		else:
			return ""
	def GetLocatedXY(self,j=-999):
		if self.located_np>j and j!=-999:
			return np.array([[self.located['x'][j],self.located['y'][j]]])
		elif j==-999:
			return np.array([self.located['x'],self.located['y']]).transpose()
		else:
			return None
	def GetLocatedZ(self,j):
		if self.located_np>j:
			return self.located['z'][j]
		else:
			return -999
	def GetLocatedLabel(self,j=-999):
		if self.located_np>j and j!=-999:
			return self.located['label'][j]
		elif j==-999:
			return self.located['label'].tolist()
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
		self.cur.execute("select count(*) from geo")
		ng=self.cur.fetchall()[0][0]
		self.cur.execute("select count(*) from beskrivelse")
		nb=self.cur.fetchall()[0][0]
		self.cur.execute("select count(*) from skitse")
		ns=self.cur.fetchall()[0][0]
		self.cur.execute("select count(*) from (select navn from geo where z<0)")
		nik=self.cur.fetchall()[0][0]
		self.cur.execute("select count(*) from (select navn from geo intersect select navn from beskrivelse)")
		ng_b=self.cur.fetchall()[0][0]
		self.cur.execute("select count(*) from (select navn from geo intersect select navn from skitse)")
		ng_s=self.cur.fetchall()[0][0]
		self.cur.execute("select count(*) from (select navn from beskrivelse union select navn from skitse except select navn from geo)")
		nng_bs=self.cur.fetchall()[0][0]
		self.cur.execute("select total_changes()")
		ntc=self.cur.fetchall()[0][0]
		msg="# punkter med (x,y)-koordinater: %i" %ng
		msg+=", heraf er %i ikke koteret.\n" %nik
		msg+="# beskrivelser: %i\n" %nb
		msg+="# skitser     : %i\n" %ns
		msg+="# punkter med koordinater og beskrivelser: %i\n" %ng_b
		msg+="# punkter med koordinater og skitser     : %i\n" %ng_s
		msg+="# punkter med beskrivelse eller skitse men uden lokation: %i\n" %nng_bs
		msg+="# totale \u00E6ndringer i datafilen: %i" %ntc
		return msg
	#STUFF FOR UPDATING THE FILE
	def UpdateDsc(self,BSK): 
		for station in list(BSK.keys()):
			bsk=BSK[station]
			#if station exists a replace will happen since name was set to unique in the create cmd
			self.cur.execute("insert or replace into beskrivelse values(?,?)",(station,bsk)) 
		self.con.commit()
	def UpdateCoords(self,coords): #accepts a dictionary with tuples as values
		for station in list(coords.keys()):
			crd=coords[station]
			#if station exists a replace will happen since name was set to unique in the create cmd
			N,E=crd
			self.cur.execute("insert or replace into geo(Navn,N,E) values(?,?,?)",(station,N,E)) 
		self.con.commit()
	def UpdateZs(self,coords): #accepts a dictionary with tuples as values
		for station in list(coords.keys()):
			crd=coords[station]
			#if station exists a replace will happen since name was set to unique in the create cmd
			Z,T=crd
			self.cur.execute("insert or replace into geo values(?,?,?,?,?)",(station,N,E,Z,T)) 
		self.con.commit()
	def UpdateSkitser(self,skitser): #a dictionary of station names and file names	
		for station in list(skitser.keys()):
			file=skitser[station]
			try:
				im=Image.open(file)
			except:
				pass
			else:
				mode=im.mode
				width=im.size[0]
				height=im.size[1]
				im=buffer(zlib.compress(im.tostring())) #kun fordi sqlite gerne vil ha' det!
				t=(station,im,mode,width,height)
				try:
					self.cur.execute("insert or replace into skitse values (?,?,?,?,?)",t)
				except:
					pass
		self.con.commit()
	

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
	cur.execute("CREATE TABLE geo (navn TEXT unique, northing REAL, easting REAL, z REAL, type TEXT)")
	cur.execute("CREATE TABLE skitse (navn TEXT unique, img BLOB, mode TEXT, width INTEGER, height INTEGER)")
	cur.execute("CREATE TABLE beskrivelse (navn TEXT unique, bsk TEXT)")
	cur.execute("CREATE TABLE typeinfo (kode TEXT, vaerdi TEXT)")
	for k,v in zip(koder,oversaet):
		cur.execute("INSERT INTO typeinfo VALUES (?,?)",(k,v))
	con.commit()
	cur.close()
	con.close()
	return True

