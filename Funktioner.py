import time
from math import *
import os
def Reject(afst): #afst. i m, bugfix for L<7m
	if afst<200:
		return 8.31*afst/1000.0+0.3
	else:
		return 4.39*sqrt(afst/1000.0)
def RejectOpst(afst):
	return 7.6*afst/1000.0+0.15
def SortFirst(x,y):
	xs=[]
	ys=[]
	xc=x[:] #kopi af x, saa x ikke modificeres!
	mgem=-10000
	jgem=-1
	while len(xc)>0:
		m=min(xc)
		if m==mgem:
			j=x.index(m,jgem+1) #hvis samme igen, saa kig laengere fremme
		else:
			j=x.index(m)
		xs.append(m)
		ys.append(y[j])
		xc.remove(m) #fjerner foerste match
		mgem=m
		jgem=j
	return xs,ys
def L1(x,y): #2-d max-norm
	return max(abs(x[0]-y[0]),abs(x[1]-y[1]))

def State2Col(x):
	if x:
		return "blue"
	else:
		return "red"
def State2msg(x):
	if x:
		return "OK"
	else:
		return "NF"
def Bool2JN(x):
	if x:
		return "JA"
	else:
		return "NEJ"

def Bool2sigte(x):
	
	if x==1:
		return "Frem"
	elif x==-1:
		return "Tilbage"
	else:
		return "NA"

def VinkelKorr(v,s,k):
	z=atan(k*sin(radians(v)))/(s-k*cos(v))+radians(v)
	return z
	
		
def MyTime():
	t=time.localtime()
	secs=float(t.tm_sec)/(60*60)
	mins=float(t.tm_min)/60
	hours=float(t.tm_hour)
	return hours+mins+secs  #tiden i timer som float
def Nu():
	t=time.asctime()
	t=t.split()[3][0:-3].replace(":",".") #vaelg tidspunktet udaf strengen
	return t
def Dato():
	t=time.localtime()
	maaned=str(t.tm_mon)
	dag=str(t.tm_mday)
	if len(dag)==1:
		dag="0"+dag
	if len(maaned)==1:
		maaned="0"+maaned
	dato=dag+"."+maaned+"."+str(t.tm_year)
	return dato
#inverse functions of date, time
def GetTime(tid):
	delim="."
	if ":" in tid:
		delim=":"
	h,m=tid.split(delim)
	return int(m),int(h)

def GetDate(date):
	delim="."
	if ":" in date:
		delim=":"
	elif "-" in date:
		delim="-"
	date=map(int,date.split(delim))
	if date[0]>365:
		date.reverse()
	return date
		

def Dato2():
	t=time.localtime()
	maaned=str(t.tm_mon)
	dag=str(t.tm_mday)
	aar=str(t.tm_year)
	aar=aar[-2:]
	if len(dag)==1:
		dag="0"+dag
	if len(maaned)==1:
		maaned="0"+maaned
	dato=aar+maaned+dag
	return dato
def Fulltime():
	t=time.asctime()
	return t

def RemRem(f):
	skip=True
	while skip:
		line=f.readline()
		if len(line)==0:
			return ""
		elif line.isspace():
			skip=True
		elif line.strip()[0]=="#":
			skip=True
		else:
			skip=False
	i=line.find("#")
	if i!=-1:
		line=line[0:i-1]
	return line.strip()

def Dec2Grad(x): #nb x en streng: DDDMMSS
	S=int(x[-2:])
	M=int(x[-4:-2])
	G=int(x[0:-5])
	return G+M/60.0+S/3600.0 

def Prepad(x,w):
	s=[]
	for i in x:
		s.append(w)
		s.append(i)
	return tuple(s)
	
def EtOrd(s):
	return s.strip().replace(" ","")

def Internationale(line):
	line=line.replace(u"\u00E5","aa")
	line=line.replace(u"\u00C5","AA")
	line=line.replace(u"\u00C6","Ae")
	line=line.replace(u"\u00D8","Oe")
	line=line.replace(u"\u00E6","ae")
	line=line.replace(u"\u00F8","oe")
	try:
		line=str(line)
	except:
		pass
		
	return line

def CompareDirs(dir1,dir2):
	dir1=str(dir1)
	dir2=str(dir2)
	dir1=dir1.replace(":","").replace("/","").replace("\\","")
	dir2=dir2.replace(":","").replace("/","").replace("\\","")
	return (dir1==dir2)

