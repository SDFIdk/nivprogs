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
PROGRAM.name="MTL"
PROGRAM.version="beta 0.1"
PROGRAM.date="15-06-11"
PROGRAM.type="MTL"
PROGRAM.about="""
MTL program skrevet i Python. 
Bugs rettes til simlk@kms.dk
"""
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
		self.Log("Basis1")
		win=MakeBasis(self)
		win.InitializeMap()
	def OnBasis2(self,event):
		self.Log("Basis2")
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
	def __init__(self,parent,low=-33,high=33): #input graenser for indeksfejl advarsler...
		wx.Panel.__init__(self,parent)
		self.sizer=wx.GridSizer(5,4,5,5)
		headings=[u"M\u00E6rke","1. kikkertstilling","2. kikkertstilling","Indeksfejl ('')"]
		for text in headings:
			field=GUI.MyText(self,text,14,style=wx.ALIGN_CENTER)
			self.sizer.Add(field,1,wx.ALL,0)
		self.columns=[[],[],[],[]]
		for row in range(4):
			field1=GUI.MyNum(self,0,5,(160,-1),fontsize=16)
			field2=GUI.MyNum(self,0,181,(160,-1),fontsize=16)
			field3=GUI.MyNum(self,179,361,(160,-1),fontsize=16)
			field4=GUI.MyNum(self,low,high,(160,-1),fontsize=16,style=wx.TE_READONLY)
			self.columns[0].append(field1)
			self.columns[1].append(field2)
			self.columns[2].append(field3)
			self.columns[3].append(field4)
			self.sizer.Add(field1,1,wx.ALL,0)
			self.sizer.Add(field2,1,wx.ALL,0)
			self.sizer.Add(field3,1,wx.ALL,0)
			self.sizer.Add(field4,1,wx.ALL,0)
		self.SetSizerAndFit(self.sizer)
	def DisableCol(self,i):
		for field in self.columns[i]:
			field.Enable(0)
	def EnableCol(self,i):
		for field in self.columns[i]:
			field.Enable(1)

#Boks med felt til pkt. og drop-down box til laegtevalg
class MTLChoiceBox(GUI.StuffWithBox):
	def __init__(self,parent,laegter):
		GUI.StuffWithBox.__init__(self,parent,label="Valg",style="vertical")
		self.point=GUI.MyTextField(self,12,size=(150,-1))
		pointsizer=GUI.FieldWithLabel(self,self.point,"Punkt:",12)
		self.laegtebox=wx.Choice(self,choices=laegter,size=(150,-1))
		self.laegtebox.SetFont(GUI.DefaultFont(12))
		laegtesizer=GUI.FieldWithLabel(self,self.laegtebox,u"L\u00E6gte:",12)
		self.AddStuff(pointsizer)
		self.AddStuff(laegtesizer)
		self.FinishUp()
#------------------------- MakeBasis Frame defined here --------------------------------------------------------------#
class MakeBasis(GUI.FullScreenWindow):
	def __init__(self, parent):
		self.laegter=["a","b"]
		self.statusdata=parent.statusdata
		self.maerker=[]
		self.colOK=False
		self.rowOK=[0,0,0,0]
		self.mode="NA"
		self.fields=[]
		self.sigte=-2*int((self.statusdata.GetSetups())==0)+1
		self.Inst=self.statusdata.GetInstruments()[0]
		GUI.FullScreenWindow.__init__(self, parent)
		self.ini=self.parent.ini  #data passed in ini-file, error limits relevant here
		self.status=GUI.StatusBox2(self,["Instrument: ","Sigte: ","Punkt: ",u"H\u00F8jdeforskel: ","Mode: "])
		self.status.Update([self.Inst.GetName(),Funktioner.Bool2sigte(self.sigte),"NA"])
		punkter=[]
		self.valg=MTLChoiceBox(self,self.laegter)
		#self.valg.kortbutton.Bind(wx.EVT_BUTTON,self.OnKort)
		self.map=PanelMap(self,self.parent.data,self.ini.mapdirs) #setup the map - a panel in the center of the screen
		self.main=GUI.ButtonBox2(self,["AUTO(*)","MANUEL","ACCEPTER","AFBRYD"],label="Styring",colsize=2)
		self.maal=OverfPanel(self,-20,20)
		self.regnebox=GUI.StatusBox2(self,["Afstand: ",u"H\u00F8jde (m1+m3): ",u"H\u00F8jde (m2+m4): ","Difference: "],label="Tjek",fontsize=12)
		self.regnebox.Update([])
		self.parent.Log("Sigte: %s" %(Funktioner.Bool2sigte(self.sigte)))
		#EVENT HANDLING SETUP#
		self.main.button[3].Bind(wx.EVT_BUTTON,self.OnCancel)
		#self.maal.Enable(0)
		#self.main.Enable(0)
		#self.valg.gobutton.Bind(wx.EVT_BUTTON,self.OnGo)
		self.CreateRow()
		#sizer=wx.BoxSizer(wx.HORIZONTAL)
		self.AddItem(self.status,0)
		self.AddItem(self.map,0)
		sizer_right=wx.BoxSizer(wx.VERTICAL)
		sizer_right.Add(self.valg,1,wx.ALL,5)
		sizer_right.Add(self.main,1,wx.ALL,5)
		self.AddItem(sizer_right,0)
		self.AddRow(2,wx.CENTER|wx.ALL)
		#self.CreateRow()
		#self.AddItem(self.main,1)
		#self.AddRow(1,wx.LEFT|wx.ALL)
		#self.AddItem(sizer)
		self.CreateRow()
		#sizer=wx.BoxSizer(wx.HORIZONTAL)
		self.AddItem(self.maal,1)
		self.AddItem(self.regnebox,1,wx.RIGHT)
		self.AddRow(1)
		#self.AddItem(sizer)
		
		#self.main.knap3.Bind(wx.EVT_BUTTON,self.Omvalg)
		#self.main.knap2.Bind(wx.EVT_BUTTON,self.Manuel)
		#self.main.knap1.Bind(wx.EVT_BUTTON,self.OnAuto)
		i=1
		#for field in self.maal.col1[1:]:
		#	field.Bind(wx.EVT_TEXT,self.Validate)
		#	field.grandfather=self
		#	field.auto=False
		#	field.overwrite=True
		#	field.sound=True
		#	#Navigation
		#	field.nexttab=self.maal.col2[i]
		#	if i==1:
		#		pt=4
		#	else:
		#		pt=i-1
		#	field.prevtab=self.maal.col3[pt]
		#	if i<4:	
		#		field.next=self.maal.col1[i+1]
		#	else:
		#		field.next=self.maal.col2[1]
		#	i+=1
		#i=1
		#for field in self.maal.col2[1:]:
		#	field.sound=True
		#	field.Bind(wx.EVT_TEXT,self.Validate)
		#	field.grandfather=self  #For auto action
		#	field.cid=i-1  #Til Auto fra feltet og frem
		#	field.type="Z" #skal vaere decimalgrader
		#	#Navigation
		#	field.nexttab=self.maal.col3[i]
		#	field.prevtab=self.maal.col1[i]
		#	if i!=4: 
		#		field.next=self.maal.col2[i+1]
		#		field.next=self.maal.col3[4]
		#	i+=1
		#i=1		
		#for field in self.maal.col3[1:]:
		#	field.sound=True
		#	field.Bind(wx.EVT_TEXT,self.Validate)
		#	field.grandfather=self  #For auto action
		#	field.cid=8-i #omvendt raekkefoelge i 2.kikkerstilling
		# 	field.prevtab=self.maal.col2[i]
		#	nt=(i % 4)+1
		#	field.nexttab=self.maal.col1[nt]
		#	if i!=1: 
		#		field.next=self.maal.col3[i-1]
		#	else:
		#		field.next=self.main
		#	i+=1
		#self.maal.col3[1].Bind(wx.EVT_TEXT_ENTER,self.SidsteRetur)  #NB-ogsaa navigation!!!!
		#self.main.under.knap2.Bind(wx.EVT_BUTTON,self.Afbryd) #afbryder-knap
		#self.main.under.knap1.Bind(wx.EVT_BUTTON,self.CloseOK)
		#self.Bind(EVT_AUTO,self.OnEvtAuto)
		self.ShowMe()
		self.valg.SetFocus()
	def InitializeMap(self): #should be called every time the frame is shown to go to gps-mode
		if self.parent.gps.isAlive():
			self.parent.map.DetachGPS()
			self.map.AttachGPS(self.parent.gps)
			self.map.SetGPSMode()
			self.map.UpdatePoints() #uses same data as parent, so this influences the parents map as well.
		else:
			self.map.SetPanMode()
		self.map.SetMap()
	def OnCancel(self,event):
		self.Close()
	def SidsteRetur(self,event):
		self.InitState()
	def OnKort(self,event):
		GPS=self.parent.GPS
		GPS.window.Show()
		GPS.window.Maximize(0)
	def OnClick(self,event):
		GPS=self.parent.GPS 
		if GPS.window.selected!=-1:
			j=GPS.window.selected
			self.valg.punkt.SetValue("%s" %GPS.window.pnavne[j])
			
	def Manuel(self,event):
		if self.mode!="MANUEL":
			self.ManuelMode()
		else:
			self.InitState()
			
	def OnEvtAuto(self,event):
		val=event.value
		if self.mode=="AUTO" or self.mode=="SINGLE AUTO":
			if val[0]=="E":
				FejlBoks(self,str(val[1]))
				self.ManuelMode()
				return
			elif val[0]!="<":
				FejlBoks(self,u"Forkert input!\nForventede en vinkelm\u00E5ling.")
				self.ManuelMode()
				return
			else:
				val=val[1]
			if self.mode=="AUTO":
				self.fields[0].SetValue(str(val))
				self.fields[0].Enable()
				self.fields=self.fields[1:]
				if len(self.fields)==0:
					self.Release()
			if self.mode=="SINGLE AUTO":
				self.fields[0].SetValue(str(val))
				self.fields[0].Enable()
				#self.fields[0].SetFocus()
				self.ManuelMode()
	def Single_Auto(self,field):
		if not self.thread.isAlive():  #Kan ogsaa tjekke for en auto-thread om noedvendigt! 
			field.Enable(0)
			self.mode="SINGLE AUTO"
			self.fields=[field]
			self.parent.Log("'Auto Mode' startes i enkelt felt.")
			self.Auto()
		else:
			WaitForThread(self)
	def Call_Auto(self,cid):
		if self.mode=="MANUEL":
			self.fields=self.maal.col2[1:]
			for i in range(0,4):  #da reverse() modificerer listen!
				self.fields.append(self.maal.col3[4-i])
			self.fields=self.fields[cid:]
			for field in self.fields:
				#field.Clear() #slet ikke felter!
				field.Enable(0)
			self.mode="AUTO"
			self.Auto()
		else:
			self.ManuelMode()
	def Call_Cancel(self):
		self.InitState()
	def OnAuto(self,event):
		if self.mode!="AUTO" and self.mode!="SINGLE AUTO":
			if self.thread!=None and self.thread.isAlive():
				WaitForThread2(self)
				self.thread.kill()
				return 
			self.fields=self.maal.col2[1:]
			for i in range(0,4):  #da reverse() modificerer listen!
				self.fields.append(self.maal.col3[4-i])
			self.mode="AUTO"
			for field in self.fields:
				#field.Clear()  #slet ikke felter
				field.Enable(0)
			self.Auto()
		else:
			self.KillAuto()
	def AfterAuto(self):
		self.parent.Log("Afslutter 'Auto Mode'")
		if self.OK:
			self.InitState()
		else:
			self.ManuelMode()
	def Auto(self):
		if self.mode=="AUTO":
			self.status.Update(field=4,text=self.mode,colour="red")
		else:
			self.status.Update(field=4,text=self.mode,colour="yellow")
		self.thread=AutoThread(self,len(self.fields),1,self.Inst.port,self.parent) 
		self.thread.setName(self.Inst.navn)
		self.thread.start()
	
	def Release(self):
		sound = wx.Sound(mmdir+'alert.wav')
		sound.Play(wx.SOUND_SYNC)
		self.parent.Log(u"M\u00E5linger fuldf\u00F8rt")
		self.AfterAuto()
	
	def KillAuto(self):
		self.parent.Log("Afbryder 'Auto Mode'")
		EnableCol(self.maal.col2)
		EnableCol(self.maal.col3)
		self.maal.Enable()
		self.thread.kill()
		self.InitState()
	def ManuelMode(self):
		#self.main.knap1.SetValue(0)
		if self.thread!=None and self.thread.isAlive():
			self.thread.kill()
		self.mode="MANUEL"  #manuel
		self.Log("Skifter til 'Manuel Mode'.")
		self.status.Update(field=4,text=self.mode,colour="green")
		EnableCol(self.maal.col2)
		EnableCol(self.maal.col3)
		self.maal.Enable()   #Overrides individual field-enables!!!!!!!
		if not self.OK:
			for col in range(0,3):
				for field in self.maal.cols[col][1:]:
					if not field.ok:
						field.SetFocus()
						return
				
		else:
			self.maal.col2[1].SetFocus()
	def Validate(self,event):
		event.GetEventObject().Validate() #valider kun kalderen!
		str=self.maal.col1[1].GetValue()  #hahaha
		if str.strip()=="monty":
			self.DoSketch()
		if str.find("test")!=-1:
			self.TestMode()
			return
		self.colOK=True
		i=1
		for field in self.maal.col1[1:]:
			#self.colOK=self.colOK&field.Validate()
			self.colOK=self.colOK&field.ok
			if field.ok and i<4: #kund de foerste tre maerker
				maerke=float(field.GetMyValue())
				field.next.SetBounds(0,maerke-0.0001) #maerker skal blive mindre
				field.next.Validate()
			i+=1
		self.main.knap1.Enable(self.colOK)   
		for row in range(1,5):
			s=True
			for col in range(0,3):
				#s=s&self.maal.cols[col][row].Validate()
				s=s&self.maal.cols[col][row].ok
			self.rowOK[row-1]=s	
		event.Skip()
		self.Udregn()
		
	def TestMode(self):
		for i in range(1,5):
			self.maal.col1[i].SetValue(str(3-i/2))
			self.maal.col2[i].SetValue(str(88.1111+i))
			self.maal.col3[i].SetValue(str(271.4949-i))
	def DoSketch(self):
		msg=Sketch.sketch
		self.Log("Doing sketch....!")
		dlg=MyLongMessageDialog(self,"You asked for it!",msg)
		dlg.ShowModal()
		dlg.Destroy()
	def Udregn(self):
		global Radius
		R=Radius
		self.z1=[0,0,0,0]
		self.z2=[0,0,0,0]
		self.z1gem=[0,0,0,0]
		self.z2gem=[0,0,0,0]
		self.ind=[0,0,0,0]
		self.maerker=[0,0,0,0]
		for row in range(0,4):
			if self.rowOK[row]:  
				self.maerker[row]=float(self.maal.col1[row+1].GetMyValue()) #foerste raekke er toptekst
				self.z1[row]=Dec2Grad(self.maal.col2[row+1].GetMyValue()) #Til grader
				self.z2[row]=Dec2Grad(self.maal.col3[row+1].GetMyValue()) #Til grader
				self.z1gem[row]=self.maal.col2[row+1].GetMyValue() #husk at gemme de oprindelige maalinger!
				self.z2gem[row]=self.maal.col3[row+1].GetMyValue()
				self.ind[row]=(self.z2[row]+self.z1[row]-360)/2 #KES-se HOVMTL05.BAS
				self.maal.col4[row+1].SetValue("%.0f" %(self.ind[row]*60*60)) #I hele sekunder (Palle)
				self.maal.col4[row+1].Validate()
		if sum(self.rowOK)==len(self.rowOK):
			#Nu regnes der saa
			self.OK=1
			#Korrigerede zenitdistancer
			z1=self.z1[0]-self.ind[0]  #Bemaerk Python indeksering!
			z2=self.z1[1]-self.ind[1]
			z3=self.z1[2]-self.ind[2]
			z4=self.z1[3]-self.ind[3]
			#COTANGENS:
			cot1=cot(radians(z1))
			cot2=cot(radians(z2))
			cot3=cot(radians(z3))
			cot4=cot(radians(z4))
			M1=self.maerker[0]
			M2=self.maerker[1]
			M3=self.maerker[2]
			M4=self.maerker[3]
			#Sigtelaengder
			try:
				self.s1=(M1-M3)/(cot1-cot3)
				self.s2=(M2-M4)/(cot2-cot4)
				self.dist=(self.s1+self.s2)*0.5
				#Instrumenthoejder (KES HOVMTL05.BAS) Minus sigte giver det rigtige fortegn!
				self.h1=-self.sigte*(M3*cot1 - M1*cot3 )/(cot1 - cot3) - 0.5 * (self.dist**2) / R 
				self.h2=-self.sigte*(M4*cot2 - M2*cot4 )/(cot2 - cot4) - 0.5 * (self.dist**2) / R
				self.hdiff=(self.h1+self.h2)*0.5
			except ZeroDivisionError:
				self.OK=0
				self.s1=0
				self.s2=0
				self.dist=0
				self.h1=0
				self.h2=0
				self.hdiff=0
				dlg=MyMessageDialog(self,"Fejl!","Division med nul!\nTjek zenitdistancer.")
				dlg.ShowModal()
				dlg.Destroy()
			
			self.Update()
		else:
			self.OK=0
			self.Update()
			
				
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
		
	def Afbryd(self,event):
		OK=True
		if self.thread!=None and self.thread.isAlive():
				self.thread.kill()
		if self.colOK or sum(self.rowOK)>0:
			dlg=OKdialog(self,"Afbrydelse!",u"Er du sikker p\u00E5, at du vil afbryde punktoverf\u00F8rslen?")
			dlg.ShowModal()
			OK=dlg.OK
			dlg.Destroy()
		if OK:
			self.Log(u"Punktoverf\u00F8rsel afbrudt kl. %s" %Nu())
			self.parent.Update()
			self.Close()
		else:
			self.InitState()
	def Omvalg(self,event):
		self.mode="NA"
		if self.thread!=None and self.thread.isAlive():
			self.thread.kill()
		self.status.Update(field=4,text=self.mode,colour=bgcolor)
		self.main.Enable(0)
		self.maal.Enable(0)
		self.valg.Enable(1)
		self.valg.SetFocus()
	def OnGo(self,event):
		self.punkt=self.valg.punkt.GetValue().replace(" ","") #slet spaces i punktnavn
		OK=True
		if OversaetPunkt(self.punkt)==-1:
			sound = wx.Sound(mmdir+'alert.wav')
			sound.Play(wx.SOUND_SYNC)
			dlg=JaNejDialog(self,u"Bem\u00E6rk!",u"Punktnummeret %s er tilsyneladende ukurant.\nVil du forts\u00E6tte alligevel?" %self.punkt)
			dlg.ShowModal()
			OK=dlg.OK
			dlg.Destroy()
			if not OK:
				self.valg.punkt.SetBackgroundColour("red")
				self.valg.punkt.SetFocus()
				self.valg.punkt.Refresh()
		if OK:
			self.valg.Enable(0)
			self.main.Enable(1)
			self.valg.punkt.SetBackgroundColour("green")
			self.valg.punkt.Refresh()
			self.punktnr=self.valg.punkt.GetSelection()
			self.laegtenr=self.valg.laegte.GetSelection()
			self.laegte=self.laegter[self.laegtenr]
			self.Update()
			self.ManuelMode()
			#self.main.SetFocus()
			
	def InitState(self):
		self.main.SetFocus()
		self.maal.Enable(0)
		self.mode="NA"
		self.status.Update(field=4,text=self.mode,colour=bgcolor)
		
	
	def Update(self):
		self.status.Update([self.Inst.navn,Bool2sigte(self.sigte),self.punkt,"%.4f m" %self.hdiff])
		self.regnebox.Update(["%.4f m" %self.dist, "%.4f m" %self.h1, "%.4f m" %self.h2, "%.1f mm" %(1000*(self.h1-self.h2))])
		self.border.Layout()
		self.main.under.knap1.Enable(self.OK)
		self.main.knap1.Enable(self.colOK)
		self.Refresh()
	def EnableCol(self,col):
		for field in col:
			field.Enable()
	def DisableCol(self,col):
		for field in col:
			field.Enable(0)
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
		self.fbtest=4.0 #frem-tilbage forkast
		self.fbunit="ne"
		self.maxdd=2.0 #max. afst. forsk.
		self.maxsl=50 #max. sigtel.
		self.maxsd=0.00012 #max inst. sd
		self.maxhd=0.00050 #max forskel mellem sigter i praes.-mode
		self.gpsport=-1 
		self.gpsbaud=-1
		self.mapdirs=[]
		self.database=None
		self.instport=5 
		self.instbaud=9600
		self.instruments=[]
		self.laegter=[]
		f=open(self.path,"r")
		line=Funktioner.RemRem(f)
		while len(line)>0:
				i=line.find(":")
				if i!=-1:
					key=line[:i].strip()
				line=line[i+1:].split()
				if key=="gps" and len(line)>0:
					self.gpsport=int(line[0])
					if len(line)>1:
						self.gpsbaud=int(line[1])
				if key=="kortmappe" and len(line)>0:
					mapdir=line[0]
					if mapdir[-1] not in ["/","\\"]:
						mapdir+="/"
					self.mapdirs.append(mapdir)
				if key=="database" and len(line)>0:
					self.database=line[0]
				if key=="instrument" and len(line)>3:
					instrumentname=line[0]
					addconst=float(line[1])
					axisconst=float(line[2])
					instrumentport=int(line[3])
					instrumentbaud=int(line[4])
					instrumenttype=line[5]
					self.instruments.append(Instrument.MTLinstrument(instrumentname,addconst,axisconst,instrumentport,instrumentbaud,instrumenttype))
				if key=="ftforkast" and len(line)>0:
					self.fbtest=float(line[0])
				if key=="fejlgraenser" and len(line)>0:
					self.maxsl=float(line[0])
					if len(line)>1:
						self.maxdd=float(line[1])
					if len(line)>2:
						self.maxsd=float(line[2])
					if len(line)>3:
						self.maxhd=float(line[3])
				if key=="laegte" and len(line)>1:
					name=line[0]
					zeroshift=float(line[1])
					self.laegter.append(MTLlaegte(name,zeroshift))
				line=Funktioner.RemRem(f)
		f.close()
		Ini=Core.Ini()
		Ini.gpsbaud=self.gpsbaud
		Ini.gpsport=self.gpsport
		Ini.mapdirs=self.mapdirs
		Ini.database=self.database
		Ini.fbtest=self.fbtest
		Ini.fbunit=self.fbunit
		if len(self.instruments)<2: 
			raise InstrumentError("Instrumenter ikke defineret i ini-filen!")
		if len(self.laegter)<1:
			raise LaegteError("Der er ikke defineret mindst een laegte i ini-filen")
		return Ini,self.instruments,self.laegter
	
		

def main():
	App=wx.App()
	#frame=MLBase(None,"Test",ini,StatusData(),ProgramType())
	frame=StartFrame(None)
	frame.Show()
	App.MainLoop()
	sys.exit()

#--------------------And here we go!-----------------------------------------------#
if __name__=="__main__":
	main()