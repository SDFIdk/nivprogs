import wx
import  wx.lib.newevent
import numpy as np
(MapSizeEvent,EVT_MAPSIZE) = wx.lib.newevent.NewEvent()
(DistEvent,EVT_DISTANCE) = wx.lib.newevent.NewEvent()
#Last bugfix: 11.03.2010
#Last update 06.05.2010: changed Array2Screen a bit, now returns floats - seems to work with the dc-methods. Added vector drawing
#Note: somehow screen updating of the MapPanel object only woks, when methods from this class are called - not when doing external hacks via various DC's.
class MapPanel(wx.Panel):
	def __init__(self,parent,size=(0,0),xul=0,yul=0,pixelsize=1.0,fixed=False):
		self.parent=parent
		wx.Panel.__init__(self,parent,size=size)
		self.canvas=wx.Window(self,size=size,style=wx.WANTS_CHARS) #so that key events can be generated
		self.sizer=wx.BoxSizer()
		if fixed:
			self.sizer.Add(self.canvas,0,wx.ALL)
		else:
			self.sizer.Add(self.canvas,1,wx.EXPAND)
		self.SetSizer(self.sizer)
		self.Fit()
		self.mapsize=(0,0)  #for lsizing events
		self.size=size
		self.pixelsize=pixelsize
		self.startpixel=pixelsize
		self.lastgpspos=(180000,180000) #dummys
		self.lastgpssize=100
		self.zoomfactors=[1]
		self.SetCoordinates(xul,yul)
		self.canvas.Bind(wx.EVT_PAINT,self.OnPaint)
		#self.canvas.Bind(wx.EVT_LEFT_DOWN, self.OnMouseLeftDown)
		self.canvas.Bind(wx.EVT_LEFT_UP, self.OnMouseLeftUp)
		self.canvas.Bind(wx.EVT_MOTION, self.OnMotion)
		self.canvas.Bind(wx.EVT_ENTER_WINDOW,self.OnEnterWindow)
		self.Buffer=wx.Bitmap(size[0],size[1])        # Ændret til py39
		self.canvas.Bind(wx.EVT_SIZE,self.OnSize)
		self._hasDragged=False
		self._dlineEnabled=False
		self._gpsonscreen=False #flag to tell DrawGPS whether to delete 'old' gps... NOT USED ANYMORE
		self.printerscale=1.0 #for thickening up things when printing
		self.viewpixelsize=self.pixelsize #for resetting after printing
		self.lastdistance=0
		self.pointsize=5
		self.isgeographic=False #Flag to set when going to geographic coords NOT USED YET
		self.unit="m"
	def SetGeographicCS(self):
		self.isgeographic=True
		self.unit="deg"
	def SetProjectedCS(self):
		self.isgeographic=False
		self.unit="m"
	def OnSize(self,event):
		size=self.canvas.GetSize()
		self.size=(size[0],size[1])
		self.SetCoordinates(self.x1,self.y2)
		if abs(size[0]-self.mapsize[0])>60 or abs(size[1]-self.mapsize[1])>60: #find a reasonable rate of updating map....
			event=MapSizeEvent(do=True)
			wx.PostEvent(self.parent,event)
	def SetCanvasSize(self,size):
		self.size=size
		self.canvas.SetSize(size)
		self.Buffer=wx.Bitmap(size[0],size[1])    #py39
		self.SetCoordinates(self.x1,self.y2)
	def SetPrintSize(self,size,scale): #used when printing
		self.viewpixelsize=self.pixelsize
		x,y=self.GetCenter()
		self.pixelsize=self.pixelsize/scale
		self.size=size
		self.SetCenter(x,y)
		self.printerscale=scale
	def SetViewSize(self): #reset coords back to where we were before printing
		x,y=self.GetCenter()
		self.size=self.canvas.GetSize()
		self.pixelsize=self.viewpixelsize
		self.SetCenter(x,y)
		self.printerscale=1.0
	def GetPrinterScale(self):
		return self.printerscale
	def GetCanvasSize(self):
		return self.size
	def GetPixelSize(self):
		return self.pixelsize
	def GetBounds(self):
		return self.x1,self.x2,self.y1,self.y2
	def GetMaxRange(self):
		return max(self.x2-self.x1,self.y2-self.y1)
	def GetXRange(self):
		return self.x2-self.x1
	def GetYRange(self):
		return self.y2-self.y1
	def SetPixelSize(self,pixelsize):
		self.pixelsize=pixelsize
		self.zoomfactors=[1]
		self.startpixel=pixelsize
	def SetCoordinates(self,x1,y2):
		self.x1=x1
		self.x2=x1+self.size[0]*self.pixelsize
		self.y1=y2-self.size[1]*self.pixelsize
		self.y2=y2
	def SetBoundary(self,x1,x2,y1,y2):
		self.x1=x1
		self.x2=x2
		self.y1=y1
		self.y2=y2
		self.pixelsize=(x2-x1)/float(self.size[0])
	def SetUpdateRegion(self,x1,x2,y1,y2):
		sc=self.Array2ScreenCoords(np.array([[x1,y2],[x2,y1]]),regionfilter=False)
		self.regionfiltermin=np.min(sc,0)
		self.regionfiltermax=np.max(sc,0)
	def ResetUpdateRegion(self):
		self.regionfiltermin=[0,0]
		self.regionfiltermax=self.size
	def GetCenter(self):
		return self.x1+(self.x2-self.x1)*0.5,self.y1+(self.y2-self.y1)*0.5
	def TestBoundary(self,x,y,f=0.1):
		xr=(self.x2-self.x1)*f
		yr=(self.y2-self.y1)*f
		return self.x2-x<xr or x-self.x1<xr or self.y2-y<yr or y-self.y1<yr
	def GetZoom(self):
		zoom=1
		for f in self.zoomfactors:
			zoom*=f
		return zoom
	def Zoom(self,x,y,factor):
		self.zoomfactors.append(factor)
		zoom=self.GetZoom()
		if abs(zoom-1)<0.01: #we should be back
			self.zoomfactors=[1]
			self.pixelsize=self.startpixel
			#print "resettinmg pixelseix"
		else:
			self.pixelsize*=factor
		x1=x-self.size[0]*0.5*self.pixelsize
		y2=y+self.size[1]*0.5*self.pixelsize
		self.SetCoordinates(x1,y2)
	def SetCenter(self,x,y):
		x1=x-self.size[0]*0.5*self.pixelsize
		y2=y+self.size[1]*0.5*self.pixelsize
		self.SetCoordinates(x1,y2)
	def UserCoords(self,x,y):  #screen to user coords, screen coords has y increasing downwards gpoing from 0 to ysize-1
		x=self.x1+(x+0.5)*self.pixelsize   #we assume click in pixelcenters!
		y=self.y2-(y+0.5)*self.pixelsize
		return x,y
	def ScreenCoords(self,x,y):
		x=(x-self.x1)/self.pixelsize  
		y=(self.y2-y)/self.pixelsize
		return x,y
	def Array2ScreenCoords(self,xy,onlyonscreen=False,regionfilter=False): #accepts numpy (n,2)-array
		SC=(xy-[self.x1,self.y2])*[1.0/self.pixelsize,-1.0/self.pixelsize] #or via a map cmd.
		if not onlyonscreen:
			return SC
		else:
			if regionfilter:
				maxlimit=self.regionfiltermax
				minlimit=self.regionfiltermin
			else:
				maxlimit=self.size
				minlimit=0
			mask=np.logical_and(SC<=maxlimit,SC>=minlimit)
			indices=np.where(np.logical_and(mask[:,0],mask[:,1]))[0]
			if indices.shape[0]>0:
				return SC[indices,:],indices
			else:
				return np.empty((0,2)),[]
	def DrawMap(self,bitmap=None,dc=None,region=None):  #xulc, yulc usually defined by mapname
		if region is not None:
			screencoords=self.Array2ScreenCoords(np.array([[region.x1,region.y1],[region.x2,region.y2]]))
			x1,y1=np.min(screencoords,axis=0)
			x2,y2=np.max(screencoords,axis=0)
			cw=x2-x1
			ch=y2-y1 #order switch
		if bitmap is not None: #only call with a valid bitmap in print mode
			w=bitmap.GetWidth()
			h=bitmap.GetHeight()
			self.mapsize=(w,h)
			if dc is None:
				if region is None:
					self.Buffer=wx.Bitmap(w,h)         #Ændret py39
					dc=wx.MemoryDC(self.Buffer)
				else:
					dc=wx.MemoryDC(self.Buffer)
					dc.SetClippingRegion(x1,y1,cw,ch)
			dc.DrawBitmap(bitmap,0,0)
			
		else:
			w,h=self.size
			if region is None:
				raster=np.ones(shape=(h,w,3),dtype=np.uint8)*255
				self.Buffer=wx.Bitmap.FromBuffer(w,h,raster)    ## Ændret til py39
			else:
				dc=wx.MemoryDC(self.Buffer)
				dc.SetClippingRegion(x1,y1,cw,ch)
				raster=np.ones(shape=(int(ch),int(cw),3),dtype=np.uint8)*255 #Ændret py39 int() tilføjet
				raster=wx.Bitmap.FromBuffer(cw,ch,raster)       ## Ændret til py39
				dc.DrawBitmap(raster,x1,y1)
		if region is None or (x1<self.lastgpspos[0]<x2 and y1<self.lastgpspos[1]<y2):
			self._gpsonscreen=False
	def SetBestPointSize(self):
		bestsize=min(max(np.ceil(4.5/self.pixelsize),2),6)
		self.pointsize=max(bestsize*self.printerscale,1)
	def DrawPolygon(self,polygon,dc=None,region=None):
		if dc is None:
			dc=wx.MemoryDC(self.Buffer)
		if region is not None:
			screencoords=self.Array2ScreenCoords(np.array([[region.x1,region.y1],[region.x2,region.y2]]))
			x1,y1=np.min(screencoords,axis=0)
			x2,y2=np.max(screencoords,axis=0)
			cw=x2-x1
			ch=y2-y1 #order switch
			dc.SetClippingRegion(x1,y1,cw,ch)
		dc.SetPen(wx.Pen(wx.BLACK,width=3*self.printerscale))
		#dc.SetBrush(wx.Brush(wx.WHITE,wx.TRANSPARENT))
		sp=self.Array2ScreenCoords(polygon)
		#dc.DrawPolygon(zip(sp[:,0].tolist(),sp[:,1].tolist()))
		dc.DrawLines(sp)
	def DrawPoints(self,coords,qual=None,labels=[],testlabeldensity=False,textcolor="black",font=None,pointcolor=wx.RED,pointsize=10,usebest=True,maxdensity=0.0005,connect=False,regionfilter=False,dc=None,region=None,shortnames=False): #coords is numpy array...
		if not usebest:
			self.pointsize=pointsize*self.printerscale
		else:
			self.SetBestPointSize()
		sc,ind=self.Array2ScreenCoords(coords,onlyonscreen=True,regionfilter=regionfilter)
		labels=np.array(labels)
		if labels.shape[0]>0: #labels must be empty or of same length as coords
			labels=labels[ind]
		if dc is None:
			dc=wx.MemoryDC(self.Buffer)
		if region is not None:
			screencoords=self.Array2ScreenCoords(np.array([[region.x1,region.y1],[region.x2,region.y2]]))
			x1,y1=np.min(screencoords,axis=0)
			x2,y2=np.max(screencoords,axis=0)
			cw=x2-x1
			ch=y2-y1 #order switch
			dc.SetClippingRegion(x1,y1,cw,ch)
		dc.SetPen(wx.Pen(wx.BLACK))
		if qual is not None: # do not connect such db-points
			qual=qual[ind]
			ind=(qual!=1)
			if ind.any():
				dc.SetBrush(wx.Brush( wx.RED, wx.SOLID ))
				pts=sc[ind]
				for i in range(0,pts.shape[0]):
					dc.DrawCircle(pts[i,0],pts[i,1],self.pointsize)
			ind=(qual==1)
			if ind.any():
				dc.SetBrush(wx.Brush( wx.GREEN, wx.SOLID ))
				pts=sc[ind]
				for i in range(0,pts.shape[0]):
					dc.DrawCircle(pts[i,0],pts[i,1],self.pointsize)
		else:
			dc.SetBrush(wx.Brush( pointcolor, wx.SOLID ))
			pts=sc
			if connect:
				self.DrawLines(pts[0:-1],pts[1:],dc=dc,coords='screen')
				dc.SetPen(wx.Pen(wx.BLACK))
			for i in range(0,pts.shape[0]):
				dc.DrawCircle(pts[i,0],pts[i,1],self.pointsize)
				
		if labels.shape[0]>0:
			do=True
			#The density calculations is *flawed* - labels might be drawn at larger scales because new pts. enter the screen
			#some kind of mean should be calculated...
			if testlabeldensity and sc.shape[0]>10:
				mini=np.min(sc,0)
				maxi=np.max(sc,0)
				box=maxi-mini
				xrange,yrange=box
				density=float(sc.shape[0])/(xrange*yrange)*self.printerscale
				if density>maxdensity:
					do=False
			if do:
				if font is not None:
					dc.SetFont(font)
				dc.SetTextForeground(textcolor)
				for i in range(0,labels.shape[0]):
					if shortnames and len(labels[i])>8:
						text=labels[i][-5:]
					else:
						text=labels[i]
					dc.DrawText(text,sc[i,0]+self.pointsize-2,sc[i,1]+self.pointsize-2)
	def DrawPositions(self,coords,dc=None):
		self.SetBestPointSize()
		sc,ind=self.Array2ScreenCoords(coords,onlyonscreen=True)
		if dc is None:
			dc=wx.MemoryDC(self.Buffer)
		dc.SetPen(wx.Pen(wx.BLACK))
		dc.SetBrush(wx.Brush( "orange", wx.SOLID ))
		for i in range(0,sc.shape[0]): #could be don via map cmd?
			dc.DrawCircle(sc[i,0],sc[i,1],self.pointsize)
	def DrawLines(self,fromp,top,color=wx.BLUE,width=2,coords='user',dc=None):
		if dc is None:
			dc=wx.MemoryDC(self.Buffer)
		dc.SetPen(wx.Pen(color,width=width*self.printerscale))
		if coords=='user':
			sc1=self.Array2ScreenCoords(fromp)
			sc2=self.Array2ScreenCoords(top)
		else:
			sc1=fromp
			sc2=top
		for i in range(sc1.shape[0]):
			dc.DrawLine(sc1[i,0],sc1[i,1],sc2[i,0],sc2[i,1])
	def DrawManyLines(self,coords,color=wx.BLUE,width=1,dc=None,region=None):
		if dc is None:
			dc=wx.MemoryDC(self.Buffer)
		if region is not None:
			screencoords=self.Array2ScreenCoords(np.array([[region.x1,region.y1],[region.x2,region.y2]]))
			x1,y1=np.min(screencoords,axis=0)
			x2,y2=np.max(screencoords,axis=0)
			cw=x2-x1
			ch=y2-y1 #order switch
			dc.SetClippingRegion(x1,y1,cw,ch)
		dc.SetPen(wx.Pen(color,width=width*self.printerscale))
		sc=self.Array2ScreenCoords(coords)
		dc.DrawLines(sc)
		
	def DrawVectors(self,fromp,top,color=wx.BLUE,width=2,drawlabels=False,labels=None,dc=None):
		from_screen=self.Array2ScreenCoords(fromp)
		to_screen=self.Array2ScreenCoords(top)
		diff=to_screen-from_screen
		N_screen=Norm(diff).reshape((diff.shape[0],1))
		N_diff=Normalize(diff)
		#tip1=from_screen+0.85*diff+0.15*diffhat
		#tip2=from_screen+0.85*diff-0.15*diffhat
		tipsizes=np.maximum(np.minimum(N_screen*0.5,15*self.printerscale),1*self.printerscale)
		tip1=RotateVectors(N_diff,np.pi/180*145)*tipsizes
		tip2=RotateVectors(N_diff,-np.pi/180*145)*tipsizes
		self.DrawLines(from_screen,to_screen,color=color,width=width,coords='screen',dc=dc)
		self.DrawLines(to_screen,to_screen+tip1,color=color,width=width,coords='screen',dc=dc)
		self.DrawLines(to_screen,to_screen+tip2,color=color,width=width,coords='screen',dc=dc)
		if drawlabels and labels is not None:
			shift=(np.sign(diff[:,1])).reshape((diff.shape[0],1))*15*(np.fliplr(N_diff)*[1,-1])
			self.DrawLabels(from_screen+diff*0.5+shift,labels,color=color,dc=dc)
	def DrawVectorScale(self,scale=10,font=None,dc=None,getextent=False):
		x,y=self.GetCanvasSize()
		l=80.0*self.printerscale #60 pixels
		L=l/scale
		if L>0.5:
			unit="m"
			factor=1.0
			shoulddivide=0.1
		elif L>0.01:
			unit="cm"
			factor=100.0
			shoulddivide=1.0
		else:
			unit="mm"
			factor=1000.0
			shoulddivide=1.0
		L=np.ceil((l*factor/scale)/shoulddivide)*shoulddivide
		l=L*scale/factor
		label="%.2f %s" %(L,unit)
		x1=x*0.08
		x2=x1+l  
		ylen=10*self.printerscale
		yoff=y*0.08
		y1=y-yoff-ylen
		y3=y-ylen*0.5-yoff
		y2=y-yoff
		if not getextent:
			if dc is None:
				dc=wx.MemoryDC(self.Buffer)
			dc.SetPen(wx.Pen(wx.BLUE,2*self.printerscale))
			dc.DrawLine(x1,y1,x1,y2) #left line
			dc.DrawLine(x1,y3,x2,y3) #middle
			dc.DrawLine(x2,y1,x2,y2) #right
			dc.SetFont(font)
			dc.SetTextForeground(wx.BLUE)
			x,y=dc.GetTextExtent(label)
			dc.DrawText(label,x1,y1-y)
		else:
			dc=wx.MemoryDC(self.Buffer)
			x,y=dc.GetTextExtent(label)
			#Return a region buffered with *5* pixels#
			ux1,uy2=self.UserCoords(x1-5,y1-y-5)
			ux2,uy1=self.UserCoords(max(x1+x,x2)+5,y2+5)
			return ux1,ux2,uy1,uy2
	
		
	def DrawMapScale(self,font=None,dc=None,getextent=False):
		x,y=self.GetCanvasSize()
		pix=self.GetPixelSize()
		l=80*self.printerscale
		L=pix*l # 60 pixels is best bar!
		if L>10000:
			factor=0.001
			shoulddivide=5
			format="%.0f km"
		elif L>5000: 
			factor=0.001
			shoulddivide=0.5
			format="%.1f km"
		elif L>200:
			factor=1.0
			shoulddivide=100.0
			format="%.0f m"
		elif L>10:
			factor=1.0
			shoulddivide=5
			format="%.0f m"
		else:
			factor=1.0
			shoulddivide=1.0
			format="%.0f m"
		L=np.ceil((L*factor)/shoulddivide)*shoulddivide
		l=(L/factor)/pix
		label=format%(L)
		xoff=x*0.08
		ylen=10*self.printerscale
		x1=x-xoff-l
		x2=x-xoff 
		yoff=y*0.08
		y1=y-yoff-ylen
		y3=y-ylen*0.5-yoff
		y2=y-yoff
		if not getextent:
			if dc is None:
				dc=wx.MemoryDC(self.Buffer)
			dc.SetPen(wx.Pen(wx.RED,2*self.printerscale))
			dc.SetFont(font)
			dc.SetTextForeground(wx.RED)
			if (x2-x1)>0:
				dc.DrawLine(x1,y1,x1,y2) #left line
				dc.DrawLine(x1,y3,x2,y3) #middle
				dc.DrawLine(x2,y1,x2,y2) #right
				x,y=dc.GetTextExtent(label)
				dc.DrawText(label,x1,y1-y)
			else:
				dc.DrawText("Error - reset map",100,100)
		else:
			dc=wx.MemoryDC(self.Buffer)
			x,y=dc.GetTextExtent(label)
			#Return a region buffered with *5* pixels#
			ux1,uy2=self.UserCoords(x1-5,y1-y-5)
			ux2,uy1=self.UserCoords(max(x1+x,x2)+5,y2+5)
			return ux1,ux2,uy1,uy2
	def DrawSpecial(self,coords,color="blue",pointsize=None): #not used in printing
		if pointsize=="best":
			self.SetBestPointSize()
		else:
			pointsize=self.pointsize
		dc=wx.MemoryDC(self.Buffer)
		#dc.BeginDrawing()    #Ændret fra py39
		dc.SetPen(wx.Pen(wx.BLACK))
		dc.SetBrush(wx.Brush(color,style= wx.SOLID ))
		sc=self.Array2ScreenCoords(coords)
		xmin=min(self.size[0],np.min(sc,0)[0])
		ymin=min(self.size[1],np.min(sc,0)[1])
		xmax,ymax=np.max(sc,0)
		for i in range(0,np.size(coords,0)):
			dc.DrawCircle(sc[i,0],sc[i,1],self.pointsize)
		#dc.EndDrawing()    #ændret fra py39
		xmin=max(0,xmin-2*self.pointsize)
		xgap=xmax-xmin+2*self.pointsize
		ymin=max(0,ymin-2*self.pointsize)
		ygap=ymax-ymin+2*self.pointsize
		return xmin,ymin,xgap,ygap
	def DrawTemporaryPoint(self,coords,color="blue",pointsize=None): #not used in printing
		if pointsize=="best":
			self.SetBestPointSize()
		else:
			pointsize=self.pointsize
		dc=wx.ClientDC(self.canvas)
		#dc.BeginDrawing()
		dc.SetPen(wx.Pen(wx.BLACK))
		dc.SetBrush(wx.Brush(color,style= wx.SOLID ))
		sc=self.Array2ScreenCoords(coords)
		xmin=min(self.size[0],np.min(sc,0)[0])
		ymin=min(self.size[1],np.min(sc,0)[1])
		xmax,ymax=np.max(sc,0)
		for i in range(0,np.size(coords,0)):
			dc.DrawCircle(sc[i,0],sc[i,1],self.pointsize)
		#dc.EndDrawing()
		xmin=max(0,xmin-2*self.pointsize)
		xgap=xmax-xmin+2*self.pointsize
		ymin=max(0,ymin-2*self.pointsize)
		ygap=ymax-ymin+2*self.pointsize
		return xmin,ymin,xgap,ygap
	def DrawGPS(self,x,y): #not used in printing
		xs,ys=self.ScreenCoords(x,y)
		sx,sy=self.size
		if self._gpsonscreen: #0<=xl<=x and 0<=yl<=y:
			self._EraseGPS()
		xtop,ytop,bestsize=self.GetBestGPSPosAndSize(xs,ys)
		self._DrawGPS(xtop,ytop,bestsize) #draw new
		self._gpsonscreen=True
		self.lastgpspos=(xtop,ytop) 
		self.lastgpssize=bestsize+1 #buffer slightly
	def _DrawGPS(self,xtop,ytop,size): #not used in printing
		#Draws/erases  gps rectangle
		self.gpsbg=wx.Bitmap(size,size)      #py39
		bufdc=wx.MemoryDC(self.Buffer)
		newdc=wx.MemoryDC(self.gpsbg)
		newdc.Blit(0,0,size,size,bufdc,xtop,ytop)
		#bufdc.BeginDrawing()  #udkomm. fra py3
		bufdc.SetPen(wx.Pen(wx.BLACK))
		bufdc.SetBrush(wx.Brush( wx.BLUE, wx.SOLID ))
		bufdc.DrawRectangle(xtop,ytop,size,size)
		#bufdc.EndDrawing()  # UDKOMM. fra py3
	def _EraseGPS(self):
		bufdc=wx.MemoryDC(self.Buffer)
		bg=wx.MemoryDC(self.gpsbg)
		bufdc.Blit(self.lastgpspos[0],self.lastgpspos[1],self.lastgpssize,self.lastgpssize,bg,0,0)
	def GetBestGPSPosAndSize(self,x,y):
		bestsize=max(3.0/self.pixelsize,6) #hmm vi er vel ca. 3 m store...
		xtop=x-bestsize*0.5
		ytop=y-bestsize*0.5
		return xtop,ytop,bestsize
	def GetGPSClippingRegion(self,x,y): #user coordinates
		xs,ys=self.ScreenCoords(x,y)
		x,y,s=self.GetBestGPSPosAndSize(xs,ys)
		#print x,y,s
		minx=min(x,self.lastgpspos[0])
		maxx=max(x,self.lastgpspos[0])
		miny=min(y,self.lastgpspos[1])
		maxy=max(y,self.lastgpspos[1])
		s=max(self.lastgpssize,s)
		xtop=minx-20
		ytop=miny-20
		w=maxx-minx+s+20
		h=maxy-miny+s+20
		#print xtop,xtop+w,ytop,ytop+h
		#print self.lastgpspos
		#print "last:", self.lastgpspos[0],self.lastgpspos[1]
		return xtop,ytop,w,h
	def DrawText(self,text,x=None,y=None,xoff=0,yoff=0,color="red",fontsize=12,centertext=False,font=None,dc=None,region=None):
		lines=text.splitlines()
		if len(lines)==0:
			return
		if centertext and x==None:
			textextent=len(lines[0])*fontsize
			x=(self.size[0]-textextent)*0.5
			y=(self.size[1]*0.5)
		elif x!=None and y!=None:
			x,y=self.ScreenCoords(x,y)
			if centertext:
				textextent=len(lines[0])*fontsize
				x-=int(textextent*0.5)
				y+=int(fontsize*0.5)
		if font is None:
			font=wx.Font(fontsize,wx.SWISS,wx.NORMAL,wx.BOLD)
		if dc is None:
			dc=wx.MemoryDC(self.Buffer)
		if region is not None:
			screencoords=self.Array2ScreenCoords(np.array([[region.x1,region.y1],[region.x2,region.y2]]))
			x1,y1=np.min(screencoords,axis=0)
			x2,y2=np.max(screencoords,axis=0)
			cw=x2-x1
			ch=y2-y1 #order switch
			dc.SetClippingRegion(x1,y1,cw,ch)
		dc.SetFont(font)
		dc.SetTextForeground(color)
		for i in range(0,len(lines)):
			dc.DrawText(lines[i],x+xoff,y+yoff+i*13)
	def DrawLabels(self,sc,labels,xoff=0,yoff=0,font=None,color=wx.BLUE,fontsize=10,dc=None):
		if font is None:
			font=wx.Font(fontsize*self.printerscale,wx.SWISS,wx.NORMAL,wx.BOLD)
		if dc is None:
			dc=wx.MemoryDC(self.Buffer)
		dc.SetFont(font)
		dc.SetTextForeground(color)
		for i in range(0,sc.shape[0]):
			dc.DrawText(labels[i],sc[i,0],sc[i,1])
	def DrawBoundingBox(self,width=2,color=wx.BLUE,dc=None):
		if dc is None:
			dc=wx.MemoryDC(self.Buffer)
		dc.SetPen(wx.Pen(color,max(width*self.printerscale,1)))
		x,y=self.GetCanvasSize()
		yoff=0 #(2+width)*self.printerscale
		xoff=0 #(2+width)*self.printerscale
		dc.DrawLine(xoff,yoff,x-xoff,yoff) #top
		dc.DrawLine(xoff,y-yoff,x-xoff,y-yoff) #botttom
		dc.DrawLine(xoff,yoff,xoff,y-yoff) #left
		dc.DrawLine(x-xoff,yoff,x-xoff,y-yoff)# right
	def DrawSignature(self,text,font=None,color=wx.BLUE,dc=None):
		if dc is None:
			dc=wx.MemoryDC(self.Buffer)
		x,y=self.GetCanvasSize()
		yoff=0 #(2+width)*self.printerscale
		xoff=0 #(2+width)*self.printerscale
		if font is not None:
			dc.SetFont(font)
		dc.SetTextForeground(color)
		xt,yt=dc.GetTextExtent(text)
		dc.DrawText(text,10*self.printerscale,y)
	def DrawScreen(self,xmin=None,ymin=None,xgap=0,ygap=0):
		dc=wx.ClientDC(self.canvas)
		if xmin is not None and ymin is not None:
			dc.SetClippingRegion(xmin,ymin,xgap,ygap)
		#dc.BeginDrawing()     # Udkommenteret py39
		dc.Clear()
		dc.DrawBitmap(self.Buffer,0,0)
		#dc.EndDrawing()       ## Udkommenteret py39
	def OnPaint(self, event):
		# All that is needed here is to draw the buffer to screen
		#self._gpsonscreen=False
		dc = wx.BufferedPaintDC(self.canvas, self.Buffer)
	def OnMotion(self, event):
		if self._dlineEnabled and event.LeftIsDown():
			if self._hasDragged:
				self._drawRubberBand(self._dpoint1, self._dpoint2) # remove old
			else:
				self._hasDragged= True
				self._dpoint1=event.GetPosition()
			self._dpoint2 = event.GetPosition()
			self._drawRubberBand(self._dpoint1, self._dpoint2) # add new
			x1,y1=self.UserCoords(self._dpoint1[0],self._dpoint1[1])
			x2,y2=self.UserCoords(self._dpoint2[0],self._dpoint2[1])
			dist=np.sqrt((x2-x1)**2+(y2-y1)**2)
			if abs(dist-self.lastdistance)>self.pixelsize: #fixed bug here
				event=DistEvent(distance=dist,stop=False)
				wx.PostEvent(self.parent,event)
			self.lastdistance=dist
	def OnMouseLeftDown(self,event):
		#self._dpoint1= event.GetPosition()
		event.Skip()
	def OnMouseLeftUp(self, event):
		if self._dlineEnabled:
			if self._hasDragged == True:
				self._drawRubberBand(self._dpoint1, self._dpoint2) # remove old
				self._dpoint2=event.GetPosition()
				self._hasDragged = False  # reset flag
				#event=DistEvent(stop=True)
				#wx.PostEvent(self.parent,event)
		event.Skip()
	def OnEnterWindow(self,event):  #delete old on enter window if left is up!
		if not event.LeftIsDown():
			if self._dlineEnabled:
				if self._hasDragged == True:
					self._drawRubberBand(self._dpoint1, self._dpoint2) # remove old
					#self._dpoint2=event.GetPosition()
					self._hasDragged = False  # reset flag
					#event=DistEvent(stop=True)
					#wx.PostEvent(self.parent,event)
		event.Skip()
	def EnableDistance(self):
		self._dlineEnabled=True
		self._hasDragged=False
		self._dpoint1=(0,0)
	def DisableDistance(self):
		self._dlineEnabled=False
	def _drawRubberBand(self, corner1, corner2):
		"""Draws/erases rect box from corner1 to corner2"""
		ptx=min(corner1[0],corner2[0])
		pty=min(corner1[1],corner2[1])
		rectWidth=abs(ptx-max(corner1[0],corner2[0]))
		rectHeight=abs(pty-max(corner1[1],corner2[1]))
		# draw rectangle
		dc = wx.ClientDC( self.canvas )
		#dc.BeginDrawing()                 
		dc.SetPen(wx.Pen(colour=wx.GREEN,width=2,style=wx.SHORT_DASH))
		dc.SetBrush(wx.Brush( wx.WHITE, wx.TRANSPARENT ) )
		dc.SetLogicalFunction(wx.INVERT)
		#dc.DrawRectangle( ptx,pty, rectWidth,rectHeight)
		dc.DrawLine(corner1[0],corner1[1],corner2[0],corner2[1])
		dc.SetLogicalFunction(wx.COPY)
		#dc.EndDrawing()
	def SaveFile(self,fileName):
		# File name has required extension
		fType = fileName[-3:].strip()
		if fType == "bmp":
		    tp= wx.BITMAP_TYPE_BMP       # Save a Windows bitmap file.
		elif fType == "jpg":
		    tp= wx.BITMAP_TYPE_JPEG      # Save a JPG file.
		else:
		    tp= wx.BITMAP_TYPE_PNG       # Save a PNG file.
		# Save Bitmap
		self.Buffer.SaveFile(fileName,tp)

def RotateVectors(XY,theta):
	R=np.array([[np.cos(theta),np.sin(theta)],[-np.sin(theta),np.cos(theta)]])
	return np.dot(XY,R)

def Normalize(XY):
	N=np.sqrt((XY**2).sum(axis=1)).reshape((XY.shape[0],1))
	N[N==0]=1
	return XY/N

def Norm(XY):
	return np.sqrt((XY**2).sum(axis=1))

class Container(wx.Frame):
	def __init__(self,parent,size):
		wx.Frame.__init__(self,parent)
		self.map=MapPanel(self,size)
		self.sizer=wx.BoxSizer()
		self.sizer.Add(self.map,0,wx.CENTER,5)
		self.SetSizerAndFit(self.sizer)
		self.Show()
	