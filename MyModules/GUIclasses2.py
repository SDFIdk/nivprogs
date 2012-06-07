import wx
import wx.lib.plot as plot
import os
import sys
BGCOLOR="light gray"

#-----------------------------------------------------------------------#
#---This module contains basic, context independt GUI-classes---#
#-----------------------------------------------------------------------#
def DefaultFont(size,bold=False):
	if bold:
		style=wx.BOLD
	else:
		style=wx.NORMAL
	return wx.Font(size,wx.SWISS,wx.NORMAL,style)
def DefaultLogFont(size,bold=False):
	if bold:
		style=wx.BOLD
	else:
		style=wx.NORMAL
	return wx.Font(size,wx.MODERN,wx.NORMAL,style)
#---------------------------------------------#
#----------Dummy Window------------------#
#---------------------------------------------#
class DummyWindow(object):
	def IsShown(*args):
		return False
	def IsShownOnScreen(*args):
		return False
	def Close(*args):
		pass
	def Show(*args):
		pass
		
#--------------------------------------------#
#------Basic wx-window classes-----------#
#--------------------------------------------#
class MainWindow(wx.Frame):
	def __init__(self,parent,**kwargs):
		wx.Frame.__init__(self,parent,**kwargs)
		#Internal vars
		self.parent=parent
		# A Statusbar in the bottom of the window
		self.CreateStatusBar() 
		#Appeareance#
		dsize=wx.GetDisplaySize()
		dsize=dsize-(40,40)
		self.SetSize(dsize)
		self.Center()
		self.SetBackgroundColour(BGCOLOR)

class SecondaryWindow(wx.Frame):
	def __init__(self,parent,**kwargs):
		wx.Frame.__init__(self,parent, **kwargs)
		#Internal vars
		self.parent=parent
		#Appeareance#
		try:
			icon=parent.GetIcon()
		except:
			pass
		else:
			self.SetIcon(icon)
		self.Center()
		self.SetBackgroundColour(BGCOLOR)

class PlainWindow(wx.Frame):
	def __init__(self,parent):
		wx.Frame.__init__(self,parent)
		self.parent=parent
		self.SetBackgroundColour(BGCOLOR)
		
class FullScreenWindow(PlainWindow):
	def __init__(self,parent):
		PlainWindow.__init__(self,parent)
		self.hsizer=wx.BoxSizer(wx.HORIZONTAL)
		self.vsizer=wx.BoxSizer(wx.VERTICAL)
		self.vsizer.AddSpacer(10) #above
		self.vsizer.AddSpacer(10) #below
		self.hsizer.AddSpacer(20) #left
		self.hsizer.Add(self.vsizer,1,wx.EXPAND,5)
		self.hsizer.AddSpacer(20) #right
		self.rowsizer=wx.BoxSizer(wx.HORIZONTAL)
		self.insert_at=1
		
	def ShowMe(self):
		self.Show()
		self.SetSizerAndFit(self.hsizer)
		self.ShowFullScreen(1)
	def LayoutSizer(self):
		#self.vsizer.Layout()
		self.hsizer.Layout()
		
	def CreateRow(self):
		self.rowsizer=wx.BoxSizer(wx.HORIZONTAL)
	def AddItem(self,item,proportion=1,style=wx.ALL,border=5):
		self.rowsizer.Add(item,proportion,style,border)
	def AddRow(self,proportion=1,style=wx.ALL,border=5):
		self.vsizer.Insert(self.insert_at,self.rowsizer,proportion,style,border)
		self.vsizer.AddSpacer(5)
		self.insert_at+=2
class PlotFrame(SecondaryWindow): #Frame for showing a single plot
	def __init__(self,parent,*args,**kwargs):
		self.parent=parent
		SecondaryWindow.__init__(self,parent,**kwargs)
		self.panel= wx.Panel(self)
		self.panel.SetBackgroundColour("yellow")
		self.button=MyButton(self.panel,"Luk",12)
		self.savebutton=MyButton(self.panel,"Gem",12)
		self.button.Bind(wx.EVT_BUTTON,self.OnClose)
		self.savebutton.Bind(wx.EVT_BUTTON,self.OnSave)
		# mild difference between wxPython26 and wxPython28
		if wx.VERSION[1] < 7:
			self.plotter = plot.PlotCanvas(self.panel, size=(550, 550))
		else:    
			self.plotter = plot.PlotCanvas(self.panel)
			self.plotter.SetInitialSize(size=(550, 550))
		self.panel.sizer=wx.BoxSizer(wx.VERTICAL)
		self.panel.hsizer=wx.BoxSizer(wx.HORIZONTAL)
		self.panel.sizer.Add(self.plotter,1,wx.EXPAND,5)
		self.panel.hsizer.Add(self.button,0,wx.ALL,5)
		self.panel.hsizer.Add(self.savebutton,0,wx.ALL,5)
		self.panel.sizer.Add(self.panel.hsizer,0,wx.ALL,5)
		self.panel.SetSizerAndFit(self.panel.sizer)
		self.Show(True)
	def OnClose(self,event):
		self.Close()
	def OnSave(self,event):
		self.plotter.SaveFile()
	def PlotData(self,times,vals,title,xlabel="",ylabel="Temperatur (grader C)",insertlines=[]):
		if len(times)>0:
			mi=min(times)-0.1
			mx=max(times)+0.1
			y1=min(vals)-1
			y2=max(vals)+1
			data=zip(times,vals)
			line = plot.PolyLine(data, colour='blue', width=2)
			graphics=[line]
			for x in insertlines:
				graphics.append(plot.PolyLine([(x,y1),(x,y2)],colour="red",width=2))
			gc = plot.PlotGraphics(graphics,title,xlabel,ylabel)
			self.plotter.Draw(gc,(mi,mx),(y1,y2))	
class MultiPlotFrame(SecondaryWindow): #Frame for showing 4 plots.
	def __init__(self,parent,**kwargs):
		self.parent=parent
		SecondaryWindow.__init__(self,parent,**kwargs)
		filemenu=wx.Menu()
		save1=filemenu.Append(wx.ID_ANY,"Gem graf 1")
		save2=filemenu.Append(wx.ID_ANY,"Gem graf 2")
		save3=filemenu.Append(wx.ID_ANY,"Gem graf 3")
		save4=filemenu.Append(wx.ID_ANY,"Gem graf 4")
		filemenu.AppendSeparator()
		luk=filemenu.Append(wx.ID_ANY,"Luk")
		menuBar = wx.MenuBar()
		menuBar.Append(filemenu,"&File")
		self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.
		self.Bind(wx.EVT_MENU,self.OnSave1,save1)
		self.Bind(wx.EVT_MENU,self.OnSave2,save2)
		self.Bind(wx.EVT_MENU,self.OnSave3,save3)
		self.Bind(wx.EVT_MENU,self.OnSave4,save4)
		self.Bind(wx.EVT_MENU,self.OnClose,luk)
		self.panel=[]
		self.plotter=[]
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.hsizer1=wx.BoxSizer(wx.HORIZONTAL)
		self.hsizer2=wx.BoxSizer(wx.HORIZONTAL)
		for i in range(0,4):
			panel= wx.Panel(self)
			self.panel.append(panel)
			plotter = plot.PlotCanvas(panel)
			plotter.SetInitialSize(size=(350, 350))
			self.plotter.append(plotter)
			panel.sizer=wx.BoxSizer()
			panel.sizer.Add(plotter,1,wx.EXPAND)
			panel.SetSizerAndFit(panel.sizer)
		self.hsizer1.Add(self.panel[0],1,wx.EXPAND,5)
		self.hsizer1.Add(self.panel[1],1,wx.EXPAND,5)
		self.hsizer2.Add(self.panel[2],1,wx.EXPAND,5)
		self.hsizer2.Add(self.panel[3],1,wx.EXPAND,5)
		self.sizer.Add(self.hsizer1,1,wx.EXPAND,5)
		self.sizer.Add(self.hsizer2,1,wx.EXPAND,5)
		self.SetSizerAndFit(self.sizer)
		self.Show(True)
	def OnClose(self,event):
		self.Close()
	def OnSave1(self,event):
		self.plotter[0].SaveFile()
	def OnSave2(self,event):
		self.plotter[1].SaveFile()
	def OnSave3(self,event):
		self.plotter[2].SaveFile()
	def OnSave4(self,event):
		self.plotter[3].SaveFile()
	def DrawVlines(self,pointlist,y1,y2,plotter):
		p=plotter
		self.plotter[p].SetEnableLegend(False)
		lines=[]
		for x in pointlist:
			lines.append(plot.PolyLine([(x,y1),(x,y2)],colour='red'))
			gc = plot.PlotGraphics(lines)
		self.plotter[p].Draw(gc)
		self.plotter[p].SetEnableLegend(True)
		

class DebugWindow(wx.Frame):
	def __init__(self,parent):
		self.parent=parent
		wx.Frame.__init__(self,parent,title="DEBUG-CONSOLE",style=wx.DEFAULT_FRAME_STYLE|wx.STAY_ON_TOP)
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.field=wx.TextCtrl(self,size=(300,-1),style=wx.TE_PROCESS_ENTER)
		self.sizer.Add(self.field,0,wx.EXPAND|wx.ALL,10)
		self.SetSizerAndFit(self.sizer)
		self.Show()
	def BindEnter(self,fct):
		self.field.Bind(wx.EVT_TEXT_ENTER,fct)
	def ClearField(self):
		self.field.Clear()
		


#-------------------------------------------------------------------------------#
#Custom text-fields and keys- designed for better visualization "in field"
#wx has a font manager, so not wasteful to use fonts for each button....
#--------------------------------------------------------------------------------#
class MyButton(wx.Button):
	def __init__(self, parent, label="", fontsize=12):
		wx.Button.__init__(self,parent,label=label)
		self.font2=wx.Font(fontsize,wx.SWISS,wx.NORMAL,wx.BOLD)
		self.font1=wx.Font(fontsize,wx.SWISS,wx.NORMAL,wx.NORMAL)
		self.SetFont(self.font1)
		self.Bind(wx.EVT_SET_FOCUS,self.OnFocus)
		self.Bind(wx.EVT_KILL_FOCUS,self.KillFocus)
	def OnFocus(self,event):
		self.SetFont(self.font2)
		self.Refresh()
		event.Skip()
	def KillFocus(self,event):
		self.SetFont(self.font1)
		self.Refresh()
		event.Skip()
	def SetFontSize(self,fs):
		self.font2=wx.Font(fs,wx.SWISS,wx.NORMAL,wx.BOLD)
		self.font1=wx.Font(fs,wx.SWISS,wx.NORMAL,wx.NORMAL)
		self.SetFont(self.font1)
#Text-field. Process enter - for browsing to a 'next'-element.
#Has a validation method to check if empty
class FileLikeTextCtrl(wx.TextCtrl):
	def __init__(self,parent,**kwargs):
		wx.TextCtrl.__init__(self,parent,**kwargs)
	def write(self,text):
		self.WriteText(text)
		self.Refresh()
	def flush(self):
		pass
	def close(self):
		self.Close()
		
class MyTextField(wx.TextCtrl): 
	def __init__(self,parent,style=wx.TE_PROCESS_ENTER,size=(-1,-1),fontsize=12):
		self.next=None
		self.nexttab=None
		self.prevtab=None
		self.keyhandler=None
		self.validator=None
		self.ok=False #is the value valid?
		self.focus=True #higlight on focus?
		self.overwrite=False #for editing.
		self.previous_bgcolor=None #for repainting when loosing focus 
		wx.TextCtrl.__init__(self,parent,style=style,size=size)
		self.SetFont(DefaultFont(fontsize))
		self.Bind(wx.EVT_TEXT_ENTER,self.OnEnter)
		self.Bind(wx.EVT_CHAR,self.OnKey)
		self.Bind(wx.EVT_SET_FOCUS,self.OnFocus)
		self.Bind(wx.EVT_KILL_FOCUS,self.OnKillFocus)
	def IsValid(self):
		return self.ok
	def ShowValidity(self):
		if self.ok:
			self.SetBackgroundColour("green")
			self.previous_bgcolour="green"
		else:
			self.SetBackgroundColour("red")
			self.previous_bgcolour="red"
		self.Refresh()
	def RegisterKeyHandler(self,fct=None):
		self.keyhandler=fct
	def SetNext(self,item):
		self.next=item
		self.nexttab=item
	def SetNextTab(self,item):
		self.nexttab=item
	def SetNextReturn(self,item):
		self.next=item
	def SetPrev(self,item):
		self.prevtab=item
	def Validate(self,colors=True):
		if self.validator is not None:
			OK=self.validator(self.GetValue().strip())
		else:
			OK=not self.IsEmpty()
		self.ok=OK
		if colors:
			self.ShowValidity()
		return OK
	def OnKey(self,event):
		key=event.GetKeyCode()
		#Navigation
		if (key==wx.WXK_DOWN or key==wx.WXK_TAB) and self.nexttab!=None:  
			self.nexttab.SetFocus()
		elif (key==wx.WXK_UP) and self.prevtab!=None:
			self.prevtab.SetFocus()
		elif self.keyhandler!=None:
			handled=self.keyhandler(key) #can return None even if handled
			if not handled:
				event.Skip()
		else:
			event.Skip()
	def OnEnter(self,event):
		if self.next!=None:
			self.next.SetFocus()
		event.Skip() #to allow a 'bling' sound
	def OnFocus(self,event):
		if self.focus:
			self.previous_bgcolour=self.GetBackgroundColour()
			self.SetBackgroundColour("yellow")
		if self.overwrite:
			self.SetSelection(-1,-1) #vaelger al tekst
		event.Skip()
	def OnKillFocus(self,event):
		if self.focus and self.previous_bgcolour is not None:
			self.SetBackgroundColour(self.previous_bgcolour)
		event.Skip()
	def Clear(self):
		self.ChangeValue("")
		self.SetBackgroundColour("white")
	def SetValidator(self,fct):
		self.validator=fct
#Static-text
class MyText(wx.StaticText):
	def __init__(self, parent, label="",fontsize=12,bold=False,style=0):
		wx.StaticText.__init__(self,parent,label=label,style=style)
		self.SetFont(DefaultFont(fontsize,bold))



#Number field, i.e. a subclass of MyText with a standard validator and some speciel methods - should be subclassed for the MTL/MGL programs
class MyNum(MyTextField):
	def __init__(self,parent,low=-999,high=999,ntype=float,maxlength=12,digitlength=None,**kwargs): 
		self.type=ntype #type of validation.
		self.digitlength=digitlength #for setting the exact # of digits
		self.parent=parent
		self.low=low
		self.high=high
		MyTextField.__init__(self,parent,**kwargs)
		self.SetMaxLength(maxlength)
		self.SetValidator(self.StandardValidator)
	def SetBounds(self,low,high):
		self.low=low
		self.high=high
	def StandardValidator(self,text):
		sval=text.replace(",",".")
		digits=""
		try:
			val=float(sval)
		except:
			OK=False
		else:
			OK=True
			digits=sval.partition(".")[2].strip()
			if (val>self.high) or (val<self.low):
				OK=False
			elif self.digitlength!=None and self.digitlength>len(digits):
				OK=False
		return OK
	def GetMyValue(self,cast=True):
		val=self.GetValue()
		val=val.replace(",",".").strip()
		if cast:
			val=self.type(val)
		return val

#-------------------------------------------------------------------#
#-Status Boxes, for showing status text.
#--------------------------------------------------------------------#
class StatusBox(wx.Panel):   #style is a dictionary: item.nr.: [fontsize,bold (1 or 0),style (e.g. wx.ALIGN_LEFT)]
	def __init__(self, parent,list=[],fontsize=12,label="Status",style={},bold=False):
		self.parent=parent
		self.list=list
		fs=fontsize
		wx.Panel.__init__(self, self.parent)
		self.box=wx.StaticBox(self,label=label)
		self.box.SetFont(wx.Font(fs,wx.SWISS,wx.NORMAL,wx.NORMAL))
		self.text=[]
		hsizers=[]
		self.bsizer=wx.StaticBoxSizer(self.box,wx.VERTICAL)
		self.sizer=wx.BoxSizer()
		for i in range(0,len(self.list)):
			if style.has_key(i):
				line=[MyText(self,self.list[i],style[i][0],bold=style[i][1]),MyText(self,"NA",style[i][0],style=style[i][2],bold=style[i][1])]
			else:
				line=[MyText(self,self.list[i],fs),MyText(self,"NA",fs,style=wx.ALIGN_LEFT,bold=bold)]
			self.text.append(line)
			hsizers.append(wx.BoxSizer(wx.HORIZONTAL))
			hsizers[i].Add(self.text[i][0],1,wx.ALL,5)
			hsizers[i].Add(self.text[i][1],1,wx.ALIGN_LEFT|wx.ALL,5)
			self.bsizer.Add(hsizers[i],1,wx.ALL|wx.EXPAND,5)
		self.sizer.Add(self.bsizer,0,wx.ALL,2)
	def UpdateStatus(self,list=[],colours=None,field=None,text=None,colour=None,label=None):    #kald med [["label","value"],.....] eller field=.. etc....
		self.list=list
		if colours!=None:
			paint=True
		else:
			paint=False
		for i in range(0,len(self.list)):
			if isinstance(self.list[i],list) and len(self.list[i])==2:
				self.text[i][0].SetLabel(self.list[i][0])
				self.text[i][1].SetLabel(self.list[i][1])
			else:
				self.text[i][1].SetLabel(self.list[i])
			if paint and colours.has_key(i):
				self.text[i][1].SetBackgroundColour(colours[i])
		if field!=None:
			if text!=None:
				self.text[field][1].SetLabel(text)
			if colour!=None:
				self.text[field][1].SetBackgroundColour(colour)
		if label!=None:
			self.box.SetLabel(label)
		self.SetSizerAndFit(self.sizer)
	def Clear(self):
		global BGCOLOR
		for i in range(0,self.N):
			self.text[i][1].SetLabel("NA")
			self.text[i][1].SetBackgroundColour(BGCOLOR)
		self.SetSizerAndFit(self.sizer)	
		
#A status box, where number og columns can be specified
class StatusBox2(wx.Panel):   
	def __init__(self, parent,list=[],fontsize=12,bold=False,label="Status",colsize=None,minlengths=[],bold_list=[]):
		self.parent=parent
		self.list=list
		self.minlengths=minlengths+(len(list)-len(minlengths))*[2]  #append a lot of 2's
		wx.Panel.__init__(self, self.parent)
		fs=fontsize
		self.N=len(self.list)
		self.cols=1
		self.colsize=self.N
		self.col_tl=[]
		if colsize!=None:
			Nc=colsize
			if Nc<self.N:
				self.colsize=Nc
				self.cols=self.N/Nc
				self.rem=self.N % Nc
				if self.rem>0:
					self.cols+=1
		self.box=wx.StaticBox(self,label=label)
		self.box.SetFont(DefaultFont(fs))
		self.text=[]
		self.bsizer=wx.StaticBoxSizer(self.box)
		self.gridsizer=wx.FlexGridSizer(self.colsize,self.cols*2,10,10)
		self.sizer=wx.BoxSizer()
		n=0
		for j in range(0,self.cols):
			i=0
			maxtext=0
			while n<self.N and i<self.colsize:
				maxtext=max(len(self.list[n]),maxtext)
				this_is_bold=bold or (n in bold_list) #not used right now
				line=[MyText(self,self.list[n],fs),MyText(self,"",fs)]
				hsizer=wx.BoxSizer(wx.HORIZONTAL)
				self.text.append(line)
				line[0].SetFont(DefaultLogFont(fontsize,True))
				line[1].SetFont(DefaultLogFont(fontsize))
				self.gridsizer.Add(line[0],1,wx.ALL|wx.EXPAND|wx.CENTER,5)
				self.gridsizer.Add(line[1],2,wx.ALL|wx.EXPAND|wx.CENTER,5)
				i+=1
				n+=1
			self.col_tl.append(maxtext)
		self.bsizer.Add(self.gridsizer,1,wx.ALL,5)
		self.sizer.Add(self.bsizer,0,wx.ALL,5)
		
	def UpdateStatus(self,inputlist=[],states=None,colours=None,field=None,text=None,label=None,colour=None):    #Hmmm, vist lettere med default vaerdier!!
		if states!=None: #dette overruler alt andet!
			for i in range(0,len(states)):
				if states[i]:
					self.text[i][1].SetLabel("OK")
					self.text[i][1].SetBackgroundColour("green")
					#self.text[i][0].SetBackgroundColour("green")
				else:
					self.text[i][1].SetLabel("ERR")
					self.text[i][1].SetBackgroundColour("red")
					#self.text[i][0].SetBackgroundColour("red")
				for text in self.text[i]:
					text.Refresh()
		else: 
			if field is None:
				if len(inputlist)==0:
					inputlist=["NA"]*self.N
				input_range=range(len(inputlist))
				field=0
			else: #well then field should be valid!
				inputlist=[text]
				input_range=[field]
				if colour!=None:
					colours={field:colour}
			if colours!=None:
				paint=True
			else:
				paint=False
			for i in input_range:
				input=inputlist[i-field]
				if isinstance(input,list) and len(input)==2:
					self.text[i][0].SetLabel(input[0])
					text_label=input[1]
				else:
					text_label=input
				if text_label is None:
					text_label="NA"
				col_nr=int(i/self.colsize)
				textl=self.col_tl[col_nr]
				#extra_space=max(0,textl-len(self.list[i]))
				#more_space=max(0,self.minlengths[i]-extra_space-len(text_label))
				extra_space=0
				more_space=0
				self.text[i][1].SetLabel("%*s%s%*s"%(extra_space,"",text_label,more_space,""))
				if paint and colours.has_key(i):
					if colours[i] is None:
						col=self.parent.GetBackgroundColour()
					else:
						col=colours[i]
					#self.text[i][0].SetBackgroundColour(col)
					self.text[i][1].SetBackgroundColour(col)
					for text in self.text[i]:
						text.Refresh()
		if label!=None:
			self.box.SetLabel(label)
		self.SetSizerAndFit(self.sizer)
	def Clear(self):
		bgcol=self.parent.GetBackgroundColour()
		for i in range(0,self.N):
			col_nr=int(i/self.colsize)
			textl=self.col_tl[col_nr]
			#extra_space=max(0,textl-len(self.list[i]))
			#more_space=max(0,self.minlengths[i]-extra_space-2)
			extra_space=0
			more_space=0
			self.text[i][1].SetLabel("%*s%s%*s"%(extra_space,"","NA",more_space,""))
			self.text[i][1].SetBackgroundColour(bgcol)
			#self.text[i][0].SetBackgroundColour(bgcol)
			for text in self.text[i]:
				text.Refresh()
		self.SetSizerAndFit(self.sizer)



class CombiBox(StatusBox):
	def  __init__(self, *args,**kwargs):
		StatusBox.__init__(self,*args,**kwargs)
		if kwargs.has_key("buttons"):
			bnames=kwargs["buttons"]
			self.buttons=[]
			line=wx.StaticLine(self,style=wx.LI_HORIZONTAL,size=(120,-1))
			self.bsizer.Add(line,1,wx.CENTER|wx.EXPAND,20)
			for b in bnames:
				knap=MyButton(self,b,12)
				self.buttons.append(knap)
				self.bsizer.Add(knap,0,wx.ALIGN_CENTER|wx.ALL|wx.EXPAND,10)

#Inventory box, should be called with a list of lists (the columns) of text items (= inventory)  - to display.
#Nb. redefined since earlier MTL versions. Not pretty.....
class InventoryBox(wx.Panel):
	def  __init__(self,parent,inventory=[], label="Inventory",fontsize=12):
		wx.Window.__init__(self,parent)
		self.fs=fontsize
		self.label=label
		self.container=wx.Panel(self)
		self.box=wx.StaticBox(self.container,label=label)
		self.box.SetFont(wx.Font(fontsize,wx.SWISS,wx.NORMAL,wx.NORMAL))
		self.field=[]
		self.vsizer=[]
		self.bsizer=wx.StaticBoxSizer(self.box,wx.HORIZONTAL)
		i=0
		for col in inventory:
			self.vsizer.append(wx.BoxSizer(wx.VERTICAL))
			self.field.append([])
			for text in col:
				field=MyText(self.container,text,self.fs,style=wx.ALIGN_CENTER)
				self.vsizer[i].Add(field,0,wx.ALL,5)
				self.field[i].append(field)
			self.bsizer.Add(self.vsizer[i])
			i+=1
		self.sizer=wx.BoxSizer()
		self.container.sizer=wx.BoxSizer()
		self.sizer=wx.BoxSizer()
		self.container.sizer.Add(self.bsizer)
		self.container.SetSizerAndFit(self.container.sizer)
		self.sizer.Add(self.container)
		self.SetSizer(self.sizer)
	def Update(self,inventory=[],label=None,field=None,text=""): #field is two-tuple... Not very elegant
		if field!=None:
			i=field[0]
			j=field[1]
			self.fields[j][i].SetLabel(text)
		else:
			self.container.Destroy()
			self.container=wx.Panel(self)
			self.box=wx.StaticBox(self.container,label=self.label)
			self.box.SetFont(wx.Font(self.fs,wx.SWISS,wx.NORMAL,wx.NORMAL))
			self.field=[]
			self.vsizer=[]
			self.bsizer=wx.StaticBoxSizer(self.box,wx.HORIZONTAL)
			i=0
			for col in inventory:
				self.vsizer.append(wx.BoxSizer(wx.VERTICAL))
				self.field.append([])
				for text in col:
					field=MyText(self.container,text,self.fs,style=wx.ALIGN_CENTER)
					self.vsizer[i].Add(field,0,wx.ALL,5)
					self.field[i].append(field)
				self.bsizer.Add(self.vsizer[i])
				i+=1
		if label!=None:
			self.box.SetLabel(label)
		self.container.sizer=wx.BoxSizer()
		self.container.sizer.Add(self.bsizer)
		self.container.SetSizerAndFit(self.container.sizer)
		self.sizer.Add(self.container)
		self.SetSizer(self.sizer)
#-----------------------------------------------------------------------------------------------------#
#--------Message and simple user input dialogs based wx.Dialog---------------------------------#
#----------------------------------------------------------------------------------------------------#

#A kind of lazy implementation of returning a status code by just storing it in the dialog and not dealing with wx'ids
class OneButtonDialog(wx.Dialog):
	def __init__(self,parent,title="",buttonsize=12,buttonlabel="OK"):
		wx.Dialog.__init__(self,parent,title=title)
		self.OK=False
		self.button=MyButton(self,buttonlabel,buttonsize)
		self.button.Bind(wx.EVT_BUTTON,self.OnOK)
		self.sizer=wx.BoxSizer(wx.VERTICAL) #base sizer of dialog
		self.sizer.Add(self.button,0,wx.ALL|wx.ALIGN_LEFT,10)
		self.Center()
	def OnOK(self,event):
		self.OK=True
		self.Close()
	def InsertObject(self,window,proportion=1,style=wx.EXPAND|wx.ALL,border=5):
		self.sizer.Insert(0,window,proportion,style,border)
#A kind of lazy implementation of returning a status code.... by just storing it in the dialog.
class TwoButtonDialog(wx.Dialog):
	def __init__(self,parent,title="",buttonsize=12,buttonlabels=["OK","CANCEL"]):
		wx.Dialog.__init__(self,parent,title=title)
		self.OK=False
		self.Cancel=False
		buttonpanel=ButtonsBelow(self,buttonsize,buttonlabels)
		buttonpanel.button1.Bind(wx.EVT_BUTTON,self.OnOK)
		buttonpanel.button2.Bind(wx.EVT_BUTTON,self.OnCancel)
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(buttonpanel,0,wx.ALL)
		self.Center()
		buttonpanel.button1.SetFocus()
	def OnCancel(self,event):
		self.Cancel=True
		self.Close()
	def OnOK(self,event):
		self.OK=True
		self.Close()
	def InsertObject(self,window,proportion=1,style=wx.EXPAND|wx.ALL,border=5):
		self.sizer.Insert(0,window,proportion,style,border) #remember to layout sizer afterwards!
	def WasCancelled(self):
		return self.Cancel
	def WasOK(self):
		return self.OK
		
class MyMessageDialog(OneButtonDialog):
	def __init__(self,parent,title="",msg="",fontsize=12):
		OneButtonDialog.__init__(self,parent,title=title,buttonsize=fontsize-1)
		text=MyText(self,msg,fontsize)
		text.SetFont(DefaultLogFont(fontsize))
		self.SetBackgroundColour(wx.WHITE)
		self.InsertObject(text,0,wx.ALL,15)
		self.SetSizerAndFit(self.sizer)

class MyLongMessageDialog(OneButtonDialog):
	def __init__(self,parent,title="",msg="",fontsize=12,size=(600,-1)):
		OneButtonDialog.__init__(self,parent,title=title,buttonsize=fontsize-1)
		text=wx.TextCtrl(self,value=msg,style=wx.TE_MULTILINE|wx.TE_READONLY,size=size)
		text.SetFont(wx.Font(fontsize,wx.MODERN,wx.NORMAL,wx.NORMAL))
		self.InsertObject(text,1,border=15)
		self.SetSizerAndFit(self.sizer)

class OKdialog(TwoButtonDialog):
	def __init__(self,parent,title="",msg="",fontsize=12,buttonlabels=["OK","FORTYD"]):
		TwoButtonDialog.__init__(self,parent,title=title,buttonlabels=buttonlabels,buttonsize=fontsize-1)
		text=MyText(self,msg,fontsize)
		self.InsertObject(text,0,wx.ALL,15)
		self.SetSizerAndFit(self.sizer)
	
class LongOKdialog(TwoButtonDialog):
	def __init__(self,parent,title="",msg1="",msg2="",msg3="",fontsize=12,buttonlabels=["OK","FORTYD"]):
		TwoButtonDialog.__init__(self,parent,title=title,buttonlabels=buttonlabels,buttonsize=fontsize-1)
		text1=MyText(self,msg1,fontsize)
		text2=wx.TextCtrl(self,value=msg2,size=(650,-1),style=wx.TE_MULTILINE|wx.TE_READONLY)
		text2.SetFont(DefaultFont(fontsize))
		text3=MyText(self,msg3,fontsize)
		self.InsertObject(text3,0,wx.ALL,5)
		self.InsertObject(text2,1,wx.ALL|wx.EXPAND,5)
		self.InsertObject(text1,0,wx.ALL,10)
		self.SetSizerAndFit(self.sizer)
	
#class JaNejDialog(OKdialog): #not needed anymore

class MyMultiChoiceDialog(TwoButtonDialog):
	def __init__(self,parent,title="",msg="",choices=[],fontsize=12):
		self.choices=choices
		TwoButtonDialog.__init__(self,parent,title=title,buttonsize=fontsize-1)
		text=MyText(self,msg,fontsize)
		self.lb=wx.CheckListBox(self,choices=choices,size=(300,-1))
		self.InsertObject(self.lb,1,wx.ALL,10)
		self.InsertObject(text,0,wx.ALL,10)
		self.SetSizerAndFit(self.sizer)
	def GetSelections(self):
		choices=[]
		for i in range(0,len(self.choices)): #there is a shortcut to this, I'm sure :-)
			if self.lb.IsChecked(i):
				choices.append(i)
		return choices
	def GetStrings(self):
		choices=[]
		for i in range(0,len(self.choices)):
			if self.lb.IsChecked(i):
				choices.append(self.choices[i])
		return choices

class MySingleChoiceDialog(TwoButtonDialog):
	def __init__(self,parent,title,msg="",choices=[],fontsize=12):
		self.choices=choices
		TwoButtonDialog.__init__(self,parent,title=title)
		text=MyText(self,msg,fontsize)
		self.lb=wx.ListBox(self,choices=choices,size=(300,-1),style=wx.LB_SINGLE)
		self.lb.SetSelection(0)
		self.InsertObject(self.lb,1,wx.ALL,10)
		self.InsertObject(text,0,wx.ALL,10)
		self.lb.SetSelection(0)
		self.SetSizerAndFit(self.sizer)
	def GetSelection(self):
		sel=self.lb.GetSelections()
		if len(sel)==1:
			return self.lb.GetSelections()[0]
		else:
			return -1
	def GetString(self):
		return self.choices[self.lb.GetSelections()[0]]
		
		
#-----------------------------------------------------------#
#-----------Classes for user input--------------#
#----------------------------------------------------------#


#Base class, sets up fields for entering text and/or numbers. Uses MyTextField and MyNum 
class EditFields(wx.Panel):
	def __init__(self,parent,textlabels=[],textvalues=[],numlabels=[],numvalues=[],bounds=[],textsize=200,fontsize=12,style='vertical',numsize=80):
		fs=fontsize
		wx.Panel.__init__(self,parent)
		if style=='horizontal':
			self.sizer=wx.BoxSizer(wx.HORIZONTAL)
		else:
			self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.field=[]
		for label in textlabels:
			sizer=wx.BoxSizer(wx.HORIZONTAL)
			text=MyText(self,label,fs)
			field=MyTextField(self,size=(textsize,-1)) 
			self.field.append(field)
			if style=='vertical':
				sizer.Add(text,1,wx.ALL|wx.ALIGN_LEFT,5)
				sizer.Add(field,1,wx.ALL|wx.ALIGN_RIGHT,5)
			else:
				sizer.Add(text,0,wx.ALL|wx.CENTER,10)
				sizer.Add(field,1,wx.ALL,10)
			self.sizer.Add(sizer,1,wx.ALL|wx.ALIGN_RIGHT|wx.EXPAND,5)
		for i in range(0,len(self.field)-1): #Navigation
			self.field[i].next=self.field[i+1]
		i=0
		for value in textvalues:
			self.field[i].SetValue(value)
			i+=1
		i=0
		self.numfield=[]
		for label in numlabels:
			sizer=wx.BoxSizer(wx.HORIZONTAL)
			text=MyText(self,label,12)
			field=MyNum(self,bounds[i][0],bounds[i][1],size=(numsize,-1)) 
			self.numfield.append(field)
			if style=='vertical':
				sizer.Add(text,1,wx.ALL|wx.ALIGN_LEFT,5) 
				sizer.Add(field,1,wx.ALL|wx.ALIGN_RIGHT,5)
			else:
				sizer.Add(text,0,wx.ALL|wx.CENTER,10)
				sizer.Add(field,1,wx.ALL,10)
			self.sizer.Add(sizer,1,wx.ALL|wx.ALIGN_RIGHT|wx.EXPAND,5)
			i+=1
		i=0
		for value in numvalues:
			self.numfield[i].SetValue(str(value))
			i+=1
		#setup key browsing	
		for i in range(0,len(self.field)-1):
			self.field[i].SetNext(self.field[i+1])
			self.field[i+1].SetPrev(self.field[i])
		if len(self.numfield)>0 and len(self.field)>0:
			self.field[0].SetPrev(self.numfield[-1])
			self.field[-1].SetNext(self.numfield[0])
			self.numfield[0].SetPrev(self.field[-1])
		elif len(self.field)>1:
			self.field[-1].SetNext(self.field[0])
			self.field[0].SetPrev(self.field[-1])
		elif len(self.numfield)>1:
			self.numfield[-1].SetNext(self.numfield[0])
			self.numfield[0].SetPrev(self.numfield[-1])
		for i in range(0,len(self.numfield)-1):
			self.numfield[i].SetNext(self.numfield[i+1])
			self.numfield[i+1].SetPrev(self.numfield[i])
		self.SetSizer(self.sizer)
	def Validate(self):
		t=True
		for field in self.field:
			t=t & field.Validate()
		for field in self.numfield:
			t=t & field.Validate()
		return t
	def DefineNextItem(self,window):
		if len(self.numfield)>0:
			self.numfield[-1].SetNext(window)
		elif len(self.field)>0:
			self.field[-1].SetNext(window)
	def DefinePrevItem(self,window):
		if len(self.field)>0:
			self.field[0].SetPrev(window)
		elif len(self.numfield)>0:
			self.numfield[0].SetPrev(window)
	def RegisterKeyHandler(self,fct,field=None):
		if field!=None:
			self.numfield[field].RegisterKeyHandler(fct)
		else:
			for field in self.numfield:
				field.RegisterKeyHandler(fct)
	def GetTextValues(self,field=None):
		if field!=None:
			return self.field[field].GetValue().strip()
		vals=[]
		for field in self.field:
			vals.append(field.GetValue().strip())
		return vals
	def GetNumValues(self,field=None): #returns string types - must typecast later...
		if field!=None:
			return self.field[field].GetMyValue().strip()
		vals=[]
		for field in self.numfield:
			vals.append(field.GetMyValue())
		return vals
		
class InputDialog(wx.Dialog):
	def __init__(self,parent,title="",textlabels=[],textvalues=[],numlabels=[],numvalues=[],bounds=[],pedantic=False,buttonlabels=["OK","AFBRYD"]):
		self.pedantic=pedantic
		wx.Dialog.__init__(self,parent,title=title)
		self.OK=False
		self.fields=EditFields(self,textlabels,textvalues,numlabels,numvalues,bounds)
		self.buttons=ButtonsBelow(self,buttonlabels=buttonlabels)
		self.buttons.button1.Bind(wx.EVT_BUTTON,self.OnOk)
		self.buttons.button2.Bind(wx.EVT_BUTTON,self.OnCancel)
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.fields,0,wx.ALL,5)
		self.sizer.Add(self.buttons,0,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)
		self.fields.DefineNextItem(self.buttons.button1)
		self.fields.RegisterKeyHandler(self.KeyHandler)
	def KeyHandler(self,keycode):
		if keycode==wx.WXK_ESCAPE:
			self.Close()
			
	def OnOk(self,event):
		if self.fields.Validate():
			self.OK=True
		if not self.pedantic or self.OK:
			self.Close()
	def WasOK(self):
		return self.OK
	def OnCancel(self,event):
		self.Close()
	def GetTextValues(self,field=None):
		return self.fields.GetTextValues(field=field)
	def GetNumValues(self,field=None):
		return self.fields.GetNumValues(field=field)
		



#----------------------------------------------------------------#
#-----Utility classes for setting up text, buttons, etc.----#
#---------------------------------------------------------------#
class ButtonBox(wx.Panel):
	def __init__(self, parent,buttons=[],style='horizontal',label="ButtonBox",fontsize=12):
		wx.Panel.__init__(self, parent)
		self.button=[]
		font=wx.Font(fontsize,wx.SWISS,wx.NORMAL,wx.NORMAL)
		self.box=wx.StaticBox(self,label=label)
		self.box.SetFont(font)
		if style=='horizontal':
			style=wx.HORIZONTAL
		else:
			style=wx.VERTICAL
		self.bsizer=wx.StaticBoxSizer(self.box,style)
		self.sizer=wx.BoxSizer()
		for b in buttons:
			button=MyButton(self,b,fontsize)
			self.button.append(button)
			self.bsizer.Add(button,1,wx.ALL|wx.CENTER|wx.EXPAND,5)
		self.sizer.Add(self.bsizer)
		self.SetSizerAndFit(self.sizer)

class ButtonBox2(wx.Panel):
	def __init__(self,parent,buttons,label="Buttons",colsize=2,fontsize=12):
		wx.Panel.__init__(self, parent)
		self.button=[]
		font=wx.Font(fontsize,wx.SWISS,wx.NORMAL,wx.NORMAL)
		self.box=wx.StaticBox(self,label=label)
		self.box.SetFont(font)
		self.boxsizer=wx.StaticBoxSizer(self.box,wx.VERTICAL)
		self.sizer=wx.BoxSizer()
		ncols=len(buttons)/colsize
		ncols+=int((len(buttons))>ncols*colsize)
		self.buttonsizer=wx.FlexGridSizer(colsize,ncols,5,5)
		for b in buttons:
			button=MyButton(self,b,fontsize)
			self.button.append(button)
			self.buttonsizer.Add(button,1,wx.ALL|wx.CENTER|wx.EXPAND,5)
		self.boxsizer.Add(self.buttonsizer)
		self.sizer.Add(self.boxsizer)
		self.SetSizerAndFit(self.sizer)

class ButtonPanel(wx.Panel):
	def __init__(self,parent,buttons=[],size=(550,100),fontsize=12):
		wx.Panel.__init__(self,parent,size=size)
		self.button=[]
		self.sizer=wx.BoxSizer(wx.HORIZONTAL)
		for b in buttons:
			button=MyButton(self,b,fontsize)
			self.button.append(button)
			self.sizer.Add(button,0,wx.ALL|wx.EXPAND,5)
		self.SetSizerAndFit(self.sizer)
	def SetButtonLabel(self,label,i=0):
		self.button[i].SetLabel(label)
		self.button[i].Refresh()
class ButtonsBelow(wx.Panel):
	def __init__(self,parent,size=12,buttonlabels=["ACCEPTER","AFBRYD"]):
		wx.Panel.__init__(self, parent)
		self.button1=MyButton(self,buttonlabels[0],size)
		self.button2=MyButton(self,buttonlabels[1],size)
		self.sizer=wx.BoxSizer(wx.HORIZONTAL)
		self.sizer.Add(self.button1,0,wx.ALL,5)
		self.sizer.Add(self.button2,0,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)

def ButtonAndField(parent,size=12,buttonlabel="hit me!",field=None,style='left',fieldsize=100,text=None):
		if text!=None:
			text=MyText(parent,text,size)
		button=MyButton(parent,buttonlabel,size)
		if style in ['left','right']:
			sizer=wx.BoxSizer(wx.HORIZONTAL)
		else:
			sizer=wx.BoxSizer(wx.VERTICAL)
		if style=='left' or style=='above':
			if text!=None:
				sizer.Add(text,1,wx.ALL|wx.Center|wx.EXPAND,5)
			sizer.Add(button,1,wx.ALL,5)
			if field!=None:
				sizer.Add(field,1,wx.ALL,5)
		else:
			if text!=None:
				sizer.Add(text,1,wx.ALL|wx.Center|wx.EXPAND,5)
			if field!=None:
				sizer.Add(field,1,wx.ALL,5)
			sizer.Add(button,1,wx.ALL,5)
		return button, sizer
		
def FieldWithLabel(parent,field=None,label="",size=12):
	text=MyText(parent,label,size)
	sizer=wx.BoxSizer(wx.HORIZONTAL)
	sizer.Add(text,0,wx.ALL|wx.CENTER,5)
	if field!=None:
		sizer.Add(field,1,wx.ALL|wx.ALIGN_LEFT|wx.CENTER,5)
	
	return sizer

#-----------------------------------------------------------#
#-----Various windows-------------------------------------#
#-----------------------------------------------------------#
class StuffWithBox(wx.Panel):
	def __init__(self,parent,style='horizontal',label="ButtonBox",fontsize=12):
		wx.Panel.__init__(self, parent)
		font=DefaultFont(fontsize)
		self.box=wx.StaticBox(self,label=label)
		self.box.SetFont(font)
		if style=='horizontal':
			style=wx.HORIZONTAL
		else:
			style=wx.VERTICAL
		self.bsizer=wx.StaticBoxSizer(self.box,style)
		self.sizer=wx.BoxSizer()
		self.sizer.Add(self.bsizer)
	def AddStuff(self,stuff):
		self.bsizer.Add(stuff,0,wx.ALL,5)
	def FinishUp(self):
		self.SetSizerAndFit(self.sizer)
		
		
class FileWindow(SecondaryWindow):
	def __init__(self,parent,title,file):
		self.file=file
		SecondaryWindow.__init__(self,parent,title=title)
		self.SetSize((800,600))
		self.text=wx.TextCtrl(self,style=wx.TE_READONLY|wx.TE_MULTILINE)
		self.text.SetFont(wx.Font(12,wx.MODERN,wx.NORMAL,wx.NORMAL))
		self.knap=MyButton(self,"OPDATER",12)
		self.knap.Bind(wx.EVT_BUTTON,self.OnOpdater)
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.sizer.Add(self.text,1,wx.EXPAND)
		self.sizer.Add(self.knap,0,wx.ALL,5)
		self.SetSizer(self.sizer)
		self.sizer.FitInside(self)
		f=open(self.file)
		self.text.SetValue(f.read()) #f will always be returned at same position as on input.
		f.close()
	def OnOpdater(self,event):
		f=open(self.file)
		self.text.SetValue(f.read())
		f.close()

class MyDscDialog(wx.Dialog): #punktbeskrivelsesdialog....
	def __init__(self,parent,title="Punktbeskrivelse",msg="",point="X",image=None,fontsize=12):
		self.point=point
		self.msg=msg
		self.title=title
		wx.Dialog.__init__(self,parent,title=title,pos=(60,100))
		try:
			icon=parent.GetIcon()
		except:
			pass
		else:
			self.SetIcon(icon)
		self.sizer=wx.BoxSizer(wx.VERTICAL)
		self.hsizer1=wx.BoxSizer(wx.VERTICAL)
		self.hsizer2=wx.BoxSizer(wx.HORIZONTAL)
		self.text=wx.TextCtrl(self,value=title+"\n"+msg,size=(400,-1),style=wx.TE_MULTILINE)
		self.text.SetFont(wx.Font(fontsize,wx.MODERN,wx.NORMAL,wx.NORMAL))
		self.hsizer1.Add(self.text,1,wx.EXPAND|wx.ALL,5)
		self.OKbutton=MyButton(self,"LUK",12)
		self.OKbutton.Bind(wx.EVT_BUTTON,self.OnOK)
		self.filebutton=MyButton(self,"GEM BSK",12)
		self.filebutton.Bind(wx.EVT_BUTTON,self.OnSave)
		if image!=None:
			self.image=wx.StaticBitmap(self,wx.ID_ANY,image)
		else:
			self.image=MyText(self,"Kunne ikke finde skitse...",12)
		self.hsizer1.Add(self.image,0,wx.ALL,5)
		self.hsizer2.Add(self.OKbutton,0,wx.ALL,10)
		self.hsizer2.Add(self.filebutton,0,wx.ALL,10)
		self.sizer.Add(self.hsizer1,1,wx.ALL|wx.EXPAND,5)
		self.sizer.Add(self.hsizer2,0,wx.ALL,5)
		self.SetSizerAndFit(self.sizer)
		self.OKbutton.SetFocus()
	def OnSave(self,event):
		name=self.point+".txt"
		f=open(name,"w")
		msg=self.title+"\n"+self.msg
		f.write(msg.encode("utf-8")) #test encoding...
		f.close()
		self.Close()
	def OnOK(self,event):
		self.Close()

	
#-----------------------------------------------------#
#--------------Message Functions------------------#
#----------------------------------------------------#
def ErrorBox(window,msg):
	dlg=MyMessageDialog(window,msg=msg,title="Fejl!")
	dlg.ShowModal()
	dlg.Destroy()

def Message(window,msg,title=u"Bem\u00E6rk:"):
	dlg=MyMessageDialog(window,msg=msg,title=title)
	dlg.ShowModal()
	dlg.Destroy()

def YesNo(window,msg,title=u"Foresp\u00F8rgsel",buttonlabels=["OK","FORTRYD"]):
	dlg=OKdialog(window,title=title,msg=msg,buttonlabels=buttonlabels)
	dlg.ShowModal()
	ok=dlg.WasOK()
	dlg.Destroy()
	return ok
