import wx
import Core #defines classes that are common to, or very similar in, MGL and MTL
import MyModules.GUIclasses2 as GUI #basic GUI-stuff
from MyModules.MLmap import PanelMap
from MyModules.ExtractKMS import Numformat2Pointname,Pointname2Numformat
import Instrument 
import numpy as np
import MTLsetup # all MTL math stuff handled here.... This is the real thing!
import Funktioner
import FileOps
import sys,os
import Sketch #just kidding!
BASEDIR=Core.BASEDIR #the directory, where the program is located
PROGRAM=Core.ProgramType()
PROGRAM.name="MTL"
PROGRAM.version="beta 0.23"
PROGRAM.date="2012-01-13"
PROGRAM.type="MTL" #vigtigt signal til diverse faellesfunktioner for MGL og MTL....
PROGRAM.about="""
MTL program skrevet i Python. 
Bugs rettes til simlk@kms.dk
"""
DEBUG="debug" in sys.argv
#TODO: Make sure that num ouput to file has "," replaced by ".". ++ DONE
#---------Various Global Vars--------------#
MAX_ROD=30.0      #Maximum rod size accepted in input fields
MIN_DECREMENT=0.0005 # A bit overdone perhaps - a var which holds the minimal allowed decrement of marks (which should decrease - measurements from top to bottom).....
MAX_LENGTH_MUTUAL=10000 # Value which determines the max input for the distance fields....
SL="*"*50
FONTSIZE=12  
#---------Main Windows defined here--------------------------------------#
class MTLmain(Core.MLBase):
	""" Main frame of MTL-prog. Derived from Core.MLBase """
	def __init__(self,parent,resfil,instruments,laegter,data,gps,ini,statusdata,size):
		Core.MLBase.__init__(self,parent,resfil,data,gps,ini,statusdata,PROGRAM,size)
		self.instruments=instruments
		statusdata.SetInstruments(instruments) #also handy to keep pointers to instruments in statusdata and handle "state" logic there!
		self.laegter=laegter
		#Define action buttons at bottom of window
		#The order that buttons appear in should reflect the ordering of self.instruments (and also in statusdata) 
		basisbuttons=[instrument.name for instrument in instruments]
		lower_panel=wx.Panel(self)
		basisbox_start=GUI.ButtonBox(lower_panel,basisbuttons+[u"Overf\u00F8r h\u00F8jde"],fontsize=self.size,label="Basis-start",style="vertical")
		middlebox=GUI.ButtonBox(lower_panel,[u"G\u00E5 til m\u00E5ling"],fontsize=self.size,label="Inst>>Inst",style="vertical")
		basisbox_slut=GUI.ButtonBox(lower_panel,[u"G\u00E5 til m\u00E5ling"],fontsize=self.size,label="Basis-slut",style="vertical")
		self.buttonboxes=[basisbox_start,middlebox,basisbox_slut]
		#SET UP EXTRA MENU ITEMS#
		self.funkmenu.AppendSeparator()
		DeleteLast=self.funkmenu.Append(wx.ID_ANY,u"Slet seneste m\u00E5ling",u"Sletter seneste opstilling i datafilen!")
		DeleteToLastHead=self.funkmenu.Append(wx.ID_ANY,u"Slet til seneste hoved","Sletter til seneste hoved i datafilen!")
		EditHead=self.funkmenu.Append(wx.ID_ANY,u"Rediger et hoved","Rediger et hoved i datafilen.")
		self.anamenu.AppendSeparator()
		FileAnalysis=self.anamenu.Append(wx.ID_ANY,u"Analyse plot","Plot analyse af data i resultatfil.")
		#EVENT HANDLING SETUP#
		basisbox_start.button[0].Bind(wx.EVT_BUTTON,self.OnBasis1)
		basisbox_start.button[1].Bind(wx.EVT_BUTTON,self.OnBasis2)
		basisbox_start.button[2].Bind(wx.EVT_BUTTON,self.OnTransferHeight)
		middlebox.button[0].Bind(wx.EVT_BUTTON,self.OnInstrument2Instrument)
		basisbox_slut.button[0].Bind(wx.EVT_BUTTON,self.OnBasisEnd)
		#extra menu items binded here#
		self.Bind(wx.EVT_MENU,self.OnEditHead,EditHead)
		self.Bind(wx.EVT_MENU,self.OnDeleteToLastHead,DeleteToLastHead)
		self.Bind(wx.EVT_MENU,self.OnDeleteLastAction,DeleteLast)
		self.Bind(wx.EVT_MENU,self.OnFileAnalysis,FileAnalysis)
		#end extra menu items   #
		sizer=wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(basisbox_start,1,wx.ALL,5)
		sizer.Add(middlebox,1,wx.ALL,5)
		sizer.Add(basisbox_slut,1,wx.ALL,5)
		lower_panel.SetSizer(sizer)
		self.rightsizer.Add(lower_panel,1,wx.EXPAND|wx.ALL,5)
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
			self.buttonboxes[0].button[2].Enable(instrumentstate>=0 and (self.statusdata.GetLastBasis() is not None))
			self.buttonboxes[0].SetFocus()
		else:
			self.buttonboxes[1].SetFocus()
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
		self.Log(SL)
		if DEBUG and self.statusdata.GetInstrumentState() is None:
			self.statusdata.SetInstrumentState(0)
		win=Instrument2Instrument(self)
	def OnBasisEnd(self,event):
		self.Log(SL)
		win=MakeBasis(self,self.statusdata.GetInstrumentState())
		win.InitializeMap()
	def OnFileAnalysis(self,event):
		fname=Core.GetFile(self,u"V\u00E6lg en resultatfil",Core.RESDIR)
		if len(fname)==0:
			return
		self.Log(SL)
		self.Log(u"L\u00E6ser %s" %fname)
		instnames=FileOps.GetInstrumentNames(fname,PROGRAM.type)
		if len(instnames)!=2:
			self.Log("Tilsyneladende ikke en MTL-resultatfil!")
			GUI.ErrorBox(self,"Tilsyneladende ikke en MTL-resultatfil!")
			return
		dists,temps,r_errs,ind1,ind2=FileOps.MTLPlotData(fname)
		if len(dists)==0:
			GUI.ErrorBox(self,"Ingen gensidige opstillinger fundet i filen.")
			return
		self.Log("Fandt %d gensidige opstillinger i %s, plotter data...." %(len(dists),fname))
		theplot=GUI.MultiPlotFrame(self,title=u"Plots af m\u00E5linger i %s." %fname)
		#plot index_errs#
		theplot.plotter[0].SetEnableLegend(True)
		ind1=np.array(ind1)
		ind2=np.array(ind2)
		pind1=GUI.plot.PolyMarker(ind1,colour="blue",size=1,legend=instnames[0],marker='square')
		pind2=GUI.plot.PolyMarker(ind2,colour="red",size=1,legend=instnames[1],marker='cross')
		graphics=[pind1,pind2]
		gc = GUI.plot.PlotGraphics(graphics,"Indeksfejl v. gensidige opstillinger","Opstilling","Indeksfejl ['']")
		theplot.plotter[0].Draw(gc)
		#plot dist#
		line = GUI.plot.PolyLine(dists, colour='blue', width=2)
		markers=GUI.plot.PolyMarker(dists,colour="red",size=1,marker='cross')
		gc=GUI.plot.PlotGraphics([line,markers],"Afstand v. gensidige opstillinger","Opstilling","Afstand [m]")
		theplot.plotter[1].Draw(gc)
		#plot r_errs#
		#line = GUI.plot.PolyLine(r_errs, colour='blue', width=2)
		markers=GUI.plot.PolyMarker(r_errs,colour="red",size=1,marker='square')
		gc=GUI.plot.PlotGraphics([markers],"Restfejl v. gensidige opstillinger","Opstilling","Restfejl ['']")
		theplot.plotter[2].Draw(gc)
		#plot temp#
		if len(temps)>0:
			line = GUI.plot.PolyLine(temps, colour='blue', width=2)
			markers=GUI.plot.PolyMarker(temps,colour="red",size=1,marker='cross')
			gc=GUI.plot.PlotGraphics([line,markers],"Temperatur v. gensidige opstillinger","Opstilling","Temp [C]")
			theplot.plotter[3].Draw(gc)
		#show plot#
		theplot.Show()
		
		
		
			
#-------------------------Instrument2Instrument Frame Defined Here----------------------------------------------#
class DistancePanel(wx.Panel):
	""" class handling (i/0) of distance measurements"""
	def __init__(self,parent,instrument_names,setup,auto_func1,auto_func2,update_func):
		wx.Panel.__init__(self,parent)
		self.SetAutoMode=auto_func1
		self.SetSingleAutoMode=auto_func2
		self.UpdateParentStatus=update_func
		self.setup=setup
		self.parent=parent
		top_line=wx.BoxSizer(wx.HORIZONTAL)
		bottom_line=wx.BoxSizer(wx.HORIZONTAL)
		text1=GUI.MyText(self,instrument_names[0],FONTSIZE,style=wx.ALIGN_CENTER)
		text2=GUI.MyText(self,instrument_names[1],FONTSIZE,style=wx.ALIGN_CENTER)
		top_line.Add(text1,1,wx.ALIGN_LEFT|wx.EXPAND)
		top_line.Add(text2,1,wx.ALIGN_RIGHT|wx.EXPAND)
		self.autobutton=GUI.MyButton(self,"AUTO (*)",FONTSIZE)
		wsize=FONTSIZE*12
		self.dfield1=GUI.MyNum(self,0,MAX_LENGTH_MUTUAL,digitlength=3,size=(wsize,-1),fontsize=FONTSIZE)
		self.dfield2=GUI.MyNum(self,0,MAX_LENGTH_MUTUAL,digitlength=3,size=(wsize,-1),fontsize=FONTSIZE)
		#BIND autobutton#
		self.autobutton.Bind(wx.EVT_BUTTON,self.OnAutoButton)
		#BIND ENTER in field2 to allow going to next state#
		self.dfield2.Bind(wx.EVT_TEXT_ENTER,self.OnEnter)
		self.dfield1.ij_id=[0,0]
		self.dfield2.ij_id=[0,1]
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
		self.status=GUI.StatusBox2(self,["Difference:","Middel:"],label="Afstand",colsize=1,fontsize=FONTSIZE-1)
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.status,1,wx.ALL,5)
		self.sizer.Add(top_line,0,wx.ALL|wx.EXPAND,5)
		self.sizer.Add(bottom_line,1,wx.ALL,5)
		
	def StartUp(self):
		self.Clear()
		self.status.Clear()
		self.Enable()
		self.fields[0].SetFocus()
		self.SetSizerAndFit(self.sizer)
	def Clear(self):
		for field in self.fields:
			field.Clear()
			field.SetBackgroundColour("white")
		
	def UpdateStatus(self):
		dist=self.setup.GetDistance()
		diff,ok=self.setup.DistanceTest()
		self.status.UpdateStatus(["%.2f cm" %(diff*100),"%.2f m" %dist],colours={0: Funktioner.State2Col(ok)})
	def OnEnter(self,event): #enter in 'last' field -> go to next state
		if self.setup.IsValid(row=0):
			self.UpdateParentStatus() #test is done in parent fct. to see if we can proceed to next state.
		else:
			event.Skip()
	def OnText(self,event): #need to determine how to go auto to next state in auto-mode
		#The strategy here should be common to all input 'setups' - thus could be put into a parent class#
		#Validate only the field issuing the event#
		field=event.GetEventObject()
		ok=field.Validate()
		row,col=field.ij_id
		self.setup.SetValidity(row,col,ok)
		if ok:
			self.setup.SetData(row,col,self.fields[col].GetValue())
			row_validity=self.setup.IsValid(row=0) 
			if row_validity:
				self.UpdateStatus()
				
		event.Skip()
	def OnChar(self,event): #easier to handle char events here, rather than via the standard 'keyhandler' setup of MyTextField....
		key=event.GetKeyCode()
		field=event.GetEventObject()
		if key==42: #char '*'
			self.SetAutoMode([self.fields[0]],[self.fields[1]]) #becuase SetAutoMode expects a 2 columns of fields .....
		elif key==47:#char '/'
			self.SetSingleAutoMode(field,field.ij_id[1])
		else:
			event.Skip() #so that text appears in the field....
	def OnAutoButton(self,event):
		self.SetAutoMode([self.fields[0]],[self.fields[1]])
		

class AutoPanel(wx.Panel):
	def __init__(self, parent, validator,text=None):
		self.parent=parent  
		self.next=None
		wx.Panel.__init__(self, parent,style=wx.RAISED_BORDER|wx.TAB_TRAVERSAL)
		wsize=(FONTSIZE+1)*11
		self.control1=GUI.MyTextField(self,fontsize=FONTSIZE+1,size=(wsize,-1))
		self.autobutton=GUI.MyButton(self,"AUTO(*)",FONTSIZE)
		self.control2=GUI.MyTextField(self,fontsize=FONTSIZE+1,size=(wsize,-1))
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
	""" Panel handling i/o of angle measurements in mutual setip """
	def __init__(self,parent,instrument_names,setup,auto_func1,auto_func2,update_func):
		wx.Panel.__init__(self,parent)
		self.setup=setup
		self.SetAutoMode=auto_func1
		self.SetSingleAutoMode=auto_func2
		self.UpdateParentStatus=update_func
		top_line=wx.BoxSizer(wx.HORIZONTAL)
		text1=GUI.MyText(self,instrument_names[0],FONTSIZE,style=wx.ALIGN_CENTER)
		text2=GUI.MyText(self,instrument_names[1],FONTSIZE,style=wx.ALIGN_CENTER)
		top_line.Add(text1,1,wx.ALIGN_LEFT|wx.EXPAND)
		top_line.Add(text2,1,wx.ALIGN_RIGHT|wx.EXPAND)
		self.status=GUI.StatusBox2(self,["H1:","H2:","Middel:","Restfejl:","Ind1:","Ind2:"],label="Seneste Sats",colsize=2,bold=True,fontsize=FONTSIZE-1)
		self.status.UpdateStatus()
		self.position1=AutoPanel(self,setup.Position1Validator,"1. kikkertstilling:")
		self.position2=AutoPanel(self,setup.Position2Validator,"2. kikkertstilling:")
		self.rows=[self.position1.fields,self.position2.fields]
		self.cols=np.array(self.rows,dtype=object).transpose().tolist()
		for row in range(2):
			for col in range(2):
				field=self.rows[row][col]
				#this id is rellay internal to this class - so we are free to choose any suitable indexing....
				field.ij_id=[row+1,col] #+1 beacuse dist fields also indexed in setup
				if row==0:
					field.SetValidator(setup.Position1Validator)
				else:
					field.SetValidator(setup.Position2Validator)
				field.Bind(wx.EVT_TEXT,self.OnText)
				field.Bind(wx.EVT_CHAR,self.OnChar)
				next_row=(row+(col>0))%2
				next_col=(col+1)%2
				prev_row=(row+(col==0))%2
				prev_col=(col+1)%2
				field.SetNextReturn(self.rows[next_row][next_col])
				field.SetNextTab(self.rows[next_row][next_col])
				field.SetPrev(self.rows[prev_row][prev_col])
		#EVENT BINDING#
		self.position1.autobutton.Bind(wx.EVT_BUTTON,self.OnAutoButton)
		self.position2.autobutton.Bind(wx.EVT_BUTTON,self.OnAutoButton)
		#EVENT BINDING ON LAST RETURN#
		self.rows[1][1].Bind(wx.EVT_TEXT_ENTER,self.OnEnter)
		#LAYOUT#
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.status,1,wx.ALL,5)
		self.sizer.Add(top_line,0,wx.ALL|wx.EXPAND,5)
		self.sizer.Add(self.position1,0,wx.ALL,5)
		self.sizer.Add(self.position2,0,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)
	def StartUp(self):
		self.Clear()
		self.Enable()
		self.rows[0][0].SetFocus()
	def UpdateStatus(self):
		h1,h2,h,rf,i_err1,i_err2,hdiff_ok,rf_ok=self.setup.Calculate()
		i_err1="%.0f''"%i_err1
		i_err2="%.0f''"%i_err2
		diff_col=Funktioner.State2Col(hdiff_ok)
		rf_col=Funktioner.State2Col(rf_ok)
		colors={0:diff_col,1:diff_col,3:rf_col}
		self.status.UpdateStatus(["%.4f m" %h1,"%.4f m" %h2,"%.4f m" %h,"%.0f''"%rf,i_err1,i_err2],colours=colors)
	def OnEnter(self,event):
		if self.setup.IsValid(row=1) and self.setup.IsValid(row=2):
			self.UpdateParentStatus()
		else:
			event.Skip()
	def OnText(self,event): 
		#Validate only the field issuing the event#
		field=event.GetEventObject()
		ok=field.Validate()
		row,col=field.ij_id
		self.setup.SetValidity(row,col,ok)
		if ok:
			self.setup.SetData(row,col,field.GetValue())
			if self.setup.IsValid():
				self.UpdateStatus()
		event.Skip()
	def OnChar(self,event): #easier to handle char events here, rather than via the standard 'keyhandler' setup of MyTextField....
		key=event.GetKeyCode()
		field=event.GetEventObject()
		row,col=field.ij_id
		if key==42: #char '*'
			self.SetAutoMode(self.cols[0][row-1:],self.cols[1][row-1:])
		elif key==47:#char '/'
			self.SetSingleAutoMode(field,field.ij_id[1])
		else:
			event.Skip() #so that text appears in the field....
	def OnAutoButton(self,event):
		self.SetAutoMode(self.cols[0],self.cols[1])
	def Clear(self):
		self.position1.Clear()
		self.position2.Clear()


class SatsEdit(GUI.TwoButtonDialog):
	"""Dialog used to select/delete valid/bad setups"""
	def __init__(self,parent,setup):
		self.parent=parent
		self.setup=setup
		self.changed=False
		GUI.TwoButtonDialog.__init__(self,parent,title="Redigering.",buttonlabels=["OK","FORTRYD"])
		keep_mask=setup.GetKeepMask()
		all=np.ones_like(keep_mask)
		nsats=keep_mask.size
		hdiffs=setup.GetHdiffs(all)
		rfejl=setup.GetRerrors(all)
		labels=["%i. sats, %.4fm, %.0f''"%(i+1,hdiffs[i],rfejl[i]) for i in range(nsats)]
		self.lb=wx.CheckListBox(self,choices=labels)
		for i in range(nsats):
			self.lb.Check(i,keep_mask[i])
		self.lb.Bind(wx.EVT_CHECKLISTBOX,self.OnCheck)
		self.lb.SetFont(GUI.DefaultFont(FONTSIZE-1))
		self.status=GUI.StatusBox2(self,[u"Middelv\u00E6rdi:","Middelfejl:","Max afvigelse:"],label=u"H\u00F8jdeforskel",minlengths=[8,8,8])
		self.InsertObject(self.lb)
		self.InsertObject(self.status)
		self.UpdateStatus()
	def OnCheck(self,event):
		index = event.GetSelection()
		self.lb.SetSelection(index) 
		self.UpdateStatus()
	def OnOK(self,event):
		nsats=self.setup.GetKeepMask().size #all 'satser'
		mask=np.zeros((nsats,),dtype=np.bool)
		for i in range(nsats):
			if self.lb.IsChecked(i):
				mask[i]=True
		nkeep=mask.sum()
		OK=True
		if nkeep==0:
			dlg=GUI.OKdialog(self.parent,u"Bekr\u00E6ft!","Vil du slette alle satser?")
			dlg.ShowModal()
			OK=dlg.WasOK()
			dlg.Destroy()
		if OK:
			if nkeep<nsats:
				self.setup.SetKeepMask(mask)
				msg=""
				for i in range(nsats):
					if not i:
						msg+="Sats %d er slettet.\n" %(i+1)
				self.parent.Log(msg)
				self.changed=True
			self.Close()
	def OnCancel(self,event):
		self.Close()
	def UpdateStatus(self):
		nsats=self.setup.GetKeepMask().size #all 'satser'
		mask=np.zeros((nsats,),dtype=np.bool)
		for i in range(nsats):
			if self.lb.IsChecked(i):
				mask[i]=True
		nkeep=mask.sum()
		self.status.Clear()
		if nkeep==1:
			self.status.UpdateStatus(["%.4f m"%self.setup.GetTotalHdiff(mask)])
		elif nkeep>1:
			mf=self.setup.GetStddev(mask)
			gen=self.setup.GetTotalHdiff(mask)
			mx=self.setup.GetMaxdev(mask)
			colors={2:Funktioner.State2Col(self.setup.MaxDevTest(mask))}
			self.status.UpdateStatus(["%.4f m"%gen,"%.1f mm"%(mf*1000),"%.1f mm" %(mx*1000)],colours=colors)
		self.SetSizer(self.sizer)
		
class Instrument2Instrument(GUI.FullScreenWindow):
	"""Main window for inst->inst setups"""
	def __init__(self, parent):
		GUI.FullScreenWindow.__init__(self, parent)
		#MODES DEFINED HERE#
		self.mode=0
		self.mmode=0  #0 : distances   1: angles, changed in the 2 SetMode fcts. below
		self.auto_fields=[[],[]] #two 'columns' to store fields for 'auto mode' in.
		self.modenames=["MANUEL","AUTO","SINGLE AUTO"]
		self.modecolors=["blue","red","yellow"]
		#END MODE SETUP - inherit stuff from parent#
		self.statusdata=parent.statusdata
		self.ini=parent.ini  #data passed in ini-file, error limits relevant here
		self.resfile=parent.resfile
		self.instruments=self.statusdata.GetInstruments()
		for instrument in self.instruments:
			instrument.SetLogWindow(self)
			instrument.SetEventHandler(self)
		inames=self.statusdata.GetInstrumentNames()
		inames=map(lambda x:x+": ",inames)
		self.aim=self.statusdata.GetInstrumentAims()
		#define setup class#
		self.setup=MTLsetup.MTLTransferSetup(self.aim,[[inst.addconst,inst.axisconst] for inst in self.instruments],self.ini)
		#define gui stuff #
		self.statusbox=GUI.StatusBox2(self,inames+["Mode: "],fontsize=FONTSIZE-1,label="Status",colsize=1,minlengths=[7,7,11],bold_list=[2])
		self.statusbox.UpdateStatus(map(Funktioner.Bool2sigte,self.aim))
		self.resultbox=GUI.StatusBox2(self,["Afstand:","Antal satser:", u"H\u00F8jdeforskel:","Middelfejl:","Max. afvigelse:"],label="Resultat",colsize=3
		,fontsize=FONTSIZE-1)
		self.resultbox.UpdateStatus([])
		self.main=GUI.ButtonBox2(self,["AFSTAND",u"TILF\u00D8J SATS","CHECK SATS(ER)","ACCEPTER","AFBRYD"],label="Styring",colsize=2,fontsize=FONTSIZE)
		self.main.button[1].Enable(0)
		self.main.button[2].Enable(0)
		self.main.button[3].Enable(0)
		self.lower=wx.Panel(self)
		self.lower.sizer=wx.BoxSizer()
		self.dpanel=DistancePanel(self.lower,inames,self.setup,self.SetAutoMode,self.SetSingleAutoMode,self.UpdateHeightStatus)
		self.spanel=SatsPanel(self.lower,inames,self.setup,self.SetAutoMode,self.SetSingleAutoMode,self.UpdateHeightStatus)
		self.lower.sizer.Add(self.dpanel)
		self.lower.sizer.Add(self.spanel)
		#EVENT HANDLING SETUP#
		self.Bind(Instrument.EVT_LOG,self.OnInstLog)
		self.Bind(Instrument.EVT_DATA,self.OnData)
		self.main.button[4].Bind(wx.EVT_BUTTON,self.OnCancel)
		self.main.button[3].Bind(wx.EVT_BUTTON,self.OnAccept)
		self.main.button[2].Bind(wx.EVT_BUTTON,self.OnCheckSats)
		self.main.button[0].Bind(wx.EVT_BUTTON,self.OnSetDistanceMode)
		self.main.button[1].Bind(wx.EVT_BUTTON,self.OnSetZMode)
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
		#WRITE TO LOG#
		self.Log(u"Starter m\u00E5ling mellem instrumenter kl. %s" %Funktioner.Nu())
		#Gaa direkte til afstand#
		self.SetDistanceMode() 
		self.ShowMe()
	def OnInstLog(self,event):
		self.Log(event.text)
	def OnData(self,event):
		id=event.id
		code,val=event.value
		if self.mode==0:
			self.instruments[id].Kill()
			return
		if code=="E" and self.mode>0:
			Core.SoundBadData()
			GUI.ErrorBox(self,val)
			self.SetManualMode() #end contorol here
			return
		elif (code=="<" and self.mmode==0) or (code=="?" and self.mmode==1):
			Core.SoundBadData()
			msg=[u"Forventede en afstandsm\u00E5ling!",u"Forventede en vinkelm\u00E5ling!"][self.mmode]
			msg+="\nSendt fra instrument: %s" %val
			GUI.ErrorBox(self,msg)
			self.SetManualMode() #end control here
			return
		if len(self.auto_fields[id])>0:
			Core.SoundGoodData()
			field=self.auto_fields[id][-1]
			field.SetValue(val)
			field.Enable()
			self.auto_fields[id]=self.auto_fields[:-1]
		if len(self.auto_fields[0])==0 and len(self.auto_fields[1])==0:
			self.UpdateHeightStatus()
			self.SetManualMode() #or something else
	def OnSetZMode(self,event):
		self.SetZMode()
	def OnSetDistanceMode(self,event):
		n=self.setup.GetNsats()
		if (n>0):
			dlg=GUI.OKdialog(self,u"Vil du g\u00E5 til afstandsm\u00E5ling?",
			u"Du har allerede m\u00E5lt %d satser.\nEr du sikker p\u00E5, at du vil starte forfra?"%n)
			dlg.ShowModal()
			ok=dlg.WasOK()
			dlg.Destroy()
			if not ok:
				return
		self.SetDistanceMode()
	def SetDistanceMode(self):
		self.Log(u"Starter afstandsm\u00E5ling.")
		self.mmode=0
		self.setup.Clear()
		self.spanel.Show(0)
		self.dpanel.Show()
		self.dpanel.StartUp()
		self.lower.SetSizerAndFit(self.lower.sizer)
		self.LayoutSizer()
		
	def SetZMode(self):
		self.Log(u"Starter satsm\u00E5ling.")
		self.mmode=1
		self.dpanel.Show(0)
		self.spanel.Show()
		self.spanel.StartUp()
		self.lower.SetSizerAndFit(self.lower.sizer)
		self.LayoutSizer()
	def SetManualMode(self):
		if self.mode==0:
			return
		self.Log(u"Skifter til 'manuel mode'. Afbryder instrumentl\u00E6sning.")
		self.mode=0
		for inst in self.instruments:
			inst.Kill()
		for col in self.auto_fields:
			for field in col:
				field.Enable()
		self.auto_fields=[[],[]]
		self.UpdateStatus()
	def SetAutoMode(self,col1,col2):
		if self.mode>0:
			self.SetManualMode()
			return
		self.Log("Skifter til 'auto mode'.")
		self.auto_fields=[col1,col2]
		for col in self.auto_fields:
			for field in col:
				field.Enable(0)
		self.mode=1
		for instrument in self.instruments:
			instrument.ReadData()
		self.UpdateStatus()
	def SetSingleAutoMode(self,field,col):
		if self.mode>0:
			self.SetManualMode()
			return
		self.auto_fields=[[],[]]
		self.auto_fields[col]=[field]
		self.Log("Skifter til 'single auto mode'.")
		field.Enable(0)
		self.mode=2
		self.instruments[col].ReadData()
		self.UpdateStatus()
	def UpdateStatus(self):
		self.statusbox.UpdateStatus(text=self.modenames[self.mode],colour=self.modecolors[self.mode],field=2)
		self.LayoutSizer()
	def PromptUser(self,msg):
		dlg=GUI.OKdialog(self,u"Fors\u00E6t?",msg+u"\nVil du fors\u00E6tte?")
		dlg.ShowModal()
		ok=dlg.WasOK()
		dlg.Destroy()
		return ok
	def UpdateHeightStatus(self): #name is a bit 'misvisende' since general status is really handled here....
		if self.mmode==0:
			diff,ok=self.setup.DistanceTest()
			msg=u"Stor forskel mellem afstandsm\u00E5linger: %.3f m" %abs(diff)
		else:
			ok=self.setup.SatsTest()
			msg=u"Den aktuelle sats opfylder ikke fejlkriterierne!"
		if not ok:
			ok=self.PromptUser(msg)
			if not ok:
				return
		if self.mmode>0:
			self.setup.AddSats()
		data=self.setup.GetStringData()
		self.resultbox.UpdateStatus(data)
		self.main.button[1].Enable(self.setup.IsValid(row=0))
		self.main.button[2].Enable(self.setup.GetNsats()>1)
		self.main.button[3].Enable(self.setup.GetNsats()>0)
		if self.mmode==0:
			self.SetZMode()
		else:
			self.spanel.Enable(0)
			self.main.button[1].SetFocus()
			self.LayoutSizer()
	def OnCheckSats(self,event):
		#opens up a dialog where 'satser' can be deleted....
		win=SatsEdit(self,self.setup)
		win.ShowModal()
		self.UpdateHeightStatus()
		win.Destroy()
	def OnAccept(self,event):
		if self.setup.GetNsats()>0:
			self.CloseOK()
			
	def CloseOK(self):
		self.Log(u"Afslutter m\u00E5ling mellem instrumenter kl. %s" %Funktioner.Nu())
		hdiff=self.setup.GetTotalHdiff()
		dist=self.setup.GetDistance()
		self.Log(u"Afstand: %.2f m, h\u00F8jdeforskel: %.4f m" %(dist,hdiff))
		self.statusdata.GotoNextInstrument() #do this before writing data.....
		self.WriteData()
		self.statusdata.AddSetup(hdiff,dist) #signal code for setup type
		if DEBUG:
			self.Log("Instrument %s carries height" %self.statusdata.GetDefiningInstrument().GetName())
		ierrs=self.setup.GetIndexErrorsAll()
		insts=self.statusdata.GetInstruments()
		for row in ierrs: #add index errors.....
			insts[0].AddIndexError(row[0])
			insts[1].AddIndexError(row[1])
		self.parent.UpdateStatus()
		self.Close()
	def WriteData(self):
		resfile=open(self.resfile,"a")
		Inst1,Inst2=self.statusdata.GetInstruments()
		keep_mask=self.setup.GetKeepMask()
		nsats=self.setup.GetNsats()
		hdiff=self.setup.GetTotalHdiff()
		dist=self.setup.GetDistance()
		#Skriv til fil
		spaces=map(len,self.statusdata.GetInstrumentNames())
		space=max(spaces)+4
		space1=spaces[0]+4
		space2=spaces[1]+4
		resfile.write("%*s %*s %*s %*s %s\n" %(-space,Inst1.GetName(),-space2,Inst2.GetName(),-10,"Satser",-12,"Afstand","Hoejdeforskel"))
		resfile.write("%*s %*s %*i %*s %.4fm\n" %(-space,Funktioner.Bool2sigte(self.aim[0]),-space2,Funktioner.Bool2sigte(self.aim[1]),-10,nsats,-12,"%.3fm"%dist,hdiff))
		#write valid data#
		satser=self.setup.GetSatser() 
		hdiffs=self.setup.GetHdiffsRaw()
		rerrs=self.setup.GetRerrors()
		for i in range(nsats):
			if i==0:
				d1,d2=map(lambda x: "%.3fm" %x,self.setup.GetDistances())
			else:
				d1,d2="",""
			resfile.write("%*s"%(-space,Inst1.GetName()+":")+"%*s" %(-10,d1)+"%*s"%(-10,satser[i,0,0])+"%*s" %(-10,satser[i,0,1])
			+"%*s" %(-10,"")+"%.4fm" %hdiffs[i,0]+"\n")
			resfile.write("%*s"%(-space,Inst2.GetName()+":")+"%*s" %(-10,d2)+"%*s"%(-10,satser[i,1,0])+"%*s"%(-10,satser[i,1,1])
			+"%*s"%(-10,"%.0f''"%rerrs[i])+"%.4fm" %hdiffs[i,1]+"\n")
		del_mask=np.logical_not(keep_mask)
		if del_mask.any(): #then write deleted data
			satser=self.setup.GetSatser(del_mask) 
			hdiffs=self.setup.GetHdiffsRaw(del_mask)
			rerrs=self.setup.GetRerrors(del_mask)
			for i in range(del_mask.sum()):
				resfile.write(";%*s"%(-space,Inst1.GetName()+":")+"%*s" %(-10,"")+"%*s"%(-10,satser[i,0,0])+"%*s" %(-10,satser[i,0,1])
				+"%*s" %(-10,"")+"%.4fm" %hdiffs[i,0]+"(SLETTET)\n")
				resfile.write(";%*s"%(-space,Inst2.GetName()+":")+"%*s" %(-10,"")+"%*s"%(-10,satser[i,1,0])+"%*s"%(-10,satser[i,1,1])
				+"%*s"%(-10,"%.0f''"%rerrs[i])+"%.4fm" %hdiffs[i,1]+"\n")
		newinstrument=self.statusdata.GetDefiningInstrument().GetName()
		resfile.write("* II %s %.3f %.6f\n"%(newinstrument,dist,hdiff))
		resfile.write("; ukorrigerede afst.: %.3f %.3f\n" %tuple(self.setup.GetData()[0].tolist()))
		if self.parent.gps.isAlive():
			try:
				x,y,dop=self.parent.gps.GetPos() 
			except:
				pass
			else:
				if dop<30:
					resfile.write("GPS: %.1f %.1f %.1f\n" %(x,y,dop))
		resfile.write("\n")
		resfile.close()
	def OnCancel(self,event):
		quit=True
		valid=self.setup.GetValidity().sum()+self.setup.GetNsats()*4
		if valid>1:
			dlg=GUI.OKdialog(self,"Vil du afslutte?",
			u"Du har foretaget %i valide m\u00E5linger.\nEr du sikker p\u00E5, at du vil aflsutte?"%valid)
			dlg.ShowModal()
			quit=dlg.WasOK()
			dlg.Destroy()
		if quit:
			self.Log(u"Afbryder m\u00E5ling mellem instrumenter.")
			self.Close()
	def Log(self,text):
		self.parent.Log(text)

#-------------------------Various Wx Windows Specialized for MTL and used in MakeBasis -------------------------------------------------#

#Panel til input af basismaalinger....
class OverfPanel(wx.Panel):
	def __init__(self,parent,basis_setup,low=-33,high=33,fontsize=12): #input graenser for indeksfejl advarsler...
		wx.Panel.__init__(self,parent)
		self.parent=parent
		self.setup=basis_setup #a class which handles field validation, data storage and calculation
		self.sizer=wx.GridSizer(5,4,5,5)
		headings=[u"M\u00E6rke","1. kikkertstilling","2. kikkertstilling","Indeksfejl ('')"]
		for text in headings:
			field=GUI.MyText(self,text,fontsize+2,style=wx.ALIGN_CENTER)
			self.sizer.Add(field,1,wx.ALL,0)
		self.columns=[[],[],[],[]]
		FS=int(fontsize+4)
		hsize=int(10*FS)
		for row in range(4):
			field1=GUI.MyNum(self,0,MAX_ROD,size=(hsize,-1),fontsize=FS) #The 'high' value here is set in the global var MAX_ROD
			field2=GUI.MyTextField(self,size=(hsize,-1),fontsize=FS)
			field3=GUI.MyTextField(self,size=(hsize,-1),fontsize=FS)
			field2.SetValidator(basis_setup.Position1Validator)
			field3.SetValidator(basis_setup.Position2Validator)
			field4=GUI.MyNum(self,low,high,size=(hsize,-1),fontsize=FS,style=wx.TE_READONLY)
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
		text=field.GetValue()
		proceed=self.parent.InputAction(text)
		if ok and proceed:
			self.setup.SetData(row,col,text)
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
	
		
#valideringsfkt. til punktnavne
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
	def __init__(self,parent,laegter,fontsize=12):
		GUI.StuffWithBox.__init__(self,parent,label="Valg",style="vertical")
		hsize=int(fontsize*10+30)
		self.point=GUI.MyTextField(self,fontsize,size=(hsize,-1))
		self.point.SetValidator(ValidatePointName)
		pointsizer=GUI.FieldWithLabel(self,self.point,"Punkt:",fontsize)
		self.laegtebox=Core.RodBox(self,laegter,size=(hsize,-1),fontsize=fontsize)
		self.laegtebox.Bind(wx.EVT_TEXT_ENTER,self.OnEnter)
		self.laegtebox.SetSelection(0)
		laegtesizer=GUI.FieldWithLabel(self,self.laegtebox,u"L\u00E6gte:",fontsize)
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
		dsize=wx.GetDisplaySize() #but we need to check this anyways....
		if dsize[0]<1200: #well not used right now
			mapproportion=2
		else:
			mapproportion=2
		self.instrument_number=instrument_number #the height status after succesful measurements should be this number.... Instrument that 'carries' height.
		self.statusdata=parent.statusdata
		self.resfile=parent.resfile
		self.ini=parent.ini  #data passed in ini-file, error limits relevant here
		self.mode=0 #modes are 0: manual and 1: auto 2; single auto - i.e. just one field....
		self.modenames=["MANUEL","AUTO","SINGLE AUTO"]
		self.modecolors=["blue","red","yellow"]
		self.auto_fields=[] #an ordered list of fields from subpanel to receive data from instrument
		self.sigte=-2*int((self.statusdata.GetSetups())==0)+1
		self.setup=MTLsetup.MTLBasisSetup(self.sigte)
		self.instrument=self.statusdata.GetInstruments()[instrument_number]
		GUI.FullScreenWindow.__init__(self, parent)
		self.status=GUI.StatusBox2(self,["Instrument: ","Sigte: ","Mode: "],fontsize=FONTSIZE-1,bold=True)
		self.valg=MTLChoiceBox(self,[rod.name for rod in self.laegter],FONTSIZE)
		startp=self.statusdata.GetEnd()
		if startp is None or self.sigte==1:
			startp=""
		self.valg.SetPoint("%s"%startp)
		self.map=PanelMap(self,self.parent.data,self.ini.mapdirs) #setup the map - a panel in the center of the screen
		self.map.RegisterPointFunction(self.PointNameHandler) #handles left-clicks on points in map - sets name in point box
		self.main=GUI.ButtonBox2(self,["AUTO(*)","MANUEL","ACCEPTER","AFBRYD"],label="Styring",colsize=2)
		index_min,index_max=self.instrument.GetIndexBounds()
		self.maal=OverfPanel(self,self.setup,index_min,index_max,FONTSIZE) #use global fontsize
		self.valg.next_item=self.maal #controls that after 'enter' in rod-selection, we should go here.... 
		self.resultbox=GUI.StatusBox2(self,["Afstand: ",u"H\u00F8jde:"],label="Resultat",fontsize=FONTSIZE-1,colsize=2,bold=True)
		self.controlbox=GUI.StatusBox2(self,[u"H\u00F8jde (m1+m3): ",u"H\u00F8jde (m2+m4): ","Difference: "],fontsize=FONTSIZE-1,label="Kontrol",bold=True)
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
		self.Bind(wx.EVT_CLOSE,self.OnEVTClose) #in order to detach gps
		#LAYOUT#
		self.UpdateStatus()
		self.CreateRow()
		sizer_left=wx.BoxSizer(wx.VERTICAL)
		sizer_left.Add(self.status,1,wx.ALL,5)
		sizer_left.Add(self.resultbox,1,wx.ALL,5)
		self.AddItem(sizer_left,1,wx.ALL,5)
		self.AddItem(self.map,mapproportion,wx.ALL,5)
		sizer_right=wx.BoxSizer(wx.VERTICAL)
		sizer_right.Add(self.valg,1,wx.ALL,5)
		sizer_right.Add(self.main,1,wx.ALL,5)
		self.AddItem(sizer_right,1,wx.ALL,5)
		self.AddRow(2,wx.CENTER|wx.ALL|wx.EXPAND)
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
			#GUI.ErrorBox(self,u"Kunne ikke \u00E5bne instrumentets com-port...")
			self.Log(u"Kunne ikke \u00E5bne instrumentets com-port...")
	def OnEVTClose(self,event):
		if self.parent.gps.isAlive():
			self.map.DetachGPS()
			self.parent.map.AttachGPS(self.parent.gps)
		event.Skip()
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
		self.Log("Doing sketch :-)")
		dlg=GUI.MyLongMessageDialog(self,"You asked for it!",msg)
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
					self.Log(msg)
					msg+=u"Vil du godkende m\u00E5lingen?"
					dlg=GUI.OKdialog(self,"Forkastelseskriterie",msg)
					dlg.ShowModal()
					OK=dlg.WasOK()
					dlg.Destroy()
					return OK
			else:
				self.Log("%s til %s ikke fundet i forkastelsesdatabasen." %(data.GetEnd(),data.GetStart()))
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
			resfile.write("# %s %s %s %s %.2f %.5f %s %.1f %d\n\n"%(start,slut,dato,tid,dist,hdiff,jside,temp,nopst))
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
	def InputAction(self,text): #called from subpanel containing text fields. Test for input with special significance...
		if "test" in text:
			self.TestMode()
			return False
		if "monty" in text:
			self.DoSketch()
			return False
		return True
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
		ini.maxdh_basis=0.001 #max. forskel mellem h1 og h2 ved basis, 
		ini.maxdelta_dist=0.05 #max. afv. mellem afst, maalinger
		ini.max_rf=20 #maks. restfejl foer advarsel...
		#FLG. Fejl er afstandsafhaengige. FEJL pr. 100m,#
		ini.maxdh_mutual=0.001 #max. forskel mellem maalt dh ved gensidige sigter,
		ini.maxdh_setups=0.005 #max. afv. mellem satser, 
		ini.maxsd_setups=0.007 #max. stdafv. ved flere satser
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
					if len(line)>0:
						ini.fbunit=line[1]
				if key=="maxdelta_dist" and len(line)>0:
					ini.maxdelta_dist=float(line[0])
				if key=="maxdh_basis" and len(line)>0:
					ini.maxdh_basis=float(line[0])
				if key=="maxdh_sats" and len(line)>0:
					ini.maxdh_mutual=float(line[0])
				if key=="maxdh_satser" and len(line)>0:
					ini.maxdh_setups=float(line[0])
				if key=="maxsd_satser" and len(line)>0:
					ini.maxsd_setups=float(line[0])
				if key=="max_restfejl" and len(line)>0:
					ini.max_rf=float(line[0])
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
	dsize=wx.GetDisplaySize() #but we need to check this anyways....
	global FONTSIZE
	if dsize[0]<1100 or dsize[1]<800: #set default fontsize for labels, input fields etc. - fields set size relative to this base size
		FONTSIZE=12
	else:
		FONTSIZE=14
	frame=StartFrame(None)
	if DEBUG:
		frame.resfile="test.txt"
		frame.InitResultFile(frame.resfile)
		frame.StartProgram()
	else:
		frame.Show()
	App.MainLoop()
	sys.exit()

#--------------------And here we go!-----------------------------------------------#
if __name__=="__main__":
	main()