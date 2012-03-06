import wx
import GUIclasses2 as GUI 
from DataClass2 import PointData
import GPS
import numpy as np
import MapBase
#Last update/bugfix 11.03,2010 simlk
#Two GUI interfaces wrapping MapBase.py for ML-programs. Simple interface designed for in-field use....
class BasePanel(wx.Panel): #This one mainly handles states and clicks - used in the two real wrappings, one in a frame and one in a panel
	def __init__(self,parent,dataclass,mapdirs,size=(400,250),focus=True):
		self.parent=parent
		wx.Panel.__init__(self,parent,size=size)
		self.SetBackgroundColour("blue")
		#STATE VARS and DATA
		self.panmode=True
		self.gpsmode=False #mutually exclusive modes
		self.clickrange=20 #20 pixels-clickrange.
		#info field
		self.info=GUI.FileLikeTextCtrl(self,size=(size[0],20),style=wx.TE_READONLY)
		self.info.SetFont(GUI.DefaultLogFont(8))# info field for dispalying text messages.
		#Set up the MapWindow
		self.Map=MapBase.MapBase(self,size[0],size[1],dataclass,mapdirs)
		self.Map.RegisterLeftClick(self.OnLeftClick)
		self.Map.RegisterRightClick(self.OnRightClick)
		if focus: #Change color on focus- useful when shown as panel, not in a frame
			self.Map.MapPanel.canvas.Bind(wx.EVT_SET_FOCUS,self.OnSetFocus) #for showing when the panel has focus
			self.Map.MapPanel.canvas.Bind(wx.EVT_KILL_FOCUS,self.OnKillFocus)
		#SETTING UP THE SIZER#
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.Map,1,wx.ALL|wx.CENTER|wx.EXPAND,2)
		self.sizer.Add(self.info,0,wx.ALL|wx.CENTER|wx.EXPAND,5)
		self.SetSizerAndFit(self.sizer)
		self.SetPanMode()
		self.Map.SetInitialCenter()
	def OnSetFocus(self,event):
		self.SetBackgroundColour("green")
		self.Refresh()
		event.Skip()
	def OnKillFocus(self,event):
		self.SetBackgroundColour("blue")
		self.Refresh()
		event.Skip()
	def SetMap(self): #parent gui should call this
		self.Map.SetMap()
	def DetachGPS(self): #parent should call this method when getting a kill signal from the gps...
		self.Map.DetachGPS()
		self.SetPanMode()
	def AttachGPS(self,gps):
		self.Map.AttachGPS(gps)
	def Log(self,text,append=False):
		self.info.SetValue(text)
	def ClearPoints(self):
		self.Map.ClearPoints()
	def GetPoints(self):
		self.Map.GetPoints()
	def ResetPlot(self):
		self.Map.ResetPlot()
	def ZoomIn(self):
		self.Map.ZoomIn()
	def ZoomOut(self):
		self.Map.ZoomOut()
	def ToggleNames(self):
		self.Map.ToggleNames()
	def ToggleTextColor(self):
		self.Map.ToggleTextColor()
	def ToggleMode(self):
		if not self.panmode:
			self.SetPanMode()
		else: 
			if self.Map.gps.isAlive(): #then we are in panmode
				self.SetGPSMode()
			else:
				self.Log("GPS ikke tilsluttet...")
	def SetPanMode(self,log=True): #naar  gps doer saa gaa til navmode!
		if not self.panmode and log:
			self.Log("Skifter til navigation via venstreklik...")
		self.panmode=True
		self.gpsmode=False
		self.Map.SetGpsCentering(False)
	def SetGPSMode(self):
		if not self.gpsmode:
			self.Log(u"Centrerer via GPS.")
		self.gpsmode=True
		self.panmode=False
		self.Map.SetGpsCentering(True)
	def OnRightClick(self,event):
		x=event.GetX()
		y=event.GetY()
		D,j=100000,-1 # just larger than clickrange :-)
		if self.Map.HasPoints():
			D,j=self.Map.ClosestLocatedPoint(x,y) #in screen coords 
		if D<self.clickrange:  #Saa er punkter plottet og defineret!
			self.Map.UnSelect()
			self.Map.Select(j)
			info=self.Map.GetHeightInfo()
			self.Log(info)
			bsk,found1=self.Map.GetLocatedInfo()
			skitse,w,h,found2=self.Map.GetLocatedSkitse()
			punkt=self.Map.GetLocatedLabel()
			if found2 or found1:
				skitse=wx.BitmapFromBuffer(w,h,skitse)
				dlg=GUI.MyDscDialog(self,title="Beskrivelse for %s" %punkt,msg=bsk,image=skitse,point=punkt)
				dlg.ShowModal()
			else:
				self.Log("--Beskrivelse og skitse kunne ikke findes...",append=True)
		else:
			self.Map.UnSelect()
		event.Skip()
		self.SetFocus()
	def OnLeftClick(self,event):
		x=event.GetX()
		y=event.GetY()
		ux,uy=self.Map.MapPanel.UserCoords(x,y)  #could be wrapped more elegantly
		D,j=10000,-1
		if self.Map.HasPoints():
			D,j=self.Map.ClosestLocatedPoint(x,y) #in screen coords 
		if D<self.clickrange:  #Saa er punkter plottet og defineret!
				self.Map.UnSelect()
				self.Map.Select(j)
				self.PointNameHandler(self.Map.GetLocatedLabel())
				info=self.Map.GetHeightInfo()
				self.Log(info)
		elif self.panmode and not self.Map.MapEngine.isRunning(): #ikke nyt koor.system naar wms-hentning paagar!
			self.Map.UnSelect()
			self.info.SetValue("")
			self.Map.GoTo(ux,uy)
		else:
			self.Map.UnSelect()
		event.Skip()
	def GoTo(self,x,y):
		self.Map.GoTo(x,y)
	def PointNameHandler(self,name):
		pass
		
class MapFrame(wx.Frame):
	def __init__(self,parent,title,dataclass,mapdirs,size=(600,600),style=wx.DEFAULT_FRAME_STYLE|wx.STAY_ON_TOP):
		self.parent=parent
		wx.Frame.__init__(self,parent,title=title,size=size)
		self.statusbar=self.CreateStatusBar()
		#Appeareance#
		try:
			self.SetIcon(self.parent.GetIcon())
		except:
			pass
		self.SetBackgroundColour(GUI.BGCOLOR)
		#STATE VARS and DATA
		self.stayalive=True #flag to turn off, when you really wanna close the window
		#Setting up the panel at the bottom of the frame
		self.bottompanel=GUI.ButtonPanel(self,["SKJUL","ZOOM IND","ZOOM UD","GPS-CENTR.","PUNKTER","PKT.NAVNE","SLET PKT.","RESET"])
		self.button=self.bottompanel.button
		self.modebutton=self.button[3]
		self.button[0].Bind(wx.EVT_BUTTON,self.OnHide)
		self.button[1].Bind(wx.EVT_BUTTON,self.OnZoomIn)
		self.button[2].Bind(wx.EVT_BUTTON,self.OnZoomOut)
		self.button[3].Bind(wx.EVT_BUTTON,self.OnToggleMode)
		self.button[4].Bind(wx.EVT_BUTTON,self.OnGetPoints)
		self.button[5].Bind(wx.EVT_BUTTON,self.OnToggleNames)
		self.button[6].Bind(wx.EVT_BUTTON,self.OnClearPoints)
		self.button[7].Bind(wx.EVT_BUTTON,self.OnReset)
		#Set up the MapWindow
		self.Map=BasePanel(self,dataclass,mapdirs,size=size,focus=False)
		#SETTING UP THE SIZER#
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.Map,6,wx.CENTER|wx.ALIGN_CENTER|wx.ALL|wx.EXPAND,10)
		self.sizer.Add(self.bottompanel,0,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)
		#Generate a dlg message for the user at init
		doprompt=False
		warnstr=""
		if dataclass is None or not dataclass.IsInitialized(): #first call here... might bu superfluous
			self.DisablePoints()
		self.Bind(wx.EVT_CLOSE,self.OnClose)
		self.Map.SetMap()
		self.DisableGPS()  #until we attach one
	def OnClose(self,event):
		if not self.stayalive:
			event.Skip()
		else:
			self.Show(0)
	def CloseMeNow(self):
		self.stayalive=False
		self.Close()
	def OnHide(self,event):
		self.Show(0)
	def OnGetPoints(self,event):
		self.Map.GetPoints()
	def OnClearPoints(self,event):
		self.Map.ClearPoints()
	def OnResetPlot(self,event):
		self.Map.ResetPlot()
	def OnToggleNames(self,event):
		self.Map.ToggleNames()
	def OnToggleMode(self,event):
		self.Map.ToggleMode()
		if self.Map.gpsmode:
			self.button[3].SetLabel("NAV-MODE")
		else:
			self.button[3].SetLabel("GPS-CENTR.")
	def OnZoomIn(self,event):
		self.Map.ZoomIn()
	def OnZoomOut(self,event):
		self.Map.ZoomOut()
	def OnReset(self,event):
		self.Map.ResetPlot()
	def DisablePoints(self):
		self.button[-1].Enable(0)
	def EnablePoints(self):
		self.button[-1].Enable(1)
	def DisableGPS(self):
		self.button[3].Enable(0)
		self.button[3].SetLabel("GPS-CENTR.")
	def EnableGPS(self):
		self.button[3].Enable()
	def AttachGPS(self,gps):
		if gps.isAlive():
			self.Map.AttachGPS(gps)
			self.EnableGPS()
	def DetachGPS(self):
		self.Map.DetachGPS() #sets panmode
		self.DisableGPS()
		
class PanelMap(BasePanel): #panel-map with keyboard interaction.
	def __init__(self,parent,dataclass,mapdirs,size=(400,250)):
		self.pointnamefct=None
		BasePanel.__init__(self,parent,dataclass,mapdirs,size)
		self.Map.MapPanel.canvas.Bind(wx.EVT_CHAR,self.OnChar)
	def OnChar(self,event):
		key=event.GetKeyCode()
		if key==45: #'-'
			self.ZoomOut()
		elif key==43: #'+'
			self.ZoomIn()
		elif key==42: #'*'
			self.Map.GetPoints(small=True) #we only update in a smaller region... (searchradius attribute)
		elif key==47: #'/'
			self.ResetPlot()
		elif key==wx.WXK_DELETE:
			self.Map.ClearPoints()
		elif key==wx.WXK_INSERT:
			self.ToggleMode()
		elif key==wx.WXK_PAGEDOWN:
			self.ToggleNames()
		elif key==wx.WXK_PAGEUP:
			self.ToggleTextColor()
		event.Skip()
	def UpdatePoints(self):
		self.Map.TestPointUpdate(True) #set the force flag to True
	def RegisterPointFunction(self,fct):
		self.pointnamefct=fct
	def PointNameHandler(self,name):
		if self.pointnamefct is not None:
			self.pointnamefct(name)