import wx
import Core #defines classes that are common to, or very similar in, MGL and MTL
import MyModules.GUIclasses2 as GUI #basic GUI-stuff
from MyModules.MLmap import PanelMap
from MyModules.ExtractKMS import Numformat2Pointname,Pointname2Numformat
import Instrument 
import numpy 
import Funktioner
import FileOps
import sys
BASEDIR=Core.BASEDIR #the directory, where the program is located
PROGRAM=Core.ProgramType()
PROGRAM.name="MGL"
PROGRAM.version="beta 1.70"
PROGRAM.exename="MGLb170.exe"
PROGRAM.date="2012-03-07"
PROGRAM.type="MGL"
PROGRAM.about="""
MGL program skrevet i Python. 
Bugs rettes til simlk@kms.dk
"""
# Prev. fix: Updated gps thread close down at exit, and gps drawing in MapPanel and MapBase. Takes less ressources now.
# Updates march 2010: v.1.6- new data class with nametypes. todo: add more attributes... 
# Fixed FBtest - parameter was always 2.0 regardless of ini-file input.
# 26.3.10 fixed Zooming in OnPointEnter - method GetCoordinates was missing in DataClass3
# 04.05.11 Added logging of sds from instrument which are sent in 'auto mode'. Needed to handle sds like hds with first and second reading etc....
#20.06.11  Changed various things after starting to develop MTL based on Core classes. Now common filereaders for MGL and MTL
#--------------------------------------------------------
#These classes take care of the datahandling and math involved in a MGL measurement.
#--------------------------------------------------------
#Changes: We now need to store sds in result file. So SD-methods etc should reflect HD stuff....
class MGLaim(object):
	def __init__(self,mode='detail',aim=1):
		self.dist=0 #distance
		self.hds=[] #list of height differences, NB: readings! Not real height differences, as the rod's zero-shift should be added
		self.rod=None
		self.sds=[] #std. error returned from instrument. Now stored parallel to the hds...
		self.nread=None #number of readings of instrument
		self.point=None
		self.mode=mode #presicion or detail mode
		self.done=False
		self.halfdone=False
		self.aim=aim
		if aim<0:
			self.daim="tilbagesigte"
		else:
			self.daim="fremsigte"
	def SetSD(self,sd): 
		self.sds=[sd]
	def AddSD(self,sd):
		self.sds=[self.sds[0],sd]
	def SetDistance(self,d):
		self.dist=d
	def SetRod(self,rod): #called with MGLlaegte class
		self.rod=rod
	def RodTest(self): #test on last reading!
		return self.rod.TestReading(self.hds[-1])
	def GetReadingDifference(self):
		return abs(self.hds[0]-self.hds[1])
	def SDTest(self,maxval=0.00012):
		if len(self.sds)==0 or self.sds[-1]<=maxval:
			return True
		return False
	def DistanceTest(self,maxval):
		if self.dist>maxval:
			return False
		return True
	def SetReading(self,h):
		self.hds=[h]
	def AddReading(self,h):
		self.hds=[self.hds[0],h]  #can be changed to handle more than 2 h.diffs...
	def SetNRead(self,nread):
		self.nread=nread
	def GetHD(self): #not really useful in itself, as it is the mean of two combined back-forward measurements we need...
		return (numpy.mean(self.hds)+self.rod.zeroshift)
	def GetHD1(self):
		return (self.hds[0]+self.rod.zeroshift)
	def GetHD2(self):
		return (self.hds[1]+self.rod.zeroshift)
	def GetHDS(self):
		return (numpy.array(self.hds)+self.rod.zeroshift).tolist()
	def GetSDS(self):
		return self.sds
	def GetSD(self):
		if len(self.sds)>0:
			return self.sds[-1]
		return None
	def HasReadings(self):
		if len(self.hds)>0:
			return True
		else:
			return False
	def Has2Readings(self):
		if len(self.hds)==2:
			return True
		else:
			return False
	def ClearReadings(self):
		self.hds=[]
		#self.dist=0, nope this is an error!
	def ClearAll(self):
		self.hds=[]
		self.sds=[]
		self.dist=0
	def ClearLastReading(self):
		self.hds=self.hds[:-1]
		self.sds=self.sds[:-1]
		self.nread=None
	def ClearReading2(self):
		if len(self.hds)==2:
			self.ClearLastReading()
	def GetDistance(self):
		return self.dist
	def IsDone(self):
		done=False
		if self.mode=='detail':
			if len(self.hds)==1 and self.dist>0:
				done=True
		else:
			if len(self.hds)==2 and self.dist>0:
				done=True
		self.done=done
		return done
	def IsHalfDone(self):
		halfdone=False
		if self.mode=='precision':
			if self.dist>0 and len(self.hds)==1:
				halfdone=True
		self.halfdone=halfdone
		return halfdone

class MGLsetup(object):
	def __init__(self,mode='detail'): # called with test class containing criteria
		self.mode=mode
		self.StartNew()
	def StartNew(self):
		self.dist=0
		self.hd=0
		self.back=MGLaim(self.mode,aim=-1)
		self.forward=MGLaim(self.mode,aim=1)
		self.aim={'back':self.back,'forward':self.forward} #utility dict for neater access.
	def HasData(self):
		return self.forward.HasReadings() or self.back.HasReadings()
	def IsDone(self):
		return (self.back.IsDone() and self.forward.IsDone())
	def GetHD(self):
		self.hd=-self.forward.GetHD()+self.back.GetHD() #same as ((h1b-h1f)+(h2b-h2f))*0.5
		return self.hd
	def GetDistance(self):
		self.dist=self.back.dist+self.forward.dist
		return self.dist
	def GetDistanceDifference(self):
		return self.back.dist-self.forward.dist
	def DistanceTest(self,maxval=2.0):
		db=self.back.dist
		df=self.forward.dist
		if db>0 and df>0:
			if abs(df-db)>maxval:
				return False
		return True
	def HDTest(self,maxval=0.0004):
		if self.mode=='precision' and self.IsDone():
			hd1=self.back.GetHD1()-self.forward.GetHD1()
			hd2=self.back.GetHD2()-self.forward.GetHD2()
			dh=hd1-hd2
			return dh,(abs(dh)<maxval)
		else:
			return 0,True
class MGLlaegte(object):
	def __init__(self,name=None,zone_low=0,zone_high=0,zeroshift=0,orientation=1):
		self.name=name
		self.zone_low=zone_low #zone not to use near top
		self.zone_high=zone_high #zone not to use near bottom
		self.zeroshift=zeroshift  #const. to add to zero level
		self.orientation=orientation #turned upside down?
	def TestReading(self,aimh):
		if self.zone_low<=aimh<=self.zone_high:
			return True
		else:
			return False
	def PresentYourself(self):
		return "%s:  nulpunktsfejl: %.5f m" %(self.name,self.zeroshift)
#----------------------------------------------------------------------------------------------------------------------
# Frame which handles all measurements in MGL. 
# State-handling principle: when data arrives via keyboard or data-com it should be displayed in status-box. This is handled by text-events in case of key-press in 'manual mode'. 
# Data arriving from instrument in 'auto mode' is inserted into text boxes without firing text-events.
# Errors are indicated by red-colors.
#  User prompting via dialogs should only be done when a measurement is completed - not for each keypress! i.e. when the user try's to accept the measurement.
#  In 'precision' mode the prompting should happen earlier, before doing the second measurement.
#-----------------------------------------------------------------------------------------------------------------------
class MGLMeasurementFrame(GUI.FullScreenWindow):
	def __init__(self,parent,mode='detail'):
		size=parent.size
		self.rods=parent.laegter #class with name and constants
		self.rodnames=[rod.name for rod in self.rods] #list of names to be sent to MGLpanel
		self.pmode=mode  #precision mode - can be "detail" or "precision", influences GUI-setup and measurement method
		self.mmode='manual' #data collection mode - can be "auto" or "manual" - 'auto' means data is loaded from instrument over COM-port
		self.aim='back'  #we are aiming 'back' or 'forward'--yeah I know, it should be backwards..... ;D
		self.nmode=1      #in precision mode, are we doing first or second measurement? can be 1 or 2.
		self.statusdata=parent.statusdata # coredata- hdiffs, distance etc---
		self.instrument=parent.instrument
		self.got_temp_from_inst=False #did we get temps send from the instrument? - then we should save them in the resfile.
		self.parent=parent
		self.ini=self.parent.ini  #data passed in ini-file, error limits relevant here
		self.resfile=self.parent.resfile #the full pathname of the result file.
		self.setup=MGLsetup(mode)
		GUI.FullScreenWindow.__init__(self,parent) #window with 5 sizer rows
		self.map=PanelMap(self,self.parent.data,self.ini.mapdirs) #setup the map - a panel in the center of the screen
		self.map.RegisterPointFunction(self.PointNameHandler)
		#setup check boxes#
		self.footsetup=wx.CheckBox(self,label="Fodopstilling.")
		self.footsetup.SetFont(GUI.DefaultFont(size-2))
		self.footsetup.Bind(wx.EVT_CHECKBOX,self.OnFoot)
		self.clearddsum=wx.CheckBox(self,label=u"Nulstil sum \u2206afst.")
		self.clearddsum.SetFont(GUI.DefaultFont(size-2))
		self.clearddsum.Bind(wx.EVT_CHECKBOX,self.OnClearDDsum)
		#end check boxes#
		if self.pmode=='detail':
			self.back=MGLpanel(self,u"Tilbagem\u00E5ling",self.rodnames,size)
			self.forward=MGLpanel(self,u"Fremm\u00E5ling",self.rodnames,size)
		else:
			self.back=MGLPpanel(self,u"Tilbagem\u00E5ling",self.rodnames,size-1)
			self.forward=MGLPpanel(self,u"Fremm\u00E5ling",self.rodnames,size-1)
		self.fields={'back':self.back,'forward':self.forward} #dict to acces fields by aim
		self.back.aim='back'   #flags for event handling - enables us to see which field should receive data.
		self.forward.aim='forward'
		#Button-panels
		self.optionpanel=GUI.ButtonPanel(self,buttons=[u"Slet m\u00E5ling","Afslut","Kort"],fontsize=size)
		if self.pmode=='detail':
			self.nextpanel=GUI.ButtonPanel(self,buttons=[u"N\u00E6ste opstilling"],fontsize=size)
		else:
			self.nextpanel=GUI.ButtonPanel(self,buttons=[u"N\u00E6ste opstilling",u"Dobbeltm\u00E5ling"])
			self.doublebutton=self.nextpanel.button[1]
			self.doublebutton.Enable(0)
		self.deletebutton=self.optionpanel.button[0]
		self.backbutton=self.optionpanel.button[1]
		self.nextbutton=self.nextpanel.button[0]
		self.mapbutton=self.optionpanel.button[2]
		#Event handling setup
		for aim in ['back','forward']:
			panel=self.fields[aim]
			panel.SetAutoHandler(self.AutoHandler)
			panel.SetDistanceHandler(self.DistanceHandler)
			panel.SetRodHandler(self.RodHandler)
			panel.SetRodEnterHandler(self.RodEnterHandler)
			panel.SetHDHandler(self.HDHandler)
			panel.SetHDEnterHandler(self.HDEnterHandler)
			panel.point.Bind(wx.EVT_TEXT_ENTER,self.OnPointEnter) #yes I know it is not style consistent, but just easier in the end....
		self.deletebutton.Bind(wx.EVT_BUTTON,self.OnDelete)
		self.nextbutton.Bind(wx.EVT_BUTTON,self.OnNext)
		self.mapbutton.Bind(wx.EVT_BUTTON,self.OnMap)
		self.backbutton.Bind(wx.EVT_BUTTON,self.OnGoBack)
		#browsing#
		self.back.DefineNextItem(self.forward.point)
		self.forward.DefineNextItem(self.nextbutton)
		#precision mode browsing, 
		if mode=="precision":
			self.forward.DefineNextItem(self.doublebutton)
			self.back.DefineNextItem2(self.forward.hd2)
			self.forward.DefineNextItem2(self.nextbutton)
			self.doublebutton.Bind(wx.EVT_BUTTON,self.OnDouble)
			opstitems=["Afst:",u"\u2206 afst.:",u"\u2206 h:","|h1-h2|:","Mode:"]
			opstminl=[4,4,6,6,6]
		else:
			opstitems=["Afst:",u"\u2206 afst.:",u"\u2206 h:","Mode:"]
			opstminl=[4,4,6,6]
		#status-boxes
		
		bfitems=["Sd:","#Afls.:" ,"Sigtelgd.:",u"L\u00E6gte:"]
		strkitems=[u"Sum \u2206 afst.:","Startpunkt:","Afst. punkt:",u"\u2206H til punkt:","#Opst.:"]
		strkminl=[2,12,2,5,3]
		self.backstatus=GUI.StatusBox2(self,bfitems,colsize=2,fontsize=size-1,label="Kontrol-tilbage")
		self.forwardstatus=GUI.StatusBox2(self,bfitems,colsize=2,fontsize=size-1,label="Kontrol-frem")
		self.bfstatus={'back':self.backstatus,'forward':self.forwardstatus} #utility dict for neater access.
		self.opststatus=GUI.StatusBox2(self,opstitems,colsize=2,fontsize=size-1,label="Opstilling",minlengths=opstminl)
		self.strkstatus=GUI.StatusBox2(self,strkitems,colsize=2,fontsize=size-1,label=u"Str\u00E6kning",minlengths=strkminl)
		self.backstatus.UpdateStatus()
		self.forwardstatus.UpdateStatus()
		self.opststatus.UpdateStatus()
		self.strkstatus.UpdateStatus()
		#Log-field
		self.log=wx.TextCtrl(self,style=wx.TE_READONLY|wx.TE_MULTILINE,size=(-1,80))
		self.log.SetFont(GUI.DefaultFont(size-1))
		#Define Layout, sizer programming still a bit of a mystery - well it not that interesting :-)
		self.CreateRow()
		if self.pmode=='detail':
			p1=1
			p2=2
		else:
			p1=1
			p2=1
		self.AddItem(self.opststatus,p1,wx.ALL,5)
		self.AddItem(self.strkstatus,p2,wx.ALL,5)
		self.AddRow(3,wx.ALIGN_CENTER|wx.EXPAND,5)
		self.CreateRow()
		vsizer1=wx.BoxSizer(wx.VERTICAL)
		vsizer2=wx.BoxSizer(wx.VERTICAL)
		vsizer3=wx.BoxSizer(wx.VERTICAL)
		hsizer=wx.BoxSizer(wx.HORIZONTAL)
		hsizer2=wx.BoxSizer(wx.HORIZONTAL)
		vsizer1.Add(self.backstatus,0,wx.ALL|wx.ALIGN_CENTER,5)
		vsizer1.Add(self.back,0,wx.ALL|wx.ALIGN_CENTER,5)
		vsizer1.Add(self.optionpanel,0,wx.ALL|wx.ALIGN_CENTER,5)
		vsizer2.Add(self.forwardstatus,0,wx.ALL|wx.ALIGN_CENTER,5)
		vsizer2.Add(self.forward,0,wx.ALL|wx.ALIGN_CENTER,5)
		vsizer2.Add(self.nextpanel,0,wx.ALL|wx.ALIGN_CENTER,5)
		vsizer3.Add(self.map,0,wx.ALL|wx.CENTER,5)
		hsizer2.Add(self.footsetup,0,wx.ALL,5)
		hsizer2.Add(self.clearddsum,0,wx.ALL,5)
		vsizer3.Add(hsizer2,0,wx.ALL,5)
		
		hsizer.Add(vsizer1,1,wx.ALL,5)
		hsizer.Add(vsizer3,0,wx.ALL|wx.CENTER,5)
		hsizer.Add(vsizer2,1,wx.ALL,5)
		self.AddItem(hsizer,1,wx.ALL,5)
		self.AddRow(12,wx.ALIGN_CENTER,5)
		self.CreateRow()
		self.AddItem(self.log,1,wx.CENTER,5)
		self.AddRow(1,wx.EXPAND|wx.CENTER,5)
		#SETUP INSTRUMENT EVENT HANDLING
		self.instrument.SetEventHandler(self)
		self.instrument.SetLogWindow(self)
		self.Bind(Instrument.EVT_LOG,self.OnInstLog)
		self.Bind(Instrument.EVT_DATA,self.OnData)
		self.ShowMe()
		if self.instrument.TestPort():
			self.Log("Instrumentet er klar...")
		else:
			self.Log(u"Kunne ikke \u00E5bne instrumentets com-port...")
		#PREPARE FOR STARTUP		
		self.back.rod.SetSelection(0)
		self.forward.rod.SetSelection(1)
		self.StartNew()
		self.SetManualMode() #the first time go to manual mode!
	def InitializeMap(self): #should be called every time the frame is shown to go to gps-mode
		if self.parent.gps.isAlive():
			self.parent.map.DetachGPS()
			self.map.AttachGPS(self.parent.gps)
			self.map.SetGPSMode()
			self.map.UpdatePoints() #uses same data as parent, so this influences the parents map as well.
		else:
			self.map.SetPanMode()
		self.map.SetMap()
	def OnMap(self,event):
		self.map.SetFocus()
	def OnPointEnter(self,event):
		obj=event.GetEventObject()
		point=obj.GetValue().strip()
		if len(point)>0 and self.map.panmode:  #if the field is not empty and not using gps-centering
			if self.parent.data is not None:
				translation=Numformat2Pointname(point)
				x,y=self.parent.data.GetCoordinates(translation)
				if x is not None and y is not None:
					self.map.GoTo(x,y)
					self.Log("Centrerer omkring indtastet punkt %s." %translation)
					self.map.UpdatePoints()
				else:
					self.Log("Kunne ikke finde koordinater for %s i databasen." %translation)
		event.Skip()
	def OnGoBack(self,event):
		self.SetManualMode()
		self.Show(0)
		if self.parent.gps.isAlive():
			self.map.DetachGPS()
			self.parent.map.AttachGPS(self.parent.gps)
		self.parent.UpdateStatus() 
	def OnFoot(self,event):
		if self.footsetup.IsChecked():
			self.Log("Fodopstilling - gps positioner lagres ikke.")
			self.footsetup.SetBackgroundColour("yellow")
		else:
			self.Log("Normal opstilling - gps positioner lagres.")
			self.footsetup.SetBackgroundColour(GUI.BGCOLOR)
		self.footsetup.Refresh()
	def OnClearDDsum(self,event):
		if self.clearddsum.IsChecked():
			self.Log("Resetter delta-afstands-sum efter punkttilslutning")
			self.clearddsum.SetBackgroundColour("yellow")
		else:
			self.Log("Resetter IKKE delta-afstands-sum punkttilslutning")
			self.clearddsum.SetBackgroundColour(GUI.BGCOLOR)
		self.clearddsum.Refresh()
	#Text-events only send in manuel mode. Auto-mode uses ChangeValue.
	#Rods are set either when a new selection is made,  when something useful is entered in measurement-fields or when return ios hit in rod-field.
	def RodHandler(self,aim):
		rod=self.rods[self.fields[aim].GetRod()]
		self.setup.aim[aim].SetRod(rod)
		if aim=='forward' and rod.zone_high<2.0 and self.forward.point.IsEmpty():
			GUI.ErrorBox(self,u"Advarsel kort l\u00E6gte i fremsigte!")
	def RodEnterHandler(self,aim):
		Core.SoundKey()
		rod=self.rods[self.fields[aim].GetRod()]
		self.setup.aim[aim].SetRod(rod)
		if aim=='forward' and rod.zone_high<2.0 and self.forward.point.IsEmpty():
			GUI.ErrorBox(self,u"Advarsel kort l\u00E6gte i fremsigte!")
		if self.instrument.GetPortStatus() and self.mmode=="manual":
			self.AutoHandler(aim)
		else:
			self.fields[aim].dist.SetFocus()
	def DistanceHandler(self,obj,aim): #MGL-panel fires this at text-events in dist-field
		status=False
		data=self.setup.aim[aim]
		if obj.Validate():		        
			data.SetDistance(obj.GetMyValue())
			status=True
		else:
			if data.GetDistance()>0:
				status=True
				data.SetDistance(0)
		if status:
			self.SetStatus()
	def HDHandler(self,obj,aim): #MGL-panel fires this on text-events
		data=self.setup.aim[aim]
		if self.nmode==1:
			SetReading=data.SetReading
			HasReading=data.HasReadings
			ClearReading=data.ClearReadings
		else:
			SetReading=data.AddReading
			HasReading=data.Has2Readings
			ClearReading=data.ClearLastReading
		status=False
		if obj.Validate(): #also set rod
			data.SetRod(self.rods[self.fields[aim].GetRod()])
			SetReading(obj.GetMyValue())
			status=True
		else:
			if HasReading():
				status=True
				ClearReading()
		if status:
			self.SetStatus()
	def HDEnterHandler(self,obj,aim): #fired by the MGL-panel when enter is hit in hd-field
		data=self.setup.aim[aim]
		changed=False
		if self.nmode==1:
			if data.HasReadings():
				obj.ChangeValue("%.5f" %data.GetHD1()) #does not fire a text-event
				changed=True
		else:
			if data.Has2Readings():
				obj.ChangeValue("%.5f" %data.GetHD2())
				changed=True
		if changed:
			self.Log("Adderer nulpunktsfejl %.1f mm i %s" %(data.rod.zeroshift,data.daim))
	def AutoHandler(self,aim):
		if self.mmode=='auto':
			self.instrument.Kill()
			self.SetManualMode(aim)
		else: #only start new thread in manual mode...
			self.aim=aim  #so that OnData knows where to put data
			self.mmode='auto'
			self.opststatus.UpdateStatus(field=-1,text="auto",colour="green")
			self.Log(u"L\u00E6ser data fra instrumentet...")
			if self.nmode==1:
				self.setup.aim[aim].SetRod(self.rods[self.fields[aim].GetRod()]) #set the rod here
				self.fields[aim].DisableTop()
			else:
				self.fields[aim].DisableBottom()
			self.fields[aim].autobutton.SetFocus()
			self.fields[aim].SetBackgroundColour("wheat")
			self.fields[aim].Refresh()
			self.instrument.ReadData()
	def OnData(self,event):
		self.instrument.SetReadState(False) #almost the same as setting 'manual' mode.
		Core.SoundGotData()
		#Core.SoundAlert()
		OK=event.OK
		if OK:
			fields=self.fields[self.aim]
			if event.temp is not None:
				self.statusdata.AddTemperature(event.temp,Funktioner.MyTime())
				self.got_temp_from_inst=True
			dist=event.dist
			hd=event.dh
			data=event.string
			sd=event.sd
			nr=event.nread
			if self.nmode==1:
				self.setup.aim[self.aim].SetSD(sd)
				self.setup.aim[self.aim].SetReading(hd)
				self.setup.aim[self.aim].SetDistance(dist)
				self.setup.aim[self.aim].SetNRead(nr)
				fields.dist.ChangeValue("%.2f" %dist) #does not send-text event
				fields.hd.ChangeValue("%.5f" %self.setup.aim[self.aim].GetHD1()) #adds the zero-error from the current rod
				fields.dist.Validate() #just to make it look great
				fields.hd.Validate()
				fields.EnableTop()
			else:
				self.setup.aim[self.aim].AddReading(hd)
				self.setup.aim[self.aim].AddSD(sd)
				self.setup.aim[self.aim].SetNRead(nr)
				fields.hd2.ChangeValue("%.5f" %self.setup.aim[self.aim].GetHD2())
				fields.hd2.Validate()
				fields.EnableBottom()
				if self.setup.IsDone():
					dh,OK=self.setup.HDTest(self.ini.maxhd)
					if OK:
						Core.SoundGoodData()
					else:
						Core.SoundBadData()
			self.Log("Data fra instrument: %s"%data)
			self.SetStatus()
			#THEN DECIDE WHICH MODE TO GO TO!
			if self.nmode==1:
				self.SetManualMode()
				if self.aim=='back':
					self.forward.point.SetFocus()
				elif self.pmode=='precision':
					self.doublebutton.SetFocus()
				else:
					self.nextbutton.SetFocus()
			else:
				if self.aim=='back':
					self.SetManualMode()
					self.forward.autobutton.SetFocus()
				else:
					self.SetManualMode()
					self.nextbutton.SetFocus()
		else:  #if error, we set 'manual' mode
			if event.hascon:
				self.Log(u"Kunne ikke l\u00E6se data fra instrumentet!")
			else: #then we couldnt open connection
				self.Log(u"Kunne ikke \u00E5bne instrumentets com-port!")
			self.SetManualMode()
	def SetManualMode(self,aim=None):
		if self.instrument.IsReading(): #should not happen....
			self.instrument.Kill()
		self.mmode='manual'
		if self.nmode==1:
			self.forward.EnableTop()
			self.back.EnableTop() #we release both, since we can kill forwards-meas. using backwards-button.
		else:
			self.forward.EnableBottom()
			self.back.EnableBottom()
		self.opststatus.UpdateStatus(field=-1,text="manuel",colour="yellow")
		if aim in ['back','forward']: #if called from AutoHandler.... otherwise focuscontrolled elsewhere.
			if self.nmode==1:
				self.fields[aim].dist.SetFocus()
			else:
				self.fields[aim].hd2.SetFocus()
		for aim in ['back','forward']:
			self.fields[aim].SetBackgroundColour(GUI.BGCOLOR)
			self.fields[aim].Refresh()
	def SetStatus(self): #Method which checks/displays status after measurements. Enables buttons. Updates Statusbox. Moving focus should be handled elsewhere
		#All this happens at key-press in 'manual' mode
		#First update f/b- statusboxes 
		for aim in ['back','forward']:
			data=self.setup.aim[aim]
			sd=data.GetSD()
			if sd is not None:
				sd_label="%.2f mm" %(sd*1000)
				sd_color=Funktioner.State2Col(data.SDTest(self.ini.maxsd))
			else:
				sd_label="NA" #maybe also set color
				sd_color=None
			if data.nread is not None:
				nr_label="%i" %data.nread
			else:
				nr_label="NA"
			d=data.GetDistance()
			if d>0:
				if not data.DistanceTest(self.ini.maxsl):
					sl_label="ERR"
					sl_color="red"
				else:
					sl_label="OK"
					sl_color="green"
			else:
				sl_label="NA"
				sl_color=None
			if len(data.hds)>0:
				if data.RodTest():
					rt_label="OK"
					rt_color="green"
				else:
					rt_label="ERR"
					rt_color="red"
			else:
				rt_label="NA"
				rt_color=None
			self.bfstatus[aim].UpdateStatus([sd_label,nr_label,sl_label,rt_label],colours={0:sd_color,2:sl_color,3:rt_color})
		if True:
			#Next update opst-statusbox#
			db=self.setup.back.dist
			df=self.setup.forward.dist
			if db>0 and df>0:
				di=self.setup.GetDistance()
				dd=self.setup.GetDistanceDifference()
				di_label="%.2f m" %di
				dd_label="%.2f m" %dd
				ddcolor=Funktioner.State2Col(self.setup.DistanceTest())
				self.statusdata.SetLastDD(dd)
				ddsum=self.statusdata.GetDDSum()
				if abs(ddsum)>4.0:
					ddsumcolor="red"
				else:
					ddsumcolor="green"
				self.strkstatus.UpdateStatus(field=0,text="%.2f m" %ddsum,colour=ddsumcolor)
			else:
				self.statusdata.SetLastDD(0)
				ddcolor=None
				di_label="NA"
				dd_label="NA"
			if self.pmode=='precision':
				if self.setup.back.IsHalfDone() and self.setup.forward.IsHalfDone() and self.nmode==1:
					self.doublebutton.Enable()
				else:
					self.doublebutton.Enable(0)
			if self.setup.IsDone(): #if we are completely done
				hdiff=self.setup.GetHD()
				hd_label="%.5f m" %hdiff
				if self.pmode=='precision':
					dh,OK=self.setup.HDTest(self.ini.maxhd)
					if not OK:
						hdt_color="red"
					else:
						hdt_color="green"
					hdt_label="%.2f mm" %(dh*1000)
				self.nextbutton.Enable()
			else:
				hd_label="NA"
				hdt_label="NA"
				hdt_color=None
				self.nextbutton.Enable(0)
			#now we can updata opst-statusbox
			if self.pmode=='detail':
				self.opststatus.UpdateStatus([di_label,dd_label,hd_label],colours={1:ddcolor})
			else:
				self.opststatus.UpdateStatus([di_label,dd_label,hd_label,hdt_label],colours={1:ddcolor,3:hdt_color})
	def UpdateStretchBox(self):
		ddsum=self.statusdata.GetDDSum()
		if abs(ddsum)>4.0:
			dd_color="red"
		else:
			dd_color="green"
		ul=["%.2f m" %ddsum]
		ul+=["%s" %self.statusdata.GetStart(),"%.2f m" %self.statusdata.GetDistance(),"%.5f m" %self.statusdata.GetHdiff()]
		ul+=["%i" %self.statusdata.GetSetups()]
		self.strkstatus.UpdateStatus(ul,colours={0:dd_color})
	def OnDelete(self,event):
		if self.mmode!='manual':
			self.SetManualMode()
		if self.nmode==2:
			if not (self.setup.back.Has2Readings() or self.setup.forward.Has2Readings()): #do we have data at bottom?
				self.nmode=1
				self.back.EnableTop()
				self.forward.EnableTop()
				self.back.DisableBottom()
				self.forward.DisableBottom()
				self.back.dist.SetFocus()
			else:
				self.back.ClearBottom() #does not send text events....
				self.forward.ClearBottom()
				self.setup.back.ClearReading2()
				self.setup.forward.ClearReading2()
				#self.SetStatus()
				self.back.hd2.SetFocus()
		else:
			if not self.setup.HasData():
				dlg=GUI.MyMessageDialog(self,u"Bem\u00E6rk",u"Hvis du vil slette flere data m\u00E5 du editere resultatfilen :-)")
				dlg.ShowModal()
			self.back.ClearTop()
			self.forward.ClearTop()
			self.setup.back.ClearAll() 
			self.setup.forward.ClearAll()
			self.back.point.SetFocus()
		self.SetStatus()
		self.UpdateStretchBox()		
	def OnDouble(self,event):
		Core.SoundKey()
		self.TestAndPrompt() #will return to here if unacceptable errors 
	def OnNext(self,event):
		self.TestAndPrompt()
	def TestAndPrompt(self): #will return to her if unacceptable errors
		#Test rej. criteria, test for start and endpoints. Prompt user
		#If ok, go to next opst, double.meas or make 'hoved' and go to next.
		#Update statusdata (strech)
		if self.nmode==2 or self.pmode=='detail':
			gotohead=False
			if self.statusdata.GetSetups()==0: #then we have just started a strech
				startp=self.back.point.GetValue()
				if len(startp)==0:
					GUI.ErrorBox(self,"Du skal indtaste et startpunkt.")
					return 
				else:
					OK=self.ValidatePointName(startp)
					if not OK:
						GUI.ErrorBox(self,"Startpunkt %s ikke korrekt!\nIndtast nyt punktnavn" %startp)
						return
					else:
						self.statusdata.SetStartPoint(startp) #set startpoint
			endp=self.forward.point.GetValue()
			if len(endp)>0:
				OK=self.ValidatePointName(endp)
				if not OK:
					GUI.ErrorBox(self,"Slutpunkt %s ikke korrekt!\nIndtast nyt punktnavn" %endp)
					return
				else: #prepare to make head!
					gotohead=True
					self.statusdata.SetEndPoint(endp)
		nerrors=0  #now do various error checks.
		errmsg=""
		if not self.setup.back.DistanceTest(self.ini.maxsl):
			nerrors+=1
			errmsg+=u"For langt bagudsigte.\n"
		if not self.setup.forward.DistanceTest(self.ini.maxsl):
			nerrors+=1
			errmsg+=u"For langt fremsigte.\n"
		if not self.setup.DistanceTest(self.ini.maxdd):
			nerrors+=1
			errmsg+=u"For h\u00F8j forskel mellem afst.-frem og afst.-tilbage: %.2f m.\n" %(abs(self.setup.GetDistanceDifference()))
		if self.pmode=='precision':
			dh,OK=self.setup.HDTest(self.ini.maxhd)
			if not OK:
				nerrors+=1
				errmsg+=u"For h\u00F8j forskel mellem dobbeltm\u00E5lte h\u00F8jdeforskelle!\n"
		if not self.setup.back.SDTest(self.ini.maxsd):
			nerrors+=1
			errmsg+=u"For h\u00F8j standardafv. fra instrument i tilbagesigte.\n"
		if not self.setup.forward.SDTest(self.ini.maxsd):
			nerrors+=1
			errmsg+=u"For h\u00F8j standardafv. fra instrument i fremsigte.\n"
		if not self.setup.back.RodTest():
			nerrors+=1
			errmsg+=u"Tilbagesigte ikke i tilladeligt omr\u00E5de af l\u00E6gten.\n"
		if not self.setup.forward.RodTest():
			nerrors+=1
			errmsg+=u"Fremsigte ikke i tilladeligt omr\u00E5de af l\u00E6gten.\n"
		if nerrors>0:
			msg=u"F\u00F8lgende fejlkriterier overskredet:\n"+errmsg+u"Vil du forts\u00E6tte alligevel?"
			dlg=GUI.OKdialog(self,"Fejl!",msg,buttonlabels=["JA","NEJ"])
			dlg.ShowModal()
			OK=dlg.WasOK()
			dlg.Destroy()
			if not OK:
				return
		if self.pmode=='detail' or self.nmode==2:
			#now update statusdata
			#self.Log("%s %i %s" %(self.pmode,self.nmode,gotohead))
			self.statusdata.AddSetup(self.setup.GetHD(),self.setup.GetDistance(),self.setup.GetDistanceDifference())
			if gotohead:
				self.UpdateStretchBox()
				OK=self.TestStretch()
				if OK: #then make head
					self.MakeHead()
				else:
					self.Log("Test ikke OK")
					self.statusdata.SubtractSetup(self.setup.GetHD(),self.setup.GetDistance()) #should be improved....
					self.UpdateStretchBox()
			else:
				self.WriteData()
				self.StartNew()
		else:
			self.GoToDouble()
	def TestStretch(self):
		if self.parent.fbtest is None:
			return True
		else:
			data=self.statusdata
			found,OK,diff,nfound,msg=self.parent.fbtest.TestStretch(data.GetStart(),data.GetEnd(),data.GetHdiff())
			if found:
				if OK:
					self.Log(msg)
					return True
				else:
					msg+=u"\nVil du godkende m\u00E5lingen?"
					dlg=GUI.OKdialog(self,"Forkastelseskriterie",msg)
					dlg.ShowModal()
					OK=dlg.WasOK()
					dlg.Destroy()
					return OK
			else:
				self.Log(msg)
				return True
	def GoToDouble(self):
		self.forward.DisableTop()
		self.back.DisableTop()
		self.forward.EnableBottom()
		self.back.EnableBottom()
		self.doublebutton.Enable(0)
		self.back.hd2.SetFocus()
		self.nmode=2
		if self.instrument.GetPortStatus():
			self.AutoHandler('back')
	def StartNew(self,swap=True):
		self.nmode=1
		self.nextbutton.Enable(0)
		self.UpdateStretchBox()
		if self.statusdata.GetSetups()>0:
			self.back.DisablePoint()
			self.back.dist.SetFocus()
		else:
			self.back.point.Enable()
			self.back.point.SetFocus()
		self.opststatus.Clear()
		self.backstatus.Clear()
		self.forwardstatus.Clear()
		self.forward.Clear()
		self.back.Clear()
		if self.statusdata.slutpunkt is not None and self.statusdata.GetSetups()==0: #do this after clear.
				self.back.point.ChangeValue(self.statusdata.slutpunkt)
		self.forward.EnableTop()
		self.back.EnableTop()
		self.forward.DisableBottom()
		self.back.DisableBottom()
		self.setup.StartNew()
		#Swap Rods:
		if swap:
			if self.statusdata.GetSetups()>0 or self.statusdata.GetSetupsAll()>0:
				backrod=self.back.rod.GetSelection()
				forwrod=self.forward.rod.GetSelection()
				self.forward.rod.SetSelection(backrod)
				self.back.rod.SetSelection(forwrod)
		if (self.statusdata.GetSetups()>0 or self.statusdata.GetSetupsAll()>0) and self.instrument.GetPortStatus():
			self.AutoHandler('back')
		else:
			self.SetManualMode()
	def MakeHead(self):
		if self.parent.fbtest is not None and self.parent.fbtest.found:
			test=self.parent.fbtest.wasok
		else:
			test=None
		temp=self.statusdata.GetTemperature()
		hvd=Core.MakeHead(self,self.statusdata,Funktioner.Dato(),Funktioner.Nu(),temp=temp,test=test)
		hvd.ShowModal()
		if hvd.WasOK():
			asphalt_temp=None
			vals=hvd.GetValues()
			if len(vals)==8:
				start,slut,dato,tid,jside,temp,asphalt_temp,ekstra=vals
			else:
				start,slut,dato,tid,jside,temp,ekstra=vals
			if start!=self.statusdata.GetStart() or slut!=self.statusdata.GetEnd():
				self.statusdata.slutpunkt=slut #if edited save this
				self.statusdata.startpunkt=start
				OK=self.TestStretch()
				if not OK: #then escape
					hvd.Destroy()
					return
			self.WriteData(True)
			dato=dato.strip().replace(" ","")
			tid=tid.strip().replace(" ","")
			jside=jside.replace(",",".").strip().replace(" ","")
			resfile=open(self.resfile,"a")
			if len(ekstra)>0:
				for line in ekstra.splitlines():
					line=Funktioner.Internationale(line)
					resfile.write(line+"\n") #ikke kommentar-tegn foran mere....
			hdiff,dist,nopst=self.statusdata.GetStretchData()
			if asphalt_temp is not None:
				resfile.write("AT: %.2f\n" %asphalt_temp)
			resfile.write("# %s %s %s %s %.2f %.5f %s %.1f %i\n\n"%(start,slut,dato,tid,dist,hdiff,jside,temp,nopst))
			resfile.close()
			#log to parents log
			self.parent.Log("Hoved:\nFra %s til %s" %(start,slut))
			self.parent.Log("Journalside: %s" %jside)
			self.parent.Log("Hdiff: %.4f m Afstand: %.2f m Opstillinger: %d" %(hdiff,dist,nopst)) 
			#now print
			if ekstra.find("dontprint")==-1:
				try:
					FileOps.Jside(self.resfile,mode=1,program="MGL")
				except Exception, msg:
					GUI.ErrorBox(self,"Fejl under udprintning af journalside!\nFortvivl ikke, denne kan gendannes fra datafilen.")
			#update data 
			if self.parent.fbtest is not None:
				OK=self.parent.fbtest.InsertStretch(start,slut,self.statusdata.GetHdiff(),self.statusdata.GetDistance(),dato,tid)
				#self.Log(repr(OK))
				if not OK:
					GUI.ErrorBox(self,"Kunne ikke inds\u00E6tte str\u00E6kningen i forkastelses-databasen.")
			self.statusdata.AddTemperature(temp,Funktioner.MyTime())
			self.statusdata.StartNewStretch()
			#if clearddsum is checked : also clear da sum, man!
			if self.clearddsum.IsChecked():
				self.statusdata.ClearDD()
				self.Log("Resetter delta-afstands-sum")
			self.back.EnablePoint()
			#start new strech
			hvd.Destroy()
			self.StartNew()
		else:
			self.statusdata.SubtractSetup(self.setup.GetHD(),self.setup.GetDistance()) #should be improved....
			self.UpdateStretchBox()
			hvd.Destroy()
		
		
	def WriteData(self,endstrech=False):
		resfile=open(self.resfile,"a")
		startstrech=False
		for aim in ['back','forward']:
			data=self.setup.aim[aim]
			if self.statusdata.GetSetups()==1 and aim=='back':
				point=self.statusdata.startpunkt
				startstrech=True
			elif endstrech and aim=='forward':
				point=self.statusdata.slutpunkt
			else:
				point=""
			if aim=='forward':
				shd="%.5f m" %self.setup.GetHD()
			else:
				shd=""
			if self.pmode=="detail":
				resfile.write("%*s %*s %*s %*.2f m %*.5f m %s\n" %(-13,data.daim,-11,point,-5,data.rod.name,-4,data.GetDistance(),-7,data.GetHD(),shd))
			else:
				hd1,hd2=data.GetHDS()
				resfile.write("%*s %*s %*s %*.2f m %*.5f m %*.5f m %s\n" %(-13,data.daim,-11,point,-5,data.rod.name,-4,data.GetDistance(),-7,hd1,-7,hd2,shd))
		if self.got_temp_from_inst:
			resfile.write("T: %s %s\n" %(self.statusdata.GetTemperature(),Funktioner.Nu()))
		#Added: Write sds
		if len(self.setup.aim['back'].GetSDS())+len(self.setup.aim['forward'].GetSDS())>0:
			text="sd:"
			for aim in ['back','forward']:
				data=self.setup.aim[aim]
				sds=data.GetSDS()
				if len(sds)>0:
					text+=" %s:" %data.daim[0]
					for sd in sds:
						text+=" %.5f m" %sd
			resfile.write(text+"\n")
		code="N"
		point=""
		if startstrech:
			code="B1"
			point=self.statusdata.startpunkt
		if endstrech:
			code="B2"
			point=self.statusdata.slutpunkt
		resfile.write("* %s %.2f %.2f %.6f %s\n" %(code,self.setup.GetDistance(),self.setup.GetDistanceDifference(),self.setup.GetHD(),point))
		if not self.footsetup.IsChecked():
			if self.parent.gps.isAlive():
				try:
					x,y,dop=self.parent.gps.GetPos() #not compl. thread safe
				except:
					pass
				else:
					if dop<30:
						resfile.write("GPS: %.1f %.1f %.1f\n" %(x,y,dop))
		else:
			resfile.write("Fodopstilling.\n")
		resfile.close()
		
	def PointNameHandler(self,name):
		name=Pointname2Numformat(name)
		if self.statusdata.GetSetups()>0 or not self.forward.point.IsEmpty(): #a way to force insertion into forward-point
			self.forward.point.SetValue(name)
		else:
			self.back.point.SetValue(name)
	def ValidatePointName(self,name): #should perhaps be defined elsewhere
		if 3<len(name)<12:
			try:
				int(name)
			except:
				pass
			else:
				return True
		return False
	def OnInstLog(self,event):
		self.Log(event.text)
	def Log(self,text):
		if self.log.GetNumberOfLines()>6:
			self.log.Clear()
		self.log.AppendText(text+"\n")
#-----------------------------------------------------------#
#Panels etc. used in the MainMGLMeasurement-frame
#------------------------------------------------------------#
class MyNumMGL(GUI.MyNum): #a MGL version of the classic GUI-class :-)
	def __init__(self,parent,low=-999,high=999,digitlength=None,ntype=float,**kwargs):
		GUI.MyNum.__init__(self,parent,low,high,digitlength=digitlength,ntype=ntype,**kwargs)
		self.sound=True #play sound on bad input?
	def OnEnter(self,event): #Overides prev event-handler 
		if (not self.ok) and self.sound and (not self.IsEmpty()):
			Core.SoundAlert()
		elif self.next!=None:
			self.next.SetFocus()
			event.Skip()
		else:
			event.Skip()
	

class MGLpanel(wx.Panel): # panel with text, two fields with two buttons to the right,
	def __init__(self,parent,title,rods=["1","2"],size=12):
		wx.Panel.__init__(self,parent)
		self.aim=None #is set from outside, can be 'back' or 'forward'
		self.rods=rods #only names, not rod-classes.
		self.point=GUI.MyTextField(self,size=(120,-1),fontsize=size)
		pointsizer=GUI.FieldWithLabel(self,field=self.point,size=size,label="Pkt:")
		self.rod=Core.RodBox(self,rods,(120,-1),fontsize=size)
		self.dist=MyNumMGL(self,0,200,2,size=(120,-1),fontsize=size) #distandsfelt
		rodsizer=GUI.FieldWithLabel(self,field=self.rod,label=u"Lgt:",size=size)
		self.hd=MyNumMGL(self,0,100,5,size=(120,-1),fontsize=size) #sigtehoejdefelt
		self.hds=[self.hd] 
		distsizer=GUI.FieldWithLabel(self,field=self.dist,size=size,label="L:")
		maalsizer=GUI.FieldWithLabel(self,field=self.hd,size=size,label="H1:")
		self.autobutton=GUI.MyButton(self,"AUTO(*)",size-1)
		#browsing#
		self.point.SetNext(self.rod)
		self.dist.SetNext(self.hd)
		self.dist.SetPrev(self.rod)
		self.hd.SetPrev(self.dist)
		#sizers#
		self.box=wx.StaticBox(self,wx.ID_ANY,label=title)
		self.box.SetFont(GUI.DefaultFont(size+1))
		self.bsizer=wx.StaticBoxSizer(self.box,wx.VERTICAL)
		self.sizer=wx.BoxSizer()
		self.bsizer.Add(pointsizer,1,wx.ALL|wx.ALIGN_RIGHT,5)
		self.bsizer.Add(rodsizer,1,wx.ALL|wx.ALIGN_RIGHT,5)
		self.bsizer.Add(distsizer,1,wx.ALL|wx.ALIGN_RIGHT,5)
		self.bsizer.Add(maalsizer,1,wx.ALL|wx.ALIGN_RIGHT,5)
		self.bsizer.Add(self.autobutton,0,wx.ALL|wx.CENTER,5)
		self.sizer.Add(self.bsizer,0,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)
	def DefinePrevItem(self,item):
		self.point.SetPrev(item)
	def DefineNextItem(self,item):
		self.hd.SetNext(item)
		self.hd.SetNextReturn(item)
	def Clear(self): #can be overridden my MGLPpanel
		self._Clear()
	def _Clear(self):
		self.hd.Clear()
		self.dist.Clear()
		self.point.Clear()
	def ClearTop(self):
		self.hd.Clear()
		self.dist.Clear()
	def EnableBottom(self):
		pass
	def DisableBottom(self):
		pass
	def EnableTop(self):
		self.hd.Enable()
		self.dist.Enable()
	def DisableTop(self):
		self.hd.Enable(0)
		self.dist.Enable(0)
	def DisablePoint(self):
		self.point.Enable(0)
	def EnablePoint(self):
		self.point.Enable(1)
		
	
	def GetRod(self):
		return self.rod.GetSelection()
	def SetAutoHandler(self,fct):
		self.autofunction=fct
		self.autobutton.Bind(wx.EVT_BUTTON,self.OnAutoButton)
		for hd in self.hds:
			hd.RegisterKeyHandler(self.AutoKey)
		self.dist.RegisterKeyHandler(self.AutoKey)
	def AutoKey(self,key):
		if key==42:
			self.autofunction(self.aim)
			return True
		else:
			return False
	def OnAutoButton(self,event):
		Core.SoundKey()
		self.autofunction(self.aim)
	def SetDistanceHandler(self,fct):
		self.distancefunction=fct
		self.dist.Bind(wx.EVT_TEXT,self.OnDistance)
	def OnDistance(self,event):
		self.distancefunction(self.dist,self.aim)
	def SetHDHandler(self,fct):
		self.hdfunction=fct
		for hd in self.hds:
			hd.Bind(wx.EVT_TEXT,self.OnHD)
	def OnHD(self,event):
		self.hdfunction(event.GetEventObject(),self.aim)
	def SetHDEnterHandler(self,fct):
		self.hdefunction=fct
		for hd in self.hds:
			hd.Bind(wx.EVT_TEXT_ENTER,self.OnHDE)
	def OnHDE(self,event):
		self.hdefunction(event.GetEventObject(),self.aim)
		event.Skip()
	def SetRodHandler(self,fct):
		self.rodfunction=fct
		self.rod.Bind(wx.EVT_COMBOBOX,self.OnRod)
	def OnRod(self,event):
		self.rodfunction(self.aim)
	def SetRodEnterHandler(self,fct):
		self.rodefunction=fct
		self.rod.Bind(wx.EVT_TEXT_ENTER,self.OnRodEnter)
	def OnRodEnter(self,event):
		self.rodefunction(self.aim)
		event.Skip()
		
	
class MGLPpanel(MGLpanel): #'precision mode' which has 2 hd-fields
	def __init__(self,parent,title,rods=[],size=12):
		MGLpanel.__init__(self,parent,title,rods,size)
		self.hd2=MyNumMGL(self,0,100,5,size=(120,-1),fontsize=size)
		self.hds=[self.hd,self.hd2]
		maalsizer=GUI.FieldWithLabel(self,field=self.hd2,size=size,label=u"H2:")
		self.bsizer.Insert(4,maalsizer,1,wx.ALL|wx.ALIGN_RIGHT,5)
		self.SetSizerAndFit(self.sizer)
	def DefineNextItem2(self,item):
		self.hd2.SetNext(item)
		self.hd2.SetNextReturn(item)
	def ClearBottom(self):
		self.hd2.Clear()
	def Clear(self):
		self.ClearBottom()
		self._Clear()
	def EnableBottom(self):
		self.hd2.Enable()
	def DisableBottom(self):
		self.hd2.Enable(0)
	
	





		
#----------Main Frame, parent of other frames in program-------------#		
class MGLmain(Core.MLBase):
	def __init__(self,parent,resfil,instrument,laegter,data,gps,ini,statusdata,size):
		Core.MLBase.__init__(self,parent,resfil,data,gps,ini,statusdata,PROGRAM,size)
		self.instrument=instrument
		self.laegter=laegter
		buttonbox=GUI.ButtonBox(self,[u"Detailm\u00E5ling",u"Pr\u00E6cisionsm\u00E5ling"],fontsize=self.size,label=u"M\u00E5ling")
		buttonbox.button[0].Bind(wx.EVT_BUTTON,self.OnGoToMeasurement)
		buttonbox.button[1].Bind(wx.EVT_BUTTON,self.OnGoToPMeasurement)
		self.rightsizer.Add(buttonbox,1,wx.EXPAND|wx.ALL,5)
		self.SetSizer(self.sizer)
		self.sizer.FitInside(self)
		buttonbox.SetFocus()
		self.mwindow=GUI.DummyWindow() #alwyas has a measurement window attribute,
	def UpdateStatus(self):
		self._UpdateStatus()
	def OnGoToMeasurement(self,event):
		if not isinstance(self.mwindow,GUI.DummyWindow):
			if self.mwindow.pmode=="precision":
				OK=True
				if self.mwindow.setup.HasData():
					dlg=GUI.OKdialog(self,u"Bem\u00E6rk",msg=u"Vil du skifte til 'detailmode' og slette den aktuelle opstilling?")
					dlg.ShowModal()
					OK=dlg.WasOK()
					dlg.Destroy()
				if OK:
					self.mwindow.Close()
					self.mwindow=MGLMeasurementFrame(self,"detail")
			else:
				self.mwindow.ShowMe()
		else:
			self.mwindow=MGLMeasurementFrame(self,"detail")
		self.mwindow.InitializeMap()
	def OnGoToPMeasurement(self,event):
		if not isinstance(self.mwindow,GUI.DummyWindow):
			if self.mwindow.pmode=="detail":
				OK=True
				if self.mwindow.setup.HasData():
					dlg=GUI.OKdialog(self,u"Bem\u00E6rk",msg=u"Vil du skifte til 'pr\u00E6cisionsmode' og slette den aktuelle opstilling?")
					dlg.ShowModal()
					OK=dlg.WasOK()
					dlg.Destroy()
				if OK:
					self.mwindow.Close()
					self.mwindow=MGLMeasurementFrame(self,"precision")
			else:
				self.mwindow.ShowMe()
		else:
			self.mwindow=MGLMeasurementFrame(self,"precision")
		self.mwindow.InitializeMap()

#---------Start up frame which inits the main frame--------------------#
class StartFrame(Core.StartFrame):
	def __init__(self,parent):
		Core.StartFrame.__init__(self,parent,PROGRAM,MGLinireader(),Core.MGLStatusData()) #initialize with these values
	def StartProgram(self):
		instrument=self.instruments[0]
		mainframe=MGLmain(None,self.resfile,self.instruments[0],self.laegter,self.data,self.gps,self.ini,self.statusdata,self.size)
		mainframe.Show()
		self.Close()

def main():
	App=wx.App()
	#frame=MLBase(None,"Test",ini,StatusData(),ProgramType())
	frame=StartFrame(None)
	frame.Show()
	App.MainLoop()
	sys.exit()

		
class MGLinireader(Core.IniReader): #add more error handling!
	def __init__(self):
		Core.IniReader.__init__(self,BASEDIR+"/MGL.ini",1,1)
		self.ini.fbtest=3.0 #frem-tilbage forkast
		self.ini.fbunit="ne"
		self.ini.maxdd=2.0 #max. afst. forsk.
		self.ini.maxsl=50 #max. sigtel.
		self.ini.maxsd=0.00012 #max inst. sd
		self.ini.maxhd=0.00050 #max forskel mellem sigter i praes.-mode
		self.ini.instport=5 
		self.ini.instbaud=9600
	def CheckAdditionalKeys(self,key,line):
		if key=="instrument" and len(line)>3:
			instrumenttype=line[1]
			instrumentname=line[0]
			instrumentport=int(line[2])
			instrumentbaud=int(line[3])
			if instrumenttype.lower().find("dini")!=-1:
				self.instruments.append(Instrument.DINI(instrumentname,instrumentport,instrumentbaud,instrumenttype))
		if key=="fejlgraenser" and len(line)>0:
			self.ini.maxsl=float(line[0])
			if len(line)>1:
				self.ini.maxdd=float(line[1])
			if len(line)>2:
				self.ini.maxsd=float(line[2])
			if len(line)>3:
				self.ini.maxhd=float(line[3])
		if key=="laegte" and len(line)>3:
			name=line[0]
			zone_low=float(line[1])
			zone_high=float(line[2])
			zeroshift=float(line[3])
			self.laegter.append(MGLlaegte(name,zone_low,zone_high,zeroshift))
			
	
if __name__=="__main__":
	main()
	
	