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
PROGRAM.date="08-08-11"
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
		state=self.statusdata.GetState()
		instrumentstate=self.statusdata.GetInstrumentState()
		#Enable buttons according to the current state defined in statusdata#
		for i in range(3):
			self.buttonboxes[i].Enable(state==i)
		if state==0:
			self.buttonboxes[0].button[2].Enable(instrumentstate>=0)
	def OnBasis1(self,event):
		win=MakeBasis(self,0)
		win.InitializeMap()
	def OnBasis2(self,event):
		win=MakeBasis(self,1)
		win.InitializeMap()
	def OnTransferHeight(self,event):
		self.Log("Transfer height")
	def OnInstrument2Instrument(self,event):
		self.Log("I til I")
	def OnBasisEnd(self,event):
		self.Log("Basis slut")
		
#-------------------------Instrument2Instrument Frame Defined Here----------------------------------------------#
#-------------------------Various Wx Windows Specialized for MTL -------------------------------------------------#

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
class MTLChoiceBox(GUI.StuffWithBox): #TODO: Fix browsing on enter hit in rodbox......
	def __init__(self,parent,laegter):
		GUI.StuffWithBox.__init__(self,parent,label="Valg",style="vertical")
		self.point=GUI.MyTextField(self,12,size=(150,-1))
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
	
#------------------------- MakeBasis Frame defined here --------------------------------------------------------------#
class MakeBasis(GUI.FullScreenWindow):
	def __init__(self, parent,instrument_number=0):
		self.laegter=parent.laegter
		self.instrument_number=instrument_number #the height status after succesful measurements should be this number.... Instrument that 'carries' height.
		self.statusdata=parent.statusdata
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
		self.valg.SetPoint("%s"%self.statusdata.GetEnd())
		self.map=PanelMap(self,self.parent.data,self.ini.mapdirs) #setup the map - a panel in the center of the screen
		self.map.RegisterPointFunction(self.PointNameHandler) #handles left-clicks on points in map - sets name in point box
		self.main=GUI.ButtonBox2(self,["AUTO(*)","MANUEL","ACCEPTER","AFBRYD"],label="Styring",colsize=2)
		self.maal=OverfPanel(self,self.setup,-20,20)
		self.valg.next_item=self.maal #controls that after 'enter' in rod-selection, we should go here.... 
		self.resultbox=GUI.StatusBox2(self,["Afstand: ",u"H\u00F8jde:"],label="Resultat",fontsize=12,colsize=2)
		self.controlbox=GUI.StatusBox2(self,[u"H\u00F8jde (m1+m3): ",u"H\u00F8jde (m2+m4): ","Difference: "],fontsize=12,label="Kontrol")
		self.resultbox.Update([])
		self.controlbox.Update([])
		#EVENT HANDLING SETUP#
		self.main.button[0].Bind(wx.EVT_BUTTON,self.OnSetAutoMode)
		self.main.button[1].Bind(wx.EVT_BUTTON,self.OnSetManualMode)
		self.main.button[2].Bind(wx.EVT_BUTTON,self.OnAccept)
		self.main.button[3].Bind(wx.EVT_BUTTON,self.OnCancel)
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
		self.Log("Sigte: %s" %(Funktioner.Bool2sigte(self.sigte)))
		#TEST INSTRUMENT#
		if not self.instrument.TestPort():
			GUI.ErrorBox(self,u"Kunne ikke \u00E5bne instrumentets com-port...")
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
		self.Log("Accept")
		mask=self.maal.GetValidity()
		if not mask.all():
			GUI.ErrorBox(self,u"Udf\u00F8r alle m\u00E5linger f\u00F8rst")
		else:
			self.CloseOK()
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
			else:
				GUI.ErrorBox(self,u"Skift til manuel mode f\u00F8rst")
		else:
			GUI.ErrorBox(self,u"Indtast m\u00E6rker f\u00F8rst")
	def SetManualMode(self):
		self.mode=0
		for field in self.auto_fields:
			field.Enable()
		self.UpdateStatus()
	def UpdateStatus(self):
		self.status.Update([self.instrument.GetName(),Funktioner.Bool2sigte(self.sigte),self.modenames[self.mode]],colours={2:self.modecolors[self.mode]})
	def UpdateHeightStatus(self):
		s,h1,h2,hdiff=self.setup.Calculate()
		dh=abs(h1-h2)
		col=Funktioner.State2Col(self.ini.maxdh_basis>=dh)
		self.controlbox.Update(["%.4f m" %h1,"%.4f m" %h2,"%.1f mm" %((h1-h2)*1000.0)],colours={2:col})
		self.resultbox.Update(["%.4f m" %s,"%.4f m" %hdiff])
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
		pass
	def OnInstLog(self,event):
		pass
	def CloseOK(self,event):
		global T0
		global Nopst
		global totaldist
		global nopst
		global dist
		global hdiff
		global fullresfilnavn
		global Temp
		global Ttimes
		global overfhdiff
		global sidsteInst
		global overfdist
		global Nhdiffs
		global Start
		global Slut
		GPS=self.parent.GPS
		GPS.window.Show(0)
		middeltid=(MyTime()+self.start)/2-T0
		self.exitstate=1
		if self.sigte==1:
			self.h=self.hdiff+hdiff
			nopst+=1
			dist+=self.dist
			hoved=LavHoved(self,self.h,dist,nopst,Start,self.punkt,Dato2(),Nu())
			hoved.ShowModal()
			if hoved.exitstate:
				T=float(hoved.edit.numfield[0].GetMyValue())
				start=hoved.edit.field[0].GetValue().strip().replace(" ","")  #slet spaces...
				slut=hoved.edit.field[1].GetValue().strip().replace(" ","")
				self.punkt=slut
				Slut=slut
				Start=start
				self.SkrivMaaling()
				dato=hoved.edit.field[2].GetValue().strip().replace(" ","")
				tid=hoved.edit.field[3].GetValue().strip().replace(" ","")
				jside=hoved.edit.field[4].GetValue().replace(",",".").strip().replace(" ","")
				Temp.append(T)
				Ttimes.append(MyTime()-T0)
				resfil=open(fullresfilnavn,"a")
				doprint=True #som default print
				if not hoved.ekstra.IsEmpty():
					ekstra=hoved.ekstra.GetValue()
					if ekstra.find("dontprint")!=-1: #paanaer hvis vi beder om ikke at goere det!
						doprint=False
					else:
						for line in ekstra.splitlines():
							line=Internationale(line)
							resfil.write(line+"\n") #ikke kommentar-tegn foran mere....
				resfil.write("# %s %s %s %s %.2f %.5f %s %.1f %i\n\n"%(start,slut,dato,tid,dist,self.h,jside,T,nopst))
				resfil.close()
				self.Log(SL)
				self.Log("Hoved:\nFra %s til %s" %(start,slut))
				self.Log("Journalside: %s" %jside)
				self.Log("Hdiff: %.4f m Afstand: %.2f m Opstillinger: %d" %(self.h,dist,nopst)) 
				#Reset og opdater
				Nhdiffs+=1
				Nopst+=nopst
				totaldist+=dist
				hdiff=0
				nopst=0  
				dist=0
				Inst1.hstate=0
				Inst2.hstate=0
				overfhdiff=-self.hdiff
				overfdist=self.dist
				self.Inst.fast=True
				sidsteInst=self.Inst
				hoved.Destroy()
				if doprint: #har vi bedt om ikke at printe??
					try:
						FileOps.Jside(fullresfilnavn)
					except Exception, msg:
						print str(msg)
						FejlBoks(self,"Fejl under udprintning af journalside!\nFortvivl ikke, denne kan gendannes fra datafilen.")
				self.Inst.ind.append(map(lambda x:60*60*x,self.ind)) #I sekunder
				self.Inst.times.append(middeltid)
				self.parent.Update()
				self.Close()
			else:
				self.exitstate=0
				hoved.Destroy()
				nopst-=1
				dist-=self.dist
				
				
		if self.sigte==-1:
			Start=self.punkt
			self.SkrivMaaling()
			self.Inst.hstate=1
			hdiff=self.hdiff
			nopst=1
			dist=self.dist
			self.Inst.ind.append(map(lambda x:60*60*x,self.ind)) #I sekunder
			self.Inst.times.append(middeltid)
			self.parent.Update()
			self.Close()
	def SkrivMaaling(self):
		global fullresfilnavn
		global Start
		global Slut
		global hdiff
		global dist
		global nopst
		global Inst1
		global Inst2
		resfil=open(fullresfilnavn,"a")
		space=max(len(Inst1.navn),len(Inst2.navn))+4
		resfil.write("%*s %*s %*s %*s %s\n" %(-13,"Basis",-space,"Instrument",-8,"Laegte",-10,"Afstand","Hoejdeforskel"))
		self.Log("Punkt: %s" %self.punkt)
		self.Log(u"L\u00E6gte: %s\n" %self.laegte)
		resfil.write("%*s %*s %*s %*s %.4fm\n" %(-13,self.punkt,-space,self.Inst.navn,-8,str(self.laegtenr+1),-10,"%.2fm"%self.dist,self.hdiff))
		#tup=Prepad(self.maerker,-8)
		tup=[]
		for i in range(0,4):
			tup.append("%.2fm"%self.maerker[i])
		tup=Prepad(tup,-8)
		resfil.write("%*s %*s %*s %*s\n" %tup)
		self.Log("%*s %*s %*s %*s" %tup)
		tup=Prepad(self.z1gem,-8) #saetter bare -8 foran hvert element
		resfil.write("%*s %*s %*s %*s "%tup)
		resfil.write("%.4fm\n" %(self.h1))
		self.Log("%*s %*s %*s %*s" %tup)
		resfil.write("%s %s %s %s %.4fm\n" %(tuple(self.z2gem+[self.h2])))
		if self.sigte==-1:
			resfil.write("* B1 %s %.3f %.6f\n" %(Start,self.dist,self.hdiff))
		else:
			resfil.write("* B2 %s %s %.3f %.6f %i %.3f %.6f\n" %(Start,self.Inst.navn,dist-self.dist,hdiff,nopst-1,self.dist,self.hdiff))
		if self.parent.GPS.alive:
			x,y,dop=self.parent.GPS.GetPos()
			if dop<10:
				resfil.write("GPS: %.1f %.1f %.1f\n" %(y,x,dop))
		self.Log("%s %s %s %s\n" %(tuple(self.z2gem)))
		self.Log("Afstand: %.2f m\nH1: %.4f m   H2: %.4f m   Hdiff: %.4f m" %(self.dist,self.h1,self.h2,self.hdiff))
		resfil.write("\n")
		resfil.close()
	
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

#THIS is the core class which handles basis setup state and math, the rest is GUI and event handling...... 
#The class has been prepared for the possibility of handling input in formats other than ddd.mmss, e.g. angles in gon or whatever.... Only need to set relevant translator and validator methods 

class MTLBasisSetup(object):
	def __init__(self,aim=1):
		#1. soejle=maerker, 2. soejle=1. kikkerstilling, 3, soejle=2. kikkertstilling
		self.raw_data=np.zeros((4,3),dtype="<S20") #raw string input from input fields.... 
		self.real_data=np.zeros((4,3)) #real numbers - angles stored in radians,...
		self.index_errors=np.zeros((4,)) #array which stores index errors - NEEDED??
		self.validity_mask=np.zeros((4,3),dtype=np.bool) #mask to mark validity of data....
		self.zformat_translator=StandardZdistanceTranslator #a function which translates input format to radians if format is OK,
		self.aim=aim
	def SetTranslator(self,func):
		self.zformat_translator=func
	def Position1Validator(self,val):
		ok,val=self.zformat_translator(val)
		return ok and 0<=val<=np.pi
	def Position2Validator(self,val):
		ok,val=self.zformat_translator(val)
		return ok and np.pi<=val<=2*np.pi
	def MarkValidator(self,val): #validates 'marks' from input column 0
		try:
			val=float(val)
		except:
			return False
		return self.rod_min<=val<=self.rod_max
	def SetValidity(self,row,col,validity):
		self.validity_mask[row,col]=validity
	def IsValid(self,row=None,col=None):
		return self.validity_mask[row,col].all()
	def SetData(self,row,col,val):
		self.raw_data[row,col]=val
		#translate#
		if col>0 and self.zformat_translator is not None:
			ok,val=self.zformat_translator(val)
		else:
			val=float(val)
		self.real_data[row,col]=val
	def GetIndexError(self,row):
		return ((self.real_data[row,1]+self.real_data[row,2]-np.pi)*0.5)*180.0/np.pi*3600.0
	def Calculate(self):
		index_err=(self.real_data[:,1]+self.real_data[:,2]-np.pi)*0.5
		z_corr=self.real_data[:,1]-index_err  #standard formel fra KES...
		M=self.real_data[:,0]  #only a 'view' not a copy!
		cot=1.0/np.tan(z_corr)
		s1=(M[0]-M[2])/(cot[0]-cot[2])
		s2=(M[1]-M[3])/(cot[1]-cot[3])
		dist=(s1+s2)*0.5
		#Instrumenthoejder (KES HOVMTL05.BAS) Minus sigte giver det rigtige fortegn!
		h1=-self.aim*(M[2]*cot[0] - M[0]*cot[2] )/(cot[0] - cot[2]) - 0.5 * (dist**2) / RADIUS   # Earth radius
		h2=-self.aim*(M[3]*cot[1] - M[1]*cot[3] )/(cot[1] - cot[3]) - 0.5 * (dist**2) / RADIUS
		hdiff=(h1+h2)*0.5
		return dist,h1,h2,hdiff
	def GetData(self):
		return self.real_data
	def GetValidity(self):
		return self.validity_mask
	
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