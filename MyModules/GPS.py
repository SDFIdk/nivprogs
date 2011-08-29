import threading
import sys
import time
from math import *
import  wx.lib.newevent
(GPSEvent,EVT_GPS) = wx.lib.newevent.NewEvent()
(KillEvent,EVT_KILL_GPS) = wx.lib.newevent.NewEvent()
(LogEvent,EVT_LOG) = wx.lib.newevent.NewEvent()
if len(sys.argv)>1 and sys.argv[1]=="gps_test":
	import gps_test as serial
else:
	import serial
#UPDATE GPS AND LL2UTM to handle W lon. --FIXED!
class DummyThread():
	def __init__(self):
		self.alive=False
	def isAlive(self):
		return False
	def kill(self):
		pass
	def DetachWindow(self):
		pass
	def join(self):
		pass
	def DefineParent(self,*args):
		pass
	def DefineWindow(self,*args):
		pass
	def TestConnection(self):
		return False
	def start(self):
		pass
class DummyWindow():
	def SetStatusText(self):
		pass
	def Plot(self,*args):
		pass
	def Close(self):
		pass
	def IsShown(self):
		return False
	def Show(self,*args):
		pass
	def IsShownOnScreen(self):
		return False
	def SetMemory(*args):
		pass
class GpsThread(threading.Thread):
	def __init__(self,parent=None,port=5,baud=4800,zone=32):
		threading.Thread.__init__(self) # init the thread
		self.x=-999
		self.y=-999
		self.parent=parent # a parent wx.window which listens to non-plotting events
		self.dop=1000
		self.OK=0
		self.speed=0
		self.time=time.clock()
		self.doptime=self.time
		self.xplot=0
		self.yplot=0
		self.zone=zone #UTM-zone boer saettes op et sted i initialisering
		self.sent=False
		self.plotwin=DummyWindow() #a window which listens to plotting events
		self.port=port
		self.baud=baud
		self.alive=False
		self.connectionstatus=False
	def TestConnection(self):
		self.connectionstatus=False
		try:
			s=serial.Serial(self.port,self.baud)
			s.close()
		except:
			pass
		else:
			self.connectionstatus=True
		return self.connectionstatus
	def GetConnectionStatus(self):
		return self.connectionstatus
	def GetPos(self):
		return self.x,self.y,self.dop
	def DefineWindow(self,win):
		self.plotwin=win
	def DetachWindow(self):
		self.plotwin=DummyWindow()
	def DefineParent(self,win): # a parent wx.window which listens to non-plotting events
		self.parent=win
	def Log(self,text):
		if self.parent is not None:
			event=LogEvent(text=text)
			wx.PostEvent(self.parent,event)
	def kill(self):
		self.alive=False
		try:
			self.gps.close()
		except:
			pass
	def run(self):
		try:
			self.gps=serial.Serial(self.port,self.baud,timeout=30)   #timeout,saa laeser den ikke en linie for evigt....
		except Exception, msg:
			#self.Log(str(msg))
			self.Log(u"Kunne ikke starte GPS-enheden!")
			event=KillEvent(kill=True)
			wx.PostEvent(self.parent,event)
			return  #stop here...
		self.alive=True
		self.Log("GPS-enheden er startet.")
		line="A B C D E F G H J K"  #hvis gps'en ikke virker til start
		while self.alive:
			time.sleep(0.12)
			code="X"
			while code!="$GPGGA" and self.alive:
				try:
					self.gps.flush()
					line=self.gps.readline()
				except:    					#Saa maa den vaere fjernet og skal draebes!
					if self.alive: #saa er den ikke lukket udefra
						self.Log(u"Kunne ikke f\u00E5 data fra GPS-enheden!\nPr\u00F8v evt. tilsutning igen via menupunkt.")
						if self.parent is not None:
							event=KillEvent(kill=True)
							wx.PostEvent(self.parent,event)
					return
				else:
					if len(line)>0 and not line.isspace():
						line=line.split(",")
						code=line[0]
			if self.alive:
				try:
					Y=line[2]
					X=line[4]
					dop=line[8]
					OK=line[6]
					EW=line[5]
					NS=line[3]
					Y=float(Y)
					X=float(X)
					OK=int(OK)
					dop=float(dop)
				except:
					self.OK=False
				else:
					if OK and self.alive:
						if EW=="W":
							X=-X
						if NS=="S":
							Y=-Y
						x,y=ll2utm(Y,X,self.zone,1) #type 1 5412.1212 =54 deg +12.1212'
						self.OK=True
						self.dop=dop
						t=time.clock()
						self.speed=sqrt((x-self.x)**2+(y-self.y)**2)/(t-self.time)*3.6
						self.time=t
						self.x=x
						self.y=y
						if (t-self.doptime)>3 and self.plotwin.IsShownOnScreen():  #kun hvert 3. sekund
							evt=GPSEvent(plot=False,dop=self.dop,x=self.x,y=self.y,speed=self.speed)
							wx.PostEvent(self.plotwin,evt)
							self.doptime=t
						if (abs(self.xplot-self.x)>0.1 or abs(self.yplot-self.y)>0.1): #doplot
							if self.alive and self.plotwin.IsShownOnScreen() and self.dop<7: #parameter kan varieres her...
								self.xplot=self.x
								self.yplot=self.y
								evt=GPSEvent(plot=True,dop=self.dop,x=self.x,y=self.y,speed=self.speed) 
								wx.PostEvent(self.plotwin,evt)
						if self.dop>7 and not self.sent:
							self.Log(u"GPS-dop %.1f, venter p\u00E5 bedre GPS-data..." %self.dop)
							self.sent=True
					else:
						self.OK=False
						if not self.sent and self.alive:
							try:
								self.Log("GPS-data endnu ikke OK. Find et sted med bedre sigtbarhed.")
							except:
								pass
							self.sent=True

def ll2utm(dlat,dlon,izone=32,type=1):  #type 1: 5423.1232=54 deg +23.1232'
	if type==1:
		Y=dlat/100
		X=dlon/100
		if Y>=0:
			Yf=floor(Y)
		else:
			Yf=ceil(Y)
		Yd=Y-Yf
		Y=Yf+Yd*100/60
		if X>=0:
			Xf=floor(X)
		else:
			Xf=ceil(X)
		Xd=X-Xf
		X=Xf+Xd*100/60
		dlat=Y
		dlon=X
	r=6378137.0
	#e2=0.006705972
	e2=0.00669437999014132   #Ifoelge Thomas!!
	k0=0.9996
	dlon0=(izone-1)*6-180+3
	radln0=dlon0*pi/180
	radlat=dlat*pi/180
	radln=dlon*pi/180
	e21=e2/(1-e2)
	n=r/sqrt(1-e2*(sin(radlat))**2)
	t=(tan(radlat))**2
	c=e21*(cos(radlat)**2)
	a=(cos(radlat))*((dlon-dlon0)*pi/180)
	s2=sin(2*radlat)
	s4=sin(4*radlat)
	s6=sin(6*radlat)
	e4=e2**2
	e6=e2*e4
	# simplified calculation for Clarke ellipsoid
	# m=(111132.0894*dlat)-(16216.94*s2)+(17.21*s4)-(.02*s6)
	# full expression for other ellipsoids
	terma=(1-e2/4-3*e4/64-5*e6/256)     
	termb=(3*e2/8+3*e4/32+45*e6/1024)
	termc=(15*e4/256+45*e6/1024)
	termd=(35*e6/3072)
	m=r*(terma*radlat-termb*s2+termc*s4-termd*s6)
	m0=0
	a2=a**2
	a3=a**3
	a4=a2**2
	a5=a3*a2
	a6=a3**2
	x=k0*n*(a+(1-t+c)*a3/6+(5-18*t+t**2+72*c-58*e21)*a5/120)
	term1=n*tan(radlat) 
	term2=(5-t+9*c+4*c**2)*a4/24
	term3=(61-58*t+t**2+600*c-330*e21)*a6/720
	y=k0*((m-m0)+term1*(a2/2+term2+term3))	
	# add 500000. to x to complete "false eastings"
	x=x+500000.0
	return x,y
