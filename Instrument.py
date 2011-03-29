import serial
import threading
import wx
import  wx.lib.newevent
import time
(LogEvent,EVT_LOG) = wx.lib.newevent.NewEvent()
(DataEvent,EVT_DATA) = wx.lib.newevent.NewEvent()
#Last update 26.3.2010
class DummyThread(object):
	def __init__(self):
		self.alive=False
	def Kill(self):
		pass
	def isAlive(self):
		return False
#Base Instrument Class, should be subclassed to MTLinstrument and MGLinstrument
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
	def IsReading(self):
		return self.isreading
	def Kill(self):
		self.thread.Kill()
		self.SetReadState(False)
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
		
