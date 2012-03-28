import os
import sys
basedir=os.getcwd()+"\\"
try:
	sys.frozen   #will pass if running py2exe executable 
except:
	mmdir=basedir+"mcontent\\"
else:
	mmdir=sys.prefix+"\\mcontent\\"
import wx
import MyModules.GUIclasses2 as GUI
import MyModules.ExtractKMS as Extract
import MyModules.GPS as GPS
import MyModules.DataClass3 as Data
from Funktioner import RemRem
import numpy as np
import MapBrowser2 as MapBrowser
import Kortforsyningen
import wx.lib.agw.foldpanelbar as fpb #foldpanelbar
import wx.lib.newevent
import time
(StdoutEvent,EVT_STDOUT) = wx.lib.newevent.NewEvent()
OGR_VECTOR_FORMATS="*.shp;*.tab;*.gml"
#Last update/bugfix  january 11, simlk - major update on layer stuff - minor bugfixes in wms errors
#Bugfix/update 25.03.11 - fixed "selected point" stuff. Now managed by DataClass - should be more clear, since this class knows all about the points....
#VisFix simplified to be ONLY a point data, and map-data viewer. No observations anymore.
Program="VisFix ver. beta 2.3"
aboutstr=u"""
Standalone-program til visualisering af h\u00F8jdefikspunkter.
Bruger GDAL til kortvisning. Bugs rettes til simlk@kms.dk
"""
class LayerBox(wx.CheckListBox):
	def __init__(self,parent,choices,size):
		self.layers=choices
		wx.CheckListBox.__init__(self,parent,choices=choices,size=size)
	def GetLayers(self):
		layers=[]
		for i in range(0,len(self.layers)):
			layers.append(self.IsChecked(i))
		return layers
	def CheckLayerByName(self,name):
		i=0
		for layer in self.layers:
			if layer.lower().find(name)!=-1:
				self.Check(i)
				break
			i+=1
	def SetState(self,states):
		i=0
		for state in states:
			self.Check(i,state)
			i+=1
class MapDirBox(wx.CheckListBox):
	def __init__(self,parent,dirs,size):
		self.mapdirs=dirs
		names=[os.path.basename(dir) for dir in dirs]
		wx.CheckListBox.__init__(self,parent,choices=names,size=size)
		for i in range(0,len(names)):
			self.Check(i)
	def GetMapDirs(self):
		dirs=[]
		for i in range(0,len(self.mapdirs)):
			dirs.append(self.IsChecked(i))
		return dirs
	def AddMapDir(self,dir):
		self.mapdirs.append(dir)
		name=os.path.basename(dir)
		self.InsertItems([name],len(self.mapdirs)-1)
		self.Check(len(self.mapdirs)-1)
class LeftPanel(wx.Panel):
	def __init__(self,parent,layers,mapdirs):
		wx.Panel.__init__(self,parent)
		y=wx.GetDisplaySize().y
		text1=wx.StaticText(self,label="Lag:")
		text2=wx.StaticText(self,label="Kortmapper:")
		if y<1000:
			ysize=100
		else:
			ysize=-1
		self.layers=LayerBox(self,choices=layers,size=(-1,ysize))
		self.showlabels=wx.CheckBox(self,label="Vis punktnavne")
		self.showlabels.SetValue(True)
		self.shortnames=wx.CheckBox(self,label="Korte navne")
		self.shortnames.SetValue(False) #must be false to match MapBase default attr.
		self.addbutton=GUI.MyButton(self,u"Tilf\u00F8j kort",10)
		losttypes=["Vis kun valide",u"Vis kun tabtg\u00E5ede"]
		self.lostbox=wx.RadioBox(self,label="Validitet",choices=losttypes,style=wx.RA_SPECIFY_COLS,majorDimension=1)
		nametypes=["HS-navne","G.M./G.I.-navne","GPS-navne"]
		self.namebox=wx.RadioBox(self,label="Punkttype",choices=nametypes,style=wx.RA_SPECIFY_COLS,majorDimension=1)
		if y<1000:
			ysize=60
		else:
			ysize=-1
		self.mapdirbox=MapDirBox(self,mapdirs,size=(-1,ysize))
		self.maptypebox=wx.RadioBox(self,label="Korttype",choices=["Disk","WMS"],style=wx.RA_SPECIFY_COLS,majorDimension=1)
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(text1,0,wx.ALL,2)
		self.sizer.Add(self.layers,0,wx.ALL,2)
		self.sizer.Add(self.showlabels,0,wx.ALL,5)
		self.sizer.Add(self.shortnames,0,wx.ALL,5)
		self.sizer.Add(self.lostbox,0,wx.ALL,2)
		self.sizer.Add(self.namebox,0,wx.ALL,2)
		self.sizer.Add(text2,0,wx.ALL,2)
		self.sizer.Add(self.mapdirbox,0,wx.ALL,2)
		self.sizer.Add(self.addbutton,0,wx.ALL,2)
		self.sizer.Add(self.maptypebox,0,wx.ALL,2)
		#self.sizer.Add(self.layers,1,wx.ALL,2)
		self.SetSizerAndFit(self.sizer)
		#self.sizer.FitInside(self)
class ZoomSlider(wx.Slider):
	def __init__(self,parent):
		self.minval=0
		self.maxval=1000
		self.maxpixelsize=500.0
		self.minpixelsize=0.5
		ysize=60
		y=wx.GetDisplaySize().y
		if y<1000:
			ysize=40
		wx.Slider.__init__(self,parent,style=wx.SL_RIGHT,minValue=self.minval,maxValue=self.maxval,size=(-1,ysize))
	def SetPixelSize(self,pixelsize):
		self.SetValue(self.PixelSize2SliderValue(pixelsize))
	def GetPixelSize(self):
		return self.SliderValue2PixelSize(self.GetValue())
	def PixelSize2SliderValue(self,pixelsize):
		ps=min(self.maxpixelsize,pixelsize)
		return int((max(0,ps-self.minpixelsize)/self.maxpixelsize)**(0.5)*self.maxval)
	def SliderValue2PixelSize(self,val):
		return max(((val/float(self.maxval))**2)*self.maxpixelsize,self.minpixelsize)
	def SetMinPixelSize(self,val):
		self.minpixelsize=float(val)
	def SetMaxPixelSize(self,val):
		self.maxpixelsize=float(val)
class ZoomPanel(wx.Panel):
	def __init__(self,parent,label="Zoom"):
		y=wx.GetDisplaySize().y
		ysize=70
		if y<1000:
			ysize=50
		wx.Panel.__init__(self,parent,size=(100,ysize))
		box=wx.StaticBox(self,label=label)
		boxsizer=wx.StaticBoxSizer(box)
		self.sizer=wx.BoxSizer()
		self.slider=ZoomSlider(self)
		boxsizer.Add(self.slider,0,wx.CENTER)
		self.sizer.Add(boxsizer)
		self.SetSizerAndFit(self.sizer)

class BottomPanel(wx.Panel):
	def __init__(self,parent):
		wx.Panel.__init__(self,parent)
		self.info=GUI.FileLikeTextCtrl(self,size=(550,100),style=wx.TE_READONLY|wx.TE_MULTILINE)
		self.info.SetFont(wx.Font(12,wx.SWISS,wx.NORMAL,wx.BOLD))# info field for dispalying text messages.
		modes=["Naviger","Punkt-mode","Digitalisering"]
		self.modebox=wx.RadioBox(self,label="Venstreklik-tilstand",choices=modes,style=wx.RA_SPECIFY_COLS,majorDimension=2)
		self.gpsbutton=wx.CheckBox(self,label="GPS-centrering")
		zoompanel=ZoomPanel(self)
		self.zoomslider=zoompanel.slider
		self.sizer=wx.BoxSizer(wx.HORIZONTAL)
		self.sizer.Add(zoompanel,0,wx.ALL,5)
		self.sizer.Add(self.info,4,wx.EXPAND|wx.ALL,5)
		self.sizer.Add(self.modebox,1,wx.EXPAND|wx.ALL,5)
		self.sizer.Add(self.gpsbutton,1,wx.ALL|wx.CENTER,5)
		self.SetSizerAndFit(self.sizer)
		
class RedirectStdout(object):
	def __init__(self,wxwindow):
		self.window=wxwindow
	def write(self,text):
		event=StdoutEvent(text=text)
		wx.PostEvent(self.window,event)

#GUI user interaction class which wraps the MapBase class 
#modes: 'panmode', 'distancemode' or 'pointmode'.. But this need not be "or"
#always has a gps, which can be a dummy thread.
class MainFrame(wx.Frame):
	def __init__(self,parent,title,Ini):
		self.Ini=Ini
		wx.Frame.__init__(self,parent,title=title)
		self.statusbar=self.CreateStatusBar()
		filemenu= wx.Menu()
		self.mapmenu=wx.Menu()
		vismenu=wx.Menu()
		self.punktmenu=wx.Menu()
		#DEMmenu=wx.Menu()
		self.about=filemenu.Append(wx.ID_ANY, "&About"," Om programmet")
		filemenu.AppendSeparator()
		pagesetup=filemenu.Append(wx.ID_ANY,u"Papirst\u00F8rrelse",u"Definer papir.")
		preview=filemenu.Append(wx.ID_ANY,"Preview","Preview udprint af plot.")
		printout=filemenu.Append(wx.ID_ANY,"Udskriv","Udskriv plot til printer.")
		filemenu.AppendSeparator()
		self.exit=filemenu.Append(wx.ID_ANY,"E&xit"," Afslut programmet")
		self.GPSstart=self.mapmenu.Append(wx.ID_ANY,"Tilslut GPS",u"Fors\u00F8g at tilutte USB-GPS via virtuel COM-port.")
		self.GPSstop=self.mapmenu.Append(wx.ID_ANY,"Stop GPS","Stopper GPS-enhed")
		#self.DefinerKort=self.mapmenu.Append(wx.ID_ANY,"Definer kortmappe","Tilslut en ny mappe med raster kort.")
		AddMapdir=self.mapmenu.Append(wx.ID_ANY,u"Tilf\u00F8j kortmappe",u"Tilf\u00F8j en kortmappe og for\u00F8g zoom-mulighederne!")
		#RemoveMapdir=self.mapmenu.Append(wx.ID_ANY,u"Fjern kortmappe","Afbryd forbindelsen til en kortmappe.")
		MakeIndex=self.mapmenu.Append(wx.ID_ANY,u"Indekser en kortmappe","Indekser en kortmappe for at kunne forbedre zoom-muligheder.")
		SetLineFile=self.mapmenu.Append(wx.ID_ANY,"Definer kystliniefil","Definerer kyst- (eller anden) linie udfra en fil i et standard vektorformat.") 
		SetPolygonFile=self.mapmenu.Append(wx.ID_ANY,u"Definer opm\u00E5lingsdistriktfil",u"Definer distrikter udfra en fil i et standard vektorformat.")
		GoToWMS=self.mapmenu.Append(wx.ID_ANY,"Kort via WMS","Definer og hent kort via kortforsyningen.")
		GoToDiskMaps=self.mapmenu.Append(wx.ID_ANY,"Kort fra disk","Vis kort fra den aktuelle kortmappe.")
		SetCenter=self.mapmenu.Append(wx.ID_ANY,u"G\u00E5 til (x,y)",u"V\u00E6lg kortudsnit.")
		self.DefinerData=self.punktmenu.Append(wx.ID_ANY,"Definer datafil",u"V\u00E6lg en sqlite-datfil.")
		MakeData=self.punktmenu.Append(wx.ID_ANY,"Dan ny datafil","Danner en ny tom sqlite datafil, som kan tilsluttes og opdateres.")
		self.GetInfoItem=self.punktmenu.Append(wx.ID_ANY,"Hent punktinformation","Hent skite og beskrivelse for et punktnavn.")
		GetStats=self.punktmenu.Append(wx.ID_ANY,"Statistik for datafil","Se information om indhold af sqlite-datafile.")
		DigitalizeItem=self.punktmenu.Append(wx.ID_ANY,"Digitaliser punkt(er)",u"Digitaliser punktkoordinater ved at klikke p\u00E5 kortet.")
		#Update datafile- submenu
		submenu=wx.Menu()
		AddIDs=submenu.Append(wx.ID_ANY,u"Tilf\u00F8j identiteter til datafil",u"Tilf\u00F8jer identiteter til alias tabellen udfra en fil med identiteter fra refgeo.")
		UpdateDsc=submenu.Append(wx.ID_ANY,"Opdater beskrivelser",u"Opdater datafilen udfra en fil med beskrivelser fra datbasen.")
		UpdateZs=submenu.Append(wx.ID_ANY,"Opdater koter","Opdater datafilen udfra en fil med koter fra refgeo.")
		UpdateKanKo=submenu.Append(wx.ID_ANY,"Opdater (x,y)-lokationer",u"Opdater lokationer vha. udtr\u00E6k fra refgeo.")
		UpdateSkitse=submenu.Append(wx.ID_ANY,"Opdater skitser","Opdater datfilen udfra en mappe med skitser.")
		MarkAsGeo=submenu.Append(wx.ID_ANY,"Marker som geometrisk",u"Marker punkter som m\u00E5lt geometrisk udfra en lokationsfil.")
		MarkAsLost=submenu.Append(wx.ID_ANY,u"Marker som tabtg\u00E5et",u"Marker punkter som tabtg\u00E5et udfra en identitetsfil.")
		self.punktmenu.AppendMenu(wx.ID_ANY,"Opdater datafil",submenu)
		#Visningsmenu
		self.ToggleNavKort=vismenu.Append(wx.ID_ANY,"Vis/skjul navigationskort","Naviger rundt via minimap.")
		self.ToggleToolBar=vismenu.Append(wx.ID_ANY,"Vis/skjul toolbar","Vis/skjul knap-toolbar.")
		SetStyle=vismenu.Append(wx.ID_ANY,"Definer plot-stil")
		#Creating the menubar.
		menuBar = wx.MenuBar()
		menuBar.Append(filemenu,"&Fil")
		menuBar.Append(self.mapmenu,"&GPS og kort")
		menuBar.Append(vismenu,"Vis")
		menuBar.Append(self.punktmenu,"&Punktdata")
		self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
		#Logging#
		self.Bind(GPS.EVT_LOG,self.OnEvtLog)
		#Appeareance#
		self.SetBackgroundColour("lightgray")
		self.SetIcon(wx.Icon(mmdir+'icon.bmp', wx.BITMAP_TYPE_ICO))
		#Menu-binding
		self.Bind(wx.EVT_MENU,self.OnToggleMinimap,self.ToggleNavKort)
		self.Bind(wx.EVT_MENU,self.OnToggleToolbar,self.ToggleToolBar)
		self.Bind(wx.EVT_MENU,self.OnGPSstart,self.GPSstart)
		self.Bind(wx.EVT_MENU,self.OnGPSstop,self.GPSstop)
		self.Bind(wx.EVT_MENU,self.OnSetLineFile,SetLineFile)
		self.Bind(wx.EVT_MENU,self.OnSetPolygonFile,SetPolygonFile)
		self.Bind(wx.EVT_MENU,self.OnAddMapDir,AddMapdir)
		#self.Bind(wx.EVT_MENU,self.OnRemoveMapdir,RemoveMapdir)
		self.Bind(wx.EVT_MENU,self.OnMakeIndex,MakeIndex)
		self.Bind(wx.EVT_MENU,self.OnExit,self.exit)
		self.Bind(wx.EVT_MENU,self.OnAbout,self.about)
		self.Bind(wx.EVT_MENU,self.OnPreview,preview)
		self.Bind(wx.EVT_MENU,self.OnPrintout,printout)
		self.Bind(wx.EVT_MENU,self.OnPageSetup,pagesetup)
		self.Bind(wx.EVT_MENU,self.OnDefinerData,self.DefinerData)
		self.Bind(wx.EVT_MENU,self.OnDisplayStats,GetStats)
		self.Bind(wx.EVT_MENU,self.OnMakeData,MakeData)
		self.Bind(wx.EVT_MENU,self.OnAddIDs,AddIDs)
		self.Bind(wx.EVT_MENU,self.OnUpdateDsc,UpdateDsc)
		self.Bind(wx.EVT_MENU,self.OnUpdateZs,UpdateZs)
		self.Bind(wx.EVT_MENU,self.OnUpdateKanKo,UpdateKanKo)
		self.Bind(wx.EVT_MENU,self.OnUpdateSkitse,UpdateSkitse)
		self.Bind(wx.EVT_MENU,self.OnMarkAsGeo,MarkAsGeo)
		self.Bind(wx.EVT_MENU,self.OnMarkAsLost,MarkAsLost)
		self.Bind(wx.EVT_MENU,self.OnGetInfo,self.GetInfoItem)
		self.Bind(wx.EVT_MENU,self.OnDigitalize,DigitalizeItem)
		self.Bind(wx.EVT_MENU,self.OnGoToWMS,GoToWMS)
		self.Bind(wx.EVT_MENU,self.OnGoToDiskMaps,GoToDiskMaps)
		self.Bind(wx.EVT_MENU,self.OnSetCenter,SetCenter)
		self.Bind(wx.EVT_MENU,self.OnSetStyle,SetStyle)
		self.Bind(GPS.EVT_KILL_GPS,self.OnGPSkill)  #hvis gps'en sender et fejl-signal!
		#Define dummy gps:
		self.gps=GPS.DummyThread()
		#Init from prev PointPlot
		#STATE VARS nad DATA
		self.panmode=True #when panning map
		#self.distancemode=False #when measuring distances
		self.pointmode=False #for clicking on points, getting info or coordinates
		#self.digitizemode=False #use when digitalizing coordinates to file
		#self.drawmode=False #used when drawing user defined text on top of map
		self.DigitalizeWindow=GUI.DummyWindow()
		#self.DrawWindow=GUI.DummyWindow()
		self.clickrange=20 #20 pixels-clickrange.
		############################
		##Setting up the panel at the bottom of the frame
		###########################
		bottompanel=BottomPanel(self)
		self.modebox=bottompanel.modebox
		self.info=bottompanel.info
		self.gpsbutton=bottompanel.gpsbutton
		self.gpsbutton.Enable(False) #gps not started yet
		self.zoomslider=bottompanel.zoomslider
		self.zoomslider.Bind(wx.EVT_SCROLL_THUMBRELEASE,self.OnZoomSlider)
		self.modebox.Bind(wx.EVT_RADIOBOX,self.OnModeBox)
		self.gpsbutton.Bind(wx.EVT_CHECKBOX,self.OnGpsButton)
		#########################
		##Define a splitter window - map to the right
		#########################
		splitter=wx.SplitterWindow(self,style=wx.SP_LIVE_UPDATE|wx.SP_3D )
		
		####################
		##Set up the MapWindow
		####################
		p2 = wx.Panel(splitter)
		p2.SetBackgroundColour("sky blue")
		self.Map=MapBrowser.Map(p2,900,700,Data.PointData(Ini['datafile']),Ini['mapdirs'],Ini['districtfile'],Ini['coastline'],self)
		p2.sizer=wx.BoxSizer()
		p2.sizer.Add(self.Map,1,wx.EXPAND)
		p2.SetSizer(p2.sizer)
		self.Map.RegisterLeftClick(self.OnLeftClick)
		self.Map.RegisterRightClick(self.OnRightClick)
		self.Map.DefineMinimap(Ini['minimap'])
		self.Map.SetCenterBasedOnData()
		#set up max and min zooms#
		self.UpdateZoomSlider()
		################
		##Set up the left tool panel
		################
		p1 = wx.Panel(splitter,style=wx.BORDER_SUNKEN)
		p1.SetBackgroundColour("wheat")
		dirs=self.Map.MapEngine.GetMapDirs()
		dirnames=[dir.GetName() for dir in dirs]
		leftpanel=LeftPanel(p1,self.Map.GetLayerNames(),dirnames)
		self.layerbox=leftpanel.layers
		self.layerbox.SetState(self.Map.GetLayers())
		self.lostbox=leftpanel.lostbox
		self.namebox=leftpanel.namebox
		self.mapdirbox=leftpanel.mapdirbox
		self.maptypebox=leftpanel.maptypebox
		self.layerbox.Bind(wx.EVT_CHECKLISTBOX,self.OnLayers) # different approach now
		self.lostbox.Bind(wx.EVT_RADIOBOX,self.OnLostType)
		self.namebox.Bind(wx.EVT_RADIOBOX,self.OnNameType)
		self.mapdirbox.Bind(wx.EVT_CHECKLISTBOX,self.OnMapDirs)
		leftpanel.showlabels.Bind(wx.EVT_CHECKBOX,self.OnToggleLabels)
		leftpanel.shortnames.Bind(wx.EVT_CHECKBOX,self.OnToggleNameLength)
		leftpanel.addbutton.Bind(wx.EVT_BUTTON,self.OnAddMapDir)
		self.maptypebox.Bind(wx.EVT_RADIOBOX,self.OnMapType)
		#####################
		## split the window            ##
		splitter.SetMinimumPaneSize(10)
		splitter.SplitVertically(p1, p2, 140)
		#SETTING UP THE FLOATING BUTTONBOX - could be done as a separate class
		self.container=wx.MiniFrame(self,style=wx.DEFAULT_FRAME_STYLE )
		self.container.sizer=wx.BoxSizer(wx.VERTICAL)
		self.container.Bind(wx.EVT_CLOSE,self.OnCloseToolbar)
		self.buttonpanel=wx.Panel(self.container)
		self.knap1=GUI.MyButton(self.buttonpanel,"SKJUL",10)
		self.knap2=GUI.MyButton(self.buttonpanel,"ZOOM IND",10)
		self.knap3=GUI.MyButton(self.buttonpanel,"ZOOM UD",10)
		#self.knap4=GUI.MyButton(self.buttonpanel,"OPM.DISTRIKT TIL/FRA",10)
		#self.knap5=GUI.MyButton(self.buttonpanel,"PUNKTER",10)
		#self.knap6=GUI.MyButton(self.buttonpanel,"PKT.NAVNE TIL/FRA",10)
		#self.knap7=GUI.MyButton(self.buttonpanel,"SLET PUNKTER",10)
		self.knap8=GUI.MyButton(self.buttonpanel,u"RESET ST\u00D8RRELSE",10)
		self.knap9=GUI.MyButton(self.buttonpanel,"GEM FIL",10)
		self.knap10=GUI.MyButton(self.buttonpanel,"STOP WMS",10)
		self.knap11=GUI.MyButton(self.buttonpanel,"VIS NAV.KORT",10)
		self.buttonpanel.topsizer=wx.BoxSizer(wx.HORIZONTAL)
		self.buttonpanel.bottomsizer=wx.BoxSizer(wx.HORIZONTAL)
		self.buttonpanel.topsizer.Add(self.knap1,0,wx.ALL,2)
		self.buttonpanel.topsizer.Add(self.knap2,0,wx.ALL,2)
		self.buttonpanel.topsizer.Add(self.knap3,0,wx.ALL,2)
		#self.buttonpanel.topsizer.Add(self.knap5,0,wx.ALL,2)
		#self.buttonpanel.topsizer.Add(self.knap6,0,wx.ALL,2)
		#self.buttonpanel.topsizer.Add(self.knap7,0,wx.ALL,2)
		self.buttonpanel.topsizer.Add(self.knap10,0,wx.ALL,2)
		self.buttonpanel.bottomsizer=wx.BoxSizer(wx.HORIZONTAL)
		self.buttonpanel.bottomsizer.Add(self.knap8,0,wx.ALL,2)
		self.buttonpanel.bottomsizer.Add(self.knap9,0,wx.ALL,2)
		self.buttonpanel.bottomsizer.Add(self.knap11,0,wx.ALL,2)
		#self.buttonpanel.bottomsizer.Add(self.knap4,0,wx.ALL,2)
		self.buttonpanel.sizer=wx.BoxSizer(wx.VERTICAL)
		self.buttonpanel.sizer.Add(self.buttonpanel.topsizer,0,wx.ALL|wx.LEFT)
		self.buttonpanel.sizer.Add(self.buttonpanel.bottomsizer,0,wx.ALL|wx.LEFT)
		self.buttonpanel.SetSizerAndFit(self.buttonpanel.sizer)
		self.knap2.Bind(wx.EVT_BUTTON,self.OnZoomIn)
		self.knap3.Bind(wx.EVT_BUTTON,self.OnZoomOut)
		#self.knap4.Bind(wx.EVT_BUTTON,self.OnTogglePolygons)
		self.knap1.Bind(wx.EVT_BUTTON,self.OnToggleToolbar)
		#self.knap6.Bind(wx.EVT_BUTTON,self.OnToggleLabels)
		self.knap8.Bind(wx.EVT_BUTTON,self.OnResetPlot)
		#self.knap7.Bind(wx.EVT_BUTTON,self.OnClearPoints)
		self.knap9.Bind(wx.EVT_BUTTON,self.OnSaveFile)
		self.knap10.Bind(wx.EVT_BUTTON,self.OnKillWMS)
		self.knap11.Bind(wx.EVT_BUTTON,self.OnToggleMinimap)
		#self.knap5.Bind(wx.EVT_BUTTON,self.OnGetPoints)
		#SETTING UP THE MINIMENU
		self.MenuKnap2=wx.NewId()
		self.MenuKnap3=wx.NewId()
		#self.MenuKnap4=wx.NewId()
		#self.MenuKnap5=wx.NewId()
		#self.MenuKnap6=wx.NewId()
		#self.MenuKnap7=wx.NewId()
		self.MenuKnap8=wx.NewId()
		self.MenuKnap9=wx.NewId()
		self.MenuKnap10=wx.NewId()
		self.MenuKnap11=wx.NewId()
		#self.MenuKnap12=wx.NewId()
		self.MenuKnap13=wx.NewId()
		self.MenuKnap14=wx.NewId()
		self.Bind(wx.EVT_MENU,self.OnZoomIn,id=self.MenuKnap2)
		self.Bind(wx.EVT_MENU,self.OnZoomOut,id=self.MenuKnap3)
		#self.Bind(wx.EVT_MENU,self.OnTogglePolygons,id=self.MenuKnap4)
		#self.Bind(wx.EVT_MENU,self.OnGetPoints,id=self.MenuKnap5)
		#self.Bind(wx.EVT_MENU,self.OnToggleLabels,id=self.MenuKnap6)
		#self.Bind(wx.EVT_MENU,self.OnClearPoints,id=self.MenuKnap7)
		self.Bind(wx.EVT_MENU,self.OnResetPlot,id=self.MenuKnap8)
		self.Bind(wx.EVT_MENU,self.OnSaveFile,id=self.MenuKnap9)
		self.Bind(wx.EVT_MENU,self.OnToggleToolbar,id=self.MenuKnap10)
		self.Bind(wx.EVT_MENU,self.OnToggleMinimap,id=self.MenuKnap11)
		#self.Bind(wx.EVT_MENU,self.OnDeletePositions,id=self.MenuKnap12)
		self.Bind(wx.EVT_MENU,self.OnKillWMS,id=self.MenuKnap13)  #draeb wms-traad - hvis du bliver utaalmodig
		self.Bind(wx.EVT_MENU,self.OnSetCenter,id=self.MenuKnap14)  #draeb wms-traad - hvis du bliver utaalmodig
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(splitter,8,wx.CENTER|wx.ALIGN_CENTER|wx.ALL|wx.EXPAND,5)
		self.sizer.Add(bottompanel,1,wx.ALL|wx.EXPAND,5)
		self.container.sizer.Add(self.buttonpanel,2,wx.EXPAND|wx.ALL|wx.CENTER)
		self.container.SetSizerAndFit(self.container.sizer)
		self.SetSizerAndFit(self.sizer)
		dsize=wx.GetDisplaySize()
		self.SetSize((dsize.x-50,dsize.y-50))
		self.Bind(wx.EVT_CLOSE,self.OnEVTClose)
		self.container.Show()
		self.Center()
		self.Update()
		self.Show()
		##################################
		##  Generate a dlg message for the user at init ##
		##################################
		doprompt=False
		warnstr=""
		if not self.Map.data.IsInitialized(): 
			#self.DisablePoints()
			#self.Map.data=None
			if Ini['datafile'] is not None:
				warnstr+=(u"Kunne ikke genkende %s som en sqlite-datafil. V\u00E6lg en fil via menupunkt.\n" %Ini['datafile'])
				doprompt=True
		if not self.Map.PolygonEngine.IsInitialized():
			self.DisablePolygons()
			if Ini['districtfile'] is not None:
				warnstr+=(u"Polygonfil %s med opm\u00E5lingsdistriker kunne ikke tilsluttes.\n" %Ini['districtfile'])
				doprompt=True
		indexname=MapBrowser.GdalMaps.GetIndexName()
		notindexed=[]
		for dir in Ini['mapdirs']:
			if not os.path.exists(dir+indexname):
				notindexed.append(dir)
		if len(notindexed)>0:
			doprompt=True
			warnstr+=u"F\u00F8lgende mapper er ikke indekseret og kan ikke tilsuttes:\n"
			for dir in notindexed:
				warnstr+="%s\n" %dir
			warnstr+="Indekser kortmapper vha. menupunkt i programmet."
		if doprompt:
			dlg=GUI.MyMessageDialog(self,u"Bem\u00E6rk:",warnstr)
			dlg.ShowModal()
			dlg.Destroy()
		self.SetPanMode()
		# Stdout
		try:
			sys.frozen
		except:
			pass
		else:
			sys.stdout=RedirectStdout(self)
			self.Bind(EVT_STDOUT,self.OnPrint)
		#Things for printing
		self.print_data = wx.PrintData()
		self.print_data.SetPaperId(wx.PAPER_A4)
		self.print_data.SetOrientation(wx.LANDSCAPE)
		self.pageSetupData= wx.PageSetupDialogData()
		self.pageSetupData.SetMarginBottomRight((25,25))
		self.pageSetupData.SetMarginTopLeft((25,25))
		self.pageSetupData.SetPrintData(self.print_data)
	def OnEVTClose(self,event):
		self.Map.CloseDown()
		if self.gps.isAlive():
			self.gps.kill()
			self.gps.join()
		event.Skip() #ellers lukkes ikke!
	def OnAbout(self,e):
		global aboutstr
		d= wx.MessageDialog( self, aboutstr,Program, wx.OK)
		d.ShowModal() # Shows it
		d.Destroy() # finally destroy it when finished.
	def OnExit(self,event):
		if self.gps.isAlive():
			self.gps.kill()
		WriteIni(self.Ini)
		self.Close()
	def OnGPSkill(self,event):
		if event.kill:
			self.DetachGPS()
			self.Log(u"GPS'en ikke tilsluttet!")
		self.Update()
	def OnUpdateDsc(self,event):
		if not self.Map.data.IsInitialized():
			self.Log("Datafil ikke tilsluttet. Kan ikke opdatere...")
			return
		file=GetFile(self,u"V\u00E6lg fil med beskrivelser.")
		if file!=-1:
			f=open(file)
			bsks,nd,nempty=Extract.GetBsk(f)
			f.close()
			msg="Fandt %i beskrivelser i %s. Tomme beskrivelser: %i. \nAntal dubletter: %i." %(len(bsks),file,nempty,nd)
			if len(bsks)>0:
				msg+=u"\nF\u00F8rste beskrivelse er for punktet:\n%s" %(bsks.keys()[0])
				msg+="\nVil du opdatere datafilen?"
				dlg=GUI.OKdialog(self,"Beskrivelser",msg)
				dlg.ShowModal()
				if dlg.WasOK():
					self.Map.data.UpdateDsc(bsks)
				dlg.Destroy()
				n=self.Map.data.GetNChanged()
				self.Log("Datafil opdateret. Opdateringer ialt: %i" %n)
			else:
				self.Log(msg)
			
	def OnUpdateZs(self,event):
		if not self.Map.data.IsInitialized():
			self.Log("Datafil ikke tilsluttet. Kan ikke opdatere...")
			return
		file=GetFile(self,u"V\u00E6lg fil med kotetr\u00E6k.")
		if file!=-1:
			f=open(file)
			zs,nd=Extract.GetZs(f)
			f.close()
			msg=u"Fandt %i koter i %s.\nAntal dubletter: %i." %(len(zs),file,nd)
			if len(zs)>0:
				msg+=u"\nF\u00F8rste kote er for punktet:\n%s" %(zs.keys()[0])
				msg+="\nVil du opdatere datafilen?"
				dlg=GUI.OKdialog(self,"Koter",msg)
				dlg.ShowModal()
				if dlg.WasOK():
					self.Map.data.UpdateZs(zs)
				dlg.Destroy()
				n=self.Map.data.GetNChanged()
				self.Log("Datafil opdateret. Opdateringer ialt: %i" %n)
			else:
				self.Log(msg)
	def OnUpdateKanKo(self,event):
		if not self.Map.data.IsInitialized():
			self.Log("Datafil ikke tilsluttet. Kan ikke opdatere...")
			return
		file=GetFile(self,u"V\u00E6lg fil med lokationer for punkter der kan koteres.")
		if file!=-1:
			f=open(file)
			crds,nd=Extract.GetLoc(f)
			f.close()
			msg=u"Fandt %i koordinats\u00E6t i %s.\nAntal dubletter: %i." %(len(crds),file,nd)
			if len(crds)>0:
				msg+=u"\nF\u00F8rste koordinats\u00E6t er for punktet:\n%s" %(crds.keys()[0])
				msg+="\nVil du opdatere datafilen?"
				dlg=GUI.OKdialog(self,"Koordinater",msg)
				dlg.ShowModal()
				if dlg.WasOK():
					self.Map.data.UpdateCoords(crds)
				dlg.Destroy()
				n=self.Map.data.GetNChanged()
				self.Log("Datafil opdateret. Opdateringer ialt: %i" %n)
			else:
				self.Log(msg)
	def OnUpdateSkitse(self,event):
		if not self.Map.data.IsInitialized():
			self.Log("Datafil ikke tilsluttet. Kan ikke opdatere...")
			return
		ddlg=wx.DirDialog(self,message=u"Angiv en mappe punktskitser",defaultPath="C://",style=wx.DD_DIR_MUST_EXIST)
		if ddlg.ShowModal()==wx.ID_OK:
			dir=ddlg.GetPath()
			skitser,nd=Extract.GetSkitser(dir)
			msg=u"Fandt %i mulige skitser i %s.\nAntal dubletter: %i." %(len(skitser),dir,nd)
			if len(skitser)>0:
				msg+=u"\nF\u00F8rste skitse er for punktet:\n%s" %(skitser.keys()[0])
				msg+="\nVil du opdatere datafilen?"
				dlg=GUI.OKdialog(self,"Skitser",msg)
				dlg.ShowModal()
				if dlg.WasOK():
					self.Map.data.UpdateSkitser(skitser)
				dlg.Destroy()
				n=self.Map.data.GetNChanged()
				self.Log("Datafil opdateret. Opdateringer ialt: %i" %n)
			else:
				self.Log(msg)
		ddlg.Destroy()
	def OnAddIDs(self,event):
		if not self.Map.HasData():
			self.Log(u"Tilslut datafil f\u00F8rst.")
			return
		file=GetFile(self,u"V\u00E6lg fil med identiteter:")
		if file!=-1:
			f=open(file)
			Stations,Nd,Ngm,Ngps=Extract.GetIDs(f)
			f.close()
			msg=u"Fandt %i stationer, %i G.M/G.I-navne og %i GPS-navne i %s.\nAntal dubletter: %i." %(len(Stations),Ngm,Ngps,file,Nd)
			if len(Stations)>0:
				msg+=u"\nF\u00F8rste station er:\n%s" %(Stations.keys()[0])
				msg+="\nVil du opdatere datafilen?"
				dlg=GUI.OKdialog(self,"Identiteter",msg)
				dlg.ShowModal()
				if dlg.WasOK():
					self.Map.data.CreateNewPoints(Stations)
				dlg.Destroy()
				n=self.Map.data.GetNChanged()
				self.Log("Datafil opdateret. Opdateringer ialt: %i" %n)
			else:
				self.Log(msg)
	def OnMarkAsGeo(self,event):
		#We choose a location file based on tradition#
		if not self.Map.data.IsInitialized():
			self.Log("Datafil ikke tilsluttet. Kan ikke opdatere...")
			return
		file=GetFile(self,u"V\u00E6lg fil med lokationer for punkter, som er m\u00E5lt geometrisk.")
		if file!=-1:
			f=open(file)
			crds,nd=Extract.GetLoc(f)
			f.close()
			msg=u"Fandt %i punkter %s.\nAntal dubletter: %i." %(len(crds),file,nd)
			if len(crds)>0:
				msg+=u"\nEksempel p\u00E5 punkt i filen:\n%s" %(crds.keys()[0])
				msg+="\nVil du opdatere datafilen?"
				dlg=GUI.OKdialog(self,u"Marker geometrisk opm\u00E5ling",msg)
				dlg.ShowModal()
				if dlg.WasOK():
					self.Map.data.MarkAsGeo(crds.keys())
				dlg.Destroy()
				n=self.Map.data.GetNChanged()
				self.Log("Datafil opdateret. Opdateringer ialt: %i" %n)
			else:
				self.Log(msg)
	def OnMarkAsLost(self,event):
		#We choose an identity file based on tradition on FixOpl#
		if not self.Map.data.IsInitialized():
			self.Log("Datafil ikke tilsluttet. Kan ikke opdatere...")
			return
		file=GetFile(self,u"V\u00E6lg fil med lokationer (punktnavne) for punkter, som er tabtg\u00E5et")
		if file!=-1:
			f=open(file)
			Stations,nd=Extract.GetLoc(f)
			f.close()
			msg=u"Fandt %i stationer" %(len(Stations))
			if len(Stations)>0:
				msg+=u"\nFilen indeholder eksempelvis stationen:\n%s" %(Stations.keys()[0])
				msg+="\nVil du opdatere datafilen?"
				dlg=GUI.OKdialog(self,"Identiteter",msg)
				dlg.ShowModal()
				if dlg.WasOK():
					self.Map.data.MarkAsLost(Stations.keys())
				dlg.Destroy()
				n=self.Map.data.GetNChanged()
				self.Log("Datafil opdateret. Opdateringer ialt: %i" %n)
			else:
				self.Log(msg)
	def OnDisplayStats(self,event):
		self.DisplayStats()
	def DisplayStats(self):
		self.Log("Henter statistik for punktfil (tager lidt tid, hvis filen ikke er indekseret...)")
		if self.Map.data.IsInitialized():
			msg=self.Map.data.GetStats()
			dmsg="Datafil: %s\n" %self.Ini['datafile']+msg
			dlg=GUI.MyMessageDialog(self,"Statistik for datafilen",dmsg)
			dlg.ShowModal()
			dlg.Destroy()
		else:
			self.Log("Datafil ikke tilsluttet.")
	def OnEvtLog(self,event):
		self.Log(event.text)
	###############
	## Vis-menu stuff ##
	###############
	def OnSetTextBlack(self,event): #really sloppy - should be improved with/when more colors...
		self.Map.SetTextColor("black")
	def OnSetTextRed(self,event): #really sloppy - should be improved with/when more colors...
		self.Map.SetTextColor("red")
	def OnSetTextBlue(self,event): #really sloppy - should be improved with/when more colors...
		self.Map.SetTextColor("blue")
	def OnSetPointFont(self,event):
		fontdata=wx.FontData()
		fontdata.SetInitialFont(GUI.DefaultFont(12))
		dlg=wx.FontDialog(self,fontdata)
		if dlg.ShowModal()==wx.ID_OK:
			fontdata=dlg.GetFontData()
			font=fontdata.GetChosenFont()
			color=fontdata.GetColour()
			self.Map.SetPointFont(font,color)
		dlg.Destroy()
	def OnSetStyle(self,event):
		style=self.Map.GetPlotStyle() #perhaps copy it?
		win=StyleFrame(self,style) #in this way the direct link to the maps plotstyle is kept.
	
	########################
	## Map Menu Stuff
	########################
	def OnMakeIndex(self,event):
		dlg=wx.DirDialog(self,message=u"Angiv en mappe med geokodede kortfiler",defaultPath="C://",style=wx.DD_DIR_MUST_EXIST)
		if dlg.ShowModal()==wx.ID_OK:
			dir=dlg.GetPath()
			try:
				self.Log("Indekser... Kan tage et par minutter for store mapper.\n") #Clear the info-field
				self.info.SetInsertionPointEnd()
				MapBrowser.GdalMaps.MakeIndex(str(dir),self.info)
			except Exception, msg:
				self.Log(str(msg))
				self.Log("Muligvis er kortmappen i brug...",append=True)
		dlg.Destroy()
	def OnDefinerKort(self,event):
		dlg=wx.DirDialog(self,message=u"Angiv en mappe med kort",defaultPath="C://",style=wx.DD_DIR_MUST_EXIST)
		if dlg.ShowModal()==wx.ID_OK:
			dir=dlg.GetPath()
			OK=self.Map.DefineMapDir(str(dir))
			if OK:
				self.Log(u"S\u00E6tter kortmappen til %s." %dir)
				self.Ini['mapdirs']=[str(dir)]
		dlg.Destroy()
	def OnShowDEM(self,event):
		dlg=wx.DirDialog(self,message=u"Angiv en mappe med DHM-filer",defaultPath="C://",style=wx.DD_DIR_MUST_EXIST)
		if dlg.ShowModal()==wx.ID_OK:
			dir=dlg.GetPath()
			OK=self.Map.DefineMapDir(str(dir),isDEM=True)
			if OK:
				self.Log(u"S\u00E6tter kortmappen til %s." %dir)
			else:
				self.Log("Kunne ikke initialisere kortmotoren...")
		dlg.Destroy()
	def OnDefineColors(self,event):
		id=event.GetId()-10000
		self.Map.MapEngine.SetColorMap(id)
		self.Map.SetMap()
	def OnAddMapDir(self,event):
		dlg=wx.DirDialog(self,message=u"Angiv en mappe med kort",defaultPath="C://",style=wx.DD_DIR_MUST_EXIST)
		if dlg.ShowModal()==wx.ID_OK:
			dir=dlg.GetPath()
			OK=self.Map.AddMapDir(str(dir))
			if OK:
				self.Log(u"Tilf\u00F8jer kortmappen %s." %dir)
				self.Ini['mapdirs'].append(str(dir))
				self.mapdirbox.AddMapDir(str(dir))
				self.UpdateZoomSlider()
				if hasattr(self.Map,"mapservice") and self.Map.mapservice=="disk":
					self.Map.SetMap()
		dlg.Destroy()
	def OnSetLineFile(self,event):
		file=GetFile(self,"Angiv en fil med data i linie-format:",wildcard=OGR_VECTOR_FORMATS)
		if file!=-1:
			ok=self.Map.DefineLineFile(file)
			if not ok:
				self.Log("Kunne ikke initialisere med filen %s." %file)
				self.Ini['coastline']=str(file)
	def OnSetPolygonFile(self,event):
		file=GetFile(self,"Angiv en fil med data i linie-format:",wildcard=OGR_VECTOR_FORMATS)
		if file!=-1:
			ok=self.Map.DefinePolygonFile(file)
			if not ok:
				self.Log("Kunne ikke initialisere med filen %s." %file)
				self.Ini['districtfile']=str(file)
	def OnRemoveMapdir(self,event):
		dirs=self.Map.MapEngine.GetMapDirs()
		dirnames=[dir.GetName() for dir in dirs]
		dlg=GUI.MyMultiChoiceDialog(self,title="Afbryd forbindelse til kortmappe(r)",msg=u"V\u00E6lg kortmappe(r):",choices=dirnames)
		dlg.ShowModal()
		if dlg.WasOK():
			selected=dlg.GetSelections()
			for i in selected:
				if self.Map.MapEngine.RemoveMapDir(dirs[i]):
					self.Log("Fjerner %s" %dirnames[i],append=True)
				else:
					self.Log("Kunne ikke fjerne %s" %dirnames[i],append=True)
		dlg.Destroy()
	def OnDefinerData(self,event):
		file=GetFile(self, u"V\u00E6lg en sqlite-datafil:")
		if file!=-1:
			try:
				self.Map.DefineData(Data.PointData(file))
			except:
				self.Log("Kunne ikke genkende %s som en sqlite-datafil." %file)
			else:
				if self.Map.data.IsInitialized():
					self.EnablePoints()
					self.Ini['datafile']=file
				else:
					self.Log("Kunne ikke genkende %s som en sqlite-datafil." %file)
		
	def OnMakeData(self,event):
		dlg=wx.FileDialog(self,u"V\u00E6lg et navn til datafilen:",wildcard="*.sqlite",style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
		if dlg.ShowModal()==wx.ID_OK:
			file=dlg.GetPath()
			OK=Data.MakeDatabase(file)
			if OK:
				self.Log("Databasefil %s genereret." %file)
			else:
				self.Log("Kunne ikke slette eksisterende fil!")
		dlg.Destroy()
		try:
			self.Map.DefineData(Data.PointData(file))
		except:
			self.Log("Kunne ikke tilslutte til den nye datafil.")
		else:
			self.Log("Database er tilsluttet.")
	
		
	def OnDigitalize(self,event):
		self.SetDigitizeMode()
		
		
	def OnGetInfo(self,event):
		self.GetInfo()
	def GetInfo(self):
		if not self.Map.data.IsInitialized():
			self.Log(u"Data ikke initialiseret. V\u00E6lg sqlite-datafil i under menu.")
			return
		dlg=GUI.InputDialog(self,title="Punktinfo",textlabels=[u"Punktnavn, eller del heraf:\n(brug % som wildcard.)  "])
		dlg.ShowModal()
		if dlg.WasOK():
			prefix=dlg.GetTextValues()[0]
			dlg.Destroy()
		else:
			dlg.Destroy()
			return
		self.Log("Henter data.....")
		names=self.Map.data.GetInfoNamesLike(prefix)
		if names is not None:
			self.Log("Fandt %i punkter." %len(names))
			if len(names)>1:
				dlg=GUI.MySingleChoiceDialog(self,"Punkter fra databasen",u"Fandt %i punkter.\nV\u00E6lg et punkt:" %len(names),choices=names)
				dlg.ShowModal()
				OK=dlg.OK
				if OK:
					punkt=dlg.GetString()
					dlg.Destroy()
				else:
					dlg.Destroy()
					return
			else:
				punkt=names[0]
			bsk,skitse,w,h,found=self.Map.data.GetSkitseAndBsk(punkt) #should be improved to see if point was found!
			if found:
				skitse=wx.BitmapFromBuffer(w,h,skitse)
				x,y=self.Map.data.GetCoordinates(punkt)
				if x is not None:
					self.Map.GoTo(x,y)
				dlg2=GUI.MyDscDialog(self,title="Beskrivelse for %s" %punkt,msg=bsk,image=skitse,point=punkt)
				dlg2.ShowModal()
				dlg2.Destroy()
			else:
				self.info.AppendText(". -Beskrivelse og skitse kunne ikke findes...")
		else:
			self.Log("Fandt ingen punkter indeholdende %s." %prefix)
	def OnGoToWMS(self,event):
		self.GoToWMS()
	def GoToWMS(self):
		choices=Kortforsyningen.GetServiceNames()
		dlg=GUI.MySingleChoiceDialog(self,"WMS-kort",u"V\u00E6lg korttype",choices)
		dlg.ShowModal()
		OK=dlg.OK
		if OK:
			choice=dlg.GetSelection()
			self.Map.EnableWMS(Kortforsyningen.GetService(choice))
			self.Map.SetMap()
			self.maptypebox.SetSelection(1)
		else:
			self.maptypebox.SetSelection(0)
		dlg.Destroy()
	def OnGoToDiskMaps(self,event):
		self.GoToDiskMaps()
	def GoToDiskMaps(self):
		self.Map.EnableDiskMaps()
		self.Map.SetMap()
		self.maptypebox.SetSelection(0)
	def OnSetCenter(self,event):
		dlg=GUI.InputDialog(self,"Definer kortudsnit",numlabels=["Easting:","Northing:","Plotrange (m):"],bounds=[(0,10**8),(0,10**10),(1,300000)])
		dlg.ShowModal()
		if dlg.WasOK():
			vals=dlg.GetNumValues()
			E=float(vals[0])
			N=float(vals[1])
			R=float(vals[2])
			self.Map.SetCenter(E,N,R)
		dlg.Destroy()
	def OnGPSstart(self,e):
		dlg=GUI.InputDialog(self,"Tilslut GPS",numlabels=["Virtuel COM-port:","Baudrate:"],bounds=[(1,100),(0,128000)],numvalues=[self.Ini['gpsport'],self.Ini['gpsbaud']])
		dlg.ShowModal()
		if dlg.WasOK():
			vals=dlg.GetNumValues()
			port=int(vals[0])-1 #Python indeksering af porte!
			baud=int(vals[1])
			self.Log(u"Fors\u00F8ger tilslutning af GPS med port %i, baudrate %i"%(port+1,baud))
			self.gps=GPS.GpsThread(self,port,baud)
			self.gps.start()
			self.Map.AttachGPS(self.gps)
			if self.gps.isAlive():
				self.gpsbutton.Enable()
			self.Ini['gpsport']=port+1
			self.Ini['gpsbaud']=baud
		dlg.Destroy()
		self.Update()	
	def OnGPSstop(self,e):
		if self.gps.isAlive():
			self.gps.kill()
			self.DetachGPS()
			self.Log("GPS-enheden stoppes...")
		self.Update() 
	def DetachGPS(self):
		self.gps=GPS.DummyThread()
		#self.knap41.Enable(0)
		self.gpsbutton.SetValue(False) 
		self.gpsbutton.Enable(False)	#disable gps-centering
		self.Map.DetachGPS()
		if not self.panmode:
			self.SetPanMode()
	def OnLukNavKort(self,e):
		self.Map.CloseMiniMap()
	def OnVisNavKort(self,e):
		self.Map.ShowMiniMap()
	def Update(self):
		self.GPSstop.Enable(self.gps.isAlive())
		self.GPSstart.Enable(not self.gps.isAlive())
		self.gpsbutton.Enable(self.gps.isAlive())
		self.GetInfoItem.Enable(self.Map.data.IsInitialized())
	def Log(self,text,append=False):
		if append:
			self.info.AppendText("\n"+text)
		else:
			self.info.SetValue(text)
		self.info.Update()
	def OnPrint(self,event): #STDOUT-EVENT (e.g. a print command)
		self.Log(event.text)
	def OnMiniMenu(self):
		popupmenu=wx.Menu()
		popupmenu.Append(self.MenuKnap2,"Zoom ind")
		popupmenu.Append(self.MenuKnap3,"Zoom ud")
		#if self.Map.PolygonEngine.IsInitialized():
		#	popupmenu.Append(self.MenuKnap4,"Opm.distrikt til/fra")
		#if self.Map.data is not None:
		#	popupmenu.Append(self.MenuKnap5,"Hent punkter")
		#	#popupmenu.Append(self.MenuKnap6,"Pkt.navne til/fra")
		#	#popupmenu.Append(self.MenuKnap7,"Slet punkter")
		popupmenu.Append(self.MenuKnap8,u"Reset kortst\u00F8rrelse")
		popupmenu.Append(self.MenuKnap9,u"Gem Fil")
		if self.container.IsShown():
			tlabel="Skjul toolbar"
		else:
			tlabel="Vis toolbar"
		popupmenu.Append(self.MenuKnap10,tlabel)
		if self.Map.minimap.IsShown():
			tlabel="Luk navigationskort"
		else:
			tlabel="Vis navigationskort"
		popupmenu.Append(self.MenuKnap11,tlabel)
		#if self.Map.positions is not None:
		#	popupmenu.Append(self.MenuKnap12,"Slet positioner")
		if self.Map.wmsthread.isAlive():
			popupmenu.Append(self.MenuKnap13,"Stop WMS-hentning")
		popupmenu.Append(self.MenuKnap14,"Go to (x,y)")
		self.PopupMenu(popupmenu)
	def OnKillWMS(self,event):
		self.Map.KillWMS()
	def OnClearPoints(self,event):
		self.Map.ClearPoints()
		self.info.SetValue("")
	def OnResetPlot(self,event):
		self.Map.ResetPlot()
	def OnToggleLabels(self,event):
		self.Map.ToggleLabels()
	def OnToggleNameLength(self,event):
		self.Map.ToggleNameLength()
	def OnSaveFile(self,event):
		dlg1 = wx.FileDialog(self, 
		"Gem kort som bmp, png, eller jpg-fil", ".", "",
		"BMP files (*.bmp)|*.bmp|PNG files (*.png)|*.png|JPG files (*.jpg)|*.jpg",
		wx.SAVE|wx.OVERWRITE_PROMPT)
		try:
			while 1:
				if dlg1.ShowModal() == wx.ID_OK:
					fileName = dlg1.GetPath()
				# Check for proper exension
					if fileName[-3:].strip() not in ['bmp','png','jpg']:
						dlg2 = wx.MessageDialog(self, 'Skal ende som\n'
						'bmp, png, or jpg',
						'File Name Error', wx.OK | wx.ICON_ERROR)
						try:
							dlg2.ShowModal()
						finally:
							dlg2.Destroy()
					else:
						break # now save file
				else: # exit without saving
					return False
		finally:
				dlg1.Destroy()
		self.Map.SaveFile(fileName)
	def OnGetPoints(self,event):
		self.Map.GetPoints()
	def OnLayers(self,event):
		self.SetLayers()
	def OnRedraw(self,event):
		self.Map.Plot()
	def SetLayers(self):
		self.Map.SetLayers(self.layerbox.GetLayers())
	def OnLostType(self,event):
		losttype=self.lostbox.GetSelection()
		self.Map.SetLostType(losttype)
	def OnNameType(self,event):
		nametype=self.namebox.GetSelection()
		self.Map.SetNameType(nametype)
	def OnMapType(self,event):
		type=self.maptypebox.GetSelection()
		if type==0:
			self.GoToDiskMaps()
		else:
			self.GoToWMS()
	def OnMapDirs(self,event):
		states=self.mapdirbox.GetMapDirs()
		self.Map.SetMapDirsUseState(states)
		self.UpdateZoomSlider()
	def OnModeBox(self,event):
		i=event.GetInt()
		if i==0:
			self.SetPanMode()
		elif i==1:
			self.SetPointMode()
		elif i==2:
			self.SetDigitizeMode()
	def OnGpsButton(self,event):
		check=self.gpsbutton.IsChecked()
		self.Map.SetGpsCentering(check)
		if not check:
			self.Log("Stopper GPS-centrering...")
	def SetPanMode(self): #naar  gps doer saa gaa til navmode!
		if not self.panmode:
			self.Log("Skifter til navigation via venstreklik...")
		self.panmode=True
		self.pointmode=False
		self.digitizemode=False
		self.modebox.SetSelection(0)
	def SetPointMode(self):
		if not self.pointmode:
			self.Log(u"Skifter til 'point-mode'. Klik p\u00E5 et punkt")
		self.pointmode=True
		self.panmode=False
		self.digitizemode=False
		self.modebox.SetSelection(1)
	def SetDigitizeMode(self):
		if not self.digitizemode:
			self.Log(u"Skifter til 'digitaliserings-mode'.")
		self.pointmode=False
		self.panmode=False
		self.digitizemode=True
		if not self.DigitalizeWindow.IsShown():
			self.DigitalizeWindow=DigitalizeWindow(self)
		else:
			self.DigitalizeWindow.SetFocus()
		self.modebox.SetSelection(2)
	def OnRightClick(self,event):
		x=event.GetX()
		y=event.GetY()
		D,j=100000,-1 # just larger than clickrange :-)
		if self.Map.HasPoints() and self.pointmode:
			D,j=self.Map.ClosestLocatedPoint(x,y) #in screen coords 
		if D<self.clickrange:  #Saa er punkter plottet og defineret!
			self.Map.UnSelect()
			self.Map.Select(j)
			info=self.Map.GetHeightInfo()
			self.Log(info)
			bsk,found1=self.Map.GetLocatedInfo()
			skitse,w,h,found2=self.Map.GetLocatedSkitse()
			punkt=self.Map.GetLocatedLabel()
			if found1 or found2: #edited 03.11
				try:
					self.dscdlg.Close()
				except:
					pass
				skitse=wx.BitmapFromBuffer(w,h,skitse)
				self.dscdlg=GUI.MyDscDialog(self,title="Beskrivelse for %s" %punkt,msg=bsk,image=skitse,point=punkt)
				self.dscdlg.Show()
			else:
				self.Log("--Beskrivelse og skitse kunne ikke findes...",append=True)
		else:
			self.OnMiniMenu()
			self.Map.UnSelect()
		event.Skip()
	def OnLeftClick(self,event):
		x=event.GetX()
		y=event.GetY()
		ux,uy=self.Map.MapPanel.UserCoords(x,y)  #could be wrapped more elegantly
		self.SetStatusText("(%.1f,%.1f)" %(ux,uy))
		if self.Map.HasPoints() and self.pointmode:
			D,j=self.Map.ClosestLocatedPoint(x,y) #in screen coords 
			if D<self.clickrange:  #Saa er punkter plottet og defineret!
				self.Map.UnSelect()
				self.Map.Select(j)
				info=self.Map.GetHeightInfo()
				self.Log(info)
			else:
				self.Log("Koordinater: (%.1f,%.1f)" %(ux,uy))
		elif self.digitizemode:
			self.Map.DrawSpecialPoint(np.array([[ux,uy]]),color="orange",pointsize="best")
			label="punktnavn"
			if self.Map.PolygonEngine.IsInitialized():
				label=self.Map.PolygonEngine.GetDistrictName(ux,uy)
			try:
				self.DigitalizeWindow.AddPoint(label,ux,uy)
			except:
				pass
		elif self.panmode and not self.Map.wmsthread.isAlive(): #ikke nyt koor.system naar wms-hentning paagar!
			self.Map.UnSelect()
			self.info.SetValue("")
			self.Map.GoTo(ux,uy)
		else:
			self.Map.UnSelect()
		event.Skip()
	def OnZoomIn(self,event):
		self.Map.ZoomIn()
		self.zoomslider.SetPixelSize(self.Map.GetPixelSize())
	def OnZoomOut(self,event):
		self.Map.ZoomOut()
		self.zoomslider.SetPixelSize(self.Map.GetPixelSize())
	def OnZoomSlider(self,event):
		pixsize=self.zoomslider.GetPixelSize()
		if self.Map.CanZoom():
			self.Map.SetPixelSize(pixsize)
		else:
			pixsize=self.Map.GetPixelSize()
			self.zoomslider.SetPixelSize(pixsize)
	def UpdateZoomSlider(self):
		dsize=wx.GetDisplaySize()
		self.zoomslider.SetMinPixelSize(self.Map.GetMinPixelSize()*0.2)
		self.zoomslider.SetMaxPixelSize(self.Map.GetMaxRange()/float(dsize.x)) #Radius in km
		self.zoomslider.SetPixelSize(self.Map.GetPixelSize())
	def OnCloseToolbar(self,event):
		self.container.Show(0)
	def OnToggleToolbar(self,event):
		if self.container.IsShown():
			self.container.Show(0)
		else:
			self.container.Show()
	def OnToggleMinimap(self,event):
		self.Map.ToggleMinimap()
	def ShowMiniMap(self):
		self.Map.ShowMiniMap()
	def CloseMiniMap(self):
		self.Map.CloseMiniMap()
	def DisablePoints(self):
		pass
	def EnablePoints(self):
		pass
	def DisablePolygons(self):
		pass
	######Printing###########
	def OnPageSetup(self,event):
		self.PageSetup()
	def OnPrintout(self,event):
		self.Printout()
	def OnPreview(self,event):
		self.PrintPreview()
	def PageSetup(self):
		"""Brings up the page setup dialog"""
		data = self.pageSetupData
		data.SetPrintData(self.print_data)
		dlg = wx.PageSetupDialog(self, data)
		try:
			if dlg.ShowModal() == wx.ID_OK:
				data = dlg.GetPageSetupData() # returns wx.PageSetupDialogData
				# updates page parameters from dialog
				self.pageSetupData.SetMarginBottomRight(data.GetMarginBottomRight())
				self.pageSetupData.SetMarginTopLeft(data.GetMarginTopLeft())
				self.pageSetupData.SetPrintData(data.GetPrintData())
				self.print_data=wx.PrintData(data.GetPrintData()) # updates print_data
		finally:
			dlg.Destroy()
	def Printout(self, paper=None):
		"""Print current plot."""
		if paper != None:
			self.print_data.SetPaperId(paper)
		pdd = wx.PrintDialogData(self.print_data)
		printer = wx.Printer(pdd)
		out = PlotPrintout(self)
		print_ok = printer.Print(self, out)
		if print_ok:
			self.print_data = wx.PrintData(printer.GetPrintDialogData().GetPrintData())
		out.Destroy()

	def PrintPreview(self):
		"""Print-preview current plot."""
		printout = PlotPrintout(self)
		printout2 = PlotPrintout(self)
		self.preview = wx.PrintPreview(printout, printout2, self.print_data)
		if not self.preview.Ok():
			wx.MessageDialog(self, "Print Preview failed.\n" \
				       "Check that default printer is configured\n", \
				       "Print error", wx.OK|wx.CENTRE).ShowModal()
		self.preview.SetZoom(70)
		# search up tree to find frame instance
		frameInst= self
		while not isinstance(frameInst, wx.Frame):
			frameInst= frameInst.GetParent()
		frame = wx.PreviewFrame(self.preview, frameInst, "Preview")
		frame.Initialize()
		frame.SetPosition(self.GetPosition())
		frame.SetSize((700,600))
		frame.Centre(wx.BOTH)
		frame.Show(True)
#Function which fetches a filename via wx.FileDialog
def GetFile(win,msg="Select a file:",wildcard="*.*"):
	dlg= wx.FileDialog(win, msg,wildcard=wildcard,style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
	if dlg.ShowModal()==wx.ID_OK:
		filename=dlg.GetPath()
	else:
		filename=-1
	dlg.Destroy()
	return filename
def GetFiles(win,msg):
	dlg= wx.FileDialog(win, msg,".",style=wx.FD_OPEN|wx.FD_MULTIPLE)
	if dlg.ShowModal()==wx.ID_OK:
		files=dlg.GetPaths()
	else:
		files=[]
	dlg.Destroy()
	return files

#class for digitalizing point coordinates
class DigitalizeWindow(wx.Frame):
		def __init__(self,parent,title="Digitaliser Punkter",size=(600,600),style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT):
			self.parent=parent
			wx.Frame.__init__(self,parent,title=title,size=size,style=style)
			self.SetBackgroundColour("lightgray")
			try:
				icon=parent.GetIcon()
			except:
				pass
			else:
				self.SetIcon(icon)
			button1=GUI.MyButton(self,"GEM FIL",12)
			button2=GUI.MyButton(self,"LUK",12)
			self.text=wx.TextCtrl(self,size=(400,100),style=wx.TE_MULTILINE)
			self.text.SetValue("#utm32_etrs89\n")
			self.sizer=wx.BoxSizer(wx.VERTICAL)
			self.buttonsizer=wx.BoxSizer(wx.HORIZONTAL)
			self.sizer.Add(self.text,1,wx.EXPAND|wx.ALL,10)
			self.buttonsizer.Add(button1,0,wx.ALL,5)
			self.buttonsizer.Add(button2,0,wx.ALL,5)
			self.sizer.Add(self.buttonsizer,0,wx.ALL,10)
			self.Bind(wx.EVT_CLOSE,self.OnEVTClose)
			button1.Bind(wx.EVT_BUTTON,self.OnSave)
			button2.Bind(wx.EVT_BUTTON,self.OnExit)
			self.SetSizerAndFit(self.sizer)
			self.Center()
			self.Show()
		def OnEVTClose(self,event):
			self.parent.DigitalizeWindow=GUI.DummyWindow()
			self.parent.SetPanMode()#important to tell the main fram, that we are not in this mode anymore
			event.Skip()
		def OnExit(self,event):
			self.Close()
		def OnSave(self,event):
			dlg = wx.FileDialog(self, "Gem koordinatfil", ".", style=wx.SAVE|wx.OVERWRITE_PROMPT)
			if dlg.ShowModal()==wx.ID_OK:
				fname=dlg.GetPath()
				f=open(fname,"w")
				text=self.text.GetValue()+"\n-1z"
				f.write(text)
				f.close()
			dlg.Destroy()
		def AddPoint(self,label,x,y):
			self.text.AppendText(label+"-          %.1f m\t%.1f m\n" %(y,x))



class FontPicker(wx.Panel):
	def __init__(self,parent,label="Font:",font=None,color="black"):
		wx.Panel.__init__(self,parent)
		#self.text=wx.TextCtrl(self,size=(400,20),style=wx.TE_MULTILINE)
		#self.text.SetFont(GUI.DefaultFont(12))
		self.font=font
		self.fontcolor=color
		label=GUI.MyText(self,label,12)
		self.fontname=wx.TextCtrl(self,value=self.font.GetNativeFontInfoUserDesc(),size=(200,-1),style=wx.TE_READONLY)
		self.fontname.SetFont(self.font)
		button=GUI.MyButton(self,u"V\u00E6lg font",12)
		button.Bind(wx.EVT_BUTTON,self.OnFont)
		self.sizer=wx.BoxSizer(wx.HORIZONTAL)
		self.sizer.Add(label,0,wx.ALL,5)
		self.sizer.Add(self.fontname,1,wx.ALL|wx.EXPAND,5)
		self.sizer.Add(button,0,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)
	def OnFont(self,event):
		fontdata=wx.FontData()
		fontdata.SetInitialFont(self.font)
		dlg=wx.FontDialog(self,fontdata)
		if dlg.ShowModal()==wx.ID_OK:
			fontdata=dlg.GetFontData()
			self.font=fontdata.GetChosenFont()
			self.fontcolor=fontdata.GetColour()
			self.fontname.SetValue(self.font.GetNativeFontInfoUserDesc())
			showfont=fontdata.GetChosenFont()
			showfont.SetPointSize(12)
			self.fontname.SetFont(showfont)
			end=self.fontname.GetLastPosition()
			self.fontname.SetStyle(0,end,wx.TextAttr(self.fontcolor))
		dlg.Destroy()

#Used to get user input on plot style.
class StyleFrame(wx.Frame):
	def __init__(self,parent,plotstyle,title="Formatering"):
		wx.Frame.__init__(self,parent,title=title,size=(600,600),style=wx.DEFAULT_FRAME_STYLE|wx.FRAME_FLOAT_ON_PARENT)
		try:
			icon=parent.GetIcon()
		except:
			pass
		else:
			self.SetIcon(icon)
		self.parent=parent
		self.plotstyle=plotstyle
		self.pointsize=wx.SpinCtrl(self,min=1,max=20,initial=plotstyle.pointsize,value="%i"%plotstyle.pointsize)
		self.pointsize.Enable(not plotstyle.usebest)
		self.usebest=wx.CheckBox(self,label=u"Brug bedste punktst\u00F8rrelse.")
		self.usebest.SetValue(plotstyle.usebest)
		self.fontpicker=FontPicker(self,label="Font til punktnavne:",font=plotstyle.font,color=plotstyle.textcolor)
		#clabel1=GUI.MyText(self,"Farve til horisontale vektorer:",12)
		#clabel2=GUI.MyText(self,"Farve til vertikale vektorer:",12)
		#clabel3=GUI.MyText(self,u"Farve p\u00E5 brugerdefinerede punkter:",12)
		#clabel4=GUI.MyText(self,u"Farve p\u00E5 forbindelseslinier:",12)
		pslabel=GUI.MyText(self,u"Punktst\u00F8rrelse:")
		#vwlabel=GUI.MyText(self,"Tykkelse af vektorer:")
		self.buttons=GUI.ButtonPanel(self,buttons=["Gentegn","OK","Fortyd"])
		#Event handling#
		self.usebest.Bind(wx.EVT_CHECKBOX,self.OnCheck2)
		#self.usebestvectorscale.Bind(wx.EVT_CHECKBOX,self.OnCheck1)
		self.buttons.button[0].Bind(wx.EVT_BUTTON,self.OnSetStyle)
		self.buttons.button[1].Bind(wx.EVT_BUTTON,self.OnClose)
		self.buttons.button[2].Bind(wx.EVT_BUTTON,self.OnCancel)
		#Sizer setup#
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		hsizer3=wx.BoxSizer(wx.HORIZONTAL)
		hsizer3.Add(pslabel,0,wx.ALL|wx.CENTER,5)
		hsizer3.Add(self.pointsize,0,wx.ALL|wx.CENTER,5)
		hsizer3.Add(self.usebest,0,wx.ALL|wx.CENTER,5)
		self.sizer.Add(hsizer3,0,wx.ALL,5)
		self.sizer.Add(self.fontpicker,0,wx.ALL,5)
		self.sizer.Add(self.buttons,0,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)
		self.SetBackgroundColour("lightgray")
		self.Show()
	def OnCheck2(self,event):
		self.pointsize.Enable(not self.usebest.IsChecked())
	def OnSetStyle(self,event):
		self.SetStyle()
		self.parent.Map.Plot(newmap=True)
	def SetStyle(self):
		newstyle=MapBrowser.PlotStyle()
		newstyle.font=self.fontpicker.font
		newstyle.textcolor=self.fontpicker.fontcolor
		newstyle.pointsize=self.pointsize.GetValue()
		newstyle.usebest=self.usebest.IsChecked()
		self.parent.Map.SetPlotStyle(newstyle)
	
	def OnClose(self,event):
		self.OnSetStyle(None)
		self.Close()
	def OnCancel(self,evnt):
		self.Close()
		


class PlotPrintout(wx.Printout):
	"""Controls how the plot is made in printing and previewing"""
	    # Do not change method names in this class,
	    # we have to override wx.Printout methods here!
	def __init__(self, win):
		"""graph is instance of plotCanvas to be printed or previewed"""
		wx.Printout.__init__(self)
		self.win = win
		self.Map=win.Map
	def HasPage(self, page):
		if page == 1:
			return True
		else:
			return False

	def GetPageInfo(self):
		return (1, 1, 1, 1)  # disable page numbers

	def OnPrintPage(self, page):
		dc = self.GetDC()  # allows using floats for certain functions
		##        print "PPI Printer",self.GetPPIPrinter()
		##        print "PPI Screen", self.GetPPIScreen()
		##        print "DC GetSize", dc.GetSize()
		##        print "GetPageSizePixels", self.GetPageSizePixels()
		# Note PPIScreen does not give the correct number
		# Calulate everything for printer and then scale for preview
		PPIPrinter= self.GetPPIPrinter()        # printer dots/inch (w,h)
		#PPIScreen= self.GetPPIScreen()          # screen dots/inch (w,h)
		dcSize= dc.GetSize()                    # DC size
		pageSize= self.GetPageSizePixels() # page size in terms of pixcels
		clientDcSize= self.Map.MapPanel.GetCanvasSize()
		# find what the margins are (mm)
		margLeftSize,margTopSize= self.win.pageSetupData.GetMarginTopLeft()
		margRightSize, margBottomSize= self.win.pageSetupData.GetMarginBottomRight()

		# calculate offset and scale for dc
		pixLeft= margLeftSize*PPIPrinter[0]/25.4  # mm*(dots/in)/(mm/in)
		pixRight= margRightSize*PPIPrinter[0]/25.4    
		pixTop= margTopSize*PPIPrinter[1]/25.4
		pixBottom= margBottomSize*PPIPrinter[1]/25.4

		plotAreaW= pageSize[0]-(pixLeft+pixRight)
		plotAreaH= pageSize[1]-(pixTop+pixBottom)

		# ratio offset and scale to screen size if preview
		if self.IsPreview():
			    ratioW= float(dcSize[0])/pageSize[0]
			    ratioH= float(dcSize[1])/pageSize[1]
			    pixLeft *= ratioW
			    pixTop *= ratioH
			    plotAreaW *= ratioW
			    plotAreaH *= ratioH
		# Set offset and scale
		dc.SetDeviceOrigin(pixLeft,pixTop)
		# Thicken up pens and increase marker size for printing
		ratioW= float(plotAreaW)/clientDcSize[0]
		ratioH= float(plotAreaH)/clientDcSize[1]
		aveScale= (ratioW+ratioH)/2
		# rescale plot to page or preview plot area
		dc.SetClippingRegion(0,0,plotAreaW,plotAreaH)
		self.Map.MapPanel.SetPrintSize((plotAreaW,plotAreaH),aveScale)
		self.Map.PrintPlot(dc=dc,signature="%s: %s" %(Program,time.asctime()))
		# rescale back to original
		self.Map.MapPanel.SetViewSize()
		#self.graph.Redraw()     #to get point label scale and shift correct
		return True









def SetUp():
	Ini=dict()
	gpsport=None
	gpsbaud=None
	mapdirs=[]
	datafile=None
	districtfile=None
	minimap=None
	coastline=None
	indexname=MapBrowser.GdalMaps.GetIndexName()
	try:
		f=open("VF.ini","r")
	except:
		pass
	else:
		line=RemRem(f)
		while len(line)>0:
			i=line.find(":")
			if i!=-1:
				key=line[:i].strip()
				print key,line[i:]
			else:
				key=None
			line=line[i+1:].split()
			if key=="gpsport" and len(line)>0:
				try:
					gpsport=int(line[0])
				except:
					pass
			if key=="gpsbaud" and len(line)>0:
				try:
					gpsbaud=int(line[0])
				except:
					pass
			if key=="mapdir" and len(line)>0:
				mapdir=line[0]
				if mapdir[-1] not in ["/","\\"]:
					mapdir+="/"
				if not os.path.exists(mapdir+indexname):
					print "Advarsel: %s ikke indekseret!" %mapdir[:-1]
				mapdirs.append(mapdir)
			if key=="datafile" and len(line)>0:
				datafile=line[0]
			if key=="districtfile" and len(line)>0:
				districtfile=line[0]
			if key=="minimap" and len(line)>0:
				minimap=line[0]
			if key=="coastline":
				coastline=line[0]
			line=RemRem(f)
	Ini['gpsbaud']=gpsbaud
	Ini['gpsport']=gpsport
	Ini['mapdirs']=mapdirs
	Ini['datafile']=datafile
	Ini['districtfile']=districtfile
	Ini['minimap']=minimap
	Ini['coastline']=coastline
	return Ini
def WriteIni(Ini):
	f=open("VF.ini","w")
	if Ini['gpsport'] is not None:
		f.write("gpsport: %i #virtuel gsp-port\n" %Ini['gpsport'])
	if Ini['gpsport'] is not None:
		f.write("gpsbaud: %i #baudrate for gsp-port\n" %Ini['gpsbaud'])
	dfile=Ini['datafile']
	if dfile is None:
		dfile=""
	f.write("datafile: %s  #sqlite-datafil\n" %dfile)
	dfile=Ini['districtfile']
	if dfile is None:
		dfile=""
	f.write("districtfile: %s #opmaalingsdistrikt (vektor) fil\n" %dfile)
	if Ini['minimap'] is not None:
		f.write("minimap: %s #oversigtskort (geokodet raster-billede)\n" %Ini['minimap'])
	if Ini['coastline'] is not None:
		f.write("coastline: %s  #kystlinie\n" %Ini['coastline'])
	if len(Ini['mapdirs'])==0:
		f.write("mapdir:  #skriv kortmappe (.tif) her\n")
	else:
		for dir in Ini['mapdirs']:
			f.write("mapdir: %s   #kortmappe (.tif)\n" %dir)
	f.close()
	return
	
def main():
	ini=SetUp()
	app = wx.App()
	frame=MainFrame(None,Program,ini)
	app.MainLoop()

if __name__=="__main__":
	main()