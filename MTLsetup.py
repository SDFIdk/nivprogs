#Core module which handles all the essential math for the MTL program
#simlk, jan. 2012
#fixed the old 'basis bug', 2012-01-04

import numpy as np
from math import cos, sin, tan, atan, pi
import sys
if "debug" in sys.argv:
	DEBUG=True
else:
	DEBUG=False
RADIUS=6385000.0   #Jordradius.

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
	def __init__(self,rows,cols,zrow,zcol): #zrow, zcol indicates where z-field subarray starts
		self.zcol=zcol #column nr. from where columns are z-distance fields (e.g. zcol=1: mrk,pos1,pos2 or  zcol=0: pos1,pos2)
		self.zrow=zrow #etc.
		self.Initialize(rows,cols) #Then we can call this method from outside....
		self.zformat_translator=StandardZdistanceTranslator #a function which translates input format to radians if format is OK,
	def Initialize(self,rows,cols):
		self.raw_data=np.zeros((rows,cols),dtype="<S20")
		self.real_data=np.zeros((rows,cols))
		self.index_errors=np.zeros((rows-self.zrow,)) #reflects only current "sats" -relative to start row for z-fields!!!
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
		val=val.replace(",",".")
		self.raw_data[row,col]=val
		#translate#
		if col>=self.zcol and row>=self.zrow and self.zformat_translator is not None:
			ok,val=self.zformat_translator(val)
		else:
			val=float(val)
		self.real_data[row,col]=val
	def GetIndexError(self,row): #for now always returns index error in seconds....Works rowwise, thus not for the transfer setup...
		ierr=((self.real_data[row,self.zcol]+self.real_data[row,self.zcol+1]-2*np.pi)*0.5)*180.0/np.pi*3600.0
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

class DummyErrs(object):
	dlimit=0.05
	hlimit=0.04
	rlimit=30
	


class MTLTransferSetup(MTLSetup):
	def __init__(self,aim,instrument_consts,err_limits=DummyErrs()):
		MTLSetup.__init__(self,3,2,1,0) #1. row = distance, 2.row pos 1, 3. row pos 2., z-fields start at row 1 =(row 2)
		self.aim=np.array(aim)
		self.instrument_consts=np.array(instrument_consts) #row 0: first inst, row 1: second inst, col 0: add const, col 1: axis const
		self.err_limits=err_limits
		self.InitData()
	def InitData(self):
		self.satser=np.empty((0,2,2),dtype='<S20') #for storing raw data
		self.keep_mask=np.empty((0,),dtype=np.bool) #mask indicating whether to keep or delete a 'sats'
		self.hdiff=None
		self.hdiffs=np.empty((0,2)) #keep h1, h2 for each sats
		self.dist=None
		self.restfejls=np.empty((0,))
		self.restfejl=None
		self.index_errs_store=np.empty((0,2))
	def Clear(self):
		self.Initialize(3,2)
		self.InitData()
	def GetDistance(self):
		#Raw distances are stored in real and raw_data - 'get' methods will apply distance correction#
		#could really be a translator here, but that might be overdoing it!#
		self.dist=self.GetDistances().mean()
		return self.dist
	def GetDistances(self):
		#Raw distances are stored in real and raw_data - 'get' methods will apply distance correction#
		return self.real_data[0]+self.instrument_consts[:,0]
	def DistanceTest(self):
		s1,s2=self.GetDistances()
		diff=abs(s1-s2)
		return diff, diff<self.err_limits.maxdelta_dist*self.dist/100.0
	
	def AddSats(self):
		self.satser=np.vstack((self.satser,np.copy(self.raw_data[None,1:,:]))) #add an axis to raw_data
		self.restfejls=np.append(self.restfejls,self.restfejl)
		self.hdiffs=np.vstack((self.hdiffs,[self.h1,self.h2]))
		self.raw_data[1:,:]=""
		self.real_data[1:,:]=0
		self.validity_mask[1:,:]=False
		self.index_errs_store=np.vstack((self.index_errs_store,self.index_errors))
		self.keep_mask=np.append(self.keep_mask,True)
		
	def Calculate(self):  #beregn aktuelle sats
		if not self.IsValid(row=0):
			return -1,-1,-1,-1,-1,-1,False,False
		index_errors=(self.real_data[1,:]+self.real_data[2,:]-2*np.pi)*0.5 #1.st row + 2. row
		self.index_errors=index_errors*180.0/np.pi*3600.0 #store in seconds
		z1c,z2c=self.real_data[1]-index_errors
		s1,s2=self.GetDistances()
		k1,k2=self.instrument_consts[:,1] #axis 1. inst, axis 2. inst
		if DEBUG:
			print("Index err: %s" %repr(index_errors*180.0/np.pi))
			print("Raw: %s" %repr(self.raw_data))
			print("Dist: %s" %repr(self.real_data[0]))
			print("Real: %s" %repr(self.real_data[1:,:]*180.0/np.pi))
		try:
			z1=tan(k2*sin(z1c))/(s1-k2*cos(z1c))+z1c #Korrigeret for Inst2's prisme-objektiv afst.
			z2=tan(k1*sin(z2c))/(s2-k1*cos(z2c))+z2c
		except:
			return -1,-1,-1,-1,-1,-1,False,False
		self.restfejl=(z1+z2-0.87*self.dist/RADIUS-np.pi)*360*60*60/(2*np.pi)  #sekunder
		self.h1=(cos(z1c)*self.dist+(0.87*self.dist**2)/(2*RADIUS)-k2)*self.aim[0]   #Refraktion saettes til k=0.13 (1-k)=0.87
		self.h2=(cos(z2c)*self.dist+(0.87*self.dist**2)/(2*RADIUS)-k1)*self.aim[1]   #Tages hensyn til afstand mellem objektiv og prisme....
		self.hdiff=(self.h1+self.h2)*0.5
		#perform various tests#
		self.dh_test=abs(self.h1-self.h2)<self.err_limits.maxdh_mutual*self.dist/100.0 #error pr. 100 m
		self.rf_test=abs(self.restfejl)<self.err_limits.max_rf*self.dist/100.0
		return self.h1,self.h2,self.hdiff,self.restfejl,self.index_errors[0],self.index_errors[1],self.dh_test,self.rf_test
	def SatsTest(self):
		return self.dh_test and self.rf_test
	def MaxDevTest(self,mask=None):
		return self.GetMaxdev(mask)<self.err_limits.maxdh_setups*self.dist/100.0
	def GetTotalHdiff(self,mask=None):
		if mask is None:
			mask=self.keep_mask
		return np.mean(self.hdiffs[mask])
	def GetHdiffs(self,mask=None):
		if mask is None:
			mask=self.keep_mask
		return self.hdiffs[mask].sum(axis=1)*0.5
	def GetHdiffsRaw(self,mask=None):
		if mask is None:
			mask=self.keep_mask
		return self.hdiffs[mask]
	def GetIndexErrorsAll(self,mask=None):
		if mask is None:
			mask=self.keep_mask
		return self.index_errs_store[mask]
	def GetRerrors(self,mask=None):
		if mask is None:
			mask=self.keep_mask
		return self.restfejls[mask]
	def GetStddev(self,mask=None):
		if mask is None:
			mask=self.keep_mask
		return np.std(self.GetHdiffs(mask))
	def GetMaxdev(self,mask=None):
		if mask is None:
			mask=self.keep_mask
		hdiffs=self.GetHdiffs(mask)
		return hdiffs.max()-hdiffs.min()
	def GetNsats(self):
		return np.sum(self.keep_mask)
	def GetStringData(self):
		nsats=self.GetNsats()
		data=["%.2f m" %self.GetDistance(),"%d" %nsats]
		if nsats>0:
			data.append("%.4f m" %self.GetTotalHdiff())
			if nsats>1:
				data.append("%.4f m" %self.GetStddev())
				data.append("%.4f m" %self.GetMaxdev())
		return data
	def SetKeepMask(self,mask):
		self.keep_mask=mask
	def GetKeepMask(self):
		return self.keep_mask
	def GetSatser(self,mask=None):
		if mask is None:
			mask=self.keep_mask
		return self.satser[mask]



#THIS is the core class which handles basis setup state and math, the rest is GUI and event handling...... 
#The class has been prepared for the possibility of handling input in formats other than ddd.mmss, e.g. angles in gon or whatever.... Only need to set relevant translator and validator methods 

class MTLBasisSetup(MTLSetup):
	def __init__(self,aim=1):
		MTLSetup.__init__(self,4,3,0,1) #1. soejle=maerker, 2. soejle=1. kikkerstilling, 3, soejle=2. kikkertstilling
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
		index_err=(self.real_data[:,1]+self.real_data[:,2]-2*np.pi)*0.5
		z_corr=self.real_data[:,1]-index_err  #standard formel fra KES...
		M=self.real_data[:,0]  #only a 'view' not a copy!
		cot=1.0/np.tan(z_corr)
		s1=(M[0]-M[2])/(cot[0]-cot[2])
		s2=(M[1]-M[3])/(cot[1]-cot[3])
		dist=(s1+s2)*0.5
		#Instrumenthoejder (KES HOVMTL05.BAS) Minus sigte giver det rigtige fortegn!
		#important bugfix: () must include the correction term!!!!
		self.h1=-self.aim*((M[2]*cot[0] - M[0]*cot[2] )/(cot[0] - cot[2]) - 0.5 * (dist**2) / RADIUS)   # Earth radius
		self.h2=-self.aim*((M[3]*cot[1] - M[1]*cot[3] )/(cot[1] - cot[3]) - 0.5 * (dist**2) / RADIUS)
		self.hdiff=(self.h1+self.h2)*0.5
		self.dist=dist
		return self.dist,self.h1,self.h2,self.hdiff
	def GetResult(self):
		return self.dist,self.h1,self.h2,self.hdiff