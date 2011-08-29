import wx
from GUIclasses2 import MyButton,MyDscDialog,MyMessageDialog,FileLikeTextCtrl,ButtonPanel
from DataClass2 import PointData
import GPS
import numpy as np
import MapBase
#Last update/bugfix 05.08.09, simlk
#GUI interface wrapping MapBase.py for ML-programs. Simple interface designed for in-field use....
class MapPanel(wx.Panel):
	def __init__(self,parent,dataclass,mapdirs,size=(400,250)):
		self.parent=parent
		wx.Panel.__init__(self,parent,size=size)
		#Appeareance#
		self.SetBackgroundColour("green")
		#STATE VARS and DATA
		self.panmode=True
		self.gpsmode=False #mutually exclusive modes
		self.clickrange=20 #20 pixels-clickrange.
		self.stayalive=True #flag to turn off, when you really wanna close the window
		self.sendpointname=False
		#Set up the MapWindow
		self.Map=MapBase.MapBase(self,size[0]-4,size[1]-4,dataclass,mapdirs)
		self.Map.RegisterLeftClick(self.OnLeftClick)
		self.Map.RegisterRightClick(self.OnRightClick)
		self.Map.SetInitialCenter()
		self.Map.SetMap()
		#key-binding
		self.Map.MapPanel.canvas.Bind(wx.EVT_CHAR,self.OnChar)
		#SETTING UP THE SIZER#
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.Map,0,wx.CENTER)
		#self.sizer.Add(self.info,0,wx.ALL,5)
		#self.sizer.Add(self.bottompanel,0,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)
		#self.sizer.FitInside(self)
		self.Bind(wx.EVT_CLOSE,self.OnEVTClose)
		if self.parent is None:
			self.Bind(GPS.EVT_LOG,self.OnEvtLog)
			self.Bind(GPS.EVT_KILL_GPS,self.OnGPSkill)
		#Generate a dlg message for the user at init
		doprompt=False
		warnstr=""
		if self.Map.data is None or not self.Map.data.IsInitialized(): #first call here... might bu superfluous
			self.DisablePoints()
			self.Map.data=None
		self.SetPanMode()
		self.SetFocus()
	def CloseMeNow(self):
		self.stayalive=False
		self.Close()
	def OnEVTClose(self,event):
		if not self.stayalive:
			self.Map.CloseDown()
			self.Map.gps.kill()
			self.Map.gps.join()
			event.Skip() #ellers lukkes ikke!
		else: #just hide
			self.Show(0)
	def OnHide(self,event):
		self.Show(0)
	def OnEvtLog(self,event):
		self.Log(event.text)
	def OnGPSkill(self,event):
		self.DetachGPS()
	def DetachGPS(self): #parent should call this method when getting a kill signal from the gps...
		self.Map.DetachGPS()
		self.SetPanMode()
	def AttachGPS(self,gps):
		self.Map.AttachGPS(gps)
		if gps.isAlive():
			self.modebutton.Enable(1)
		else:
			self.SetPanMode(log=False)
	def Log(self,text,append=False):
		try:
			self.parent.Log(text)
		except:
			pass
	def ClearPoints(self):
		self.Map.ClearPoints()
	def OnChar(self,event):
		key=event.GetKeyCode()
		if key==45: #'-'
			self.Map.ZoomOut()
		elif key==43: #'+'
			self.Map.ZoomIn()
		elif key==42: #'*'
			self.Map.GetPoints()
		elif key==392: #'/'
			self.Map.ResetPlot()
		event.Skip()
	def OnGetPoints(self,event):
		self.Map.GetPoints()
	def OnResetPlot(self,event):
		self.Map.ResetPlot()
	def OnToggleMode(self,event):
		if not self.panmode:
			self.SetPanMode()
		elif self.Map.gps.isAlive():
			self.SetGPSMode()
	def SetPanMode(self,log=True): #naar  gps doer saa gaa til navmode!
		if not self.panmode and log:
			self.Log("Skifter til navigation via venstreklik...")
		#self.modebutton.SetLabel("GPS-CENTR.")
		#if self.Map.gps.isAlive():
		#	self.modebutton.Enable(1)
		#else:
		#	self.modebutton.Enable(0)
		self.panmode=True
		self.gpsmode=False
		self.Map.SetGpsCentering(False)
	def SetGPSMode(self):
		if not self.gpsmode:
			self.Log(u"Centrerer via GPS.")
			self.modebutton.SetLabel("NAVIGER")
			self.modebutton.Enable(1)
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
				dlg=MyDscDialog(self,title="Beskrivelse for %s" %punkt,msg=bsk,image=skitse,point=punkt)
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
		self.Log("%.1f %.1f" %(ux,uy))
		D,j=10000,-1
		if self.Map.HasPoints():
			D,j=self.Map.ClosestLocatedPoint(x,y) #in screen coords 
		if D<self.clickrange:  #Saa er punkter plottet og defineret!
				self.Map.UnSelect()
				self.Map.Select(j)
				if self.sendpointname:
					try:
						self.pointwindow.GotPointName(self.Map.GetLocatedLabel())
					except:
						pass
				info=self.Map.GetHeightInfo()
				self.Log(info)
		elif self.panmode and not self.Map.MapEngine.isRunning(): #ikke nyt koor.system naar wms-hentning paagar!
			self.Map.UnSelect()
			#self.info.SetValue("")
			self.Map.GoTo(ux,uy)
		else:
			self.Map.UnSelect()
		#self.SetStatusText("Koordinater: (%.1f,%.1f)" %(ux,uy))
		event.Skip()
	def OnZoomIn(self,event):
		self.Map.ZoomIn()
	def OnZoomOut(self,event):
		self.Map.ZoomOut()
	def OnReset(self,event):
		self.Map.ResetPlot()
	def OnDeletePositions(self,event):
		self.Map.DeletePositions()
	def DisablePoints(self):
		self.button[-1].Enable(0)
	def EnablePoints(self):
		self.button[-1].Enable(1)
	def SetPointWindow(self,win):
		self.sendpointname=True
		self.pointwindow=win