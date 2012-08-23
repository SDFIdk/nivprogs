#TEST CLASS FOR COM PORT OUTPUT TO MTL PROGRAM
import time
import random
PARITY_EVEN="ost"
class Serial(object):
	def __init__(self,*args,**kwargs):
		self.open=True
		self.return_angles=True
		self.has_done=0
	def close(self):
		self.open=False
	def write(self,text):
		if (text!=(chr(6) + "006" + chr(3) + chr(13) + chr(10))):
			raise Exception("Oh no!")
	def flush(self):
		pass
	def returnDistances(self):
		self.return_angles=False
	def readline(self):
		#what to expect??
		if (not self.open):
			return "hjdhjhjhd"
		if not self.return_angles:
			dist=100+random.random()*50.0
			line="?x00"+("%.3f" %dist).replace(".","")
		else:
			if self.has_done<4:
				ang="895959"
			else:
				ang="1800101"
			line="<00"+ang+"+"
		time.sleep(0.2+random.random())
		self.has_done+=1
		return line
	def read(self):
		pass
	
		