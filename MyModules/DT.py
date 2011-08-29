import scipy.ndimage as image
import numpy as np
import sys
import time
ROUND=np.array([[0,0,1,1,0,0],[0,1,1,1,1,0],[1,1,1,1,1,1],[1,1,1,1,1,1],[0,1,1,1,1,0],[0,0,1,1,0,0]])

def Log(text):
	sys.stdout.write(text+"\n")
def GetDepth():
	return np.loadtxt("multibeam.mat",skiprows=6)

def DTMtest():
	return (np.loadtxt("C:\\DHMDATA\\DTM\\DTM_1km_6160_704.asc",skiprows=6)>=2.5)

def Open(A,fp=ROUND):
	return image.morphology.binary_opening(A,fp)
	
	
def GetBoundary(A,return_distance=False):
	D=image.morphology.distance_transform_cdt(A,metric='taxicab')
	if return_distance:
		return (D==1),D
	else:
		return (D==1)

def DX(A): #remember to typecast A before calling
	fp=np.array([[0,0,0],[-1,0,1],[0,0,0]])
	return image.filters.correlate(A,fp)

def DY(A):
	fp=np.array([[0,-1,0],[0,0,0],[0,1,0]]) #dy oriented 'downwards'
	return image.filters.correlate(A,fp)



def Gradient(A):
	dy=DY(A).reshape((A.shape[0],A.shape[1],1))
	dx=DX(A).reshape((A.shape[0],A.shape[1],1))
	return np.concatenate((dy,dx),axis=2) #y-is first axis in array indexing.

def BigHat(A): #rotate vectorfield in positive direction
	X=np.zeros(A.shape)
	X[:,:,0]=A[:,:,1]
	X[:,:,1]=-A[:,:,0]
	return X

def Hat(A): #rotate vector in positive direction
	return np.array([A[1],-A[0]])


def Laplacian(A):
	return DX(DX(A))+DY(DY(A))

def First(A):
	A=Open(A)
	A=ENI(A)
	return Open(A)

def ENI(A,cut=-3,rad=3): #enlarge narrow islands and 'odder'
	t=time.clock()
	D=image.morphology.distance_transform_edt(np.logical_not(A))
	N=np.logical_and((Laplacian(D)<=cut),D<=rad)
	D=image.morphology.distance_transform_edt(np.logical_not(N))
	A[D<=rad]=0
	print time.clock()-t
	return A

	


class Curve(object):
	def __init__(self,npoints):
		self.points=np.zeros((npoints,2))
		self.closed=False
		self.orientation=1 #means 'deep side' is to the left

def Trace(A):
	Bd,D=GetBoundary(A,return_distance=True)
	BdC,Nc=image.measurements.label(Bd,np.ones((3,3)))
	Log("Boundary components: %i" %Nc)
	slices=image.measurements.find_objects(BdC)
	#print D.shape
	TG=-BigHat(Gradient(D)) #rotate gradient, as to walk around region in positive direction
	TG[TG<0]=-1 #make it binary
	TG[TG>0]=1
	#print TG.shape
	Reg=(((np.abs(TG)).sum(axis=2))>0) #regular points
	EP=(image.filters.correlate(Bd.astype(np.uint8),np.ones((3,3)),mode='constant')==2) #possible endpoints
	nep=EP.sum()  #number of endpoints, to check in the end.
	curves=[]
	Log("Tracing.....")
	for nc in range(1,Nc+1):
		Log("Component %i:" %nc)
		sl=slices[nc-1]
		#print sl[0].start,sl[0].stop
		C=np.zeros((sl[0].stop-sl[0].start+2,sl[1].stop-sl[1].start+2),dtype=np.uint8) #make collar of zeros around
		#print C.shape, BdC[sl].shape
		C[1:-1,1:-1]=(BdC[sl]==nc) #enlarge with zeros around...
		npoints=np.sum(C)
		curve=Curve(2*npoints)
		GS=np.zeros(C.shape,dtype=np.bool)
		GS[1:-1,1:-1]=(np.logical_and(Reg[sl],C[1:-1,1:-1]))  #good set of regular points
		LG=np.zeros((C.shape[0],C.shape[1],2),dtype=np.int8)
		LG[1:-1,1:-1]=TG[sl]
		endi,endj=np.where(np.logical_and(EP[sl],C[1:-1,1:-1])) #possible endpoints
		Log("Points: %i." %npoints)
		Log("Endpoints: %i." %endi.size)
		if endi.size>0:
			Log("Setting start and end point.")
			curve.closed=False
			if endi.size>2:
				Log("Error, component has %i endpoints!")
			i,j=endi[0]+1,endj[0]+1  #starting point, index rel. to C
			endp=endi[1]+1,endj[1]+1 #check what happens if startp right in corner!!
			if (i==1 and LG[i,j,0]<0) or (i==C.shape[0]-2 and LG[i,j,0]>0): #start point at top or bottom
				endp=np.array([i,j])
				i,j=endi[1]+1,endj[1]+1 #the we start in the other end!
				print "adjusting 1"
			if (j==1 and LG[i,j,1]<0) or (j==C.shape[1]-2 and LG[i,j,1]>0): #starting left or right
				endp=np.array([i,j])
				i,j=endi[1]+1,endj[1]+1
				print "adjusting 2"
			print C.shape,(i,j),LG[i,j]
		else:
			curve.closed=True
			i=1
			j=np.where(C[1,:])[0][0]
		#print i,j
		if not GS[i,j]:
			Log("Error: Start point is not regular!")
			#and then do something!
		#initialize#
		ncrit=0
		done=0  #amount really done -1
		start=np.array([i,j])
		current=np.copy(start)
		closure=100
		lastshift=current-start
		curve.points[done]=current
		while done<2*npoints-2 and (closure>2 or done<3):  #assuming no very small loops exist
			#print TG[current[0],current[1]].shape,current.shape
			next=current+LG[current[0],current[1]] #tracing step
			#if ((next>0).sum()<2 or ((next+1)<C.shape).sum()<2) and not curve.closed:  #walked past boundary??
			#	#Log("Hit boundary.")
			#	#print current,next,LG[current[0],current[1]],C.shape, start
			#	if np.abs(next-endp).sum()<3:
			#		break
			if not GS[next[0],next[1]]:
				ncrit+=1
				win=(C[current[0]-1:current[0]+2,current[1]-1:current[1]+2])
				win[1,1]=0  #delete current
				win[1-lastshift[0],1-lastshift[1]]=0 #delete previous
				posi,posj=np.where(win)
				if posi.size==0:
					Log("Could not continue component past index %i." %done)
					#print win.sum()
					break
				else:
					next=np.array([posi[0]+current[0]-1,posj[0]+current[1]-1])
			lastshift=next-current
			current=next
			done+=1
			curve.points[done]=current
			if curve.closed:
				closure=np.abs(current-start).sum()
			else:
				closure=np.abs(current-endp).sum()
			#print closure
			#if done%100==0:
			#	print done, closure
		#print done,closure
		if curve.closed:
			curve.points[done+1]=start
			done+=1
		curve.points=(curve.points[0:done+1]+[sl[0].start-1,sl[1].start-1])
		curves.append(curve)
		Log("Done... Traced %i points and did %i tracing corrections." %(done,ncrit))
	return curves