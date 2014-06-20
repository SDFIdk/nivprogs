import wx
import MapPanel
import GdalMaps
import GPS 
import MapBase
from DataClass2 import PointData
import wms_client
import numpy as np
wms_client.SetLogin("kms1","adgang") #should be setup by the user...
#Implements a base class MapBase for handling maps via wms or GDALMaps and point data (sqlite) via DataClass2
#Direct user action and "mode"-handling should be wrapped on top of the MapBase class.
#This is a simpler version (no obs layers) of a previous implementation - i.e a new branch....
#Last edit: 04.01.2011, simlk
#BUG: punktnavne skrives naar kun lille del af skaermen opdateres!!!! TODO!
#BUG: In DrawPoints and DrawSpecial... None type in Array2ScreenCoords... FIXED in MapBase, self.selected=-1 in TestPointUodate
#BUG: In plot: if affected region!=ALL we can have NoneTypes in AffectedRegion.... Somehow, FIXED 
#New: Now selected attribute is kept in data class
class DummyWindow(): #Mapbrowser har altid et nav-vindue, som spoerges om det er vist.
	def SetStatusText(self):
		pass
	def Plot(self,*args):
		pass
	def Close(self):
		pass
	def IsShown(self):
		return False
	def Show(self,*args):
		pass
	def SetMemory(self,*args):
		pass
		
class MiniMap(wx.MiniFrame): #old style implementation,. Kunne godt bruge MapPanel.... parent SKAL have en minimap attribut og en SetMap metode...
	def __init__(self,parent,title,x,y,mapfile=None):
		self.parent=parent
		self.SetupMap(mapfile)
		wx.MiniFrame.__init__(self,parent,title=title,size=(self.xpix,self.ypix),style=wx.DEFAULT_FRAME_STYLE)
		self.panel=wx.Panel(self,size=(self.xpix,self.ypix))
		self.panel.Bind(wx.EVT_PAINT,self.OnPaint)
		self.panel.Bind(wx.EVT_LEFT_DOWN,self.OnLeftClick)
		self.sizer=wx.BoxSizer()
		self.sizer.Add(self.panel,0,wx.CENTER)
		self.SetSizerAndFit(self.sizer)
		self.x=x
		self.y=y
		#self.mapradius=float(self.parent.mapradius)
		self.Bind(wx.EVT_CLOSE,self.OnClose)
		self.Show()
	def SetupMap(self,mapfile):
		if mapfile is None:
			self.map=wx.EmptyBitmap(400,400)
			self.xpix=400
			self.ypix=400
			self.x1=450000
			self.x2=890000
			self.y1=6100000
			self.y2=6500000
		else:
			self.map,self.x1,self.x2,self.y1,self.y2=GdalMaps.GetMap(mapfile,600)
			self.xpix=self.map.GetWidth()
			self.ypix=self.map.GetHeight()
	def OnClose(self,event):
		self.parent.minimap=DummyWindow()
		event.Skip()
	def OnLeftClick(self,event):
		if True:
			x=event.GetX()
			y=event.GetY()
			x,y=self.UC(x,y)
			self.x=x
			self.y=y
			self.Plot()
			self.parent.x=self.x
			self.parent.y=self.y
			#if self.mapradius<L1(self.parent.center,self.parent.mapcenter)+300: #hvis under 700m til buffer-kortgraense...:
			self.parent.SetMap()
			self.parent.UnSelect()
	def Plot(self):
		dc=wx.ClientDC(self.panel)
		dc.Clear()
		dc.DrawBitmap(self.map,0,0)
		dc.SetBrush(wx.Brush( wx.RED, wx.SOLID ))
		x,y=self.SC(self.x,self.y)  #Position
		xrad=6
		yrad=6
		dc.DrawRectangle(x-xrad*0.5,y-yrad*0.5,xrad,yrad)
	def OnPaint(self,event):
		dc=wx.PaintDC(self.panel)
		dc.DrawBitmap(self.map,0,0)
		dc.SetBrush(wx.Brush( wx.RED, wx.SOLID ))
		x,y=self.SC(self.x,self.y)  #Position
		xrad=6
		yrad=6
		dc.DrawRectangle(x-xrad*0.5,y-yrad*0.5,xrad,yrad)
	def UC(self,x,y):
		xr=float(self.x2-self.x1)
		yr=float(self.y2-self.y1)
		x=self.x1+x*xr/self.xpix
		y=(self.ypix-y)*yr/self.ypix+self.y1
		return x,y
	def SC(self,x,y):
		xr=float(self.x2-self.x1) #for at undgaa integer division!
		yr=float(self.y2-self.y1)
		x=int((x-self.x1)/xr*self.xpix)
		y=int(self.ypix-(y-self.y1)/yr*self.ypix)
		return x,y

#Most of the stuff here not used anymore.... Only pointsize and pointfont really....
class PlotStyle(object):
	def __init__(self):
		self.font=wx.Font(12,wx.SWISS,wx.NORMAL,wx.NORMAL) #default-vals
		self.textcolor="black"
		self.hvcolor="blue"
		self.vvcolor="red"
		self.pointsize=12
		self.shortnames=False
		self.usebest=True
		self.pointcolor="red"
		self.connect=False
		self.scalefont=wx.Font(15,wx.SWISS,wx.NORMAL,wx.BOLD)
		self.vectorscale=20 # 20 pixels pr. m
		self.usebestvectorscale=True
		self.drawvectorlabels=True
		self.vectorwidth=2
		self.connectioncolor="red"
	def IsEqual(self,other):
		isequal=(self.font==other.font)
		isequal&=(self.textcolor==other.textcolor)
		isequal&=(self.hvcolor==other.hvcolor)
		isequal&=(self.vvcolor==other.vvcolor)
		isequal&=(self.pointsize==other.pointsize)
		isequal&=(self.usebest==other.usebest)
		return isequal


#A slight expansion of MapBase. Allows for wms-threads, but uses a non threaded map fetcher from disk, rather than the MapThread from MapBase.
class Map(MapBase.MapBase): 
	def __init__(self,parent,winx=600,winy=600,dataclass=None,mapdirs=[],polygonfile=None,linefile=None,realparent=None,plotstyle=None):
		MapBase.MapBase.__init__(self,parent,winx=winx,winy=winy,dataclass=dataclass,mapdirs=mapdirs,realparent=realparent)
		#STATE VARS nad DATA -more 'layers' here than in MapBase
		self.mapservice="disk" #can be disk or wms 
		self.wmsthread=GPS.DummyThread() #always has a wms-thread, with methods isAlive and kill
		self.MapEngine=GdalMaps.MapEngine() #fetches maps from disk- overrules MapBases threaded MapEngine
		if len(mapdirs)>0:   #Start up the MapEngine
			for dir in mapdirs:
				self.AddMapDir(dir,setmap=False)
		if self.MapEngine.IsInitialized():
			pixelsize=self.MapEngine.GetXPixelsize()
		else:
			pixelsize=1.0 #standard
		self.PolygonEngine=GdalMaps.PolygonReader() #should be switched on from outside - not used in base class
		if polygonfile is not None:
			self.PolygonEngine.Initialize(polygonfile)
		self.LineEngine=GdalMaps.LineReader()
		if linefile is not None:
			self.LineEngine.Initialize(linefile)
		############################
		## define 'layers'
		############################
		self.drawlayer=np.array(self.GetValidLayers())
		self.drawlayer|=[True,False,True,False,True] #this is the default
		self.pointlayer=2 #index to pointlayer - easier to change here
		self.layernames=["Kortbaggrund","Kystlinie","Punkt-database",u"Opm\u00E5lingsdistrikter","Kortskala"]
		self.Layer_Methods=[self.DrawMap,self.DrawLines,self.DrawPoints,self.DrawPolygons,self.DrawScaleBar]
		self.LastDrawExtents=np.zeros((len(self.layernames),5)) #first col=intersects yes/no, col 1-5=x1,x2,y1,y2
		#stuff for determining drawing of layers
		self.lastdraw=None
		self.lastdrawcoords=None
		self.lastpointfetch=None
		###########################
		#Style stuff
		if plotstyle is not None:
			self.plotstyle=plotstyle
		else:
			self.plotstyle=PlotStyle()
		#CUSTOM EVENTS
		self.Bind(MapPanel.EVT_DISTANCE,self.OnDistance)
		self.Bind(wms_client.EVT_WMS,self.SetMap)  #sendes af wms-klienten naar kort er hentet
		self.minimap=DummyWindow()
	def OnDistance(self,event):
		dist=event.distance
		self.Log("Afstand: %.0f m" %dist)
	def CloseDown(self):
		self.wmsthread.kill()
		if self.gps.isAlive(): #saa skal vi ikke logge data til dette vindue!
			self.gps.DetachWindow()
		if self.data is not None:
			self.data.Disconnect()
		self.MapEngine.Close()
	def KillWMS(self):
		if self.wmsthread.isAlive():
			self.wmsthread.kill()
			self.Log("Stopper wms-download")
	def EnableDistance(self):
		self.MapPanel.EnableDistance()
	def DisableDistance(self):
		self.MapPanel.DisableDistance()
	def ZoomIn(self): #centers around gpspos, when using gps-centering
		if self.wmsthread.isAlive():
			self.Log("Vent til WMS-hentning er aflsuttet.")
		else:
			if self.gpscentering and self.gotvalidgpspos: #if we have navigated away in the meantime...
				self.x=self.gpsx
				self.y=self.gpsy
				if self.MapPanel.GetPixelSize()<self.MapEngine.GetMinPixelsize()*0.1:
					return
			self.MapPanel.Zoom(self.x,self.y,0.5)
			self.SetMap()
	def ZoomOut(self):
		if self.wmsthread.isAlive():
			self.Log("Vent til WMS-hentning er aflsuttet.")
		else:
			self.MapPanel.Zoom(self.x,self.y,2)
			self.SetMap()
	def CanZoom(self):
		if not self.wmsthread.isAlive():
			return True
		else:
			self.Log("Vent til WMS-hentning er aflsuttet.")
			return False
	def SetPixelSize(self,size):
		pixsize=self.MapPanel.GetPixelSize()
		if size!=pixsize:
			self.MapPanel.SetPixelSize(size)
			self.SetMap()
	def GetMinPixelSize(self):
		#todo update wms metadata
		return self.MapEngine.GetMinPixelsize()
	def GetMaxRange(self): 
		#todo update wms bounding boxes!
		return self.MapEngine.GetMaxRadius()*1000.0 #in km
	def GetPixelSize(self):
		return self.MapPanel.GetPixelSize()
	def SetMap(self,event=None,plot=True):#ellers kan nuvaerende kort bruges... og det burde eksistere!
		doplot=False 
		self.MapPanel.SetCenter(self.x,self.y)
		if self.drawlayer[0]:
			if self.mapservice=="disk":
				doplot=True & plot
				if self.MapEngine.IsInitialized():
					R=self.MapEngine.GetMaxRadius()
					x1,x2,y1,y2=self.MapPanel.GetBounds()
					
					size=self.MapPanel.GetCanvasSize()
					try:
						M,nx1,nx2,ny1,ny2=self.MapEngine.GetMap(x1,x2,y1,y2,size[0],size[1])
					except Exception, msg:
						self.map=wx.EmptyBitmap(size[0],size[1])
						self.Log(str(msg)+"\nKortet kunne ikke opdateres!")
					else:
						self.map=M
						self.MapPanel.SetCenter(nx1+(nx2-nx1)*0.5,ny1+(ny2-ny1)*0.5)
						#self.Log("Easting: %.0f m til %0.f m,   Northing: %.0f m til %.0f m" %(nx1,nx2,ny1,ny2))
				else:
					self.Log("Definer kortmappe...")
			elif event is None and not self.wmsthread.isAlive() and self.drawlayer[0]:  #saa WMS-service
				doplot=False #plot foerst naar kortet kommer!
				size=self.MapPanel.GetCanvasSize()
				x1,x2,y1,y2=self.MapPanel.GetBounds()
				text="Henter kort via Kortforsyningen - vent..."
				self.MapPanel.DrawText(text,fontsize=16,color="red",centertext=True)
				self.MapPanel.DrawScreen()
				self.wmsthread=wms_client.WMSthread(self,x1,x2,y1,y2,size[0],size[1],self.wmsmaptype) #start traaden...
			elif isinstance(event,wms_client.WMSMapEvent):
				doplot=True & plot
				size=self.MapPanel.GetCanvasSize()
				self.map,OK,x1,x2,y1,y2=self.wmsthread.GetMap(size[0],size[1])
				if OK:
					self.MapPanel.SetBoundary(x1,x2,y1,y2)
					#self.Log("Easting: %.0f m til %0.f m,   Northing: %.0f m til %.0f m" %(x1,x2,y1,y2))
		else:
			doplot=True & plot
		if doplot:
			if self.minimap.IsShown():
				self.minimap.x=self.x
				self.minimap.y=self.y
				self.minimap.Plot()
			self.Plot(newmap=True)
	def DefinePolygonFile(self,fname):
		self.PolygonEngine.Initialize(str(fname))
		return self.PolygonEngine.IsInitialized()
	def DefineLineFile(self,fname):
		self.LineEngine.CloseDown()
		self.LineEngine.Initialize(fname)
		return self.LineEngine.IsInitialized()
	def TogglePolygons(self):
		self.drawpolygons=self.drawpolygons^True
		if self.drawpolygons and not self.PolygonEngine.IsInitialized():
			self.Log("Definer polygonfil!")
		self.Plot()
	def DefineMapDir(self,dir,isDEM=False):
		OK=self.MapEngine.Initialize(dir,isDEM)
		if OK:
			self.ResetPlot()
			self.SetInitialCenter(realcenter=True)
			self.SetMap()
		else:
			self.Log(u"Kunne ikke s\u00E6tte kortmappen til %s. Indekser kortmappen vha. menupunkt." %dir)
		return OK
	def AddMapDir(self,dir,setmap=True):
		OK=self.MapEngine.AddMapDir(dir)
		if OK and setmap:
			if self.MapEngine.GetNumberOfDirs()==1:
				self.ResetPlot()
				self.SetInitialCenter(realcenter=True)
				self.SetMap()
		elif not OK:
			self.Log(u"Kunne ikke tif\u00F8je kortmappen %s. Indekser kortmappen vha. menupunkt." %dir)
		return OK
	def SetCenterBasedOnData(self):
		if self.MapEngine.IsInitialized() and self.MapEngine.GetNumberOfDirs()>0:
			self.SetInitialCenter(realcenter=False)
		elif self.LineEngine.IsInitialized():
			x1,x2,y1,y2=self.LineEngine.GetBounds()
			cx=(x2+x1)*0.5
			cy=(y1+y2)*0.5
			r=(x2-x1)*0.1
			self.x,self.y=cx,cy
			self.SetPixelSize(r/800.0)
	def DefineMinimap(self,file):
		self.minimapfile=file
	def ToggleMinimap(self):
		if self.minimap.IsShown():
			self.CloseMiniMap()
		else:
			self.ShowMiniMap()
	def ShowMiniMap(self):
		self.minimap=MiniMap(self,"Oversigtskort",self.x,self.y,self.minimapfile)
	def CloseMiniMap(self):
		if self.minimap.IsShown():
			self.minimap.Close()
		self.minimap=DummyWindow()
	def EnableWMS(self,type):
		self.mapservice="wms"
		self.wmsmaptype=type
	def EnableDiskMaps(self):
		self.mapservice="disk"
	def GetMapType(self):
		return self.mapservice
	def Plot(self,x=None,y=None,w=0,h=0,newmap=False): #overrides base-class plot
		#This is a bit complicated - trying to get rendering as fast as possible - could probably be greatly simplified.
		#called from SetMap, GetPoints, SetLayers, GPS-action: OnGps, SetGPSCentering, 
		self.Log("Rendering....")
		if self.lastdraw is not None:
			switchoff=np.logical_and(self.lastdraw,np.logical_not(self.drawlayer))
			switchon=np.logical_and(np.logical_not(self.lastdraw),self.drawlayer)
		else:
			switchoff=np.ones(self.drawlayer.shape,dtype=np.bool)
			switchon=np.ones(self.drawlayer.shape,dtype=np.bool)
		valid_layers=self.GetValidLayers()
		should_draw=np.logical_and(self.drawlayer,valid_layers)
		switchoff&=valid_layers
		switchon&=valid_layers
		should_draw[0]=True
		### Determine what to update #########
		self.lastdraw=np.copy(self.drawlayer)
		if switchon.any():
			if switchon[0]:
				self.SetMap(plot=False)
			AffectedRegion=Box()
			i=np.where(switchon)[0][0]
			self.LastDrawExtents[i]=self.Layer_Methods[i]()
			itest,ax1,ax2,ay1,ay2=self.LastDrawExtents[i]
			if itest:
				AffectedRegion.Extend(ax1,ax2,ay1,ay2)
				for layer in range(i+1,self.drawlayer.shape[0]): #draw layers on top
					if should_draw[layer]:
						self.LastDrawExtents[layer]=self.Layer_Methods[layer](AffectedRegion)
			else:
				return
		elif switchoff.any():
			if switchoff[0]:
				self.map=None
			AffectedRegion=Box()
			i=np.where(switchoff)[0][0]
			itest,ax1,ax2,ay1,ay2=self.LastDrawExtents[i]
			if itest:
				AffectedRegion.Extend(ax1,ax2,ay1,ay2)
				for layer in range(0,self.drawlayer.shape[0]):
					if should_draw[layer]:
						#print AffectedRegion.GetBounds()
						self.LastDrawExtents[layer]=self.Layer_Methods[layer](AffectedRegion)
			else:
				return
		else:
			AffectedRegion="ALL"
			for layer in range(0,self.drawlayer.shape[0]):
				if should_draw[layer]:
					self.LastDrawExtents[layer]=self.Layer_Methods[layer]()
		if AffectedRegion!="ALL":
			screencoords=self.MapPanel.Array2ScreenCoords(np.array([[AffectedRegion.x1,AffectedRegion.y1],[AffectedRegion.x2,AffectedRegion.y2]]))
			x,y=np.min(screencoords,axis=0)
			x2,y2=np.max(screencoords,axis=0)
			w=x2-x
			h=y2-y #order switch
		self.MapPanel.DrawScreen(x,y,w,h)
		x1,x2,y1,y2=self.MapPanel.GetBounds()
		if self.gpscentering and self.gotvalidgpspos and (x1<self.gpsx<x2) and (y1<self.gpsy<y2): #FIX THIS!!!!! 
			self.DrawGPS()
		self.Log("Easting: %.0f m til %0.f m,   Northing: %.0f m til %.0f m" %(x1,x2,y1,y2))
	def DrawGPS(self):
		x,y,w,h=self.MapPanel.GetGPSClippingRegion(self.gpsx,self.gpsy)
		s1,s2=self.MapPanel.GetCanvasSize()
		if (0<=x<s1 or 0<x+w<=s1) and (0<=y<s2 or 0<y+h<=s2): #if clipping region on screen!
			self.MapPanel.DrawGPS(self.gpsx,self.gpsy)
			self.MapPanel.DrawScreen(x,y,w,h)
	def DrawMap(self,UpdateRegion=None):
		x1,x2,y1,y2=self.MapPanel.GetBounds()
		self.MapPanel.DrawMap(self.map,region=UpdateRegion) #kan vaere None
		return 1,x1,x2,y1,y2 #always affects entire screen on switch on/off
	def DrawPoints(self,UpdateRegion=None):
		ps=self.plotstyle
		x1,x2,y1,y2=self.MapPanel.GetBounds()
		if (not self.gpscentering) or (not self.gotvalidgpspos): #otherwise point localisation is controlled by gps
			#this is safe to do every time because Locate checks if it's the same request as before....
			self.data.Locate(x1,x2,y1,y2,self.losttype,self.nametype) #do somethin with self.selected here! *DONE*
		lx1,lx2,ly1,ly2=self.data.GetLocatedBounds()
		if UpdateRegion is not None:
			bx1,bx2,by1,by2=UpdateRegion.GetBounds()
		else:
			bx1,bx2,by1,by2=x1,x2,y1,y2 #TODO
		if TestOverlap(lx1,lx2,ly1,ly2,bx1,bx2,by1,by2):
			xy=self.data.GetLocatedXY() #numpy array
			qual=self.data.GetLocatedQuality()
			if not self.drawlabels:
				labels=[]
			else:
				labels=self.data.GetLocatedLabels()
			self.MapPanel.SetUpdateRegion(bx1,bx2,by1,by2)
			self.MapPanel.DrawPoints(xy,qual,labels,True,ps.textcolor,ps.font,wx.RED,ps.pointsize,ps.usebest,connect=False,regionfilter=True,shortnames=self.shortnames)
			self.MapPanel.ResetUpdateRegion()
			#print self.selected, self.data.GetLocatedXY(self.selected)
			xy=self.data.GetSelectedXY()
			if xy is not None:
				self.MapPanel.DrawSpecial(xy)
			if self.drawlabels:
				return 1,x1,x2,y1,y2
			else:
				x1,x2,y1,y2=Intersection(lx1,lx2,ly1,ly2,bx1,bx2,by1,by2)
				return 1,x1,x2,y1,y2
		else:
			return 0,-1,-1,-1,-1
	def DrawLines(self,UpdateRegion=None):
		ps=self.plotstyle
		x1,x2,y1,y2=self.MapPanel.GetBounds()
		lines=self.LineEngine.GetLines(x1,x2,y1,y2) #this is safe, because last fetch is cached....
		AffectedRegion=Box()
		for line in lines:
			self.MapPanel.DrawManyLines(line,region=UpdateRegion)
			lx1,ly1=line.min(axis=0)
			lx2,ly2=line.max(axis=0)
			AffectedRegion.Extend(lx1,lx2,ly1,ly2)
		if len(lines)>0:
			lx1,lx2,ly1,ly2=AffectedRegion.GetBounds()
			if TestOverlap(x1,x2,y1,y2,lx1,lx2,ly1,ly2):
				x1,x2,y1,y2=Intersection(x1,x2,y1,y2,lx1,lx2,ly1,ly2)
				return 1,x1,x2,y1,y2
		else:
			return 0,-1,-1,-1,-1
	
	def DrawPolygons(self,UpdateRegion=None):
		ps=self.plotstyle
		x1,x2,y1,y2=self.MapPanel.GetBounds()
		polygons=self.PolygonEngine.GetPolygons(x1,x2,y1,y2)
		plotlabels=len(polygons)<20 #True or False
		AffectedRegion=Box()
		for polygon in polygons:
			coords=polygon.GetPolyCoords()
			self.MapPanel.DrawPolygon(coords)
			lx1,ly1=coords.min(axis=0)
			lx2,ly2=coords.max(axis=0)
			AffectedRegion.Extend(lx1,lx2,ly1,ly2)
			if plotlabels:
				if len(polygons)>1:
					labelpos=polygon.GetLabelCoords()
					self.MapPanel.DrawText(polygon.GetLabel(),labelpos[0],labelpos[1],centertext=True,fontsize=16,region=UpdateRegion)
				else:
					self.MapPanel.DrawText(polygon.GetLabel(),centertext=True,fontsize=18,region=UpdateRegion)
		if len(polygons)>0:
			lx1,lx2,ly1,ly2=AffectedRegion.GetBounds()
			if TestOverlap(lx1,lx2,ly1,ly2,x1,x2,y1,y2): 
				if plotlabels:
					return 1,x1,x2,y1,y2
				else:
					x1,x2,y1,y2=Intersection(x1,lx2,ly1,ly2,x1,x2,y1,y2) 
					return 1,x1,x2,y1,y2
		return 0,-1,-1,-1,-1
			
	def DrawScaleBar(self,UpdateRegion=None):
		ps=self.plotstyle
		self.MapPanel.DrawMapScale(ps.scalefont)
		x1,x2,y1,y2=self.MapPanel.DrawMapScale(getextent=True)
		return 1,x1,x2,y1,y2
	
	
	def PrintPlot(self,dc=None,signature=""): #overrides base-class plot
		ps=self.plotstyle
		##Scale up fonts##
		##We are responsible for setting the right fonts, mappanel will take care of lines etc.
		pscale=self.MapPanel.GetPrinterScale()
		fs1=ps.font.GetPointSize()
		ps.font.SetPointSize(fs1*pscale)
		fs2=ps.scalefont.GetPointSize()
		ps.scalefont.SetPointSize(fs2*pscale)
		#end scale up fonts#
		oldmap=None
		if self.drawlayer[0] and self.mapservice=="disk":
			oldmap=self.map
			self.SetMap(plot=False)
			self.MapPanel.DrawMap(self.map,dc=dc) #kan vaere None
		if self.drawlayer[1] and self.LineEngine.IsInitialized():
			x1,x2,y1,y2=self.MapPanel.GetBounds()
			lines=self.LineEngine.GetLines(x1,x2,y1,y2)
			for line in lines:
				self.MapPanel.DrawManyLines(line,dc=dc)
		if self.HasPoints() and self.drawlayer[2]:
			xy=self.data.GetLocatedXY() #numpy array
			qual=self.data.GetLocatedQuality()
			if not self.drawlabels:
				labels=[]
			else:
				labels=self.data.GetLocatedLabels()
			self.MapPanel.DrawPoints(xy,qual,labels,True,ps.textcolor,ps.font,wx.RED,ps.pointsize,ps.usebest,connect=False,dc=dc)
			
		#opm. distrikt
		if self.drawlayer[3] and self.PolygonEngine.IsInitialized():
			x1,x2,y1,y2=self.MapPanel.GetBounds()
			polygons=self.PolygonEngine.GetPolygons(x1,x2,y1,y2)
			plotlabels=len(polygons)<20 #True or False
			for polygon in polygons:
				self.MapPanel.DrawPolygon(polygon.GetPolyCoords(),dc=dc)
				if plotlabels:
					if len(polygons)>1:
						labelpos=polygon.GetLabelCoords()
						self.MapPanel.DrawText(polygon.GetLabel(),labelpos[0],labelpos[1],centertext=True,fontsize=16*pscale,dc=dc)
					else:
						self.MapPanel.DrawText(polygon.GetLabel(),centertext=True,fontsize=18*pscale,dc=dc)
		if self.drawlayer[4]:
			self.MapPanel.DrawMapScale(ps.scalefont,dc=dc)
		#Print Text - if there is some#
		dc.DestroyClippingRegion()
		self.MapPanel.DrawBoundingBox(dc=dc)
		self.MapPanel.DrawSignature(signature,wx.Font(12*pscale,wx.SWISS,wx.NORMAL,wx.NORMAL),dc=dc)
		#Rescale Fonts back#
		ps.font.SetPointSize(fs1)
		ps.scalefont.SetPointSize(fs2)
		#Restore Map#
		if oldmap is not None:
			self.map=oldmap
	def SetLayers(self,layers): #only called on changes.. SetMap and point updates handled in plot...
		self.drawlayer=np.array(layers)
		valid_layers=np.array(self.GetValidLayers())
		if self.lastdraw is None:
			self.Plot()
		else:
			changes=(self.drawlayer!=self.lastdraw)
			nv=np.where(np.logical_and(changes,np.logical_not(valid_layers)))[0]
			if nv.size>0:
				lname=self.layernames[nv[0]]
				self.Log("Layer %s is not initialized - no plotting." %lname)
			changes&=valid_layers
			if changes.any():
				self.Plot()
	def GetLayerNames(self):
		return self.layernames
	def GetLayers(self):
		return self.drawlayer.tolist()
	def GetValidLayers(self):
		layers=[self.MapEngine.IsInitialized(),self.LineEngine.IsInitialized(),self.data.IsInitialized(),self.PolygonEngine.IsInitialized(),True]
		return layers
	def SetMapDirsUseState(self,states):
		self.MapEngine.SetMapDirsUseState(states)
		if self.drawlayer[0]:
			self.SetMap()
	def SetPlotStyle(self,plotstyle):
		self.plotstyle=plotstyle
	def GetPlotStyle(self):
		return self.plotstyle
	def ToggleLabels(self): #Overrides basclass method
		self.drawlabels=self.drawlabels^1  #reverse bit
		if self.HasPoints():
			self.Plot()
	def ToggleNameLength(self):
		self.shortnames=self.shortnames^1
		if self.HasPoints() and self.drawlabels and self.nametype==0:
			self.Plot()
	def HasPoints(self): #overrides parent class
		if self.data.IsInitialized() and self.data.NumbersLocated()>0 and self.drawlayer[self.pointlayer]:
			return True
		return False
	
def Norm(X):
	return np.sqrt((X**2).sum(axis=1))

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
class Box(object):
	def __init__(self):
		self.x1=None
		self.x2=None
		self.y1=None
		self.y2=None
	def Extend(self,x1,x2,y1,y2):
		if self.x1 is None:
			self.x1=x1
		else:
			self.x1=min(x1,self.x1)
		if self.x2 is None:
			self.x2=x2
		else:
			self.x2=max(x2,self.x2)
		if self.y1 is None:
			self.y1=y1
		else:
			self.y1=min(y1,self.y1)
		if self.y2 is None:
			self.y2=y2
		else:
			self.y2=max(y2,self.y2)
	def GetBounds(self):
		return self.x1,self.x2,self.y1,self.y2
	def Intersects(self,other):
		x1,x2,y1,y2=self.GetBounds()
		x_1,x_2,y_1,y_2=other.GetBounds()
		return TestOverlap(x1,x2,y1,y2,x_1,x_2,y_1,y_2)
def Intersection(x11,x12,y11,y12,x21,x22,y21,y22):
	x31=max(x11,x21)
	x32=min(x12,x22)
	y31=max(y11,y21)
	y32=min(y12,y22)
	return x31,x32,y31,y32
		
class MapData(object):
	def __init__(self,file,x1,x2,y1,y2):
		self.file=file
		self.x1=x1
		self.x2=x2
		self.y1=y1
		self.y2=y2
	def GetBitmap(self):
		return wx.Bitmap(self.file)
