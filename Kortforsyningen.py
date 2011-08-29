#Definerer Kortforsyningens korttyper
from MyModules.wms_client import WMSservice
SERVICES=[]
SERVICES.append(WMSservice(u"DTK-Sk\u00E6rmkort","topo_skaermkort",["dtk_skaermkort"]))
SERVICES.append(WMSservice("DTK-kort25","topo25",["topo25_klassisk_2008"]))
SERVICES.append(WMSservice(u"DTK-kort50","topo50",["dtk_2cm_2007"]))
#SERVICES.append(WMSservice(u"Kort 10- klassisk","kort10k",["kort10]))
SERVICES.append(WMSservice(u"Ortofoto","ortofoto",["Orto_dk"],"jpeg"))
#SERVICES.append(WMSservice(u"Kort200","topo_dtk",["3"]))
#SERVICES.append(WMSservice(u"Euro-gr\u00E6nser","ebm",[]))
SERVICES.append(WMSservice("Vektor-basic","kms_vector_basic_01",["SKOV","SOE","KOMMUNE","AMT","BYKERNE","VEJ6M","FIXPUNKT"]))
SERVICES.append(WMSservice("Administrative enheder","adm_500_2008_r",["KOM500_2008"]))
def GetServiceNames():
	names=[]
	for service in SERVICES:
		names.append(service.screenname)
	return names
def GetService(i=0):
	return SERVICES[i]
