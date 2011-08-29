basestring="""
http://kortforsyningen.kms.dk/service?
servicename=servicename
&REQUEST=GetMap
&VERSION=1.1.1
&SRS=EPSG:25832
&BBOX=xmin,ymin,xmax,ymax
&WIDTH=WIDTH
&HEIGHT=HEIGHT
&STYLES=
&LAYERS=
&ignoreillegallayers=TRUE
&FORMAT=image/png
&BGCOLOR=0xffffff
&TRANSPARENT=FALSE
&EXCEPTIONS=application/vnd.ogc.se_inimage
&login=login
&password=password
"""
GetCap="""
http://kortforsyningen.kms.dk/service?request=GetCapabilities
&version=1.1.0
&login=kms1
&password=adgang
&servicename=servicename
&service=WMS
"""
import threading
import wx
import urllib
import cStringIO
import wx.lib.newevent
(WMSMapEvent,EVT_WMS) = wx.lib.newevent.NewEvent()
wx.InitAllImageHandlers()
class WMSservice(object):
	def __init__(self,screenname="",servicename="",layers=[],imagetype="png"):
		self.screenname=screenname
		self.servicename=servicename
		self.layers=layers
		self.imagetype=imagetype
def SetLogin(login="",pword=""):
	global basestring
	basestring=basestring.replace("=login","=%s" %login)
	basestring=basestring.replace("=password","=%s" %pword)
class WMSthread(threading.Thread):
	def __init__(self,window,x1,x2,y1,y2,width,height,service):
		threading.Thread.__init__(self)
		self.x1=x1
		self.x2=x2
		self.y1=y1
		self.y2=y2
		self.width=width
		self.height=height
		self.window=window
		url=basestring.replace("xmin",str(x1)).replace("ymin",str(y1)).replace("xmax",str(x2)).replace("ymax",str(y2))
		url=url.replace("WIDTH=WIDTH","WIDTH=%i" %width).replace("HEIGHT=HEIGHT","HEIGHT=%i" %height)
		url=url.replace("=servicename","=%s" %service.servicename)
		url.replace("png",service.imagetype)
		if len(service.layers)>0:
			lstring=""
			for layer in service.layers:
				lstring+=layer+","
			lstring=lstring[0:-1] #delete last ','
			url=url.replace("&LAYERS=","&LAYERS=%s" %lstring)
		url=url.replace("\n","") #slet newlines
		self.url=url
		self.start() #starter sig selv
	def kill(self):
		self.alive=False
	def run(self):
		self.alive=True
		self.OK=True
		msg=""
		self.im=""
		try:
			f=urllib.urlopen(self.url)
			inf=str(f.info())
		except:
			self.alive=False
			self.OK=False
			msg=u"Kunne ikke \u00E5bne wms-forbindelse."
		else:
			if inf.find("image")==-1:
				self.OK=False
				msg="Kunne ikke genkende url som billede."
			else:
				chunk="juhu girls"
				while self.alive and len(chunk)>0:
					try:
						chunk=f.read(2048)
					except:
						self.OK=False
						msg="Fejl under download af kort"
						break
					self.im+=chunk
				try:
					f.close()
				except:
					pass
		self.msg=msg
		if self.alive:
			if self.OK:
				self.im=cStringIO.StringIO(self.im)
				self.im=wx.ImageFromStream(self.im)
			event=WMSMapEvent(OK=self.OK)
			try:
				wx.PostEvent(self.window,event)
			except:
				pass
	def GetMap(self,width,height):
		if not self.OK:
			map=wx.EmptyBitmap(width,height)
			dc=wx.MemoryDC(map)
			dc.SetFont(wx.Font(14,wx.SWISS,wx.NORMAL,wx.NORMAL))
			dc.SetTextForeground("white")
			textextent=14*len(self.msg)
			xpos=(width-textextent)*0.5
			ypos=(height*0.5)
			dc.DrawText(self.msg,xpos,ypos)
			return map,self.OK,0,0,0,0
		else:
			if self.width!=width or self.height!=height: #reskaler hvis skaermstoerrelse er aendret.
				fx=float(width)/self.width
				fy=float(height)/self.height
				if fx>=fy:
					self.im.Rescale(width,int(round(fx*self.height)))
					pixsize=(self.x2-self.x1)/float(width)
				else:
					self.im.Rescale(int(round(self.width*fy)),height)
					pixsize=(self.y2-self.y1)/float(height)
				self.im.Resize((width,height),(0,0))
				self.x2=self.x1+width*pixsize
				self.y1=self.y2-height*pixsize
			return self.im.ConvertToBitmap(),self.OK,self.x1,self.x2,self.y1,self.y2
		
def WMSmap(x1,x2,y1,y2,width,height,servicename="DTK_Skaermkort"):
	url=basstring.replace("xmin",str(x1)).replace("ymin",str(y1)).replace("xmax",str(x2)).replace("ymax",str(y2))
	url=url.replace("WIDTH=WIDTH","WIDTH=%i" %width).replace("HEIGHT=HEIGHT","HEIGHT=%i" %height)
	url=url.replace("=servicename","=%s" %servicename)
	if servicename=="ortofoto":
		url=url+"&LAYERS=Orto_dk"
		url=url.replace("png","jpeg")
		mr=max(x2-x1,y2-y1)
		if mr>4000:
			url=url+"&Jpegquality=30"
		elif mr>2000:
			url=url+"&Jpegquality=40"
		else:
			url=url+"&Jpegquality=80"
	url=url.replace("\n","") #slet newlines
	
	try:
		f=urllib.urlopen(url)
		inf=str(f.info())
		#print inf
		g=f.read()
		f.close()
	except:
		return False, None, u"Kunne ikke \u00E5bne wms-forbindelse"
	if inf.find("image")!=-1:
		g=cStringIO.StringIO(g)
		im=wx.ImageFromStream(g)
		im=im.ConvertToBitmap()
		return True, im, "All OK"
	else:
		return False, None, str(g)
def GetBoundingBox(servicename="DTK_Skaermkort"):
	url=GetCap.replace("=servicename","=%s" %servicename)
	url=url.repace("\n","")
	try:
		f=urllib.urlopen(url)
		inf=str(f.info())
		xmlinfo=f.read()
		f.close()
	except:
		return False, None, None,u"Kunne ikke \u00E5bne wms-forbindelse"
	xmlinfo=str(xmlinfo)
	lookfor='<BoundingBox SRS="EPSG:25832"'  #look for UTM32 info
	i=xmlinfo.find(lookfor)
	if i==-1:
		return False, None, None,u"Kunne ikke finde bbox-information"
	j=xmlinfo.find("\n",i)
	bbox=xmlinfo[i+len(lookfor):j].replace('"',"").replace("/>","").split()  #here's the info
	x2=bbox[0].replace("maxx=","")
	y2=bbox[1].replace("maxy=","")
	x1=bbox[2].replace("minx=","")
	y2=bbox[3].replace("miny=","")
	try:
		x1=float(x1)
		x2=float(x2)
		y1=float(y1)
		y2=float(y2)
	except:
		return False, None, None, u"Kunne ikke konvertere til floats"
	i=xmlinfo.find("Scale hint")
	if i==-1:
		return True, (x1,x2,y1,y2), None, "Bbox OK, scale hint ikke fundet"
	else: #look for scale hint
		return True, (x1,x2,y1,y2), None, "Bbox OK, scale hint ikke fundet"
		
		
	
		
		
	
	
		
	