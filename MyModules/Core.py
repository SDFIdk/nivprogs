from . import GUIclasses2 as GUI
import os
import sys
import serial
from . import GPS 
from . import MLmap as Map
import wx
import sounddevice as sd
import soundfile as sf
from . import DataClass3 as DataClass
from .GdalMaps import INDEXNAME
from .ExtractKMS import IdenticalTranslation
#We do not want to support pointname translations from to old 'numeric format anymore'
Numformat2Pointname=IdenticalTranslation
Pointname2Numformat=IdenticalTranslation
from .Analysis import GetSummaRho
import time
from . import Funktioner as Fkt
from . import FileOps
import numpy as np
from . import FBtest
import glob
import sqlite3
#no more support for frozen dists...
BASEDIR=os.path.realpath(os.path.join(os.path.dirname(__file__),".."))
DEBUG="debug" in sys.argv
MMDIR=os.path.join(BASEDIR,"mcontent","") 
RESDIR=os.path.join(BASEDIR,"resultatfiler")
RESDIR_SHORT=os.path.basename(RESDIR) #to be shown on screen
IS_PRECISION=False #precision mode means special options in "MakeHead"
PRECISION_LIMIT=2.5
SL="*"*50
#UPDATE THIS STRING ON UPDATE
CORE_VERSION="1.0.1"
#TODO: Logtext in StartFrame not shown 'naar uheldig begyndelsesstoerrelse...'
#Todo: Unicode stuff in filenames and desc. in StartFrame?
#LAST EDIT: 2014-07-08

def SetPrecisionMode(ini,program="MGL"):
	global IS_PRECISION
	if ini.fbunit=="ne" and ini.fbtest<PRECISION_LIMIT and program.upper()=="MGL":
		IS_PRECISION=True
	else:
		IS_PRECISION=False
	return IS_PRECISION


#Ini and status data container classes
		
class StatusData(object): #data-beholder til datatyper faelles for MGL og MTL
	def __init__(self):
		self.Clear()
	def Clear(self):
		self._Clear()
	def _Clear(self):
		self._setups=np.empty((0,2)) #hdiff,dist,type
		self._last_stretch=np.empty((0,2)) #det er nu nemmere at holde data i hukommelsen - dette er seneste skridt mod at holde alt i huk!
		self.Nopst=0 #Alle opst.
		self.Nstraek=0
		self.Dist=0 #total afstand opmaalt
		self.startpunkt=None #aktuelt startpunkt
		self.slutpunkt=None #seneste slutpunkt
		self.Temps=[] #liste med temperaturer
		self.Ttimes=[] #liste med tidspunkter for temp. maalinger
		self.dato=None
		self.starttime=0
		self.projekt="Ikke defineret."
	def GotoNextInstrument(): #implemented for mtl-statusdata
		pass
	def ClearCurrentStretch(self):
		self._setups=np.empty((0,2))
		self.startpunkt=None
	def SetStartTime(self,stime):
		self.starttime=stime
	def SetDate(self,dato):
		if dato!=self.dato:
			self.dato=dato
			self.ResetTemperature()
	def GetDate(self):
		return self.dato
	def GetTimeString(self):
		timer=int(self.starttime)
		min=int((self.starttime-timer)*60)
		return self.dato+" %s:%.02i" %(timer,min)
	def SetStart(self,punkt):
		self.startpunkt=punkt
	def SetEnd(self,punkt):
		self.slutpunkt=punkt
	def GetStart(self):
		return self.startpunkt
	def GetEnd(self):
		return self.slutpunkt
	def ResetTemperature(self):
		self.Temps=[] #liste med temperaturer
		self.Ttimes=[] #liste med tidspunkter for temp. maalinger
	def AddTemperature(self,temp,ttime):
		self.Temps.append(temp)
		self.Ttimes.append(ttime-self.starttime)
	def GetTemperature(self):
		if len(self.Temps)>0:
			return "%.1f" %self.Temps[-1]
		else:
			return "NA"
	def AddSetup(self,hdiff=0,dist=0):
		self._AddSetup(hdiff,dist)
	def _AddSetup(self,hdiff=0,dist=0):
		self._setups=np.vstack((self._setups,[hdiff,dist]))
	def _StartNewStretch(self):
		self.Nopst+=self.GetSetups()
		self.Dist+=self.GetDistance()
		self.Nstraek+=1
		self._last_stretch=np.copy(self._setups)
		self._setups=np.empty((0,2))
		self.startpunkt=None
	def SubtractSetup(self,*args):
		self._SubtractSetup(*args)
	def _SubtractSetup(self,*args):
		self._setups=self._setups[:-1] # deletes last row
	def StartNewStretch(self):
		self._StartNewStretch()
	def SetStartPoint(self,name):
		self.startpunkt=name
	def SetEndPoint(self,name):
		self.slutpunkt=name
	def AddStretch(self,slut,dist,nopst): #not really used anywhere, yet
		self.slutpunkt=slut
		self.Dist+=dist
		self.Nopst+=nopst
		self.Nstraek+=1
	def GetStretches(self):
		return self.Nstraek
	def GetStretchData(self):
		return self.GetHdiff(),self.GetDistance(),self.GetSetups()
	def GetHdiff(self):
		if self._setups.shape[0]>0:
			return self._setups[:,0].sum()
		else:
			return 0.0
	def GetDistanceAll(self):
		return self.Dist
	def GetDistance(self):
		if self._setups.shape[0]>0:
			return self._setups[:,1].sum()
		else:
			return 0.0
	def GetSetupsAll(self):
		return self.Nopst
	def GetSetups(self):
		return self._setups.shape[0]
	def SetProject(self,proj):
		self.projekt=proj
	def GetProject(self):
		return self.projekt
	def GotoNextInstrument(self): #overridden in MTLStatusData
		pass
		
class MGLStatusData(StatusData):
		def __init__(self):
			StatusData.__init__(self)
			self.ddist=[0]
			self.lambdas=[] #list of hd-difs, to monitor instrument 'sinking'. Only relevant for precision modes...
		def AddSetup(self,hdiff=0,dist=0,dd=0,lam=0): #overrides previous
			self.ddist[-1]=dd
			self.ddist.append(0)
			self.lambdas.append(lam)
			self._AddSetup(hdiff,dist)
		def ClearDD(self):
			self.ddist=[0]
		def GetDDSum(self):
			return sum(self.ddist)
		def GetSumLambda(self):
			return sum(self.lambdas)
		def SetLastDD(self,dd):
			self.ddist[-1]=dd
		def SubtractSetup(self,*args):
			self._SubtractSetup(*args)
			self.ddist=self.ddist[0:-1] #we should always have nopst>0 when calling this
			del self.lambdas[-1]
			
#------This class handles MTL "state logic" - here we keep pointers to the instruments also --------------------#			
class MTLStatusData(StatusData):
		def __init__(self):
			StatusData.__init__(self)
			self.instrumentstate=0 #defines which instrument that 'holds the height' (should be 0 or 1 tp point into the instrument list)
			self.instruments=[]
		def SetInstruments(self,instruments): #This must be set before this class can be used to anything
			self.instruments=instruments
		def GetInstruments(self):
			return self.instruments
		def GetInstrumentNames(self):
			return [inst.GetName() for inst in self.instruments]
		def SetInstrumentState(self,state):
			self.instrumentstate=state
		def GetInstrumentState(self):
			return self.instrumentstate
		def GetInstrumentAims(self):
			return np.array([1,-1])*(1-2*self.instrumentstate) #Well, I know that a one-liner can be harder to decode - in essense: aim is [1,-1] or [-1,1]
		def GetDefiningInstrument(self):
			return self.instruments[self.instrumentstate]
		def GetLastBasis(self):
			if self._last_stretch.shape[0]>0:
				return self._last_stretch[-1][0:2]
			return None
		def GotoNextInstrument(self):
			self.instrumentstate=(self.instrumentstate+1)%2
			
			
class Ini(object):
	"""
	Object for holding stuff defined in ini-file - should be overridden by specific program MTL/MGL
	"""
	def __init__(self):
		self.Reset()
		self.fbtest=3.5
		self.fbunit="ne"
		self.project_files=[] #defines files relevant for current project - set up in main window
		self.fb_use_all=False
	def Reset(self):
		#remove things which could be empty with no sensible defaults
		#a subclass may override sensible defaults above and also this method...
		self.mapdirs=[]
		self.database=None
		self.gbsport=-1
		self.gbsbaud=-1

class ProgramType(object):
	def __init__(self):
		self.name="MGL v.1"
		self.type="MGL"
		self.about="Hello world!"
		self.version="0.01"

class ResFile(object):
	def __init__(self,name,fpointer):
		self.fname=name
		self.file=fpointer

class RodBox(wx.ComboBox):  #common box used to select rods in MGL and MTL
	def __init__(self,parent,rods,size=(120,-1),fontsize=12):
		wx.ComboBox.__init__(self,parent,choices=rods,size=size,style=wx.TE_PROCESS_ENTER)
		self.SetFont(GUI.DefaultFont(fontsize))
		self.Bind(wx.EVT_CHAR,self.OnChar)
	def OnChar(self,event):
		key=event.GetKeyCode()
		if key in [wx.WXK_DOWN,wx.WXK_UP]: #kill all other events to make it in practice read only!
			event.Skip()  


# Main window with functionality common to MGL and MTL
class MLBase(GUI.MainWindow): 
	def __init__(self,parent,resfile,database,gps,ini,statusdata,programtype,size=12,**kwargs): #must be called with Ini-data- and additional program specific  args. Size refers to fontsize parameter,,,
		#--SETUP STATE VARS--#
		if statusdata.GetDate() is None:
			statusdata.SetStartTime(Fkt.MyTime()) #tid i timer
			statusdata.SetDate(Fkt.Dato())
		self.starttime=time.asctime()
		self.ini=ini
		self.fbtest=None #will be set up below
		self.statusdata=statusdata #statusdata-klasse, der opbevarer 'status' data
		self.resfile=resfile  #resultatfil 
		self.ini.project_files=[resfile]
		self.program=programtype
		self.size=size
		self.mwindow=GUI.DummyWindow() #both MGL and MTL progs should have a mwindow with a map attr. (when shown)
		#--INIT THE FRAME AND SETUP GUI-STUFF--#
		GUI.MainWindow.__init__(self,parent, title=programtype.name,style=wx.MINIMIZE_BOX|wx.MAXIMIZE_BOX|wx.CLOSE_BOX|wx.RESIZE_BORDER|wx.SYSTEM_MENU|wx.CAPTION|wx.CLIP_CHILDREN)
		self.SetIcon(wx.Icon(MMDIR+"icon.bmp", wx.BITMAP_TYPE_ICO))
		# Setting up the menu.
		self.filemenu= wx.Menu()
		self.anamenu=wx.Menu()
		self.funkmenu=wx.Menu()
		self.punktmenu=wx.Menu()
		about=self.filemenu.Append(wx.ID_ANY, "&About"," Om programmet")
		self.filemenu.AppendSeparator()
		exit=self.filemenu.Append(wx.ID_ANY,"E&xit"," Afslut programmet")
		#Punkt-Menu#
		self.GPSsetup=self.punktmenu.Append(wx.ID_ANY,"Tilslut GPS","Fors\u00F8g at tilutte USB-GPS via virtuel COM-port")
		self.ShowMap=self.punktmenu.Append(wx.ID_ANY,"Vis kort","Viser den aktuelle (gps) position")
		#Analyse-Menu#
		MeasTemp=self.anamenu.Append(wx.ID_ANY,"M\u00E5l temperatur","Opdater temperatur")
		WriteComment=self.anamenu.Append(wx.ID_ANY,"Skriv kommentar til fil","Skriv en kommentar (tryk/temp osv.) til resultatfil")
		self.anamenu.AppendSeparator()
		CompareHdiff=self.anamenu.Append(wx.ID_ANY,"Sammenlign h\u00F8jdeforskelle","Sammenlign m\u00E5lte h\u00F8jdeforskelle med database.")
		SumHeights=self.anamenu.Append(wx.ID_ANY,"Summer h\u00F8jdeforskelle","Beregn lukkesummer etc....")
		ShowFBdata=self.anamenu.Append(wx.ID_ANY,"Vis forkastelseskriterie-database","Viser data i forkastelseskriteriedatabasen.")
		OutlierAnalysis=self.anamenu.Append(wx.ID_ANY,"Forkastelseskriterie-analyse","Foretag en outlier analyse af str\u00E6kninger.") 
		SummaRho=self.anamenu.Append(wx.ID_ANY,"Summa rho-analyse","Foretag en detaljeret summa rho analyse af resultatfilen.")
		#SetProjectFiles=self.anamenu.Append(wx.ID_ANY,u"Definer projekt-resultatfiler",u"Definer resultatfiler til frem/tilbage test.")
		#MakeReject=self.anamenu.Append(wx.ID_ANY,u"Generer forkastelseskriterie-database",u"Genererer sqlite-datafil til test af frem-tilbage m\u00E5linger")
		self.anamenu.AppendSeparator()
		TTgraph=self.anamenu.Append(wx.ID_ANY,"&Temperatur-Tid","Graf over temperatur efter opstart.")
		FBgraph=self.anamenu.Append(wx.ID_ANY,"Plot frem-tilbage testkriterie","Plot af testkriterie.")
		#Rediger-Menu#
		ShowFile=self.funkmenu.Append(wx.ID_ANY,"Vis resultatfil","Viser resultatfilen i et nyt vindue.")
		SkrivJS=self.funkmenu.Append(wx.ID_ANY,"Udskriv journalside","Udksriver journalsider fra datafilen.")
		#SET UP EXTRA MENU ITEMS#
		self.funkmenu.AppendSeparator()
		DeleteLast=self.funkmenu.Append(wx.ID_ANY,"Slet seneste m\u00E5ling","Sletter seneste opstilling i datafilen!")
		DeleteToLastHead=self.funkmenu.Append(wx.ID_ANY,"Slet til seneste hovede","Sletter til seneste hoved i datafilen!")
		EditHead=self.funkmenu.Append(wx.ID_ANY,"Rediger et hoved","Rediger et hovede i datafilen.")
		#TjekPunkter=self.funkmenu.Append(wx.ID_ANY,"Tjek punktnumre",u"Tjek overs\u00E6ttelse af punktnumre i datafilen.")
		TjekJsider=self.funkmenu.Append(wx.ID_ANY,"Tjek journalsider","Tjek journalsider i datafil(er).")
		# Creating the menubar.
		menuBar = wx.MenuBar()
		menuBar.Append(self.filemenu,"&File")
		menuBar.Append(self.funkmenu,"&Rediger")
		menuBar.Append(self.anamenu,"&Analyse")
		menuBar.Append(self.punktmenu,"&Punkter")
		self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
		#Menu-Binding
		self.Bind(wx.EVT_MENU,self.OnExit,exit)
		self.Bind(wx.EVT_MENU,self.OnAbout,about)
		self.Bind(wx.EVT_MENU,self.OnGPSsetup,self.GPSsetup)
		#self.Bind(wx.EVT_MENU,self.OnGPSstop,self.GPSstop)
		self.Bind(wx.EVT_MENU,self.OnShowMap,self.ShowMap)
		self.Bind(wx.EVT_MENU,self.OnMeasTemp,MeasTemp)
		self.Bind(wx.EVT_MENU,self.OnWriteComment,WriteComment)
		self.Bind(wx.EVT_MENU,self.OnCompareHdiff,CompareHdiff)
		self.Bind(wx.EVT_MENU,self.OnSumHeights,SumHeights)
		self.Bind(wx.EVT_MENU,self.OnShowFBdata,ShowFBdata)
		self.Bind(wx.EVT_MENU,self.OnOutlierAnalysis,OutlierAnalysis)
		self.Bind(wx.EVT_MENU,self.OnSummaRho,SummaRho)
		self.Bind(wx.EVT_MENU,self.OnTTgraph,TTgraph)
		self.Bind(wx.EVT_MENU,self.OnFBgraph,FBgraph)
		self.Bind(wx.EVT_MENU,self.OnShowFile,ShowFile)
		self.Bind(wx.EVT_MENU,self.OnSkrivJS,SkrivJS)
		#self.Bind(wx.EVT_MENU,self.OnTjekPunkter,TjekPunkter)
		#self.Bind(wx.EVT_MENU,self.OnMakeReject,MakeReject)
		self.Bind(wx.EVT_MENU,self.OnTjekJsider,TjekJsider)
		self.Bind(wx.EVT_MENU,self.OnEditHead,EditHead)
		self.Bind(wx.EVT_MENU,self.OnDeleteToLastHead,DeleteToLastHead)
		self.Bind(wx.EVT_MENU,self.OnDeleteLastAction,DeleteLast)
		#self.Bind(wx.EVT_MENU,self.OnSetProjectFiles,SetProjectFiles)
		#Logging#
		self.logger = Logger(self,size)
		#Status Bokse#
		self.status1=GUI.StatusBox2(self,["Dato: ","Fil: ","Projekt: ","Temperatur: "],label="Data",colsize=2,fontsize=self.size)
		sl=["Str\u00E6kninger: ","Opm\u00E5lt distance: ","#opstillinger: ","Seneste pkt.: "]
		self.status2=GUI.StatusBox2(self,sl,label="Afsluttede Str\u00E6kninger",colsize=2,fontsize=self.size)
		sl=["Punkt: ","\u2206H: ","#opstillinger: ","Afstand: "]
		self.status3=GUI.StatusBox2(self,sl,label="Aktuel Str\u00E6kning",colsize=2,fontsize=self.size)
		self.sizer=wx.BoxSizer(wx.HORIZONTAL)
		self.rightsizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.logger,1,wx.EXPAND|wx.ALL,5)
		self.rightsizer.Add(self.status1,1,wx.EXPAND|wx.ALL,5)
		self.rightsizer.Add(self.status2,1,wx.EXPAND|wx.ALL,5)
		self.rightsizer.Add(self.status3,1,wx.EXPAND|wx.ALL,5)
		self.sizer.Add(self.rightsizer,1,wx.EXPAND|wx.ALL,5)
		#Setup Point Data#
		self.data=database
		#Setup The Map#
		self.map=Map.MapFrame(self,"Kort",self.data,self.ini.mapdirs)
		#Setup GPS#
		self.gps=gps
		self.Bind(GPS.EVT_LOG,self.OnEvtLog)
		self.Bind(GPS.EVT_KILL_GPS,self.OnGPSKill)
		self.gps.DefineParent(self)
		self.gps.start()
		self.map.AttachGPS(self.gps)
		#update#
		self._UpdateStatus()
		#set and log status.
		self.Log("%s %s igangsat %s." %(self.program.name,self.program.version,self.starttime))
		self.Log("Core.py version: %s" %CORE_VERSION)
		self.Log("Punktnumre / navne overs\u00E6ttes ikke mere. What you see is what you get!")
		self.AttachFBtest()
		if self.data is None or not self.data.IsInitialized():
			self.map.DisablePoints()
			self.Log("Punktdatabase ikke tilsluttet.")
			self.data=None
		else:
			self.Log("Punktdatabase tilsluttet.")
		#On Close kill gps
		self.Bind(wx.EVT_CLOSE,self.OnClose)
		if DEBUG:
			debug_win=GUI.DebugWindow(self)
			debug_win.BindEnter(self.OnDebugCMD)
	def OnDebugCMD(self,event):
		field=event.GetEventObject()
		text=field.GetValue()
		try:
			exec(text)
		except Exception as msg:
			print(msg)
		else:
			field.Clear()
		
	def OnClose(self,event):
		self.gps.kill()
		if self.gps.is_alive():
			self.gps.join()
		event.Skip()
	def UpdateStatus(self): #should be overruled bu subclasses
		self.UpdateStatus()
	def _UpdateStatus(self):
		data=self.statusdata
		hdiff,dist,nopst=data.GetStretchData()
		project=data.GetProject()
		if len(project)>18:
			project=project[0:17]+"..."
		self.status1.UpdateStatus([Fkt.Dato(),os.path.basename(self.resfile),project,data.GetTemperature()])
		self.status2.UpdateStatus([str(data.GetStretches()),"%.2f m" %data.GetDistanceAll(),str(data.GetSetupsAll()),data.GetEnd()])
		self.status3.UpdateStatus([data.GetStart(),"%.4f m" %hdiff, str(nopst),"%.2f m"%dist])
		self.SetSizer(self.sizer)
		self.sizer.FitInside(self)
	def OnEvtLog(self,event):
		self.Log(event.text)
	def Log(self,text):
		self.logger.AppendText(text+"\n")
	def OnExit(self,e):
		#self.resfile.file.close()
		self.Close()
	def OnAbout(self,e):
		aboutstr=self.program.about
		title=self.program.name
		d= wx.MessageDialog( self, aboutstr,title, wx.OK)
		d.ShowModal() 
		d.Destroy() 
	#-------GPS SETUP FUNKTIONER-----------#
	def OnGPSsetup(self,event):
		dlg=GUI.InputDialog(self,"Tilslut GPS",numlabels=["Virtuel COM-port:","Baudrate:"],bounds=[(1,100),(0,128000)],numvalues=[self.ini.gpsport,self.ini.gpsbaud])
		dlg.ShowModal()
		if dlg.WasOK():
			vals=dlg.GetNumValues()
			port=int(vals[0])-1 #Python indeksering af porte! -1 fjernet
			baud=int(vals[1])
			self.Log("Fors\u00F8ger tilslutning af GPS med port %i, baudrate %i"%(port+1,baud))
			self.gps=GPS.GpsThread(self,port,baud)
			self.gps.start()
			self.map.AttachGPS(self.gps)
		dlg.Destroy()
		self._UpdateStatus()	
	
	def OnGPSKill(self,event):
		self.Log("GPS ikke tilsluttet.")
		self.gps=GPS.DummyThread()
		self.map.DetachGPS()
		if self.mwindow.IsShownOnScreen(): #this frame handles gps-kill events for the mwindow also
			try:
				self.mwindow.map.DetachGPS()
			except:
				pass
	#-----KORT FUNKTIONER-------------------#
	def OnShowMap(self,event):
		self.map.Show()
		self.map.Maximize(0)
		self.map.Center()
	def GetNetData(self):
		if self.fbtest is None or self.data is None:
			return [],[]
		lines=list(self.fbtest.GetDatabase().keys())
		stations=[x[0] for x in lines]
		stations.extend([x[1] for x in lines])
		stations=list(map(Numformat2Pointname,stations))
		unique_stations=list(set(stations))
		data=self.data.GetManyCoordinates(unique_stations)
		s_lines=[np.empty((0,2)),np.empty((0,2))]
		d_lines=[np.empty((0,2)),np.empty((0,2))]
		s_data=dict()
		for station,x,y in data:
			s_data[Pointname2Numformat(station)]=(x,y)
		for line in lines:
			s1,s2=line
			if s1 in s_data and s2 in s_data:
				fromp=s_data[s1]
				top=s_data[s2]
				if (s2,s1) in lines:
					d_lines[0]=np.vstack((d_lines[0],fromp))
					d_lines[1]=np.vstack((d_lines[1],top))
				else:
					s_lines[0]=np.vstack((s_lines[0],fromp))
					s_lines[1]=np.vstack((s_lines[1],top))
		return s_lines,d_lines
					
					
				
		
		
			
	#-------ANALYSEFUNKTIONER------------#
	def OnSumHeights(self,e):
		AnalyserNet(self,self.resfile)
	def SumHeights(self,fil):
		heads=FileOps.Hoveder(fil)
		if len(heads)==0:
			dlg=MyMessageDialog(self,"Fejl","Ingen hoveder fundet i filen!")
			dlg.ShowModal()
			dlg.Destroy()
			return
		msg=FileOps.FilStatus(fil)
		dlg = MySumDialog( self, "Summer H\u00F8jdeforskelle.",msg+"V\u00E6lg str\u00E6kning(er):", heads)
		dlg.ShowModal()
	def OnCompareHdiff(self,event):
		if self.data is not None:
			CompareHdiffs(self,self.resfile,self.data)
		else:
			self.Log("Punktdatabase ikke tilsluttet.")
	def OnMakeReject(self,event):
		#deprecated#
		pass
	def OnSetProjectFiles(self,event):
		#deprecated#
		pass
	def AttachFBtest(self,resfiles=None):
		if resfiles is None:
			if self.ini.fb_use_all:
				resfiles=GetResultFiles(self.program.type)
			else:
				resfiles=[self.resfile]
		data,nerrors=FBtest.MakeRejectData(resfiles)
		self.fbtest=FBtest.FBreject(data,self.program.type,self.ini.fbtest,self.ini.fbunit)
		self.Log("Dannede forkastelseskriterie database med %d resultatfil(er) og %d str\u00E6kninger." %(len(resfiles),len(data)))
		if nerrors>0:
			self.Log("%d fejl i l\u00E6sning af filer ved dannelse af database..." %nerrors)
		if DEBUG:
			self.Log("%s" %repr(resfiles))
			self.Log(repr(data))
			self.ShowFBdata()
		self.ini.project_files=resfiles #might be useful!
	def OnShowFBdata(self,event):
		self.ShowFBdata()
		
	def ShowFBdata(self):
		if self.fbtest is None:
			GUI.ErrorBox(self,"Forkastelsesdatabase ikke defineret!")
			return
		dlg=GUI.MyLongMessageDialog(self,"Forkastelseskriterie-database",self.fbtest.GetData(),size=(800,-1))
		dlg.ShowModal()
		dlg.Destroy()
	
	def OnOutlierAnalysis(self,event):
		if self.fbtest is None:
			GUI.ErrorBox(self,"Forkastelsesdatabase ikke defineret!")
			return
		OK,msg=self.fbtest.OutlierAnalysis()
		if OK:
			GUI.Message(self,msg,"Outlier Analyse")
			return
		dlg=GUI.MyLongMessageDialog(self,"Frem-tilbage/outlier Analyse",msg,size=(800,-1))
		dlg.ShowModal()
		dlg.Destroy()
	def OnSummaRho(self,event):
		ok,msg=GetSummaRho(self.resfile)
		if ok:
			dlg=GUI.MyLongMessageDialog(self,"Summa rho analyse",msg,size=(800,-1))
			dlg.ShowModal()
			dlg.Destroy()
		else:
			GUI.ErrorBox(self,msg)
	def OnMeasTemp(self,e):
		tframe=GUI.InputDialog(self,title="Temperaturm\u00E5ling",numlabels=["Temperatur: "],bounds=[(-50,55)],pedantic=True)
		tframe.ShowModal()
		if tframe.WasOK():
			t=tframe.GetNumValues()[0]
			self.statusdata.AddTemperature(t,Fkt.MyTime())
			self._UpdateStatus()
			f=open(self.resfile,"a")
			f.write("T: %.1f  %s\n" %(t,Fkt.Nu()))
			f.close()
		tframe.Destroy()
	def OnTTgraph(self,event):
		theplot=GUI.PlotFrame(self,title="Temperaturgraf")
		theplot.PlotData(self.statusdata.Ttimes,self.statusdata.Temps,"Temperatur v. tid",'Timer efter opstart '+self.statusdata.GetTimeString())
	def OnFBgraph(self,event):
		theplot=GUI.PlotFrame(self,title="Forkastelseskriterie")
		theplot.plotter.SetEnableLegend(True)
		unit=self.ini.fbunit
		par=self.ini.fbtest
		n=5
		step=par*0.2
		plot_range=[par+step*i for i in range(-2,n-2)]
		graphics=[]
		colors=["blue","red","green","black","orange","cyan","pink"]
		next=0
		for param in plot_range:
			col=colors[next % len(colors)]
			data=FBtest.GetPlotData(self.program.type,param,unit)
			line = GUI.plot.PolyLine(data, colour=col, width=1,legend="%.2f %s" %(param,unit))
			graphics.append(line)
			next+=1
		line_global_min=GUI.plot.PolyLine(FBtest.GetGlobalMinLine(self.program),colour="lightblue",legend="bagatelgr\u00E6nse")
		graphics.append(line_global_min)
		gc = GUI.plot.PlotGraphics(graphics,"Plot af forkastelseskriterie","Afstand [m]","Tolerance [mm]")
		theplot.plotter.Draw(gc)
	def OnWriteComment(self,e):
		dlg=GUI.InputDialog(self,"Skriv kommentar i fil",["Kommentar:"])
		dlg.ShowModal()
		if dlg.OK:
			kom=dlg.GetTextValues()[0]
			f=open(self.resfile,"a")
			f.write(";%s\n" %kom)
			f.close()
			self.Log("Skriver %s til fil." %kom)
		dlg.Destroy()
	
	#------REDIGERINGSFUNKTIONER-----------#
	def OnSkrivJS(self,e): #skriv en specificeret Jside.
		heads=FileOps.Hoveder(self.resfile)
		if len(heads)==0:
			dlg=GUI.MyMessageDialog(self,"Fejl","Ingen hoveder fundet i filen!")
			dlg.ShowModal()
			dlg.Destroy()
			return
		list=[felt[6] for felt in heads]
		dlg = GUI.MyMultiChoiceDialog( self,
		"Udskriv journalside(r).",  "V\u00E6lg journalside(r):",list)
		#dlg.SetFont(wx.Font(14,wx.SWISS,wx.NORMAL,wx.NORMAL))
		dlg.ShowModal()
		if DEBUG:
			mode=3
		else:
			mode=2
		if dlg.OK:
			selections = dlg.GetSelections()
			if len(selections)>0:
				strings = [list[x] for x in selections]
				for JS in strings:
					try:
						OK=FileOps.Jside(self.resfile,mode,JS,self.program.type)  #Kald med mode2, saa soeges efter Jsidenr...mode 3=test
					except:
						GUI.ErrorBox(self,"Fejl under udskrivning...")
					else:	
						if not OK:
							dlg2=GUI.MyMessageDialog(self,"Fejl","Kunne ikke finde journalsiden %s i resultatfilen!"%JS)
							dlg2.ShowModal()
							dlg2.Destroy()
						else:
							self.Log("Udskriver journalside %s.\n" %JS)
				
		dlg.Destroy()
	
	def OnTjekJsider(self,e):
		files=SelectResultFiles(self,self.program.type)
		if len(files)>0:
			nerrors,msg=TjekJsider(files)
			if nerrors>0:
				msg="Fandt %i journalsidefejl:\n"%nerrors+msg
				dlg=GUI.MyLongMessageDialog(self,title="Journalsidetjek",msg=msg,size=(800,-1),fontsize=11)
			else:
				dlg=GUI.MyMessageDialog(self,title="Journalsidetjek",msg="Alle journalsider tilsyneladende OK.")
			dlg.ShowModal()
			dlg.Destroy()
	def OnShowFile(self,e):
		win=GUI.FileWindow(self,"Resultatfil",self.resfile)
		win.Show()
	#These methods not activated in Core class#
	def OnEditHead(self,e):
		self.EditHead()
	def OnDeleteToLastHead(self,e):
		if self.statusdata.GetSetups()>0:
			self.DeleteToLastHead()
		else:
			GUI.ErrorBox(self,"Der er ingen m\u00E5linger efter seneste hovede.")
	def OnDeleteLastAction(self,e):
		if self.statusdata.GetSetups()>0:
			self.DeleteLastAction()
		else:
			GUI.ErrorBox(self,"Kan ikke slette f\u00F8r seneste hovede.\nRediger selv i datafilen og tilslut.") 
	def EditHead(self):
		heads=FileOps.Hoveder(self.resfile)
		if len(heads)==0:
			dlg=GUI.ErrorBox(self,"Ingen hoveder fundet i resultatfilen.")
			return
		choices=["Fra %s til %s. J.side: %s" %(head[0],head[1],head[6]) for head in heads]
		dlg=GUI.MySingleChoiceDialog(self,"Hoveder","v\u00E6lg et hovede",choices)
		dlg.ShowModal()
		if not dlg.WasOK():
			dlg.Destroy()
			return
		sel=int(dlg.GetSelection())
		head=heads[sel]
		dlg.Destroy()
		dlg=GUI.InputDialog(self,"Rediger hovede",["Fra:","Til:","dato:","tid:","journalside:"],head[0:4]+[head[6]],["Afstand:","Hdiff:","Temp:",
		"#opst:"],head[4:6]+head[7:9],[(0,100000),(-10000,10000),(-100,100),(0,1000)])
		dlg.ShowModal()
		if not dlg.WasOK():
			dlg.Destroy()
			return
		textvals=dlg.GetTextValues()
		numvals=dlg.GetNumValues()
		dlg.Destroy()
		newhead=textvals[0:4]+numvals[0:2]+[textvals[4]]+numvals[2:]
		self.Log("Erstatter hovede: %s" %(choices[sel]))
		FileOps.EditHead(self.resfile,sel,newhead)
	def DeleteToLastHead(self):
		if not GUI.YesNo(self,"Er du sikker p\u00E5 at du vil slette?","Slet til hovede."):
			return
		self.statusdata.ClearCurrentStretch()
		FileOps.DeleteToLastHead(self.resfile)
		self.Log(SL)
		self.Log("Sletter til seneste hovede. Tjek evt. resultatfil i menupunkt 'rediger'.")
		self.UpdateStatus()
	def DeleteLastAction(self):
		nopst=self.statusdata.GetSetups()
		if nopst==0:
			return
		if not GUI.YesNo(self,"Er du sikker p\u00E5 at du vil slette?","Slet seneste m\u00E5ling."):
			return
		if nopst==1:
			self.statusdata.ClearCurrentStretch()
		elif nopst>1:
			self.statusdata.GotoNextInstrument()
			self.statusdata.SubtractSetup()
		FileOps.DeleteLastAction(self.resfile)
		self.Log(SL)
		self.Log("Sletter seneste m\u00E5ling. Tjek evt. resultatfil i menupunkt 'rediger'.")
		self.UpdateStatus()
	

class FilPanel(wx.Panel):
	def __init__(self, parent,size=12):
		wx.Panel.__init__(self,parent)
		self.fields=GUI.EditFields(self,textlabels=["Resultatfil:","Projektbeskrivelse:"],textsize=200,fontsize=size)  #ændret
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.field1=self.fields.field[0]
		self.field2=self.fields.field[1]
		self.knap=GUI.MyButton(self,"F\u00F8j til eksisterende fil",size)
		self.sizer.Add(self.fields,1,wx.ALL,5)
		self.sizer.Add(self.knap,0,wx.ALL,5)
		self.SetSizer(self.sizer)
		self.fields.DefineNextItem(self.knap)
	def Validate(self):
		return self.fields.Validate()
	def GetValues(self):
		return self.fields.GetTextValues()
		
class StartFrame(wx.Frame): #a common GUI-base class for setting up things
	def __init__(self,parent,program,inireader,statusdata): #inireader is a function handle to something reading an ini-file. inipath is used to check if the inifile really exists
		#set font sizes. Smaller for bad resolution, to enable things to fit on screen...
		dsize=wx.GetDisplaySize()
		if dsize[1]<800 or dsize[0]<1200:
			self.size=10
		else:
			self.size=12
		#Init data
		self.startstate=True #are we ready to start the program?
		self.parent=parent
		self.program=program
		self.data=None
		self.inireader=inireader #handle to function reading ini-file
		self.statusdata=statusdata
		#Set FBtest database#
		#SetTestFile(program.type)
		#Init the Frame#
		wx.Frame.__init__(self,parent,title=program.name)
		#Appeareance
		self.SetBackgroundColour("light gray")
		self.SetIcon(wx.Icon(MMDIR+"icon.bmp", wx.BITMAP_TYPE_ICO))
		#Setup gps+Instruments
		self.Setup() #after init, because GPS needs a window as parent... And before StausBox2....
		statusline=["GPS:"]
		for inst in self.instruments:
			statusline.append(inst.GetName()+":")
		self.portstatus=GUI.StatusBox2(self,statusline,colsize=1,label="Port-status",fontsize=self.size) # a port statusline in the top
		self.portstatus.UpdateStatus()
		self.log=wx.TextCtrl(self,style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_RICH2)
		self.log.SetFont(wx.Font(self.size-1,wx.MODERN,wx.NORMAL,wx.NORMAL))
		#self.criterium=GUI.EditFields(self,textlabels=["Forkastelseskriterie:"],textvalues=["%.2f %s"%(self.ini.fbtest,self.ini.fbunit)],fontsize=self.size,textsize=100)
		self.maalere=GUI.EditFields(self,textlabels=["M\u00E5ler-1:","M\u00E5ler-2:"],fontsize=self.size,style='horizontal',textsize=100)
		self.fil=FilPanel(self,size=self.size)
		buttons=GUI.ButtonPanel(self,["START","OPDATER"],fontsize=self.size)
		self.startbutton=buttons.button[0]
		self.updatebutton=buttons.button[1]
		self.fil.knap.Bind(wx.EVT_BUTTON,self.OnAddToFile)
		self.updatebutton.Bind(wx.EVT_BUTTON,self.OnUpdateButton)
		self.startbutton.Bind(wx.EVT_BUTTON,self.OnStart)
		#Set up browsing
		#self.criterium.DefineNextItem(self.maalere)
		self.maalere.DefineNextItem(self.fil.field1)
		self.fil.field2.next=self.startbutton #if we hit return
		self.fil.field2.nexttab=self.fil.knap #if we are tabbinng
		self.maalere.SetFocus()
		#Set up sizers
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.portstatus,0,wx.ALL,3)
		self.sizer.Add(self.log,10,wx.ALL|wx.EXPAND,5)
		#self.sizer.Add(self.criterium,0,wx.ALL,3)
		self.sizer.Add(self.maalere,0,wx.ALL,3)
		self.sizer.Add(self.fil,0,wx.ALL,3)
		self.sizer.Add(buttons,0,wx.ALL,3)
		self.sizer.Add((-1,20),1,wx.EXPAND)
		dsize=dsize-(20,20)
		self.SetSize(dsize)
		self.SetSizer(self.sizer)
		self.sizer.FitInside(self)
		#self.Show()
		self.Center()
		#Get status and print stuff in log
		self.Log("Initialiserer:")
		self.TestPorts()
		self.LogStatus()
		self.Refresh()
	def TestPorts(self):
		states=[self.gps.TestConnection()]
		for inst in self.instruments:
			states.append(inst.TestPort())
		self.portstatus.UpdateStatus(states=states)
	def OnUpdateButton(self,event):
		#self.log.Clear()
		self.Log("Initialiserer:")
		self.Setup()
		self.TestPorts()
		self.LogStatus()
		self.log.Refresh()
	def Setup(self):
		if self.data is not None:
			self.data.Disconnect()
		if not os.path.exists(self.inireader.path):
			GUI.ErrorBox(None,"Ini-filen %s eksisterer ikke!\nKan ikke starte programmet." %self.inireader.path)
			self.Close()
		try:
			self.ini,self.instruments,self.laegter=self.inireader.Read()
		except Exception as msg:
			GUI.ErrorBox(None,"Fejl under l\u00E6sning af ini-fil:\n%s\nKan ikke starte programmet."%str(msg))
			self.Close()
		else:
			#Setup GPS#
			self.gps=GPS.GpsThread(None,self.ini.gpsport,self.ini.gpsbaud) #parent should be None here - because the real parent
			self.data=DataClass.PointData(self.ini.database)  #is the MLBase-frame which gets the gps as input. 
		#decide whether precision_mode should be set#
		SetPrecisionMode(self.ini,self.program.type)
		if DEBUG:
			for key in list(self.ini.__dict__.keys()):
				print(key,self.ini.__dict__[key])
		
		
	def LogStatus(self):
		for inst in self.instruments:
			self.Log(inst.PresentYourself())
		self.Log("GPS: port %i, baudrate %i" %(self.ini.gpsport,self.ini.gpsbaud))
		if self.gps.GetConnectionStatus():
			self.Log("GPS-enheden er tilsluttet.")
		else:
			self.Log("GPS-enheden er ikke tilsluttet.","RED")
		self.Log("L\u00E6gter:")
		for laegte in self.laegter:
			self.Log("%s" %laegte.PresentYourself())
		self.Log("Forkastelseskriterie for frem-tilbage str\u00E6kninger: %.2f %s" %(self.ini.fbtest,self.ini.fbunit))
		if IS_PRECISION:
			self.Log("Der m\u00E5les i pr\u00E6cisions-tilstand.")
		for mappe in self.ini.mapdirs:
			if mappe[-1] not in ["/","\\"]:
					mappe+="/"
			if not os.path.exists(mappe+INDEXNAME):
				warn="ikke indekseret!"
				style="RED"
			else:
				warn="OK."
				style=None
			self.Log("Kortmappe: %s, %s" %(mappe[:-1],warn),style=style)
		self.Log("Database: %s" %self.ini.database)
		if not os.path.exists(self.ini.database):
			self.Log("Database eksisterer ikke!","RED")
		elif self.data is not None and self.data.IsInitialized():
			self.Log("Database tilsluttet.")
		if not os.path.exists(RESDIR):
			self.Log("%s findes ikke. Genererer mappen..." %RESDIR_SHORT)
			os.mkdir(RESDIR)
		for inst in self.instruments:
			if inst.GetPortStatus():
				msg="OK."
				style=None
			else:
				msg="kunne ikke \u00E5bnes!"
				style="RED"
			self.Log("%s: port %i %s" %(inst.GetName(),inst.GetPort(),msg),style=style)
		resfiles=GetResultFiles()
		if self.ini.fb_use_all:
			self.Log("Bruger ALLE %d resultatfiler i mappen %s til frem/tilbage-test." %(len(resfiles),RESDIR_SHORT))
		else:
			self.Log("Bruger kun den aktuelle resultatfil til frem/tilbage-test.")
		if hasattr(self.ini,"angle_unit"):
			self.Log("Bruger vinkelenhed: %s" %self.ini.angle_unit)
		if hasattr(self.ini,"use_corrections"):
			if not self.ini.use_corrections:
				self.Log("NB: Korrektioner er sl\u00E5et FRA!")
		self.Log("Dette kan reguleres i ini-filen....")
		
	def OnStart(self,event):
		self.startstate=(self.maalere.Validate() and self.fil.Validate())
		if self.startstate:
			m1,m2=self.maalere.GetTextValues()
			fname,bsk=self.fil.GetValues()
			self.resfile=os.path.join(RESDIR,fname)
			if os.path.exists(self.resfile):
				dlg=GUI.OKdialog(self,"Bem\u00E6rk!","\nFilen findes allerede.\nVil du tilslutte til den?")
				dlg.ShowModal()
				OK=dlg.WasOK()
				dlg.Destroy()
				if OK:
					self.AddToFile()
				else:
					self.fil.field1.Clear()
			else:
				self.InitResultFile(self.resfile,m1,m2,bsk)
				self.StartProgram()
	
	def InitResultFile(self,fname,m1="a",m2="b",bsk="test"):
		resfil=open(fname,"w")
		#Start resultatfil#
		resfil.write("%*s %s %s %s\n"%(-19,"Program:",self.program.name,self.program.version,self.program.date))
		resfil.write("%*s %s\n"%(-19,"Filnavn:",fname))
		resfil.write("%*s %s\n" %(-19,"Projektbeskrivelse:",bsk))
		resfil.write("%*s %s %s\n" %(-19,"Dato og tid:",Fkt.Dato(),Fkt.Nu()))
		resfil.write("%*s %s %s\n" %(-19,"Maalerinitialer:",m1,m2))
		for instrument in self.instruments:
			resfil.write("%s\n" %instrument.PresentYourself(short=True))
		resfil.write("Laegter:\n")
		for laegte in self.laegter:
			resfil.write("%s\n" %laegte.PresentYourself())
		resfil.write("%*s %.2f %s\n" %(-19,"Forkastelseskriterie:",self.ini.fbtest,self.ini.fbunit))
		resfil.write("* Slut paa header\n")
		self.statusdata.SetProject(bsk)
		resfil.close()
		
	def StartProgram(self): #should be overridden by subclass -append is a flag to see if we are appending to a file
		pass
	def OnAddToFile(self,event):
		dlg = wx.FileDialog(self, message="V\u00E6lg en fil",defaultDir=RESDIR, defaultFile="",
		wildcard="*.*",
		style=wx.FD_OPEN)
		if dlg.ShowModal()==wx.ID_OK:
			fname=dlg.GetFilename()
			dir=dlg.GetDirectory()
			if os.path.realpath(dir)==os.path.realpath(RESDIR):
				if fname.find("backup")!=-1:
					GUI.ErrorBox(self,"Backup filen skal omd\u00F8bes, inden der kan tilsluttes til den.")
				else:
					self.resfile=RESDIR+"/"+fname
					self.fil.field1.SetValue(fname)
					self.fil.field2.SetValue("")
					dlg.Destroy() #since we might not return here
					self.AddToFile()
			else:
				GUI.ErrorBox(self,"Resultatfilen skal ligge i %s." %RESDIR_SHORT)
		else:
			dlg.Destroy()
	def AddToFile(self):
		if True:#try:
			isres,isok,msg=FileOps.ReadResultFile(self.resfile,self.statusdata,self.instruments,self.program.type)  #was self.filereader(self.resfile,self.statusdata)
		else: #except Exception,msg:
			GUI.ErrorBox(self,"Fejl under l\u00E6sning af fil:\n %s\nMuligvis er den forkert formateret." %str(msg))
			return
		if isres:
			data=self.statusdata
			self.fil.field2.SetValue(data.GetProject()) #.decode('utf-8') NEW
			imsg="Data for resultatfil:\n"
			imsg+="Projekt: %s\n" %data.GetProject() #.decode('utf-8')
			imsg+="Afsluttede Str\u00E6k: %i\n#Opst.: %i\nSamlet afstand %.2f m\n" %(data.GetStretches(),data.GetSetupsAll(),data.GetDistanceAll())
			if data.GetSetups()>0:
				imsg+="Uafsluttet str\u00E6kning:\n"
				imsg+="Fra: %s, #opst: %i, afstand: %.2f m\n" %(data.GetStart(),data.GetSetups(),data.GetDistance())
			msg=imsg+msg+"\n\nVil du tilslutte til filen?"
			dlg=GUI.OKdialog(self,"Bem\u00E6rk!",msg)
			dlg.ShowModal()
			OK=dlg.WasOK()
			dlg.Destroy()
			if OK:
				self.StartProgram()
			else:
				self.fil.field1.Clear()
				self.fil.field2.Clear()
				data.Clear()
		else:
			GUI.ErrorBox(self,"Filen er tilsyneladende ikke en korrekt resultatfil.")
			
	def Log(self,text,style=None): 
		start=self.log.GetLastPosition()
		self.log.AppendText(text+"\n")
		end=self.log.GetLastPosition()
		if style is not None:
			self.log.SetStyle(start,end,wx.TextAttr(style))
		self.log.Refresh()	
		
#--------------------------------------------------#		
#varoious analysis and data control functions#
#------------------------------------------------#

def CompareHdiffs(win,file,data): #a bit messy, could be better
	selections=[]
	heads=FileOps.Hoveder(file)
	if len(heads)==0:
		GUI.ErrorBox(win,"Ingen hoveder fundet i filen!")
		return
	list=["Fra %s til %s" %(felt[0],felt[1]) for felt in heads]
	msg=FileOps.FilStatus(file)
	dlg = GUI.MyMultiChoiceDialog( win, "Sammenlign H\u00F8jdeforskelle.", msg+"V\u00E6lg str\u00E6kning(er):", list)
	dlg.ShowModal()
	if dlg.WasOK():
		selections = dlg.GetSelections()
	if len(selections)>0:
		Fra=dict()
		Til=dict()
		valgte=[]
		for i in selections:
			valgte.append(heads[i])
			Fra[heads[i][0]]=-999 #ogsaa nodata-value i datafil!
			Til[heads[i][1]]=-999
		FindFra=list(map(Numformat2Pointname,list(Fra.keys())))
		FindTil=list(map(Numformat2Pointname,list(Til.keys()))) 
		FraH=data.GetHeights(FindFra)
		TilH=data.GetHeights(FindTil)
		notfoundfra=[]
		notfoundtil=[]
		for h,valgt in zip(FraH,list(Fra.keys())):
			Fra[valgt]=h
			if h is None or h<-100: #means not found or no height
				notfoundfra.append(valgt)
		for h,valgt in zip(TilH,list(Til.keys())):
			Til[valgt]=h
			if h is None or h<-100:
				notfoundtil.append(valgt)
		notfound=set(notfoundfra).union(set(notfoundtil))
		msg=""
		for hoved in valgte:  #definer MyLongMessageDialog...
			hfra=Fra[hoved[0]]
			htil=Til[hoved[1]]
			if (hfra is not None and hfra>-100) and (htil is not None and hfra>-100):  #nodata-value
				msg+="Fra %s til %s:\n" %(hoved[0],hoved[1])
				h_db=htil-hfra
				h_m=float(hoved[5])
				diff=(h_m-h_db)*1e3
				ne=abs(diff)/np.sqrt(float(hoved[4])*1e-3)
				msg+="M\u00E5lt: %s m, Database: %.4f m, diff: %.2f mm, %.2f ne\n" %(hoved[5],h_db,diff,ne)
		if len(notfound)>0:
			msg+="F\u00F8lgende punkters koter blev ikke fundet i databasen:\n"
			for station in notfound:
				msg+=station+"\n"
		dlg2=GUI.MyLongMessageDialog(win,"Sammenligning af h\u00F8jder.",msg,12)
		dlg2.ShowModal()
		dlg2.Destroy()
	dlg.Destroy()


def AnalyserNet(win,fil):
	heads=FileOps.Hoveder(fil)
	if len(heads)==0:
		dlg=GUI.MyMessageDialog(win,"Fejl","Ingen hoveder fundet i filen!")
		dlg.ShowModal()
		dlg.Destroy()
		return
	msg=FileOps.FilStatus(fil)
	dlg = MySumDialog( win, "Summer H\u00F8jdeforskelle.",msg+"V\u00E6lg str\u00E6kning(er):", heads)
	dlg.ShowModal()


					
					
				
		
def TjekJsider(files): #tjekker journalsider i en liste af res-filer.
	con=sqlite3.connect(":memory:")
	cur=con.cursor()
	cur.execute("CREATE TABLE head (start TEXT, end TEXT,date TEXT, hdiff REAL, jside TEXT, file TEXT)")
	ndone=0
	Jsides=dict()
	nerrors=0
	msg=""
	for file in files:
		heads=FileOps.Hoveder(file)
		for head in heads:
			jside=head[6]
			fra=head[0]
			til=head[1]
			err=False
			spl=jside.split(".")
			if len(spl)!=2:
				err=True
			else:
				try:
					ext=int(spl[1])
				except:
					err=True
			if err:
				nerrors+=1
				msg+="Ukurankt journalside: %s, str\u00E6kning: %s til %s, fil: %s\n" %(jside,fra,til,os.path.basename(file))
			else:
				cur.execute("INSERT INTO head VALUES (?,?,?,?,?,?)",(fra,til,head[2],float(head[5]),jside,os.path.basename(file))) #this first
				jside=spl[0]
				if jside in Jsides:
					Jsides[jside].append(ext)
				else:
					Jsides[jside]=[ext]
				
				ndone+=1
	con.commit()
	for jside in list(Jsides.keys()):
		data=Jsides[jside]
		data.sort()
		if data[0]!=1 or len(data)!=data[len(data)-1]:
			nerrors+=1
			msg+="Fejl ved journalside %s, f\u00F8lgende sider fundet:\n" %(jside)
			pattern="%s%s" %(jside,"%")
			cur.execute("SELECT * FROM head WHERE jside like ?",(pattern,))
			found=cur.fetchall()
			if found is not None and len(found)>0:
				for this in found:
					msg+="Fra %s til %s, dato: %s, jside: %s, fil:%s\n" %(this[0],this[1],this[2],this[4],this[5])
	cur.close()
	con.close()
	return nerrors,msg
	
	
	

#---Dialog for summation of measured 'stretches'---#
class MySumDialog(GUI.TwoButtonDialog):
	def __init__(self,parent,title,msg="",heads=[],fontsize=12):
		self.heads=heads
		GUI.TwoButtonDialog.__init__(self,parent,title=title)
		text=GUI.MyText(self,msg,fontsize)
		list=["Fra %s til %s" %(felt[0],felt[1]) for felt in heads]
		self.lb=wx.CheckListBox(self,choices=list,size=(300,-1))
		self.lb.Bind(wx.EVT_CHECKLISTBOX,self.OnCheck)
		self.result1=GUI.MyText(self,"Sum:  ",12)
		self.result2=GUI.MyText(self,"Sum/sqrt(afst):  ",12)
		self.InsertObject(self.result2,0,wx.ALL,10)
		self.InsertObject(self.result1,0,wx.ALL,10)
		self.InsertObject(self.lb,1,wx.ALL,10)
		self.InsertObject(text,0,wx.ALL,10)
		self.SetSizerAndFit(self.sizer)
	def OnCheck(self,event):
		sum=0
		dist=0
		for i in range(0,len(self.heads)): #I'm sure there should be a shortcut but somehow GetSelections doesn't seem to work!
			if self.lb.IsChecked(i):
				sum+=float(self.heads[i][5])  #hoejdeforskel
				dist+=float(self.heads[i][4])**2
		dist=np.sqrt(dist)
		self.result1.SetLabel("Sum: %.4f m" %sum)
		self.result2.SetLabel("Sum/sqrt(afst): %.4f m/sqrt(km)" %(sum/dist*1000))


def GetResultFiles(program="MGL"):
	allfiles=glob.glob(RESDIR+"/*")
	goodfiles=[]
	for fname in allfiles:
		if FileOps.TjekHeader(fname,program):
			goodfiles.append(fname)
	return goodfiles

def SelectResultFiles(win,program="MGL"):
	goodfiles=GetResultFiles()
	if len(goodfiles)==0:
		GUI.ErrorBox(win,"Programmet s\u00F8ger efter filer i %s, men kunne ikke finde nogen %s-resultatfiler!"  %(RESDIR_SHORT,program))
		return []
	dlg = GUI.MyMultiChoiceDialog( win, 
	"V\u00E6lg resultatfiler",
	"Fundne filer", list(map(os.path.basename,goodfiles)))
	dlg.ShowModal()
	OK=dlg.WasOK()
	if OK:
		selections = dlg.GetSelections()
		files = [goodfiles[x] for x in selections]
		dlg.Destroy()
		return files
	else:
		dlg.Destroy()
		return []

#class used to fetch a file#
def GetFile(win,msg="Select a file:",defaultDir=None,style=wx.FD_OPEN,wildcard="*.*"):
	if defaultDir is not None:
		dlg= wx.FileDialog(win, msg,defaultDir,wildcard=wildcard,style=style)
	else:
		dlg= wx.FileDialog(win, msg,wildcard=wildcard,style=style)
	if dlg.ShowModal()==wx.ID_OK:
		filename=dlg.GetPath()
	else:
		filename=""
	dlg.Destroy()
	return filename

#Logging class
class Logger(wx.Panel):
	def __init__(self,parent,fs=10):
		self.parent=parent
		wx.Panel.__init__(self, parent, style=wx.RAISED_BORDER)
		self.log = wx.TextCtrl(self,wx.ID_ANY,style= wx.TE_MULTILINE | wx.TE_READONLY)
		self.savebutton=GUI.MyButton(self,"Save LOG",fs)
		self.savebutton.Bind(wx.EVT_BUTTON,self.OnSave)
		self.clearbutton=GUI.MyButton(self,"Clear LOG",fs)
		self.clearbutton.Bind(wx.EVT_BUTTON,self.OnClear)
		self.hsizer=wx.BoxSizer(wx.HORIZONTAL)
		self.hsizer.Add(self.savebutton,0,wx.ALL,5)
		self.hsizer.Add(self.clearbutton,0,wx.ALL,5)
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.log,1,wx.EXPAND)
		self.sizer.Add(self.hsizer,0,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)
		self.log.SetFont(wx.Font(fs-2,wx.MODERN,wx.NORMAL,wx.NORMAL))
	def OnSave(self,event):
		Nlog=0
		fname=Fkt.Dato().replace(".","-").replace(":","-")+".log"
		while os.path.exists(os.path.join(BASEDIR,fname)):
			Nlog+=1
			fname=Fkt.Dato().replace(".","-").replace(":","-")+"_"+str(Nlog)+".log"
		self.log.AppendText("Saving %s...\n" %fname)
		f=open(os.path.join(BASEDIR,fname),"w") 
		f.write(self.log.GetValue()) # .encode('utf-8')) py2to3
		f.close()
	def OnClear(self,event):
		self.log.SetValue("")
	def AppendText(self,text):
		self.log.AppendText(text)
	def Write(self,text):
		self.log.AppendText(text)
		
		
#class to enter 'hoved' data into:
class MakeHead(GUI.InputDialog):
	def __init__(self,parent,statusdata,dato,tid,jside="",temp=None,test=None):
		textlabels=["Fra:","Til:","Dato:","Tid:","Journalside:"]
		textvals=[statusdata.GetStart(),statusdata.GetEnd(),dato,tid]
		numlabels=["Temperatur:"]
		bounds=[(-40,45)]
		if IS_PRECISION: #global var defined at top of this module
			numlabels.append("Asfalttemp.:")
			bounds.append((-40,80))
		try:
			float(temp)
		except:
			numvals=[]
		else:
			numvals=[temp]
		GUI.InputDialog.__init__(self,parent,"Hoved",textlabels,textvals,numlabels,numvals,bounds=bounds,pedantic=True)
		status=GUI.StatusBox2(self,["H\u00F8jdeforskel:","Afstand:","#Opst:"],colsize=1,label="Str\u00E6kning")
		testbox=GUI.StatusBox2(self,["Frem-tilbage test:"],label="Forkastelseskriterie")
		if test is not None:
			
			if test:
				test="OK"
				testcol="green"
			else:
				test="IKKE OK"
				testcol="red"
		else:
			test="IKKE FUNDET"
			testcol=None
		status.UpdateStatus(["%.5f m" %statusdata.GetHdiff(),"%.2f m" %statusdata.GetDistance(),"%i" %statusdata.GetSetups()])
		testbox.UpdateStatus([test],colours={0:testcol})
		self.ekstra=GUI.EditFields(self,["Ekstra information (tryk, vandtemp., etc.):"])
		self.sizer.Insert(0,status,0,wx.ALL,5)
		self.sizer.Insert(1,testbox,0,wx.ALL,5)
		self.sizer.Insert(3,self.ekstra,0,wx.ALL,5)
		self.ekstra.DefineNextItem(self.buttons.button1)
		self.fields.DefineNextItem(self.ekstra)
		self.ekstra.DefinePrevItem(self.fields)
		self.SetSizerAndFit(self.sizer)
		self.Center()
		jsfield=self.fields.field[-1]
		jsfield.SetValidator(JsideValidator)
		jsfield.SetFocus() #at the journalside-field
	def GetValues(self):
		vals=self.GetTextValues()+self.GetNumValues()+self.ekstra.GetTextValues()
		return vals
def JsideValidator(value):
	value=value.replace(",",".")
	spl=value.split(".")
	if len(spl)!=2:
		return False
	else:
		try:
			js=int(spl[0])
			ext=int(spl[1])
		except:
			return False
		else:
			if 100000<=js<=999999 and 0<ext<=9:
				return True
			else:
				return False
				

#---------------------------------------------#
# Ini reader base class                          #
#----------------------------------------------#

class InstrumentError(Exception):
	def __init__(self,msg="Kunne ikke definere instrumentet!"):
		self.msg=msg
	def __str__(self):
		return self.msg
		
class LaegteError(Exception):
	def __init__(self,msg=""):
		self.msg=msg
	def __str__(self):
		return self.msg


class IniReader(object):
	def __init__(self,path,n_inst,min_laegter=1):
		self.path=path
		self.ini=Ini()
		self.laegter=[]
		self.instruments=[]
		self.n_inst=n_inst
		self.min_laegter=min_laegter
	def Read(self):
		self.laegter=[]
		self.instruments=[]
		self.ini.Reset() #implement this method to reset stuff that should be reset...
		f=open(self.path,"r")
		line=Fkt.RemRem(f)
		while len(line)>0:
			i=line.find(":")
			if i!=-1:
				key=line[:i].strip()
			else:
				line=Fkt.RemRem(f)
				continue
			line=line[i+1:].split()
			if key=="gps" and len(line)>0:
				self.ini.gpsport=int(line[0])
				if len(line)>1:
					self.ini.gpsbaud=int(line[1])
			if key=="kortmappe" and len(line)>0:
				mapdir=line[0]
				if mapdir[-1] not in ["/","\\"]:
					mapdir+="/"
				self.ini.mapdirs.append(mapdir)
			if key=="database" and len(line)>0:
				self.ini.database=line[0]
			if key=="ftforkast" and len(line)>0:
				self.ini.fbtest=float(line[0])
				if len(line)>1:
					self.ini.fbunit=line[1]
			if key=="ft_brug_alle":
				if len(line)>0:
					try:
						ok=int(line[0])
					except:
						pass
					else:
						self.ini.fb_use_all=bool(ok)
			self.CheckAdditionalKeys(key,line)
			line=Fkt.RemRem(f)
		f.close()
		if len(self.instruments)!=self.n_inst: 
			raise InstrumentError("Korrekt antal instrumenter ikke defineret i ini-filen!")
		if len(self.laegter)<self.min_laegter:
			raise LaegteError("Der er ikke defineret mindst %d laegte i ini-filen" %self.min_laegter)
		return self.ini,self.instruments,self.laegter
	def CheckAdditionalKeys(self,key,line):
		#override this method in subclass#
		pass
	


#-------------------------------------#
# Sound Alert  
#-------------------------------------#
def SoundAlert():
	data, fs = sf.read(MMDIR+'chord.wav')
	sd.play(data,fs)
def SoundGotData():
	data ,fs = sf.read(MMDIR+'gotdata.wav')
	sd.play(data,fs)
def SoundBadData():
	data, fs = sf.read(MMDIR+'alert.wav')
	sd.play(data,fs)
def SoundGoodData():
	data,fs = sf.read(MMDIR+'gooddata.wav')
	sd.play(data,fs)
def SoundKey():
	data,fs = sf.read(MMDIR+'ding.wav')
	sd.play(data,fs)