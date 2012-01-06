import sqlite3
import MyModules.GUIclasses2 as GUI
import numpy as np
import os
import FileOps
#Last fix 14.04.10, simlk. Changed "centering error", which should make the test more forgiving at small distances - at large distances it has no effect. 
def MTLtest(hdiffin,found,dist,parameter):
	dist=dist/1000.0
	diff=np.fabs(hdiffin+np.mean(found)) #this is in m - test in mm
	DLIM=0.2 #km
	if dist<DLIM:
		FKLIN=(np.sqrt(DLIM)*parameter-0.3)/DLIM
		return np.abs(diff*1000)-FKLIN*dist+0.3
	else:
		return np.abs(diff*1000)-parameter*np.sqrt(dist)
def MGLtest(hdiffin,found,dist,parameter):
	diff=np.fabs(hdiffin+np.mean(found)) #this is in m - test in mm
	test=diff*1000-np.sqrt((((1+1.0/found.size)*0.5)*parameter**2*(dist/1000.0)+0.1**2)) #add "centering-error". Also reflects the number of found. 
	#print diff,dist,parameter,found.size,test
	return test
class FBreject(object): 
	def __init__(self,database,program="MGL",parameter=2.0):
		if program=="MGL":
			self.testfunction=MGLtest
		else:
			self.testfunction=MTLtest
		self.parameter=parameter
		self.initialized=False
		self.found=False
		self.wasok=False
		try:
			self.connection=sqlite3.connect(database)
			self.cur=self.connection.cursor()
		except:
			pass
		else:
			self.initialized=True
	def TestStretch(self,start,end,hdiff): #returns foundstretch,testresult, diff,#found
		self.found=False
		self.wasok=False
		if not self.initialized:
			return False,False,0,0
		else:
			try:
				self.cur.execute("SELECT hdiff,dist FROM stretch WHERE start=? AND end=?",(end,start)) #swap order, to look for forward-meas
				data=self.cur.fetchall()
			except Exception, msg:
				print repr(msg)
				return False,False,0,0
			else:
				if data is not None and len(data)>0:
					found=np.array(data)
					test=self.testfunction(hdiff,found[:,0],np.mean(found[:,1]),self.parameter)
					isok=test<0
					self.found=True
					self.wasok=isok
					return True,isok,np.abs(test),found.size
				else:
					return False,False,0,0
	def InsertStretch(self,start,end,hdiff,dist,date,time):
		if not self.initialized:
			return True #we havent done anyting
		else:
			try:
				start=start.strip()
				end=end.strip()
				self.cur.execute("INSERT INTO stretch VALUES (?,?,?,?,?,?)",(start,end,hdiff,dist,date,time))
			except Exception, msg:
				print repr(msg)
				return False
			else:
				self.connection.commit()
				return True
	def IsInitialized(self):
		return self.initialized
	def GetNumber(self):
		self.cur.execute("SELECT count(*) FROM stretch")
		return self.cur.fetchone()[0]
	def Disconnect(self):
		try:
			self.cur.close()
			self.connection.close()
		except:
			pass

def MakeRejectData(resfiles,databasename):
	con=sqlite3.connect(databasename)
	cur=con.cursor()
	try:
		cur.execute("CREATE TABLE stretch (start TEXT, end TEXT, hdiff REAL, dist REAL, date TEXT, time TEXT)")
	except:
		return False,0,0
	nstrk=0
	nerrors=0
	for file in resfiles:
		heads=FileOps.Hoveder(file)
		for head in heads:
			try:
				cur.execute("INSERT INTO stretch VALUES (?,?,?,?,?,?)",(head[0],head[1],head[5],head[4],head[2],head[3]))
			except Exception, msg:
				print repr(msg)
				nerrors+=1
			else:
				nstrk+=1
	con.commit()
	cur.close()
	con.close()
	return True,nstrk,nerrors