import threading
import wx
import  wx.lib.newevent
import time
from math import sqrt
import sys
if "fakeMTL" in sys.argv:
	import MyModules.FakeMTLserial as serial
	is_fake=True
else:
	import serial
	is_fake=False
DEBUG="debug" in sys.argv
(LogEvent,EVT_LOG) = wx.lib.newevent.NewEvent()
(DataEvent,EVT_DATA) = wx.lib.newevent.NewEvent()
#Last update 2011-11-30
class DummyThread(object):
	def __init__(self):
		self.alive=False
	def Kill(self):
		pass
	def isAlive(self):
		return False
#Base Instrument Class, should be subclassed to MTLinstrument and MGLinstrument
#Threads created by subclasses should implement a 'Kill' method.....
#TODO: Perhaps set the thread object to a dummy thread after kill or SetReadState(False)
class Instrument(object):
	def __init__(self,name="instrument",port=5,baudrate=1000,type="ost"):
		self.name=name #screen name
		self.port=port #com-port
		self.baudrate=baudrate #baudrate for com-port
		self.type=type #Tech. type of instrument
		self.portstatus=False #flag to show if the com-port is OK.
		self.eventhandler=None #threads should send data here
		self.logwindow=None #where to send log messages
		self.isreading=False
		self.thread=DummyThread()
	def GetName(self):
		return self.name
	def TestPort(self):
		self.portstatus=False
		if self.port<0:
			self.portstatus=True
		else:
			try:
				s=serial.Serial(self.port-1,self.baudrate)
				s.close()
			except:
				pass
			else:
				self.portstatus=True
		return self.portstatus
	def PresentYourself(self,short=False): #could be overridden
		if short:
			return "Instrument: %s,  type: %s." %(self.name,self.type)
		else:
			return "Instrument: %s,  type: %s, com-port: %i" %(self.name,self.type,self.port)
	def GetPort(self):
		return self.port
	def GetPortStatus(self):
		return self.portstatus
	def SetEventHandler(self,win):
		self.eventhandler=win
	def SetLogWindow(self,win):
		self.logwindow=win
	def SetReadState(self,state=False):
		self.isreading=state
	def IsReading(self):  #Perhaps return self.thread.isAlive() instead here, so the user doesn't have to set the state manually!!!!!!
		return self.isreading
	def Kill(self):
		self.thread.Kill()
		self.SetReadState(False)


#------------------------MTL instruments defined here----------------------------------------#

class MTLinstrument(Instrument): #well really a Topcon instrument for now....
	def __init__(self,name="",addconst=0.0,axisconst=0.0,port=5,baudrate=4800,type="TOPCON",id=0):
		Instrument.__init__(self,name,port,baudrate,type)
		self.axisconst=axisconst
		self.addconst=addconst
		self.id=id #needed to distinguish events called from diff. instruments...
		#Stuff needed to get the typical index error from the instrument#
		self.index_max=30
		self.index_min=-33
		self.index_mean=0
		self.index_std=0
		self.index_var=0
		self.nmeas=0
	def PresentYourself(self,short=False): #could be overridden
		if short:
			return "Instrument: %s, konstanter: %.5f m %.4f m, type: %s." %(self.name,self.addconst,self.axisconst,self.type)
		else:
			return "Instrument: %s,  konstanter: %.5f m %.4f m, type: %s, com-port: %i" %(self.name,self.addconst,self.axisconst,self.type,self.port)
	def ReadData(self,expect=None): #is really common, at least, to instruments communicating via (virtual) com-port.....
		try:
			con=serial.Serial(self.port-1,self.baudrate,timeout=800,parity=serial.PARITY_EVEN,bytesize=7,stopbits=2)  #nb, 1 eller 2??
			if (is_fake and expect=="?"):
				con.returnDistances()
			
		except Exception,msg: #well this is easiest since the eventhandler should be listening...
			event=DataEvent(id=self.id,value=['E',(u'Instrumentets com port (port %i) kunne ikke \u00E5bnes'%self.port)+"\n"+repr(msg) ]) #for at foelge samme standard som traaden bruger, se nedenfor
			wx.PostEvent(self.eventhandler,event)
		else:
			self.portstatus=True  #flag to signal that the we can connect to instrument.
			self.thread=TopconThread(con,self.eventhandler,self.logwindow,self.id,self.name)
			self.SetReadState(True)
	def AddIndexError(self,index_error): #*Usually* index error should be in seconds...
		self.nmeas+=1
		self.index_mean=self.index_mean*(self.nmeas-1)/(self.nmeas)+index_error/self.nmeas
		#not exact - but should converge#
		self.index_var=(self.index_var*(self.nmeas-1)+(index_error-self.index_mean)**2)/self.nmeas
		self.index_std=sqrt(self.index_var)
		if self.nmeas>3:
			self.index_max=self.index_mean+1.8*self.index_std
			self.index_min=self.index_max-1.8*self.index_std
			if DEBUG:
				print "ierr-limits:",self.index_min,self.index_max
	def GetIndexBounds(self):
		return self.index_min,self.index_max


# This thread more or less copied from earlier versions of the program.
# Sends events to logwindow with a .text attr and to 'eventhandler' window which handles data.
#  DataEvents has an id attr (to distinguish instruments) and a value attr, which is a list: [code,data]
# The code can be: 
# ? - means the data is a distance reading
# < - means the data is an angle reading
# E - which means that an error occured. 'Data' is then an error msg.
class TopconThread(threading.Thread):
	def __init__(self,connection,eventhandler,logwin,id,name):
		threading.Thread.__init__(self) # init the thread
		self.connection=connection
		self.eventhandler=eventhandler
		self.logwindow=logwin
		self.id=id
		self.name=name
		self.accept_code=chr(6) + "006" + chr(3) + chr(13) + chr(10) #magisk accept-kode, som skal sendes tilbage til instrumentet
		self.start()
	def Kill(self):
		self.alive=False
		try:
			self.connection.close()
		except:
			pass
		text=u"L\u00E6sning fra %s blev afbrudt." %self.name
		event=LogEvent(text=text)
		wx.PostEvent(self.logwindow,event)
	def run(self):
		self.alive=True
		try:
			self.connection.flush()  #er denne raekkefoelge optimal?? Maaske laese lineien to gange??
			s=self.connection.readline()
			#Write accept code 4 times#
			for j in range(0,4):
				self.connection.write(self.accept_code)
			self.connection.close()
		except Exception,msg:
			try:
				self.connection.close()
			except:
				pass
			msg=u"Fejl ved l\u00E6sning fra instrument:\n"+str(msg)
			self.alive=False
			evt=DataEvent(id=self.id,value=["E",msg])
			wx.PostEvent(self.eventhandler,evt)
		else:
			if self.alive: #betyder at eventhandler-vinduet skulle eksistere endnu!
				send=False
				if s[0]=="?": #afstand
					val=s[2:s.find("m")].lstrip("0") #fjern nuller foran og foerste 2 tegn
					val=val[0:-3]+"."+val[-3:] #indsaet ., vi antager 3 decimaler
					val=["?",val]
					send=True
				elif s[0]=="<": #vinkel
					val=s[1:s.find("+")].lstrip("0") #fjern foerste tegn og nuller og behold frem til +
					val=val[0:-4]+"."+val[-4:] #indsaet ., vi antager 4 decimaler
					val=["<",val]
					send=True
			try:
				self.connection.close()
			except:
				pass
			if self.alive and send:
				time.sleep(0.5) #do we really need this?? Tries to avoid comm. errors from long distance analog signals....
				evt=DataEvent(id=self.id,value=val)
				wx.PostEvent(self.eventhandler,evt)
					
			


#------------------------MGL instruments defined here----------------------------------------#
class DINI(Instrument):
	def __init__(self,name="",port=5,baudrate=9600,type="DINI11"):
		Instrument.__init__(self,name,port,baudrate,type)
		#Differentiate between new and old DINI's. New ones end a measurement with a newline
		self.readline=False
		if type.lower()=="dini003": #new instruments ends data-string with 'backslash n'
			self.readline=True
	def PresentYourself(self,short=False): #could be overridden
		if short:
			return "Instrument: %s,  type: %s." %(self.name,self.type)
		else:
			return "Instrument: %s,  type: %s, com-port: %i, newline: %s" %(self.name,self.type,self.port,self.readline)
	def ReadData(self):
		try:
			con=serial.Serial(self.port-1,self.baudrate,stopbits=1,bytesize=8,parity=serial.PARITY_NONE)
		except: #well this is easiest since the eventhandler should be listening...
			event=DataEvent(OK=False,hascon=False)
			wx.PostEvent(self.eventhandler,event)
		else:
			self.portstatus=True  #flag to signal that the we can connect to instrument.
			self.thread=DiniThread(con,self.eventhandler,self.logwindow,readline=self.readline)
			self.SetReadState(True)

#DINI-data format implemented here --- could be separated out in a function so that the thread-setup can be used for other insts.
class DiniThread(threading.Thread):
	def __init__(self,connection,eventhandler,logwin,readline=False):
		threading.Thread.__init__(self)
		self.connection=connection
		self.eventhandler=eventhandler
		self.logwindow=logwin
		self.readline=readline
		self.start()
	def run(self):
		self.alive=True
		#kill old data lingering in the sweet morning air
		self.connection.flush() 
		try:
			if self.readline:
				data=self.connection.readline()
			else:
				data=self.connection.read(78)
		except Exception, msg:
			if self.logwindow is not None:
				if self.alive:
					text=u"Kunne ikke l\u00E6se data fra instrumentet!\n"+repr(msg)	
				else:
					text=u"L\u00E6sning fra instrumentet afbrudt."
				event=LogEvent(text=text)
				wx.PostEvent(self.logwindow,event)
				self.alive=False
		else:
			OK=False
			sd=0
			dist=0
			dh=0
			nread=0
			temp=None
			if len(data)>0 and len(data.split())>6:
				try:
					d=data.split()
					sd=float(d[-1])
					dist=float(d[-3])
					dh=float(d[-5])
					nread=int(d[-7])
				except:
					OK=False
				else:
					OK=True
					if len(d)>8 and d[-8]=="C":
						try:
							temp=float(d[-9])
						except:
							pass
		try:
			self.connection.close()
		except:
			pass
		if self.alive and self.eventhandler is not None:
			event=DataEvent(OK=OK,string=data,dist=dist,dh=dh,sd=sd,nread=nread,temp=temp,hascon=True)
			wx.PostEvent(self.eventhandler,event)
	def Kill(self):
		self.alive=False
		try:
			self.connection.close()
		except:
			pass
		
