import Funktioner
import datetime
import MyModules.GUIclasses2 as GUI
import numpy as np
import os
import FileOps
#fix 14.04.10, simlk. Changed "centering error", which should make the test more forgiving at small distances - at large distances it has no effect. 
# Last edit: 2012-01-09 fixed mtl test. Unified.
#Rejcection criteria reflects a model variance for meas. of a strectch, should correpond to a variance of half the parameter used in the test. 
def MTL_var_model_linear(dist,parameter):
	dist=dist/1000.0
	return (dist*parameter+0.1)**2
	
def MTL_var_model(dist,parameter):
	dist=dist/1000.0
	DLIM=0.2 #km
	if dist<DLIM:
		FKLIN=(np.sqrt(DLIM)*parameter-0.3)/DLIM
		return (FKLIN*dist+0.3)**2
	else:
		return (parameter**2*dist)

def MGL_var_model(dist,parameter):
	dist=dist/1000.0
	return (np.sqrt(dist)*parameter+0.05)**2   #add a centering err....
	
def Test_old(hdiffin,found,dist,parameter,var_model):
	diff=np.fabs(hdiffin+np.mean(found)) #this is in m - test in mm
	return diff*1000-np.sqrt(((1+1.0/found.size)*0.5)*var_model(dist,parameter))

def Test(std_total,dist,parameter,var_model):
	return std_total*1000-np.sqrt(var_model(dist,parameter))

def MGLtest(hdiffin,found,dist,parameter):
	diff=np.fabs(hdiffin+np.mean(found)) #this is in m - test in mm
	test=diff*1000-np.sqrt((((1+1.0/found.size)*0.5)*parameter**2*(dist/1000.0)+0.1**2)) #add "centering-error". Also reflects the number of found. 
	#print diff,dist,parameter,found.size,test
	return test
	
class FBreject(object): 
	def __init__(self,database,program="MGL",parameter=2.0,unit="ne"):
		if program=="MGL":
			self.var_model=MGL_var_model
		else:
			if unit=="ne":
				self.var_model=MTL_var_model
			else:
				self.var_model=MTL_var_model_linear
		self.parameter=parameter
		self.initialized=False
		self.found=False
		self.wasok=False
		self.database=database
		self.initialized=True
	def GetData(self):
		data=""
		for key in self.database.keys():
			s=self.database[key]
			data+="%s->%s: dist: %.2f m\n" %(key[0],key[1],s.dist)
			for i in range(len(s.hdiffs)):
				data+="%.2f %s %s\n" %(s.hdiffs[i],s.times[i].isoformat(),s.jpages[i])
		return data
	def GetDatabase(self):
		return self.database
	def TestStretch(self,start,end,hdiff): #returns foundstretch,testresult, diff,#found
		self.found=False
		self.wasok=False
		msg=""
		key_back=(end,start)
		key_forward=(start,end)
		nforward=0
		nback=0
		hdiffs_all=np.empty((0,))
		dists=[]
		if self.database.has_key(key_back):
			s_back=self.database[key_back]
			nback+=len(s_back.hdiffs)
			if nback>0:
				dists.append(s_back.dist)
				hdiffs_all=np.append(hdiffs_all,np.array(s_back.hdiffs)*-1.0)
		if self.database.has_key(key_forward):
			s_forward=self.database[key_forward]
			nforward+=len(s_forward.hdiffs)
			if nforward>0:
				dists.append(s_forward.dist)
				hdiffs_all=np.append(hdiffs_all,np.array(s_forward.hdiffs))
		msg+=u"%s->%s er tidligere m\u00E5lt %d gange, og %d gange i modsat retning." %(start,end,nforward,nback)
		nall=len(hdiffs_all)
		if len(hdiffs_all)>0:
			d=np.mean(dists)
			if len(hdiffs_all)>1:
				raw_mean=np.mean(hdiffs_all)
				raw_std=np.std(hdiffs_all,ddof=1)
				msg+="\nAfst: %.2f m, hdiff_middel: %.4f m, std-dev: %.2f mm" %(d,raw_mean,raw_std*1000)
			msg+=u"\nEfter inds\u00E6ttelse af ny m\u00E5ling:\n"
			hdiffs_new=np.append(hdiffs_all,[hdiff])
			new_mean=np.mean(hdiffs_new)
			new_std=np.std(hdiffs_new,ddof=1)
			msg+=u"hdiff_middel: %.4f m, std_dev: %.2f mm" %(new_mean,new_std*1000)
			diff=Test(new_std,d,self.parameter,self.var_model)
			isok=diff<0
			self.found=True
			self.wasok=isok
			if isok:
				msg+="\nDen samlede standardafvigelse er OK.\n"
			else:
				msg+=u"\nDen samlede standarafvigelse er IKKE OK, lav flere m\u00E5linger!\n"
				if len(hdiffs_all)>1 and new_std>raw_std: #or something more fancy
					msg+=u"Den nye m\u00E5ling er tilsyneladende en outlier og kan evt. omm\u00E5les!\n"
				return True,isok,abs(diff),len(hdiffs_all),msg
		else:
			msg=u"%s->%s er ikke m\u00E5lt tidligere" %(start,end)
			self.found=False
			self.wasok=True
			return True,True,0,0,msg
			
			
	def InsertStretch(self,start,end,hdiff,dist,dato,tid,jside=""):
		if not self.initialized:
			return True #we havent done anyting
		data=self.database
		try:
			start=start.strip()
			end=end.strip()
			key=(start,end)
			m,h=Funktioner.GetTime(tid)
			day,month,year=Funktioner.GetDate(dato)
			date=datetime.datetime(year,month,day,h,m)
			if data.has_key(key):
				data[key].AddStretch(hdiff,dist,date,jside)
			else:
				data[key]=Stretch()
				data[key].AddStretch(hdiff,dist,date,jside)
		except Exception, msg:
			print repr(msg)
			return False
		else:
			
				return True
	def IsInitialized(self):
		return self.initialized
	def GetNumber(self):
		return len(self.database)
	def Disconnect(self):
		pass
			
def GetPlotData(program="MGL",parameter=2.0,unit="ne"):
	if program=="MGL":
		var_model=MGL_var_model
	else:
		if unit=="ne":
			var_model=MTL_var_model
		else:
			var_model=MTL_var_model_linear
	dists=np.arange(0,1500,10)
	out=np.sqrt(map(lambda x: var_model(x,parameter), dists))
	return np.column_stack((dists,out))
	
class Stretch(object):
	def __init__(self):
		self.hdiffs=[]
		self.dist=0
		self.times=[]
		self.jpages=[]
	def AddStretch(self,hdiff,dist,date,jpage=""):
		n=float(len(self.hdiffs))+1
		self.dist=self.dist*(n-1)/n+dist/n
		self.hdiffs.append(hdiff)
		self.times.append(date)
		self.jpages.append(jpage)

def MakeRejectData(resfiles):
	data=dict()
	nstrk=0
	nerrors=0
	for file in resfiles:
		heads=FileOps.Hoveder(file)
		for head in heads:
			try:
				key=(head[0],head[1])
				hdiff=float(head[5])
				dist=float(head[4])
				jside=head[6]
				tid=head[3]
				dato=head[2]
				m,h=Funktioner.GetTime(tid)
				day,month,year=Funktioner.GetDate(dato)
				date=datetime.datetime(year,month,day,h,m)
			except Exception, msg:
				print repr(msg)
				nerrors+=1
			else:
				if data.has_key(key):
					data[key].AddStretch(hdiff,dist,date,jside)
				else:
					data[key]=Stretch()
					data[key].AddStretch(hdiff,dist,date,jside)
				nstrk+=1
	return data,nerrors