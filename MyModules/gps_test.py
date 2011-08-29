import time
from random import random
PARITY_EVEN=None
def MyTime():
	t=time.localtime()
	secs=float(t.tm_sec)/(60*60)
	mins=float(t.tm_min)/60
	hours=float(t.tm_hour)
	return hours+mins+secs  #tiden i timer som float
class Serial():
	def __init__(self,*args,**kwargs):
		self.count=0
		self.start=time.clock()
	def readline(self):
		t=time.clock()
		cor=(time.clock()-self.start)*0.04  #80km i timen
		Y=str(5512.0000 +cor)
		X=str(948.0000 + cor)
		#print X,Y
		return "$GPGGA,X,%s,N,%s,E,1,x,1,x,x,x" %(Y,X)
	def close(self):
		pass
	def open(self):
		pass
	def flush(self):
		pass
	def write(self,text):
		pass
		