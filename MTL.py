import wx
import Core #defines classes that are common to, or very similar in, MGL and MTL
import MyModules.GUIclasses2 as GUI #basic GUI-stuff
from MyModules.MLmap import PanelMap
from MyModules.ExtractKMS import Numformat2Pointname,Pointname2Numformat
import Instrument 
import numpy as np
import Funktioner
import FileOps
import sys
BASEDIR=Core.BASEDIR #the directory, where the program is located
PROGRAM=Core.ProgramType()
PROGRAM.name="MTL"
PROGRAM.version="beta 0.1"
PROGRAM.date="26-08-11"
PROGRAM.type="MTL" #vigtigt signak til diverse faellesfunktioner for MGL og MTL....
PROGRAM.about="""
MTL program skrevet i Python. 
Bugs rettes til simlk@kms.dk
"""
DEBUG=True
#---------Various Global Vars--------------#
RADIUS=6385000.0   #Jordradius.
MAX_ROD=30.0      #Maximum rod size accepted in input fields
MIN_DECREMENT=0.0005 # A bit overdone perhaps - a var which holds the minimal allowed decrement of marks (which should decrease - measurements from top to bottom).....
MAX_LENGTH_MUTUAL=10000 # Value which determines the max input for the distance fields....
SL="*"*50
FONTSIZE=12  #Well, wxWindows should really use this on init - TODO....
#---------Main Windows defined here--------------------------------------#
class MTLmain(Core.MLBase):
	def __init__(self,parent,resfil,instruments,laegter,data,gps,ini,statusdata,size):
		Core.MLBase.__init__(self,parent,resfil,data,gps,ini,statusdata,PROGRAM,size)
		self.instruments=instruments
		statusdata.SetInstruments(instruments) #also handy to keep pointers to instruments in statusdata and handle "state" logic there!
		self.laegter=laegter
		#Define action buttons at bottom of window
		#The order that buttons appear in should reflect the ordering of self.instruments (and also in statusdata) 
		basisbuttons=[instrument.name for instrument in instruments]
		basisbox_start=GUI.ButtonBox(self,basisbuttons+[u"Overf\u00F8r h\u00F8jde"],fontsize=self.size,label="Basis-start",style="vertical")
		middlebox=GUI.ButtonBox(self,[u"G\u00E5 til m\u00E5ling"],fontsize=self.size,label="Inst>>Inst",style="vertical")
		basisbox_slut=GUI.ButtonBox(self,[u"G\u00E5 til m\u00E5ling"],fontsize=self.size,label="Basis-slut",style="vertical")
		self.buttonboxes=[basisbox_start,middlebox,basisbox_slut]
		#SET UP EXTRA MENU ITEMS#
		self.funkmenu.AppendSeparator()
		DeleteLast=self.funkmenu.Append(wx.ID_ANY,u"Slet seneste m\u00E5ling",u"Sletter seneste opstilling i datafilen!")
		DeleteToLastHead=self.funkmenu.Append(wx.ID_ANY,u"Slet til seneste hoved","Sletter til seneste hoved i datafilen!")
		#EVENT HANDLING SETUP#
		basisbox_start.button[0].Bind(wx.EVT_BUTTON,self.OnBasis1)
		basisbox_start.button[1].Bind(wx.EVT_BUTTON,self.OnBasis2)
		basisbox_start.button[2].Bind(wx.EVT_BUTTON,self.OnTransferHeight)
		middlebox.button[0].Bind(wx.EVT_BUTTON,self.OnInstrument2Instrument)
		basisbox_slut.button[0].Bind(wx.EVT_BUTTON,self.OnBasisEnd)
		sizer=wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(basisbox_start,1,wx.ALL,5)
		sizer.Add(middlebox,1,wx.ALL,5)
		sizer.Add(basisbox_slut,1,wx.ALL,5)
		self.rightsizer.Add(sizer,1,wx.EXPAND|wx.ALL,5)
		self.SetSizer(self.sizer)
		self.sizer.FitInside(self)
		basisbox_start.SetFocus()
		self.mwindow=GUI.DummyWindow() #alwyas has a measurement window attribute,
		self.UpdateStatus()
	def UpdateStatus(self):
		self._UpdateStatus()
		allowed_actions=[True,False,False]
		if self.statusdata.GetSetups()>0:
			allowed_actions=[False,True,True]
		instrumentstate=self.statusdata.GetInstrumentState()
		#Enable buttons according to the current state defined in statusdata#
		for i in range(3):
			self.buttonboxes[i].Enable(allowed_actions[i] or DEBUG)
		if allowed_actions[0]:
			self.buttonboxes[0].button[2].Enable(instrumentstate>=0)
	def OnBasis1(self,event):
		self.Log(SL)
		win=MakeBasis(self,0)
		win.InitializeMap()
	def OnBasis2(self,event):
		self.Log(SL)
		win=MakeBasis(self,1)
		win.InitializeMap()
	def OnTransferHeight(self,event):
		self.Log(SL)
		hdiff,dist=self.statusdata.GetLastBasis()
		hdiff*=-1  #aiming backwards...
		self.statusdata.AddSetup(hdiff,dist)
		start=self.statusdata.GetEnd()
		self.statusdata.SetStart(start)
		instname=self.statusdata.GetDefiningInstrument().GetName()
		resfile=open(self.resfile,"a")
		self.Log(u"Overf\u00F8rer instrumenth\u00F8jde til %s" %instname)
		resfile.write("%*s %*s %*s %s\n" %((-12,"Basis",-12,"Instrument",-18,"Overfoert afstand","Overfoert hoejdeforskel")))
		resfile.write("%*s %*s %*s %.4fm\n" %(-12,start,-12,instname,-18,"%.2fm"%dist,hdiff))
		resfile.write("* B1 %s " %start+"%.3f %.6f\n" %(dist,hdiff))
		if self.gps.isAlive():
			try:
				x,y,dop=self.gps.GetPos() #not compl. thread safe
			except:
				pass
			else:
				if dop<30:
					resfile.write("GPS: %.1f %.1f %.1f\n" %(x,y,dop))
		resfile.close()
		self.UpdateStatus()
	def OnInstrument2Instrument(self,event):
		win=Instrument2Instrument(self)
		self.Log(SL)
		self.Log("II")
		self.statusdata.AddSetup(1.0,400.0)
		self.statusdata.SetInstrumentState((self.statusdata.GetInstrumentState()+1)%2)
		self.Log("Instrument %s now carries the height..." %(self.statusdata.GetInstrumentNames()[self.statusdata.GetInstrumentState()]))
		self.UpdateStatus()
	def OnBasisEnd(self,event):
		self.Log(SL)
		win=MakeBasis(self,self.statusdata.GetInstrumentState())
		win.InitializeMap()
#-------------------------Instrument2Instrument Frame Defined Here----------------------------------------------#
class DistancePanel(wx.Panel):
	def __init__(self,parent,instrument_names,setup,auto_func1,auto_func2):
		wx.Panel.__init__(self,parent)
		self.SetAutoMode=auto_func1
		self.SetSingleAutoMode=auto_func2
		self.setup=setup
		top_line=wx.BoxSizer(wx.HORIZONTAL)
		bottom_line=wx.BoxSizer(wx.HORIZONTAL)
		text1=GUI.MyText(self,instrument_names[0],FONTSIZE,style=wx.ALIGN_CENTER)
		text2=GUI.MyText(self,instrument_names[1],FONTSIZE,style=wx.ALIGN_CENTER)
		top_line.Add(text1,1,wx.ALIGN_LEFT|wx.EXPAND)
		top_line.Add(text2,1,wx.ALIGN_RIGHT|wx.EXPAND)
		self.autobutton=GUI.MyButton(self,"AUTO (*)",FONTSIZE)
		self.dfield1=GUI.MyNum(self,0,MAX_LENGTH_MUTUAL,digitlength=3,size=(180,-1))
		self.dfield2=GUI.MyNum(self,0,MAX_LENGTH_MUTUAL,digitlength=3,size=(180,-1))
		self.fields=[self.dfield1,self.dfield2]
		for i in range(2):
			field=self.fields[i]
			next=(i+1)%2
			field.SetNext(self.fields[next])
			field.SetNextTab(self.fields[next])
			field.SetPrev(self.fields[next])
			field.Bind(wx.EVT_TEXT,self.OnText)
			field.Bind(wx.EVT_CHAR,self.OnChar)
		bottom_line.Add(self.dfield1,1,wx.ALL,5)
		bottom_line.Add(self.autobutton,0,wx.ALL,5)
		bottom_line.Add(self.dfield2,1,wx.ALL,5)
		self.status=GUI.StatusBox2(self,["Difference:","Middel:"],label="Afstand",colsize=1,fontsize=FONTSIZE)
		self.status.UpdateStatus([])
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.status,1,wx.ALL,5)
		self.sizer.Add(top_line,0,wx.ALL|wx.EXPAND,5)
		self.sizer.Add(bottom_line,1,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)
	def OnText(self,event): 
		#Validate only the field issuing the event#
		field=event.GetEventObject()
		ok=field.Validate()
		pass #do something here,,,
		event.Skip()
	def OnChar(self,event): #easier to handle char events here, rather than via the standard 'keyhandler' setup of MyTextField....
		key=event.GetKeyCode()
		field=event.GetEventObject()
		if key==42: #char '*'
			self.SetAutoMode(self.fields)
		elif key==47:#char '/'
			self.SetSingleAutoMode(field)
		else:
			event.Skip() #so that text appears in the field....
		

class AutoPanel(wx.Panel):
	def __init__(self, parent, validator,text=None):
		self.parent=parent  
		self.next=None
		wx.Panel.__init__(self, parent,style=wx.RAISED_BORDER|wx.TAB_TRAVERSAL)
		self.control1=GUI.MyTextField(self,fontsize=FONTSIZE+2,size=(160,-1))
		self.autobutton=GUI.MyButton(self,"AUTO(*)",FONTSIZE)
		self.control2=GUI.MyTextField(self,fontsize=FONTSIZE+2,size=(160,-1))
		self.control1.SetValidator(validator)
		self.control2.SetValidator(validator)
		self.sizer=wx.BoxSizer(wx.HORIZONTAL)
		text=GUI.MyText(self,text,FONTSIZE)
		self.sizer.Add(text,0,wx.ALL|wx.ALIGN_CENTER_VERTICAL,5)
		self.sizer.Add(self.control1,0,wx.ALL,15)
		self.sizer.Add(self.autobutton,0,wx.ALL,15)
		self.sizer.Add(self.control2,0,wx.ALL,15)
		self.fields=[self.control1,self.control2]
		self.SetSizerAndFit(self.sizer)
	def Clear(self):
		for field in self.fields:
			field.Clear()
			field.SetBackgroundColour("white")
	

class SatsPanel(wx.Panel):
	def __init__(self,parent,instrument_names,setup,auto_func1,auto_func2):
		wx.Panel.__init__(self,parent)
		self.setup=setup
		self.SetAutoMode=auto_func1
		self.SetSingleAutoMode=auto_func2
		top_line=wx.BoxSizer(wx.HORIZONTAL)
		text1=GUI.MyText(self,instrument_names[0],FONTSIZE,style=wx.ALIGN_CENTER)
		text2=GUI.MyText(self,instrument_names[1],FONTSIZE,style=wx.ALIGN_CENTER)
		top_line.Add(text1,1,wx.ALIGN_LEFT|wx.EXPAND)
		top_line.Add(text2,1,wx.ALIGN_RIGHT|wx.EXPAND)
		self.status=GUI.StatusBox2(self,["H1:","H2:","Middel:","Restfejl:","Ind1:","Ind2:"],label="Seneste Sats",colsize=2,bold=True,fontsize=13)
		self.status.UpdateStatus()
		self.position1=AutoPanel(self,setup.Position1Validator,"1. kikkertstilling:")
		self.position2=AutoPanel(self,setup.Position2Validator,"2. kikkertstilling:")
		self.zfields=self.position1.fields+self.position2.fields #list of pointers to z-fields..
		for row in range(2):
			for col in range(2):
				field=self.zfields[col+2*row]
				field.ij_id=[row,col]
				field.Bind(wx.EVT_TEXT,self.OnText)
				field.Bind(wx.EVT_CHAR,self.OnChar)
				next=(col+2*row+1)%4
				prev=(next-2)%4
				field.SetNextReturn(self.zfields[next])
				field.SetNextTab(self.zfields[next])
				field.SetPrev(self.zfields[prev])
		#LAYOUT#
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.status,1,wx.ALL,5)
		self.sizer.Add(top_line,0,wx.ALL|wx.EXPAND,5)
		self.sizer.Add(self.position1,0,wx.ALL,5)
		self.sizer.Add(self.position2,0,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)
	def OnText(self,event): 
		#Validate only the field issuing the event#
		field=event.GetEventObject()
		ok=field.Validate()
		row,col=field.ij_id
		self.setup.SetValidity(row,col,ok)
		if ok:
			self.setup.SetData(row,col,field.GetValue())
			row_validity=self.setup.IsValid(row=row)
			if row_validity:
				pass
				#self.columns[3][row].SetValue("%.0f"%self.setup.GetIndexError(row))
				#self.columns[3][row].Validate()
			if self.setup.IsValid():
				#self.parent.UpdateHeightStatus()
				pass
		event.Skip()
	def OnChar(self,event): #easier to handle char events here, rather than via the standard 'keyhandler' setup of MyTextField....
		key=event.GetKeyCode()
		field=event.GetEventObject()
		row,col=field.ij_id
		if key==42: #char '*'
			start_field=col+2*row
			self.SetAutoMode(self.zfields[start_field:])
		elif key==47:#char '/'
			self.SetSingleAutoMode(field)
		else:
			event.Skip() #so that text appears in the field....
	
		
class Instrument2Instrument(GUI.FullScreenWindow):
	def __init__(self, parent):
		GUI.FullScreenWindow.__init__(self, parent)
		self.setup=MTLTransferSetup()
		self.mode=0
		self.modenames=["MANUEL","AUTO","SINGLE AUTO"]
		self.modecolors=["green","red","yellow"]
		self.statusdata=parent.statusdata
		self.instruments=self.statusdata.GetInstruments()
		inames=self.statusdata.GetInstrumentNames()
		inames=map(lambda x:x+": ",inames)
		self.statusbox=GUI.StatusBox2(self,inames+["Mode: "],fontsize=FONTSIZE,label="Status",colsize=1,minlengths=[7,7,11])
		self.aim=np.array([1,-1])*(1-2*int(self.statusdata.GetInstrumentState()==0)) #Well, I know that a one-liner can be harder to decode - in essense: aim is [1,-1] or [-1,1]
		self.statusbox.UpdateStatus(map(Funktioner.Bool2sigte,self.aim))
		self.resultbox=GUI.StatusBox2(self,["Afstand:","Antal satser:", u"H\u00F8jdeforskel:","Middelfejl:","Max. afvigelse:"],label="Resultat",colsize=3
		,fontsize=FONTSIZE)
		self.resultbox.UpdateStatus([])
		self.main=GUI.ButtonBox2(self,["AFSTAND",u"TILF\u00D8J SATS","CHECK SATS(ER)","ACCEPTER","AFBRYD"],label="Styring",colsize=2,fontsize=FONTSIZE)
		self.lower=wx.Panel(self)
		self.lower.sizer=wx.BoxSizer()
		self.dpanel=DistancePanel(self.lower,inames,self.setup,self.SetAutoMode,self.SetSingleAutoMode)
		self.spanel=SatsPanel(self.lower,inames,self.setup,self.SetAutoMode,self.SetSingleAutoMode)
		self.lower.sizer.Add(self.dpanel)
		self.lower.sizer.Add(self.spanel)
		#EVENT HANDLING SETUP#
		#self.main.buttons1.knap3.Bind(wx.EVT_BUTTON,self.SletSats)
		self.main.button[-1].Bind(wx.EVT_BUTTON,self.CloseOK)
		self.main.button[0].Bind(wx.EVT_BUTTON,self.OnSetDistanceMode)
		self.main.button[1].Bind(wx.EVT_BUTTON,self.OnSetZMode)
		#self.main.buttons2.knap2.Bind(wx.EVT_BUTTON,self.Fortryd)
		#LAYOUT#
		self.CreateRow()
		self.AddItem(self.statusbox,1,wx.ALIGN_LEFT)
		#rsizer=wx.BoxSizer(wx.VERTICAL)
		#rsizer.Add(self.main)
		#rsizer.Add(self.satsstatus)
		self.AddRow(1,wx.ALL|wx.ALIGN_LEFT,5)
		self.CreateRow()
		self.AddItem(self.resultbox,0,wx.ALL|wx.ALIGN_LEFT,5)
		#self.AddRow(0,wx.ALL|wx.ALIGN_LEFT,5)
		#self.CreateRow()
		self.AddItem(self.main,0,wx.ALL,5)
		self.AddRow(2,wx.ALL|wx.ALIGN_LEFT,5)
		self.CreateRow()
		self.AddItem(self.lower)
		self.AddRow(3,wx.ALL|wx.ALIGN_CENTER,10)
		self.UpdateStatus()     
		self.SetDistanceMode() #Gaa direkte til afstand
		self.ShowMe()
	def OnSetZMode(self,event):
		self.SetZMode()
	def OnSetDistanceMode(self,event):
		self.SetDistanceMode()
		#self.sizer.Layout()
	def SetDistanceMode(self):
		self.spanel.Show(0)
		self.dpanel.Show()
		self.lower.SetSizerAndFit(self.lower.sizer)
		#self.sizer.Layout()
	def SetZMode(self):
		self.dpanel.Show(0)
		self.spanel.Show()
		self.lower.SetSizerAndFit(self.lower.sizer)
		#self.SetSizerAndFit(self.sizer)
	def SetAutoMode(self,fields):
		self.auto_fields=fields
		self.mode=1
		self.UpdateStatus()
	def SetSingleAutoMode(self,field):
		self.auto_fields=[field]
		self.mode=2
		self.UpdateStatus()
	def UpdateStatus(self):
		self.statusbox.UpdateStatus(text=self.modenames[self.mode],colour=self.modecolors[self.mode],field=2)
		self.resultbox.UpdateStatus(["1.00000","2.12121","23.121212"])
	def CloseOK(self,event):
		self.Close()

#-------------------------Various Wx Windows Specialized for MTL and used in MakeBasis -------------------------------------------------#

#Panel til input af basismaalinger....
class OverfPanel(wx.Panel):
	def __init__(self,parent,basis_setup,low=-33,high=33): #input graenser for indeksfejl advarsler...
		wx.Panel.__init__(self,parent)
		self.parent=parent
		self.setup=basis_setup #a class which handles field validation, data storage and calculation
		self.sizer=wx.GridSizer(5,4,5,5)
		headings=[u"M\u00E6rke","1. kikkertstilling","2. kikkertstilling","Indeksfejl ('')"]
		for text in headings:
			field=GUI.MyText(self,text,14,style=wx.ALIGN_CENTER)
			self.sizer.Add(field,1,wx.ALL,0)
		self.columns=[[],[],[],[]]
		for row in range(4):
			field1=GUI.MyNum(self,0,MAX_ROD,size=(160,-1),fontsize=16) #The 'high' value here is set in the global var MAX_ROD
			field2=GUI.MyTextField(self,size=(160,-1),fontsize=16)
			field3=GUI.MyTextField(self,size=(160,-1),fontsize=16)
			field2.SetValidator(basis_setup.Position1Validator)
			field3.SetValidator(basis_setup.Position2Validator)
			field4=GUI.MyNum(self,low,high,size=(160,-1),fontsize=16,style=wx.TE_READONLY)
			self.columns[0].append(field1)
			self.columns[1].append(field2)
			self.columns[2].append(field3)
			self.columns[3].append(field4)
			self.sizer.Add(field1,1,wx.ALL,0)
			self.sizer.Add(field2,1,wx.ALL,0)
			self.sizer.Add(field3,1,wx.ALL,0)
			self.sizer.Add(field4,1,wx.ALL,0)
		#Set up event handling and field navigation#
		for col in range(3):
			for row in range(4):
				field=self.columns[col][row]
				if col>0:
					field.Bind(wx.EVT_CHAR,self.OnChar)
				field.Bind(wx.EVT_TEXT,self.OnText)
				nextrow=(row+1)%4
				nextcol=(col+int(row==3))%3
				nexttabrow=(row+int(col==2))%4
				nexttabcol=(col+1)%3
				prevtabcol=(col-1)%3
				prevtabrow=(row+3*(int(col==0)))%4
				field.SetNextReturn(self.columns[nextcol][nextrow])
				field.SetNextTab(self.columns[nexttabcol][nexttabrow])
				field.SetPrev(self.columns[prevtabcol][prevtabrow])
				field.ij_id=[row,col] #a custom id, to identify the field position in event handlers....
		self.SetSizerAndFit(self.sizer)
		#a list of zdist fields in the order they are *usually* measured:
		#top-> bottom + bottom-> top
		self.zfields=self.columns[1]+self.columns[2][::-1] 
	def DisableCol(self,i):
		for field in self.columns[i]:
			field.Enable(0)
	def EnableCol(self,i):
		for field in self.columns[i]:
			field.Enable(1)
	def OnText(self,event): 
		#Validate only the field issuing the event#
		field=event.GetEventObject()
		ok=field.Validate()
		row,col=field.ij_id
		self.setup.SetValidity(row,col,ok)
		if ok:
			self.setup.SetData(row,col,self.columns[col][row].GetValue())
			row_validity=self.setup.IsValid(row=row)
			if row_validity:
				self.columns[3][row].SetValue("%.0f"%self.setup.GetIndexError(row))
				self.columns[3][row].Validate()
			if self.setup.IsValid():
				self.parent.UpdateHeightStatus()
			if col==0 and row<3: #marks should decrease..... Not really reflected anywhere else... This is just a simple signal to the user....
				mark=float(field.GetMyValue())
				self.columns[0][row+1].SetBounds(0,mark-MIN_DECREMENT)  #uses a global var for this 'minimal' step...
		event.Skip()
	def OnChar(self,event): #easier to handle char events here, rather than via the standard 'keyhandler' setup of MyTextField....
		key=event.GetKeyCode()
		field=event.GetEventObject()
		row,col=field.ij_id
		if key==42: #char '*'
			start_field=(col-1)*4+row
			self.parent.SetAutoMode(self.zfields[start_field:])
		elif key==47:#char '/'
			self.parent.SetSingleAutoMode(field)
		else:
			event.Skip() #so that text appears in the field....
	
		
#Boks med felt til pkt. og drop-down box til laegtevalg
def ValidatePointName(name): #should perhaps be defined elsewhere
	if 3<len(name)<12:
		try:
			int(name)
		except:
			pass
		else:
			return True
	return False
class MTLChoiceBox(GUI.StuffWithBox): #TODO: Fix browsing on enter hit in rodbox......
	def __init__(self,parent,laegter):
		GUI.StuffWithBox.__init__(self,parent,label="Valg",style="vertical")
		self.point=GUI.MyTextField(self,12,size=(150,-1))
		self.point.SetValidator(ValidatePointName)
		pointsizer=GUI.FieldWithLabel(self,self.point,"Punkt:",12)
		self.laegtebox=Core.RodBox(self,laegter,size=(150,-1),fontsize=12)
		self.laegtebox.Bind(wx.EVT_TEXT_ENTER,self.OnEnter)
		self.laegtebox.SetSelection(0)
		laegtesizer=GUI.FieldWithLabel(self,self.laegtebox,u"L\u00E6gte:",12)
		self.AddStuff(pointsizer)
		self.AddStuff(laegtesizer)
		self.FinishUp()
		self.next_item=None #remember to set this attr to control browsing
	def SetPoint(self,point):
		self.point.SetValue(point)
		self.point.Validate()
	def GetPoint(self):
		return self.point.GetValue().strip()
	def GetRod(self):
		return self.laegtebox.GetSelection()
	def OnEnter(self,event):
		if self.next_item is not None:
			self.next_item.SetFocus()
		else:
			event.Skip()
		#....other stuff like checking point name etc.....#
		self.point.Validate()
#------------------------- MakeBasis Frame defined here --------------------------------------------------------------#
class MakeBasis(GUI.FullScreenWindow):
	def __init__(self, parent,instrument_number=0):
		self.laegter=parent.laegter
		self.instrument_number=instrument_number #the height status after succesful measurements should be this number.... Instrument that 'carries' height.
		self.statusdata=parent.statusdata
		self.resfile=parent.resfile
		self.ini=parent.ini  #data passed in ini-file, error limits relevant here
		self.mode=0 #modes are 0: manual and 1: auto 2; single auto - i.e. just one field....
		self.modenames=["MANUEL","AUTO","SINGLE AUTO"]
		self.modecolors=["green","red","yellow"]
		self.auto_fields=[] #an ordered list of fields from subpanel to receive data from instrument
		self.sigte=-2*int((self.statusdata.GetSetups())==0)+1
		self.setup=MTLBasisSetup(self.sigte)
		self.instrument=self.statusdata.GetInstruments()[instrument_number]
		GUI.FullScreenWindow.__init__(self, parent)
		self.status=GUI.StatusBox2(self,["Instrument: ","Sigte: ","Mode: "])
		self.valg=MTLChoiceBox(self,[rod.name for rod in self.laegter])
		startp=self.statusdata.GetEnd()
		if startp is None or self.sigte==1:
			startp=""
		self.valg.SetPoint("%s"%startp)
		self.map=PanelMap(self,self.parent.data,self.ini.mapdirs) #setup the map - a panel in the center of the screen
		self.map.RegisterPointFunction(self.PointNameHandler) #handles left-clicks on points in map - sets name in point box
		self.main=GUI.ButtonBox2(self,["AUTO(*)","MANUEL","ACCEPTER","AFBRYD"],label="Styring",colsize=2)
		index_min,index_max=self.instrument.GetIndexBounds()
		self.maal=OverfPanel(self,self.setup,index_min,index_max)
		self.valg.next_item=self.maal #controls that after 'enter' in rod-selection, we should go here.... 
		self.resultbox=GUI.StatusBox2(self,["Afstand: ",u"H\u00F8jde:"],label="Resultat",fontsize=12,colsize=2)
		self.controlbox=GUI.StatusBox2(self,[u"H\u00F8jde (m1+m3): ",u"H\u00F8jde (m2+m4): ","Difference: "],fontsize=12,label="Kontrol")
		self.resultbox.UpdateStatus([])
		self.controlbox.UpdateStatus([])
		#EVENT HANDLING SETUP#
		self.main.button[0].Bind(wx.EVT_BUTTON,self.OnSetAutoMode)
		self.main.button[1].Bind(wx.EVT_BUTTON,self.OnSetManualMode)
		self.main.button[2].Bind(wx.EVT_BUTTON,self.OnAccept)
		self.main.button[3].Bind(wx.EVT_BUTTON,self.OnCancel)
		self.maal.columns[2][3].Bind(wx.EVT_TEXT_ENTER,self.OnLastReturn)
		self.instrument.SetLogWindow(self)
		self.instrument.SetEventHandler(self)
		self.Bind(Instrument.EVT_LOG,self.OnInstLog)
		self.Bind(Instrument.EVT_DATA,self.OnData)
		#LAYOUT#
		self.UpdateStatus()
		self.CreateRow()
		sizer_left=wx.BoxSizer(wx.VERTICAL)
		sizer_left.Add(self.status,0,wx.ALL,5)
		sizer_left.Add(self.resultbox,0,wx.ALL,5)
		self.AddItem(sizer_left,1,wx.ALL|wx.ALIGN_LEFT,5)
		self.AddItem(self.map,2,wx.ALL,5)
		sizer_right=wx.BoxSizer(wx.VERTICAL)
		sizer_right.Add(self.valg,1,wx.ALL,5)
		sizer_right.Add(self.main,1,wx.ALL,5)
		self.AddItem(sizer_right,1,wx.ALL,5)
		self.AddRow(2,wx.ALIGN_LEFT|wx.ALL)
		#self.CreateRow()
		#self.AddItem(self.resultbox,1,wx.ALL|wx.ALIGN_LEFT,5)
		#self.AddRow(0,wx.ALL)
		self.CreateRow()
		self.AddItem(self.maal,1)
		self.AddItem(self.controlbox,1)
		self.AddRow(1,wx.ALL)
		self.ShowMe()
		self.valg.SetFocus()
		if DEBUG:
			self.TestMode()
		#WRITE TO LOG#
		self.Log(u"Starter basism\u00E5ling kl. %s" %Funktioner.Nu())
		self.Log("Sigte: %s, instrument: %s" %(Funktioner.Bool2sigte(self.sigte),self.instrument.GetName()))
		#TEST INSTRUMENT#
		if not self.instrument.TestPort():
			GUI.ErrorBox(self,u"Kunne ikke \u00E5bne instrumentets com-port...")
			self.Log(u"Kunne ikke \u00E5bne instrumentets com-port...")
	def InitializeMap(self): #should be called every time the frame is shown to go to gps-mode
		if self.parent.gps.isAlive():
			self.parent.map.DetachGPS()
			self.map.AttachGPS(self.parent.gps)
			self.map.SetGPSMode()
			self.map.UpdatePoints() #uses same data as parent, so this influences the parents map as well.
		else:
			self.map.SetPanMode()
		self.map.SetMap()
	def PointNameHandler(self,name):
		name=Pointname2Numformat(name)
		self.valg.SetPoint(name)
	def OnCancel(self,event):
		quit=True
		valid=self.setup.GetValidity()[:,1:].sum()
		if valid>1:
			dlg=GUI.OKdialog(self,"Vil du afslutte?",
			u"Du har foretaget %i valide m\u00E5linger.\nEr du sikker p\u00E5, at du vil aflsutte?"%valid)
			dlg.ShowModal()
			quit=dlg.WasOK()
			dlg.Destroy()
		if quit:
			self.Log(u"Afbryder basism\u00E5ling.")
			self.Close()
	def OnAccept(self,event):
		mask=self.setup.GetValidity()
		if not mask.all():
			GUI.ErrorBox(self,u"Udf\u00F8r alle m\u00E5linger f\u00F8rst")
		else:
			OK=self.valg.point.Validate()
			if OK:
				self.CloseOK()
			else:
				GUI.ErrorBox(self,"Indtast punktnavn.")
				self.valg.point.SetFocus()
	def OnLastReturn(self,event):
		mask=self.setup.GetValidity()
		if mask.all():
			self.main.button[2].SetFocus()
		else:
			event.Skip()
	def OnSetAutoMode(self,event):
		self.SetAutoMode(self.maal.zfields) 
	def OnSetManualMode(self,event):
		self.SetManualMode()
	def SetAutoMode(self,fields):
		mask=self.setup.GetValidity()
		maerker_ok=(mask[:,0].sum()==4) 
		if maerker_ok:
			if self.mode==0:
				self.mode=1
				self.auto_fields=fields
				for field in fields:
					field.Enable(0)
				#....etc......#
				self.UpdateStatus()
				self.instrument.ReadData()
			else:
				GUI.ErrorBox(self,u"Skift til manuel mode f\u00F8rst")
		else:
			GUI.ErrorBox(self,u"Indtast m\u00E6rker f\u00F8rst")
	def SetSingleAutoMode(self,field):
		mask=self.setup.GetValidity()
		maerker_ok=(mask[:,0].sum()==4) 
		if maerker_ok:
			if self.mode==0:
				self.mode=2
				self.auto_fields=[field]
				field.Enable(0)
				self.UpdateStatus()
				self.instrument.ReadData()
			else:
				GUI.ErrorBox(self,u"Skift til manuel mode f\u00F8rst")
		else:
			GUI.ErrorBox(self,u"Indtast m\u00E6rker f\u00F8rst")
	def SetManualMode(self):
		self.mode=0
		self.instrument.Kill() 
		for field in self.auto_fields:
			field.Enable()
		self.UpdateStatus()
	def UpdateStatus(self):
		self.status.UpdateStatus([self.instrument.GetName(),Funktioner.Bool2sigte(self.sigte),self.modenames[self.mode]],colours={2:self.modecolors[self.mode]})
	def UpdateHeightStatus(self):
		s,h1,h2,hdiff=self.setup.Calculate()
		dh=abs(h1-h2)
		col=Funktioner.State2Col(self.ini.maxdh_basis>=dh)
		self.controlbox.UpdateStatus(["%.4f m" %h1,"%.4f m" %h2,"%.1f mm" %((h1-h2)*1000.0)],colours={2:col})
		self.resultbox.UpdateStatus(["%.4f m" %s,"%.4f m" %hdiff])
	def TestMode(self):
		for i in range(0,4):
			self.maal.columns[0][i].SetValue(str(3-i*0.5))
			self.maal.columns[1][i].SetValue(str(88.1111+i))
			self.maal.columns[2][i].SetValue(str(271.4949-i))
	def DoSketch(self):
		msg=Sketch.sketch
		self.Log("Doing sketch....!")
		dlg=MyLongMessageDialog(self,"You asked for it!",msg)
		dlg.ShowModal()
		dlg.Destroy()
	def OnData(self,event):
		if self.mode>0: #some sort of auto mode...
			code,val=event.value
			if code=='E':
				Core.SoundBadData()
				GUI.ErrorBox(self,unicode(val))
				self.SetManualMode()  #leave function here...
			elif code!='<':
				Core.SoundBadData()
				GUI.ErrorBox(self,u"Forventede en vinkelm\u00E5ling!")
				self.SetManualMode()  #leave function here...
			else: #then code is '<' and we have angles...
				field=self.auto_fields.pop([0])
				field.SetValue(val) #issues a text-event which triggers event handlers... Watch out that these dont send the thread of control astray!!!!
				if len(self.auto_fields)==0:
					self.SetManualMode()
					self.Valg.SetFocus()
					Core.SoundGoodData()
				else:
					self.instrument.ReadData()
		else: #somehow the the instrument is still sending data - so kill the damn' thread
			self.instrument.Kill()
	def OnInstLog(self,event):
		self.Log(event.text)
	def TestStretch(self):
		if self.parent.fbtest is None:
			return True
		else:
			data=self.statusdata
			found,OK,diff,nfound=self.parent.fbtest.TestStretch(data.GetStart(),data.GetEnd(),data.GetHdiff())
			#self.Log(repr(found)+repr(OK)+repr(diff)+repr(nfound))
			if found:
				if OK:
					self.Log(u"Fremm\u00E5ling fundet, forkastelseskriterie overholdt.")
					return True
				else:
					msg=u"Forkastelseskriterie for frem og tilbage-m\u00E5lte str\u00E6kninger overksredet med %.1f mm.\n" %diff
					msg+=u"Vil du godkende m\u00E5lingen?"
					dlg=GUI.OKdialog(self,"Forkastelseskriterie",msg)
					dlg.ShowModal()
					OK=dlg.WasOK()
					dlg.Destroy()
					return OK
			else:
				return True
	def CloseOK(self): 
		#TODO: UPDATE INDEX ERRORS FOR INSTRUMENT!#
		s,h1,h2,hdiff=self.setup.GetResult()
		#Perhaps add test for abs(h1-h2)<self.ini.maxdh_basis here....
		point=self.valg.GetPoint()
		self.statusdata.AddSetup(hdiff,s)
		if self.sigte==1: #then we should make head and start new stretch. Also test back vs. forward here, if available.
			self.statusdata.SetEnd(point)
			OK=self.TestStretch()
			if OK:
				OK=self.MakeHead() #like in MGL - almost
				if OK:
					#We need to keep a pointer to the last hdiff and dist.... This is done internally in statusdata....
					self.statusdata.StartNewStretch()
				else:
					self.statusdata.SubtractSetup() #leave function here...
					return
			else:
				self.statusdata.SubtractSetup() #leave function here...
				return
		else:
			self.statusdata.SetStart(point)
			self.WriteData(point)
		self.statusdata.SetInstrumentState(self.instrument_number)
		self.Log(u"Afslutter basism\u00E5ling kl. %s" %Funktioner.Nu())
		index_errors=self.setup.GetIndexErrors()
		for i_err in index_errors:
			self.instrument.AddIndexError(i_err)
		self.parent.UpdateStatus()
		self.Close()  
	def MakeHead(self):
		if self.parent.fbtest is not None and self.parent.fbtest.found:
			test=self.parent.fbtest.wasok
		else:
			test=None
		temp=self.statusdata.GetTemperature()
		hvd=Core.MakeHead(self,self.statusdata,Funktioner.Dato(),Funktioner.Nu(),temp=temp,test=test)
		hvd.ShowModal()
		if hvd.WasOK():
			start,slut,dato,tid,jside,temp,ekstra=hvd.GetValues()
			if start!=self.statusdata.GetStart() or slut!=self.statusdata.GetEnd():
				self.statusdata.SetEnd(slut) #if edited save this
				self.statusdata.SetStart(start)
				OK=self.TestStretch()
				if not OK: #then escape  #TODO: Check this!!!!!!!!
					hvd.Destroy()
					return False
			self.WriteData(slut)
			dato=dato.strip().replace(" ","")
			tid=tid.strip().replace(" ","")
			jside=jside.replace(",",".").strip().replace(" ","")
			resfile=open(self.resfile,"a")
			if len(ekstra)>0:
				for line in ekstra.splitlines():
					line=Funktioner.Internationale(line)
					resfile.write(line+"\n") #ikke kommentar-tegn foran mere....
			hdiff,dist,nopst=self.statusdata.GetStretchData()
			resfile.write("# %s %s %s %s %.2f %.5f %s %.1f %i\n\n"%(start,slut,dato,tid,dist,hdiff,jside,temp,nopst))
			resfile.close()
			#log to parents log
			self.parent.Log("Hoved:\nFra %s til %s" %(start,slut))
			self.parent.Log("Journalside: %s" %jside)
			self.parent.Log("Hdiff: %.4f m Afstand: %.2f m Opstillinger: %d" %(hdiff,dist,nopst)) 
			#now print
			if ekstra.find("dontprint")==-1:
				try:
					FileOps.Jside(self.resfile,mode=1,program="MTL")
				except Exception, msg:
					GUI.ErrorBox(self,"Fejl under udprintning af journalside!\nFortvivl ikke, denne kan gendannes fra datafilen.")
			#update data 
			if self.parent.fbtest is not None:
				OK=self.parent.fbtest.InsertStretch(start,slut,self.statusdata.GetHdiff(),self.statusdata.GetDistance(),dato,tid)
				if not OK:
					GUI.ErrorBox(self,"Kunne ikke inds\u00E6tte str\u00E6kningen i forkastelses-databasen.")
			self.statusdata.AddTemperature(temp,Funktioner.MyTime())
			hvd.Destroy()
			return True
		else:
			hvd.Destroy()
			return False
	def WriteData(self,point):
		resfile=open(self.resfile,"a")
		space=max(map(len,self.statusdata.GetInstrumentNames()))+4
		rod_names=[rod.GetName() for rod in self.laegter]
		rod_name=rod_names[self.valg.GetRod()]
		rspace=max(map(len,rod_names))
		dist,h1,h2,hdiff=self.setup.GetResult()
		resfile.write("%*s %*s %*s %*s %s\n" %(-13,"Basis",-space,"Instrument",-rspace,"Laegte",-10,"Afstand","Hoejdeforskel"))
		self.Log("Punkt: %s" %point)
		self.Log(u"L\u00E6gte: %s\n" %rod_name)
		resfile.write("%*s %*s %*s %*s %.4fm\n" %(-13,point,-space,self.instrument.GetName(),-rspace,rod_name,-10,"%.2fm"%dist,hdiff))
		tup=tuple(map(lambda x:"%.2fm"%x, self.setup.GetData()[:,0]))
		resfile.write("%-8s %-8s %-8s %-8s\n" %tup)
		resfile.write("%-8s %-8s %-8s %-8s "%tuple(self.setup.GetRawData()[:,1].tolist()))
		resfile.write("%.4fm\n" %(h1))
		resfile.write("%-8s %-8s %-8s %-8s "%tuple(self.setup.GetRawData()[:,2].tolist()))
		resfile.write("%.4fm\n" %(h2))
		if self.sigte==-1:
			resfile.write("* B1 %s %.3f %.6f\n" %(point,dist,hdiff))
		else:
			resfile.write("* B2 %s %.3f %.6f\n" %(point,dist,hdiff)) #Well we break the backw. comp. of the file format here... Shouldn't be important.
		if self.parent.gps.isAlive():
			try:
				x,y,dop=self.parent.gps.GetPos() 
			except:
				pass
			else:
				if dop<30:
					resfile.write("GPS: %.1f %.1f %.1f\n" %(x,y,dop))
		self.Log("Afstand: %.2f m\nH1: %.4f m   H2: %.4f m   Hdiff: %.4f m" %(dist,h1,h2,hdiff))
		resfile.write("\n")
		resfile.close()
	
	def Log(self,text):
		self.parent.Log(text)

			
				
			
#---------Start up frame which inits the main frame--------------------#
class StartFrame(Core.StartFrame):
	def __init__(self,parent):
		Core.StartFrame.__init__(self,parent,PROGRAM,MTLinireader(),Core.MTLStatusData()) #initialize with these values
	def StartProgram(self):
		mainframe=MTLmain(None,self.resfile,self.instruments,self.laegter,self.data,self.gps,self.ini,self.statusdata,self.size)
		mainframe.Show()
		self.Close()
#---------------------- Core MTL-classes, state, maths, etc. handled here----------------------------------------------------#
def StandardZdistanceTranslator(val): # A validator for input in the format ddd.mmss - by using other validators, field 'types' can be changed flexibly
	sval=val.replace(",",".").strip()
	digits=""
	try:
		fval=float(sval)
	except:
		return False,0
	digits=sval.partition(".")[2]
	if len(digits)!=4 or int(digits[0:2])>59 or int(digits[2:])>59:
		return False,0
	S=int(sval[-2:]) #sekunder
	M=int(sval[-4:-2]) #minutter
	G=int(sval[0:-5])  #grader
	return True,np.pi*(G+M/60.0+S/3600.0)/180.0   #returns radians

#Base class which validates (and translates) input from z-distance fields
class MTLSetup(object):
	def __init__(self,rows,cols,zcol=0):
		self.Initialize(rows,cols) #Then we can call this method from outside....
		self.zcol=zcol #column nr. from where columns are z-distance fields (e.g. zcol=1: mrk,pos1,pos2 or  zcol=0: pos1,pos2)
		self.zformat_translator=StandardZdistanceTranslator #a function which translates input format to radians if format is OK,
	def Initialize(self,rows,cols):
		self.raw_data=np.zeros((rows,cols),dtype="<S20")
		self.real_data=np.zeros((rows,cols))
		self.index_errors=np.zeros((rows,)) #reflects only current "sats"
		self.validity_mask=np.zeros((rows,cols),dtype=np.bool) #reflects only current "sats"
	def SetTranslator(self,func):
		self.zformat_translator=func
	def Position1Validator(self,val):
		ok,val=self.zformat_translator(val)
		return ok and 0<=val<=np.pi
	def Position2Validator(self,val):
		ok,val=self.zformat_translator(val)
		return ok and np.pi<=val<=2*np.pi
	def SetValidity(self,row,col,validity):
		self.validity_mask[row,col]=validity
	def IsValid(self,row=None,col=None):
		return self.validity_mask[row,col].all()
	def SetData(self,row,col,val):
		self.raw_data[row,col]=val
		#translate#
		if col>=self.zcol and self.zformat_translator is not None:
			ok,val=self.zformat_translator(val)
		else:
			val=float(val)
		self.real_data[row,col]=val
	def GetIndexError(self,row): #for now always returns index error in seconds....
		ierr=((self.real_data[row,self.zcol]+self.real_data[row,self.zcol+1]-np.pi)*0.5)*180.0/np.pi*3600.0
		self.index_errors[row]=ierr
		return ierr
	def GetIndexErrors(self):
		return self.index_errors
	def GetData(self):
		return self.real_data
	def GetRawData(self):
		return self.raw_data
	def GetValidity(self):
		return self.validity_mask

class MTLTransferSetup(MTLSetup):
	def __init__(self,aim=[1,-1]):
		MTLSetup.__init__(self,2,2,0)
		self.aim=aim
		self.satser=[]
		self.hdiff=None
		self.dist=None
		self.restfejl=None
	def SetDistance(self,dist):
		self.dist=dist
	def AddSats(self):
		self.satser.append(self.raw_data,self.hdiff,self.restfejl)
		self.Initialize()
	
		
	
#THIS is the core class which handles basis setup state and math, the rest is GUI and event handling...... 
#The class has been prepared for the possibility of handling input in formats other than ddd.mmss, e.g. angles in gon or whatever.... Only need to set relevant translator and validator methods 

class MTLBasisSetup(MTLSetup):
	def __init__(self,aim=1):
		MTLSetup.__init__(self,4,3,1) #1. soejle=maerker, 2. soejle=1. kikkerstilling, 3, soejle=2. kikkertstilling
		self.aim=aim
		self.h1=None
		self.h2=None
		self.dist=None
		self.hdiff=None
	def MarkValidator(self,val): #validates 'marks' from input column 0
		try:
			val=float(val)
		except:
			return False
		return self.rod_min<=val<=self.rod_max
	def Calculate(self):
		index_err=(self.real_data[:,1]+self.real_data[:,2]-np.pi)*0.5
		z_corr=self.real_data[:,1]-index_err  #standard formel fra KES...
		M=self.real_data[:,0]  #only a 'view' not a copy!
		cot=1.0/np.tan(z_corr)
		s1=(M[0]-M[2])/(cot[0]-cot[2])
		s2=(M[1]-M[3])/(cot[1]-cot[3])
		dist=(s1+s2)*0.5
		#Instrumenthoejder (KES HOVMTL05.BAS) Minus sigte giver det rigtige fortegn!
		self.h1=-self.aim*(M[2]*cot[0] - M[0]*cot[2] )/(cot[0] - cot[2]) - 0.5 * (dist**2) / RADIUS   # Earth radius
		self.h2=-self.aim*(M[3]*cot[1] - M[1]*cot[3] )/(cot[1] - cot[3]) - 0.5 * (dist**2) / RADIUS
		self.hdiff=(self.h1+self.h2)*0.5
		self.dist=dist
		return self.dist,self.h1,self.h2,self.hdiff
	def GetResult(self):
		return self.dist,self.h1,self.h2,self.hdiff
	
#----------Initialisation classes, definition of rods etc.-----------------#
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

class MTLlaegte(object):
	def __init__(self,name=None,zeroshift=0,zone_low=0,zone_high=0,orientation=1):
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
		return "%s:  konstant: %.5f m" %(self.name,self.zeroshift)
	def GetName(self):
		return self.name

class MTLinireader(object): #add more error handling!
	def __init__(self):
		self.path=BASEDIR+"/MTL.ini"
	def Read(self):
		#default vaerdier#
		ini=Core.Ini()
		ini.fbtest=4.0 #frem-tilbage forkast
		ini.fbunit="ne"
		ini.maxdh_basis=0.001 #max. forskel mellem h1 og h2 ved basis
		ini.maxdh_mutual=0.005 #max. forskel mellem maalt dh ved gensidige sigter
		ini.maxdh_setups=0.005 #max. afv. mellem satser
		ini.maxsd_setups=0.01 #max. stdafv. ved flere satser
		ini.gpsport=-1 
		ini.gpsbaud=-1
		ini.mapdirs=[]
		ini.database=None
		ini.instport=5 
		ini.instbaud=9600
		instruments=[]
		laegter=[]
		f=open(self.path,"r")
		line=Funktioner.RemRem(f)
		while len(line)>0:
				i=line.find(":")
				if i!=-1:
					key=line[:i].strip()
				line=line[i+1:].split()
				if key=="gps" and len(line)>0:
					ini.gpsport=int(line[0])
					if len(line)>1:
						ini.gpsbaud=int(line[1])
				if key=="kortmappe" and len(line)>0:
					mapdir=line[0]
					if mapdir[-1] not in ["/","\\"]:
						mapdir+="/"
					ini.mapdirs.append(mapdir)
				if key=="database" and len(line)>0:
					ini.database=line[0]
				if key=="instrument" and len(line)>3:
					instrumentname=line[0]
					addconst=float(line[1])
					axisconst=float(line[2])
					instrumentport=int(line[3])
					instrumentbaud=int(line[4])
					instrumenttype=line[5]
					instruments.append(Instrument.MTLinstrument(instrumentname,addconst,axisconst,instrumentport,instrumentbaud,instrumenttype))
				if key=="ftforkast" and len(line)>0:
					ini.fbtest=float(line[0])
				if key=="fejlgraenser" and len(line)>0:
					ini.maxsl=float(line[0])
					if len(line)>1:
						ini.maxdh_basis=float(line[1])
					if len(line)>2:
						ini.maxdh_mutual=float(line[2])
					if len(line)>3:
						ini.maxdh_setups=float(line[3])
					if len(line)>4:
						ini.maxsd_setups=float(line[4])
					
				if key=="laegte" and len(line)>1:
					name=line[0]
					zeroshift=float(line[1])
					laegter.append(MTLlaegte(name,zeroshift))
				line=Funktioner.RemRem(f)
		f.close()
		if len(instruments)<2: 
			raise InstrumentError("Instrumenter ikke defineret i ini-filen!")
		if len(laegter)<1:
			raise LaegteError("Der er ikke defineret mindst een laegte i ini-filen")
		return ini,instruments,laegter
	
		

def main():
	App=wx.App()
	frame=StartFrame(None)
	frame.Show()
	App.MainLoop()
	sys.exit()

#--------------------And here we go!-----------------------------------------------#
if __name__=="__main__":
	main()