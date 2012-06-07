import Funktioner
import datetime
import MyModules.GUIclasses2 as GUI
import numpy as np
import os
import FileOps
#fix 14.04.10, simlk. Changed "centering error", which should make the test more forgiving at small distances - at large distances it has no effect. 
# Last edit: 2012-01-09 fixed mtl test. Unified, 2012-04-23: fixed possible None return val in TestStretch
#Rejcection criteria reflects a model variance for meas. of a strectch, should correpond to a variance of half the parameter used in the test. 

# Test is really - for two meas:
#par=prec=reject_par/2.....
#|diff|<2*sqrt(var_model(d,par)) - always linear in par. 
#No more Centering err/ constant 'avoid zero' term! 
#Thus the var-models are artificial close to zero. Instead a global min is defined (0,3 mm for now)!!!!!

GLOBAL_MIN_DEV=0.3 #twice precision on mean

def MTL_var_model_linear(dist,parameter):
	dist=dist/1000.0
	return (dist*parameter)**2
	
def MTL_var_model(dist,parameter):
	dist=dist/1000.0
	DLIM=0.2 #km
	c_err=0 #divided by two below because 'precision' is (defined to be)  half of 'reject par'
	if dist<DLIM:
		FKLIN=(np.sqrt(DLIM)*parameter-c_err*0.5)/DLIM
		return (FKLIN*dist+c_err*0.5)**2
	else:
		return (parameter**2*dist)

def MGL_var_model(dist,parameter):
	dist=dist/1000.0
	c_err=0.0 #divided by two below because 'precision' is (defined to be)  half of 'reject par'
	return (np.sqrt(dist)*parameter+c_err*0.5)**2   #add a centering err....
	

	
class FBreject(object): 
	def __init__(self,database,program="MGL",parameter=2.0,unit="ne"):
		if program=="MGL":
			self.var_model=MGL_var_model
		else:
			if unit=="ne":
				self.var_model=MTL_var_model
			else:
				self.var_model=MTL_var_model_linear
		self.unit=unit
		self.parameter=parameter
		self.precision=parameter*0.5 #this is the correpsonding 'precision'
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
				data+="dh: %.4f m tid: %s j-side: %s\n" %(s.hdiffs[i],s.times[i].isoformat().replace("T",","),s.jpages[i])
		return data
	def GetDatabase(self):
		return self.database
	def TestStretch(self,start,end,hdiff): #returns foundstretch,testresult,#found,msg
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
		msg+=u"%s->%s er tidligere m\u00E5lt %d gang(e), og %d gang(e) i modsat retning.\n" %(start,end,nforward,nback)
		nall=len(hdiffs_all)
		if len(hdiffs_all)>0:
			d=np.mean(dists)
			norm_d=np.sqrt(d/1e3)
			msg+="Afstand: %.2f m\n" %d
			if len(hdiffs_all)>1:
				raw_mean=np.mean(hdiffs_all)
				raw_std=np.std(hdiffs_all,ddof=1)
				raw_prec=raw_std/np.sqrt(len(hdiffs_all))
				raw_max_diff=hdiffs_all.max()-hdiffs_all.min()
				msg+=u"hdiff_middel: %.4f m, max-diff: %.2f mm (%.2f ne)\n" %(raw_mean,raw_max_diff*1000,raw_max_diff*1e3/norm_d)
				msg+="std_dev: %.2f mm, std_dev(middel): %.2f mm (%.2f ne)\n" %(raw_std*1000,raw_prec*1000,raw_prec*1e3/norm_d)
			msg+=u"\nEfter inds\u00E6ttelse af ny m\u00E5ling:\n"
			hdiffs_new=np.append(hdiffs_all,[hdiff])
			new_mean=np.mean(hdiffs_new)
			new_std=np.std(hdiffs_new,ddof=1)
			new_prec=new_std/np.sqrt(len(hdiffs_new))
			new_max_diff=hdiffs_new.max()-hdiffs_new.min()
			msg+=u"hdiff_middel: %.4f m, max-diff: %.2f mm (%.2f ne)\n" %(new_mean,new_max_diff*1000,new_max_diff*1e3/norm_d)
			msg+="std_dev: %.2f mm, std_dev(middel): %.2f mm (%.2f ne)\n" %(new_std*1000,new_prec*1000,new_prec*1e3/norm_d)
			msg+="\nForkastelsesparameter: %.3f %s." %(self.parameter,self.unit)
			max_dev=self.GetMaxDev(d) #in mm!!
			if len(hdiffs_new)==2:
				msg+=" Vil acceptere |diff|<%.2f mm" %(2*max_dev)
			isok=(new_prec*1e3<=max_dev)
			self.found=True
			self.wasok=isok
			if isok:
				msg+=u"\nDen samlede standardafvigelse p\u00E5 middel er OK.\n"
			else:
				msg+=u"\nDen samlede standarafvigelse p\u00E5 middel er IKKE OK\n" 
				msg+=u"Foretag flere m\u00E5linger!\n"
			if len(hdiffs_all)>1 and new_prec>raw_prec: #or something more fancy
				msg+=u"Den nye m\u00E5ling er tilsyneladende en outlier og kan evt. omm\u00E5les!\n"
				isok=False
			return True,isok,len(hdiffs_all),msg
		else:
			msg=u"%s->%s er ikke m\u00E5lt tidligere" %(start,end)
			self.found=False
			self.wasok=True
			return True,True,0,msg
			
	def GetMaxDev(self,dist): #max dev in mm!
		return max(np.sqrt(self.var_model(dist,self.precision)),GLOBAL_MIN_DEV*0.5)
			
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
	def OutlierAnalysis(self):
		data=self.database.copy()
		msg=""
		noutliers=0
		nbad=0
		keys=data.keys()
		for key_forward in keys:
			l_msg="%s->%s:" %key_forward
			key_back=(key_forward[1],key_forward[0])
			if not key_forward in data: #could happen since we delete stuff below
				continue
			s_forward=data[key_forward]
			hdiffs_all=np.array(s_forward.hdiffs)
			nforward=len(s_forward.hdiffs)
			dists=[s_forward.dist]
			nback=0
			if key_back in data:
				s_back=data[key_back]
				nback=len(s_back.hdiffs)
				if nback>0:
					dists.append(s_back.dist)
					hdiffs_all=np.append(hdiffs_all,np.array(s_back.hdiffs)*-1.0)
			d=np.mean(dists)
			l_msg+=u" m\u00E5lt %d gange frem og %d gange tilbage." %(nforward,nback)
			report=False
			if len(hdiffs_all)>1:
				std_dev=np.std(hdiffs_all,ddof=1)
				m=np.mean(hdiffs_all)
				#same test as above#
				prec=std_dev/np.sqrt(len(hdiffs_all))
				max_dev=self.GetMaxDev(d) #in mm
				#print max_dev,prec
				is_ok=(prec*1e3<=max_dev)
				if not is_ok:
					nbad+=1
					report=True
					l_msg+="\nForkastelseskriterie IKKE overholdt."
					l_msg+=u"\nTilladt fejl p\u00E5 middel: %.2f mm, aktuel fejl: %.2f mm" %(max_dev,prec*1e3)
				if len(hdiffs_all)>2:
					dh=np.fabs(hdiffs_all-m)
					outlier_limit=1.5*std_dev
					if len(hdiffs_all)==3:
						outlier_limit=1.1*std_dev
					I=np.where(np.fabs(dh)>outlier_limit)[0]
					if I.size>0:
						report=True
						l_msg+="\nOutliere:"
						for i in I:
							noutliers+=1
							if i>nforward-1:
								i-=nforward
								s=s_back
							else:
								s=s_forward
							l_msg+=u"\nHdiff: %.4f m, m\u00E5lt %s, journalside: %s" %(s.hdiffs[i],s.times[i].isoformat().replace("T"," "),s.jpages[i])
							hdiffs_new=np.delete(hdiffs_all,i)
							new_prec=np.std(hdiffs_new,ddof=1)/np.sqrt(len(hdiffs_new))
							l_msg+=u"\nFejl p\u00E5 middel: %.2f mm, fejl p\u00E5 middel uden denne m\u00E5ling: %.2f mm" %(prec*1e3,new_prec*1e3)
				if report:
					msg+="\n"+"*"*60+"\n"+l_msg
				
				
			#Finally delete that entry#
			del data[key_forward]
			if nback>0:
				del data[key_back]
		nprob=noutliers+nbad
		if nprob==0:
			return True,u"Ingen problemer fundet"
		lmsg=u"%*s %d\n" %(-42,u"#overtr\u00E6delser af forkastelseskriterie:",nbad)
		lmsg+=u"%*s %d\n" %(-42,"#outliere:",noutliers)
		return False,lmsg+msg
			
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
	precision=0.5*parameter  #since parameter is 'reject-parameter' and we define precison as half of dat - man :-)
	out=2*np.sqrt(map(lambda x: var_model(x,precision), dists))
	return np.column_stack((dists,out))

def GetGlobalMinLine(program="MGL"):
	dists=[0,400.0]
	hs=[GLOBAL_MIN_DEV,GLOBAL_MIN_DEV]
	return np.column_stack((dists,hs))
	
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