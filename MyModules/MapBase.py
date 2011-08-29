import wx
import MapPanel
import GdalMaps
import GPS 
from DataClass3 import PointData
import numpy as np
#Implements a base class MapBase for handling maps via wms or GDALMaps and point data (sqlite) via DataClass2
#Direct user action and "mode"-handling should be wrapped on top of the MapBase class.
#Last edit: 06.05.2010, simlk - fonts in pointlabels, fixed nametype in TestPointUpdate, working towards implementing "projections"
#--MapBase--#
#Base class for handling maps. Most user interaction should be wrapped on top.
#Now slightly extended so that VisFix only implements a few extra things, like wms-maps, on top. Well a lot more in later versions...
#Modified so that this class always has a PointData class, i.e. self.data is never None! Fix this in methods checking if data is not None...
#TODO:
#Use internal dataclass state vars for TestPointUpdate - no more pointcenterx etc.....
#Fix selected point stuff - should perhaps be in DataClass
class MapBase(wx.Panel): #Base class for mapping and data access- no direct user interaction!
	def __init__(self,parent,winx=600,winy=600,dataclass=None,mapdirs=[],realparent=None):
		#STATE VARS nad DATA
		self.map=None
		#self.selected=-1 #not used anymore...
		if dataclass is None:
			self.data=PointData()
		else:
			self.data=dataclass   #Connecting to sqlite-db, getting point info
		self.usegps=False  #As standard dont use gps- use method to attach gps.
		self.gotvalidgpspos=False #standard. Vi venter til dette flag er sat med at plotte gps
		self.gpscentering=False
		self.gpsx=0
		self.gpsy=0
		self.pointcenterx=0 #for updating points in gps-mode
		self.pointcentery=0
		self.searchradius=6000
		self.pointradius=0  #radius of located points
		self.gps=GPS.DummyThread()  #can call kill method on the gps...Needed??
		self.MapEngine=GdalMaps.MapThread(self,mapdirs) #fetches maps from disk, using threads
		if self.MapEngine.IsInitialized():
			pixelsize=self.MapEngine.GetXPixelsize()
		else:
			pixelsize=1.0 #standard
		self.drawlabels=True  #Draw labels as standard
		self.shortnames=False #dont use short names as standard
		self.size=(winx,winy) #gem til et evt. reset... default window size
		self.x=0 #this is where we are!
		self.y=0 # -"-"-"-"
		if realparent is None:
			self.parent=parent
		else:
			self.parent=realparent
		self.textcolor="black" #color of pointnames
		self.textcolors=["black","yellow","green"]
		self.textcolorindex=0
		self.pointfont=None #set default font here
		self.losttype=0 # 0: valide 1: tabtgaaede - used when fetching points from sqlite-db
		self.nametype=0 #0: hsnavne 1:gmgi-navne 2:gps-navne - used when fetching points from sqlite-db
		self.newpoints=False
		#NOW init the wx.Panel		
		wx.Panel.__init__(self,parent) 
		self.MapPanel=MapPanel.MapPanel(self,(winx,winy),0,0,pixelsize) #Mappanel which contains all the graphics
		self.MapPanel.DisableDistance() #distances not used here
		#CUSTOM EVENTS
		self.Bind(MapPanel.EVT_MAPSIZE,self.OnMapSize)
		self.Bind(GdalMaps.EVT_MAP,self.SetMap)  #sendes af wms-klienten naar kort er hentet
		self.Bind(GPS.EVT_GPS,self.OnGPS) #nye koordinater fra gps-traaden
		self.sizer=wx.BoxSizer()
		self.sizer.Add(self.MapPanel,1,wx.EXPAND)
		self.SetSizer(self.sizer)
		self.SetBackgroundColour("lightgray")
		#On Close - do certain stuff
		self.Bind(wx.EVT_CLOSE,self.OnClose)
	def OnClose(self,event):
		if self.gps.isAlive(): #saa skal vi ikke logge data til dette vindue!
			self.gps.DetachWindow()
		self.MapEngine.kill()
		event.Skip()
	def SetTextColor(self,color):
		self.textcolor=color
		if self.HasPoints():
			self.Plot()
	def ToggleTextColor(self):
		self.textcolorindex=(self.textcolorindex+1)%3
		self.SetTextColor(self.textcolors[self.textcolorindex])
	def SetPointFont(self,font,color):
		self.pointfont=font
		self.textcolor=color
		if self.HasPoints():
			self.Plot()
	def SetLostType(self,type):
		if type in [0,1]:
			self.losttype=type
			self.GetPoints()
	def SetNameType(self,type):
		if type in [0,1,2]:
			self.nametype=type
			self.GetPoints()
	def ToggleNames(self):
		self.nametype=(self.nametype+1)%3
		self.GetPoints()
	def GetHeightInfo(self):
		if self.data.selected is not None:
			h,info=self.data.GetSelectedZ()
			if h is None:
				h="ikke koteret."
			else:
				h="%.3fm" %h
			text=u"Punkt: %s   H\u00F8jde: %s" %(self.data.GetSelectedLabel(),h)
			if info is not None:
				text+=" "+info
			return text
		return ""
	def GetLocatedInfo(self):
		return self.data.GetSelectedInfo()
	def GetLocatedLabel(self):
		return self.data.GetSelectedLabel()
	def GetLocatedSkitse(self):
		return self.data.GetSelectedSkitse()
	def HasPoints(self):
		if self.data.IsInitialized() and self.data.NumbersLocated()>0:
			return True
		return False
	def ClosestLocatedPoint(self,x,y,coords="screen"): #in screen coords
		if coords=="screen":
			x,y=self.MapPanel.UserCoords(x,y)
		D,j=self.data.ClosestLocatedPoint(x,y)
		if coords=="screen":
			D=D/float(self.MapPanel.GetPixelSize())
		return D,j
	def Log(self,text):
		try:
			self.parent.Log(text)
		except:
			pass
	def RegisterLeftClick(self,fct):
		self.MapPanel.canvas.Bind(wx.EVT_LEFT_DOWN,fct)
	def RegisterRightClick(self,fct):
		self.MapPanel.canvas.Bind(wx.EVT_RIGHT_DOWN,fct)
	def ResetPlot(self):
		pixelsize=self.MapEngine.GetXPixelsize()
		if pixelsize==0:
			pixelsize=2
		self.MapPanel.SetPixelSize(pixelsize)
		self.MapPanel.SetCenter(self.x,self.y)
		self.SetMap()
	
	def OnMapSize(self,event): #called from the mappanel....
		self.SetMap()
	def ClearPoints(self):
		if self.data is not None:
			self.data.Clear()
		#self.selected=-1
		self.Plot()
	def GetPoints(self,plot=True,small=False): #ONLY-called from user event... e.g changed nametype
		if self.data is not None and self.data.IsInitialized():
			if small:
				range=self.searchradius
				cx,cy=self.MapPanel.GetCenter()
				x1=cx-range
				x2=cx+range
				y1=cy-range
				y2=cy+range
			else:
				x1,x2,y1,y2=self.MapPanel.GetBounds()
			self.data.Locate(x1,x2,y1,y2,self.losttype,self.nametype)  #if slow should be implemented as a thread...
			self.Log("Hentede %i %s-punkter. " %(self.data.NumbersLocated(),self.data.GetNameType(self.nametype)))
			#self.selected=-1
			self.newpoints=True #signal that we have update points - used in derived classes
			if plot:
				self.Plot()
	def TestPointUpdate(self,force=False): #force flag to force a point update with searchradius
		if self.data.IsInitialized():
			xrange=self.MapPanel.GetXRange()
			yrange=self.MapPanel.GetYRange()
			if (self.x-self.pointcenterx)>self.pointradius-500 or abs(self.y-self.pointcentery)>self.pointradius-500 or force:
				#print "updating"
				range=self.searchradius
				self.data.Locate(self.x-range,self.x+range,self.y-range,self.y+range,self.losttype,self.nametype)  #if slow should be implemented as a thread...
				#self.selected=-1
				self.newpoints=True #signal that we have updated points - used in derived classes
				self.Log("Hentede %i punkter." %self.data.NumbersLocated())
				self.pointcenterx=self.x
				self.pointcentery=self.y
				self.pointradius=range
				return True
			else:
				return False
	def SetGpsCentering(self,on=False): #only call this method with True self.gps is alive....
		self.gpscentering=on
		if on:
			x, y,dop=self.gps.GetPos()
			if dop<30:
				self.x,self.y=x,y
				self.gpsx,self.gpsy=x,y
				self.gotvalidgpspos=True
				self.Log("GPS-position: (%.1f,%.1f)" %(self.x,self.y))
				self.TestPointUpdate()
			else:
				self.Log(u"GPS-data ikke valide. Venter p\u00E5 bedre position...")
				self.gotvalidgpspos=False
				return
			if self.MapPanel.TestBoundary(self.x,self.y,0.3):
				self.SetMap()
			else:
				self.Plot()
	def OnGPS(self,event):
		doplot=event.plot
		if doplot:
			self.gpsx=event.x
			self.gpsy=event.y
			self.gotvalidgpspos=True
			if self.gpscentering:
				self.x=event.x  #bilposition fra gps'en
				self.y=event.y
				if self.MapPanel.TestBoundary(self.x,self.y,0.2):
					self.TestPointUpdate()
					self.SetMap()
				else:
					update=self.TestPointUpdate()
					
					if update:
						self.Plot()
					else:
						x,y,w,h=self.MapPanel.GetGPSClippingRegion(self.gpsx,self.gpsy)
						s1,s2=self.MapPanel.GetCanvasSize()
						if (0<=x<s1 or 0<x+w<=s1) and (0<=y<s2 or 0<y+h<=s2): #if clipping region on screen!
							self.MapPanel.DrawGPS(self.x,self.y)
							self.MapPanel.DrawScreen(x,y,w,h)
							
		dop=event.dop
		speed=event.speed
		try:
			self.parent.SetStatusText("GPS-dop: %.1f,  hastighed: %.1f km/t" %(dop,speed))
		except:
			pass
	def ZoomIn(self): #centers around gpspos, when using gps-centering
		if not self.MapEngine.isRunning():
			if self.gpscentering and self.gotvalidgpspos: #if we have navigated away in the meantime...
				self.x=self.gpsx
				self.y=self.gpsy
			self.MapPanel.Zoom(self.x,self.y,0.5)
			self.SetMap()
	def ZoomOut(self):
		if not self.MapEngine.isRunning():
			self.MapPanel.Zoom(self.x,self.y,2)
			self.SetMap()
	def GoTo(self,x,y):
		self.x=x
		self.y=y
		self.SetMap()
	def SetMap(self,event=None):#ellers kan nuvaerende kort bruges... og det burde eksistere!
		doplot=False 
		self.MapPanel.SetCenter(self.x,self.y)
		if event is None and not self.MapEngine.isRunning():
				if self.MapEngine.IsInitialized():
					x1,x2,y1,y2=self.MapPanel.GetBounds()
					size=self.MapPanel.GetCanvasSize()
					self.MapEngine.StartThread(x1,x2,y1,y2,size[0],size[1])
				else:	
					self.Log("Definer kortmappe(r) i ini-fil.")
		elif isinstance(event,GdalMaps.MapEvent):
			doplot=True
			size=self.MapPanel.GetCanvasSize()
			self.map,x1,x2,y1,y2=self.MapEngine.FetchMap()
			size=self.MapPanel.GetCanvasSize()
			w=self.map.GetWidth()
			h=self.map.GetHeight()
			if size[0]!=w or size[1]!=h:
				self.MapPanel.SetCanvasSize((w,h))
				self.sizer.Layout()
			self.MapPanel.SetBoundary(x1,x2,y1,y2)
			self.Log("E: %.0f m til %0.f m, N: %.0f m til %.0f m" %(x1,x2,y1,y2))
		if doplot:
			self.Plot()
	def Plot(self,x=None,y=None,w=0,h=0):
		self.MapPanel.DrawMap(self.map) #kan vaere None
		if self.HasPoints():
			xy=self.data.GetLocatedXY() #numpy array
			qual=self.data.GetLocatedQuality()
			if not self.drawlabels:
				labels=[]
			else:
				labels=self.data.GetLocatedLabels()
			self.MapPanel.DrawPoints(xy,qual,labels,testlabeldensity=True,textcolor=self.textcolor,font=self.pointfont,shortnames=self.shortnames)
			xy=self.data.GetSelectedXY()
			if xy is not None:
				self.MapPanel.DrawSpecial(xy)
		self.MapPanel.DrawScreen(x,y,w,h)
	def DrawSpecialPoint(self,xy,color="red",pointsize=None):
		xs,ys,xg,yg=self.MapPanel.DrawSpecial(xy,color=color,pointsize=pointsize)
		self.MapPanel.DrawScreen(xs,ys,xg,yg)
	def UnSelect(self):
		if self.data.GetSelected() is not None:
			q=self.data.GetSelectedQuality()
			if q==0:
				color="red"
			else:
				color="green"
			self.DrawSpecialPoint(self.data.GetSelectedXY(),color=color)
		self.data.UnSelect()
	def Select(self,j):
		self.data.Select(j)
		if self.data.GetSelected() is not None:
			self.DrawSpecialPoint(self.data.GetSelectedXY(),color="blue")
	def AttachGPS(self,gps):
		self.gps=gps
		self.gotvalidgpspos=False 
		self.gps.DefineWindow(self)
		if self.gps.isAlive():
			self.usegps=True
			
	def DetachGPS(self): #bruges hvis gps-traaden stadig koerer videre i hovedprogrammet, men ikka skal logge til dette vindue
		if self.gps.isAlive():
			self.gps.DetachWindow()
		self.gotvalidgpspos=False 
		self.gps=GPS.DummyThread()
		self.usegps=False
		self.gpscentering=False
	
	def DefineData(self,dataclass):
		if self.data.IsInitialized():
			self.data.Disconnect()
		self.data=dataclass
	def HasData(self):
		if self.data is None or not self.data.IsInitialized():
			return False
		else:
			return True
	def SetInitialCenter(self,realcenter=False):
		self.x,self.y=575160,6224150 #default, aarhus if coords is utm32
		if self.MapEngine.IsInitialized():
			x,y=self.MapEngine.MAPDIRS[0].GetCenter()
			if (not(500000<x<750000 and 6150000<y<6300000)) or realcenter: #then it looks like where not in dk,utm32
				self.x,self.y=x,y
			
	def SetCenter(self,x,y,R=None):
		self.x,self.y=x,y
		if R!=None:
			x1,x2=x-R,x+R
			y1,y2=y-R,y+R
			self.MapPanel.SetBoundary(x1,x2,y1,y2)
		self.SetMap()
	def SaveFile(self,fname):
		self.MapPanel.SaveFile(fname)
	def ToggleLabels(self):
		self.drawlabels=self.drawlabels^1  #reverse bit
		self.Plot()
	def ToggleNameLength(self):
		self.shortnames=self.shortnames^1
		if self.drawlabels:
			self.Plot()