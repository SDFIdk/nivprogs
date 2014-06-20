import os
import sys
try:
	sys.frozen   #will pass if running py2exe executable 
except:
	pass #not needed, put gdal binaries on PATH
else:
	exedir=sys.prefix+"\\"
	os.environ["PATH"] += ";"+exedir
from osgeo import gdal
from osgeo import gdal_array
from osgeo.gdalconst import *
from osgeo import ogr
import glob
import numpy as np
import wx
import sqlite3
import os
import sys
import threading
#from shapely.wkb import loads
import wx.lib.newevent
(MapEvent,EVT_MAP) = wx.lib.newevent.NewEvent()
wx.InitAllImageHandlers()
#Last update 20.04.2010 added inuse attribute to mapdirs, simlk
#MapEngine.GetMap will return a map whose upper left corner is (x1,y2) and whose lower right corner is (x2,y1) approximately.
def Jet():
	table=[[Lin(i,100,255,80),Lin(i,90,200,80),Lin(i,0,150,90)] for i in range(0,256)]
	return (np.array(table)).astype(np.uint8)
def Lin(x,xmin,xmax,beta):
	if x>xmax:
		return int(255*np.exp(-(x-xmax)*0.05))
	if x<xmin:
		return int(beta*np.exp(-(xmin-x)*0.05))
	val=min(255,int(beta+(x-xmin)*(255.0-beta)/(xmax-xmin)))
	return val
GRAY=np.array([(i,i,i) for i in range(0,256)]).astype(np.uint8)
EXPERIMENTAL=np.array([(max(0,(i-150)*155.0/100),min(i,255-i)*0.5,max(0,255-i*255.0/100)) for i in range(0,256)]).astype(np.uint8)
EXPERIMENTAL[0]=[0,0,0]
DEMTYPE=".asc"  #suffix for DEM-files...
COLORMAPS=[Jet(),GRAY,EXPERIMENTAL]
COLORNAMES=["Jet","Grayscale","Exp"]
INDEXNAME="mapindex.sqlite"
ABSOLUTE_MIN=-3
def GetIndexName():
	return INDEXNAME
def GetColormaps():
	return COLORMAPS
def GetColornames():
	return COLORNAMES
def NewColorMap(Cmap):
	for i in range(np.size(Cmap,0)):
		R=Cmap[i,0]
		G=Cmap[i,1]
		B=Cmap[i,2]
		if R>G+10 and R>B+10: #red to grey
			Cmap[i]=[150,150,150]
		if G>R+10 and G>B+10: #green to white
			Cmap[i]=[255,255,255]
		if abs(G-R)<20 and abs(G-B)<20 and abs(B-R)<20 and G+R+B<3*50:
			Cmap[i]=[0,0,0]
	return Cmap.astype(np.uint8)
def Array2Color(X,scaledown=False,absolute=False,hmax=50.0):
	m=max(ABSOLUTE_MIN,np.min(X))
	M=np.max(X)
	gap=float(M-m)
	if absolute:
		return np.minimum(255,(X-ABSOLUTE_MIN)*(255.0/hmax)).astype(np.uint8)
	if scaledown:
		A=(np.sqrt((X-m)/gap)*255.0).astype(np.uint8)
		return A
	else:
		return np.round((X-m)*(255.0/gap)).astype(np.uint8)

class MapDir():
	def __init__(self,dir,isDEM=False):
		self.INITIALIZED=False
		self.XPIXEL=0
		self.YPIXEL=0
		self.XSIZE=0
		self.YSIZE=0
		self.RKM=0
		self.isDEM=isDEM
		if dir[-1] not in ["/","\\"]:
				dir+="\\"
		self.MAPDIR=dir
		if os.path.exists(dir+INDEXNAME): #if already indexed, then we're happy...
			try:
				self.CON=sqlite3.connect(dir+INDEXNAME)
				self.CURSOR=self.CON.cursor()
			except:
				pass
			else:
				self.INITIALIZED=True
				
		elif isDEM:  #otherwise we might be looking at a DEM on a read only drive... TODO- add support for general read only drives...
			self.CON,self.CURSOR=MakeIndex(dir,sys.stdout,memory=True,type=DEMTYPE)
			self.INITIALIZED=True
		if self.INITIALIZED:
			self.CURSOR.execute("SELECT * FROM metadata")
			data=self.CURSOR.fetchone()
			self.METADATA=data
			self.XPIXEL=float(data[3])
			self.YPIXEL=np.fabs(data[4])
			self.XSIZE=int(data[1])
			self.YSIZE=int(data[2])
			self.CON.create_function("TestOverlap",8,TestOverlap)
			self.RKM=int(np.round(self.XSIZE*self.XPIXEL/1000.0))
			self.MAPTYPE=type
			self.INUSE=True
	def Close(self):
		try:
			self.CON.close()
		except:
			pass
	def GetName(self):
		return self.MAPDIR[0:-1]
	def GetUseState(self):
		return self.INUSE
	def SetUseState(self,state=True):
		self.INUSE=state
	def GetCenter(self):
		if self.INITIALIZED:
			x1=self.METADATA[5]
			x2=self.METADATA[6]
			y1=self.METADATA[7]
			y2=self.METADATA[8]
			return (x2-x1)*0.5+x1,(y2-y1)*0.5+y1
		else:
			return -1,-1
	def GetRadius(self):
		return 6*self.RKM
	def GetXPixelsize(self):
		return self.XPIXEL
	def IsInitialized(self):
		return self.INITIALIZED
	def Coor2File(self,x,y):
		if self.INITIALIZED:  
			self.CURSOR.execute("SELECT filename FROM mapindex WHERE xmin<=? AND xmax>=? AND ymin<=? AND ymax>=?",(x,y))
			filename=self.CURSOR.fetchone() #hopefully only one!
			return filename
		else:
			return ""
	def GetOverlappingFiles(self,xmin,xmax,ymin,ymax):
		if self.INITIALIZED:
			self.CURSOR.execute("SELECT filename FROM mapindex WHERE TestOverlap(xmin,xmax,ymin,ymax,?,?,?,?)",(xmin,xmax,ymin,ymax))
			names=self.CURSOR.fetchall()
			return map(lambda x: str(x[0]), names)
		else:
			return []
	
class MapEngine(object):
	def __init__(self):
		self.INITIALIZED=False
		self.DIRNAMES=[]
		self.MAPDIRS=[]
		self.COLORMAP=COLORMAPS[0] #Default
	def Close(self):
		for dir in self.MAPDIRS:
			dir.Close()
	def Initialize(self,dir,isDEM=False):
		mapdir=MapDir(dir,isDEM)
		if mapdir.IsInitialized():
			self.MAPDIRS=[mapdir]
			self.INITIALIZED=True
			self.DIRNAMES=[mapdir.GetName()]
			self.mapdir=mapdir
			return True
		else:
			return False
	def SetColorMap(self,i):
		if i<len(COLORMAPS):
			self.COLORMAP=COLORMAPS[i]
	def SetBestMapDir(self,xmin,xmax,ymin,ymax,xwin,ywin):
		xpix=(xmax-xmin)/float(xwin) 
		yrange=(ymax-ymin)/1000.0
		xrange=(xmax-xmin)/1000.0 #range in km
		range=max(xrange,yrange)
		inuse=[dir for dir in self.MAPDIRS if dir.GetUseState()]
		if len(inuse)==0:
			return False
		storedir=inuse[0]
		mindiff=10000000
		maxrange=0
		maxrangedir=storedir
		for dir in inuse:
			overlap=True #default value
			data=dir.METADATA
			x1=data[5]
			x2=data[6]
			y1=data[7]
			y2=data[8]
			overlap=TestOverlap(x1,x2,y1,y2,xmin,xmax,ymin,ymax)
			if overlap:
				diff=abs(dir.XPIXEL-xpix)
				if diff<mindiff:
					storedir=dir
					mindiff=diff
				if dir.GetRadius()>maxrange:
					maxrange=dir.GetRadius()
					maxrangedir=dir
		if range>storedir.GetRadius():
			if range>maxrange:
				return False
			else:
				storedir=maxrangedir
		self.mapdir=storedir
		return True
	def AddMapDir(self,dir,isDEM=False):
		if dir in self.DIRNAMES:
			return False
		mapdir=MapDir(dir,isDEM)
		OK=mapdir.IsInitialized()
		if OK:
			self.MAPDIRS.append(mapdir)
			self.INITIALIZED=True
			self.DIRNAMES=[dir.GetName() for dir in self.MAPDIRS]
			self.mapdir=mapdir
		return OK
	def RemoveMapDir(self,dir):
		try:
			dir.Close()
			self.MAPDIRS.remove(dir)
			del dir
		except:
			return False
		else:
			self.DIRNAMES=[dir.GetName() for dir in self.MAPDIRS]
			if len(self.MAPDIRS)==0:
				self.INITIALIZED=False
			return True
	def GetMapDirs(self):
		return self.MAPDIRS
	def GetMapDirsUseState(self):
		return [dir.GetUseState() for dir in self.MAPDIRS]
	def SetMapDirsUseState(self,states):
		i=0
		for state in states:
			self.MAPDIRS[i].SetUseState(state)
			i+=1
	def GetNumberOfDirs(self):
		return len(self.MAPDIRS)
	def GetMaxRadius(self): #return max-radius in KM
		maxrange=0
		for dir in self.MAPDIRS:
			if dir.GetUseState():
				maxrange=max(maxrange,dir.GetRadius())
		if maxrange==0:
			maxrange=1000 #improve!!!
		return maxrange
	def GetXPixelsize(self):
		return self.mapdir.XPIXEL
	def GetMinPixelsize(self):
		mps=10*6
		for dir in self.MAPDIRS:
			if dir.GetUseState():
				mps=min(mps,dir.GetXPixelsize())
		if mps==10*6:
			mps=1.0
		return mps
	def IsInitialized(self):
		return self.INITIALIZED
	def ReturnError(self,text,xwin,ywin):
		buffer=wx.EmptyBitmap(xwin,ywin)
		dc=wx.MemoryDC(buffer)
		dc.SetFont(wx.Font(14,wx.SWISS,wx.NORMAL,wx.NORMAL))
		dc.SetTextForeground("white")
		textextent=14*len(text)
		xpos=(xwin-textextent)*0.5
		ypos=(ywin*0.5)
		dc.DrawText(text,xpos,ypos)
		return buffer
	def GetMap(self,xmin,xmax,ymin,ymax,xwin,ywin):
		if not self.INITIALIZED:
			M=self.ReturnError("Initialize the map-engine first!",xwin,ywin)
			return M,xmin,xmax,ymin,ymax
		OK=self.SetBestMapDir(xmin,xmax,ymin,ymax,xwin,ywin)
		if not OK:
			M=self.ReturnError("Zoom range not supported!",xwin,ywin)
			return M,xmin,xmax,ymin,ymax
		try:
			files=self.mapdir.GetOverlappingFiles(xmin,xmax,ymin,ymax)
			if self.mapdir.isDEM:
				raster=np.zeros(shape=(ywin,xwin),dtype=np.uint8)
			else:
				raster=np.ones(shape=(ywin,xwin,3),dtype=np.uint8)*255  #RGB
			for file in files:
				dataset=gdal.Open(self.mapdir.MAPDIR+file,GA_ReadOnly)
				w=dataset.RasterXSize
				h=dataset.RasterYSize 
				geo=dataset.GetGeoTransform()
				x1=float(geo[0])
				y2=float(geo[3])
				xpix=float(geo[1])
				ypix=float(geo[5]) #negative by default
				x2=x1+xpix*w
				y1=y2+ypix*h
				sx1,sx2,sy1,sy2=self.GetExtent(xmin,xmax,ymin,ymax,x1,x2,y1,y2,w,h)
				bx1,bx2,by1,by2=self.GetExtent(x1,x2,y1,y2,xmin,xmax,ymin,ymax,xwin,ywin)
				bufx=bx2-bx1
				bufy=by2-by1
				if bufx>0 and bufy>0:
					raster[by1:by2,bx1:bx2]=self.UseGdal(dataset,sx1,sy1,sx2-sx1,sy2-sy1,bufx,bufy)
			if raster.ndim<3:
				raster=self.COLORMAP[Array2Color(raster)[:,:],:]
			return wx.BitmapFromBuffer(xwin,ywin,raster),xmin,xmax,ymin,ymax  #whole span of map from top corner to lower right corner (NOT center of pixels!)
		except Exception, msg:
			print str(msg)
			M=self.ReturnError("Error: %s" %str(msg),xwin,ywin)
			return M,xmin,xmax,ymin,ymax
	def GetExtent(self,x1,x2,y1,y2,x1r,x2r,y1r,y2r,w,h): 
		xcell=float(x2r-x1r)/w
		ycell=float(y2r-y1r)/h
		xl=round((x1-x1r)/xcell)
		yt=round((y2r-y2)/ycell)
		xl=int(max(xl,0))
		yt=int(max(yt,0))
		xr=round((x2-x1r)/xcell)
		yb=round((y2r-y1)/ycell)
		xr=int(min(w,xr))
		yb=int(min(h,yb))
		return xl,xr,yt,yb #left,right,top,bottom
	def UseGdal(self,dataset,xul,yul,sx,sy,bufx,bufy,isDEM=False):
		nbands=dataset.RasterCount
		if nbands==1:
			band=dataset.GetRasterBand(1)
			cols=None
			if not isDEM:
				cols=band.GetRasterColorTable()
			if cols is not None:
				colortable=np.array([cols.GetColorEntry(i)[0:3] for i in range(0,cols.GetCount())],dtype=np.uint8)
				raster=band.ReadAsArray(xul,yul,sx,sy,bufx,bufy).astype(np.uint8)
				raster=colortable[raster[:,:],:]
			else: #Then we just read the raster and use a common color table later
				raster=band.ReadAsArray(xul,yul,sx,sy,bufx,bufy)
			return raster
		else: #then we are dealing with RGB-bands
			raster=np.zeros(shape=(bufy,bufx,3))
			for i in range(0,3):
				band=dataset.GetRasterBand(i+1)
				raster[:,:,i]=band.ReadAsArray(xul,yul,sx,sy,bufx,bufy)
			return raster
class MapThread(MapEngine,threading.Thread):
	def __init__(self,win,mapdirs):
		threading.Thread.__init__(self)
		MapEngine.__init__(self)
		self.goflag1=threading.Event() #trying to increase thread-safety :-)
		self.goflag2=threading.Event()
		self.goflag1.clear()  #these flags are managed by the main thread of control...
		self.goflag2.clear()
		self.running=False
		self.alive=False
		self.setDaemon(True)  #a daemonic thread....
		self.mapwindow=win
		self.mapdirs=mapdirs #not intefering with MAPDIRS attribute
		self.start()
	def isRunning(self):
		return self.running
	def kill(self):
		self.alive=False
		self.goflag1.set()
		self.goflag2.set()
	def StartThread(self,x1,x2,y1,y2,w,h):
		self.x1=x1
		self.x2=x2
		self.y1=y1
		self.y2=y2
		self.w=w
		self.h=h
		self.goflag1.set() #release myself
		self.goflag2.clear()
	def run(self):
		self.alive=True
		for dir in self.mapdirs: #sqlite objects must be created in this thread!
			self.AddMapDir(dir)
		while self.alive:
			self.goflag1.wait()
			if self.alive:
				self.running=True
				self.map,self.x1,self.x2,self.y1,self.y2=self.GetMap(self.x1,self.x2,self.y1,self.y2,self.w,self.h)
				event=MapEvent(gotmap=True)
				wx.PostEvent(self.mapwindow,event)
				self.running=False
				self.goflag2.wait()
			if not self.alive: #then we go a kill-signal and close sqlite objects in this thread...
				self.Close() #method inherited from MapEngine
	def FetchMap(self):
		self.goflag1.clear() #move on!
		self.goflag2.set()
		return self.map,self.x1,self.x2,self.y1,self.y2
			
def GetMap(mapfile,xwin=600,colortable=GRAY):
	dataset=gdal.Open(mapfile,GA_ReadOnly)
	xsize=dataset.RasterXSize
	ysize=dataset.RasterYSize
	scale=float(xwin)/xsize
	ywin=int(round(scale*ysize))
	raster=np.zeros(shape=(ywin,xwin,3),dtype=np.uint8)
	geo=dataset.GetGeoTransform()
	xmin=float(geo[0])
	ymax=float(geo[3])
	xpix=geo[1]
	ypix=geo[5]
	xmax=xmin+xpix*xsize
	ymin=ymax+ypix*ysize
	nbands=dataset.RasterCount
	if nbands==1:
		band=dataset.GetRasterBand(1)
		cols=band.GetRasterColorTable()
		if cols is not None:
			colortable=np.array([cols.GetColorEntry(i)[0:3] for i in range(0,cols.GetCount())],dtype=np.uint8)
			raster=band.ReadAsArray(0,0,xsize,ysize,xwin,ywin).astype(np.uint8)
			raster=colortable[raster[:,:],:]
		else:#otherwise use a default color table-- probably will never happen :-()
			raster=Array2Color(band.ReadAsArray(0,0,xsize,ysize,xwin,ywin))	
			raster=colortable[raster[:,:],:]
	else: #presumably a shortcut method exists.... anyways we read all three 'RGB' bands explicitly, assuming this is the case,,,
		for i in range(0,3):
			band=dataset.GetRasterBand(i+1)
			raster[:,:,i]=band.ReadAsArray(0,0,xsize,ysize,xwin,ywin)
	return wx.BitmapFromBuffer(xwin,ywin,raster),xmin,xmax,ymin,ymax  #whole span of map from top corner to lower right corner (NOT center of pixels!)


def GetPixel(self,xulc,yulc,x,y): #ul-center! faas fra kortnavn i kms-standard kortdir.
		yul=yulc+self.XPIXEL*0.5
		xul=xulc-self.YPIXEL*0.5
		xgap=float((x-xul))/self.XPIXEL
		ygap=float((yul-y))/self.YPIXEL
		xoff=0
		yoff=0
		if xgap<0:        #because int rounds down, and up for negative numbers....
			xgap-=1
		if ygap<0:
			ygap-=1
		return int(xgap),int(ygap) #pixel 0-4999 corresponds to 5000 pixels



class IndexThread(threading.Thread):
	def __init__(self,dir,type=None):
		threading.Thread.__init__(self)
		self.window=win
		self.type=type
		self.dir=dir
	def run(self):
		MakeIndex(self.dir,sys.stdout,type=self.type)
		

def MakeIndex(dir,out,memory=False,type=None):
	olddir=os.getcwd()
	os.chdir(dir)
	if type is not None:
		pat="*%s" %type
	else:
		pat="*" #the same effect, really since None="" :-)
	files=glob.glob(pat)
	if not memory:
		fname=INDEXNAME
		if os.path.exists(fname):
			os.remove(fname)
	else:
		fname=":memory:"
	con=sqlite3.connect(fname)
	cur=con.cursor()
	cur.execute("CREATE TABLE mapindex (filename TEXT, xmin REAL, xmax REAL, ymin REAL, ymax REAL)")
	cur.execute("CREATE TABLE metadata (nfiles INTEGER, xsize REAL, ysize REAL, xpixelsize REAL, ypixelsize REAL, xmin REAL, xmax REAL, ymin REAL, ymax REAL)") 
	Nok=0
	avxs=0
	avys=0
	avxpix=0
	avypix=0
	minx=10**10
	miny=10**10
	maxx=-10**10
	maxy=-10**10
	for file in files:
		try:
			dataset=gdal.Open(file,GA_ReadOnly)
			xsize=dataset.RasterXSize
			ysize=dataset.RasterYSize 
			geo=dataset.GetGeoTransform()
		except:
			pass
		else:
			Nok+=1
			xmin=float(geo[0])
			ymax=float(geo[3])
			xpix=geo[1]
			ypix=geo[5] #neg by default
			xmax=xmin+xpix*xsize
			ymin=ymax+ypix*ysize
			minx=min(xmin,minx)
			maxx=max(xmax,maxx)
			miny=min(ymin,miny)
			maxy=max(ymax,maxy)
			thelist=(file,xmin,xmax,ymin,ymax)
			cur.execute("INSERT INTO mapindex VALUES (?,?,?,?,?)",thelist)
			con.commit()
			avxpix+=xpix
			avypix+=ypix
			avxs+=xsize
			avys+=ysize
			if Nok%100==0:
				out.write("Files done: %i\n" %Nok)
	if Nok>0:
		avxs=float(avxs)/Nok
		avys=float(avys)/Nok
		avxpix=float(avxpix)/Nok
		avypix=float(avypix)/Nok
		thelist=(Nok,avxs,avys,avxpix,avypix,minx,maxx,miny,maxy)
		cur.execute("INSERT INTO metadata VALUES (?,?,?,?,?,?,?,?,?)",thelist)
		con.commit()
	os.chdir(olddir)
	out.write("Index %s created with %i files.\n" %(fname,Nok))
	out.write("Av. pixx %.1f, av. pixy %.1f, av. xsize %i, av. ysize %i\n" %(avxpix, avypix,avxs, avys))
	out.write("Bounding box: xmin=%.1f xmax=%.1f ymin=%.1f ymax=%.1f\n" %(minx,maxx,miny,maxy))
	if not memory:
		con.close()
		return
	else:
		return con,cur
class Polygon():
	def __init__(self,coords,label,placelabel="ul"):
		self.coords=coords
		self.label=label
	def GetPolyCoords(self):
		return self.coords
	def GetLabel(self):
		return self.label
	def GetLabelCoords(self):
		return np.mean(self.coords,0)
		
		

class PolygonReader(): #reads polygon (opmaalingsdistrikter) from shapefile
	def __init__(self):
		self.source=None
		self.layer=None
		self.INITIALIZED=False
		self.polygons=None
		self.lastfetch=None
	def Initialize(self,fname):
		try:
			self.source=ogr.Open(fname)
			self.layer=self.source.GetLayer(0) #we assume its the first layer we want
		except Exception,msg:
			print repr(msg)
		else:
			self.INITIALIZED=True
	def IsInitialized(self):
		return self.INITIALIZED
	def GetPolygons(self,minx,maxx,miny,maxy):
		if not self.INITIALIZED:
			return
		if (minx,maxx,miny,maxy)==self.lastfetch:
			return self.polygons
		self.layer.SetSpatialFilterRect(minx,miny,maxx,maxy)
		nf=self.layer.GetFeatureCount()
		polygons=[]
		for i in xrange(0,nf):
			feature=self.layer.GetNextFeature()
			label=feature.GetFieldAsString(0) # we assume that this field is the label for the feature
			geom=feature.GetGeometryRef()  #geometry class
			type=geom.GetGeometryType()
			if (type==ogr.wkbPolygon or type==ogr.wkbPolygon25D):
				#boundary=loads(geom.GetBoundary().ExportToWkb()) #quick and dirty using geos
				coords=np.array(geom.GetBoundary().GetPoints())
				#print coords.shape
				if coords.shape[1]>2:
					coords=coords[:,0:2]
				polygons.append(Polygon(coords,label))
			#TODO: else do some kind of logging....
		self.polygons=polygons
		self.lastfetch=(minx,maxx,miny,maxy)
		return polygons
	def GetDistrictName(self,x,y): #kind of stupid, could possibly be done better via ogr
		if not self.INITIALIZED:
			return None
		name=""
		self.layer.SetSpatialFilterRect(x-10,y-10,x+10,y+10)
		nf=self.layer.GetFeatureCount()
		features=[]
		point=ogr.Geometry(ogr.wkbPoint)
		point.AddPoint_2D(x,y)
		for i in range(0,nf):
			feature=self.layer.GetNextFeature()
			features.append(feature)
		for feature in features:
			polygon=feature.GetGeometryRef()
			if polygon.Contains(point):
				name=feature.GetFieldAsString(0)
				break
		return name

class LineReader(object):
	def __init__(self):
		self.source=None
		self.layer=None
		self.INITIALIZED=False
		self.lines=None
		self.lastfetch=None
	def Initialize(self,fname):
		self.lines=None
		self.lastfetch=None
		self.layer=None
		try:
			self.source=ogr.Open(str(fname))
			self.layer=self.source.GetLayer(0) #we assume its the first layer we want
		except Exception,msg:
			self.INITIALIZED=False
			print msg
		else:
			self.INITIALIZED=True
	def IsInitialized(self):
		return self.INITIALIZED
	def GetLines(self,minx,maxx,miny,maxy):
		if not self.INITIALIZED:
			return
		if self.lastfetch==(minx,maxx,miny,maxy):
			return self.lines
		self.layer.SetSpatialFilterRect(minx,miny,maxx,maxy)
		nf=self.layer.GetFeatureCount()
		#print nf
		lines=[]
		for i in range(0,nf):
			feature=self.layer.GetNextFeature()
			geom=feature.GetGeometryRef()
			type= geom.GetGeometryType()
			if type==ogr.wkbLineString or type==ogr.wkbLineString25D:
				#geom=loads(geom.ExportToWkb()) #geometry class
				coords=np.array(geom.GetPoints())
				#print coords.shape
				if coords.shape[1]>2:
					coords=coords[:,0:2]
				#print coords.mean()
				#npoints=geom.GetPointCount()
				#coords=np.zeros((npoints,2))
				#for j in range(0,npoints):
				#	point=geom.GetPoint_2D(j) 
				#	coords[j,:]=point
				lines.append(coords)
		self.lastfetch=(minx,maxx,miny,maxy)
		self.lines=lines
		return lines
	def GetBounds(self):
		if not self.INITIALIZED:
			return 0,10,0,10
		nf=self.layer.GetFeatureCount() #reset filter???
		coords=np.empty((0,2))
		for i in range(0,3):
			feature=self.layer.GetNextFeature()
			geom=feature.GetGeometryRef()
			if True: #geom.GetGeometryType()==ogr.wkbLineString:
				npoints=geom.GetPointCount()
				nextcoords=np.zeros((npoints,2))
				for j in range(0,npoints):
					point=geom.GetPoint_2D(j) 
					nextcoords[j,:]=point
				coords=np.vstack((coords,nextcoords))
		x1,y1=np.min(coords,axis=0)
		x2,y2=np.max(coords,axis=0)
		return x1,x2,y1,y2
	def CloseDown(self):
		try:
			self.source=None #invokes gc
			self.layer=None
		except:
			pass
			
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
	return int(xhit & yhit) #to be able to register the function in sqlite!
		