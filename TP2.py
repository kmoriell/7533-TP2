#!env python
import pybgpstream
import pprint
import time
import sys
from selenium import webdriver
from netaddr import *
import functools

colectores = [ 'route-views.saopaulo', 'route-views.perth']
ASNames = {}
PrefijosAnunciados = {}


class AS:
	_aspath = list()
	_nextHop = ''
	_prefix = ''
	_proveedor = ''
	__as_name_proveedor = ''		
	def __init__(self, aspath, nextHop, prefix, obtenerNombre = True):
		self._aspath = aspath
		self._nextHop = nextHop
		self._prefix = prefix		
		if obtenerNombre:
			self._proveedor = int(self._aspath[-2]) # el elemento que esta inmediamente anterior al ultimo
			self._as_name_proveedor = obtenerASName(self._proveedor)
    			
def obtenerRIB(time_init, time_end, collector):	
	stream = pybgpstream.BGPStream(from_time=time_init,
		until_time=time_end,
		filter='type ribs and collector %s' % (collector))
	ASs = list()
	for elem in stream:
		aspath = elem.fields["as-path"].split(' ')
		nextHop = elem.fields["next-hop"].strip()
		prefix = elem.fields["prefix"].strip()		
		_as = AS(aspath, nextHop, prefix, False)
		ASs.append(_as)					
	return ASs

def obtenerRutas(target_as, time_init, time_end, collector, obtenerNombre = True):
	global PrefijosAnunciados
	stream = pybgpstream.BGPStream(from_time=time_init,
		until_time=time_end,
		filter='type ribs and collector %s and path %s' % (collector, target_as))
	ASs = list()
	for elem in stream:
		if int(elem.fields["as-path"].split(' ')[-1]) == target_as:
			aspath = list()
			for as_path in elem.fields["as-path"].split(' '):
				if as_path not in aspath:
					aspath.append(as_path)
			nextHop = elem.fields["next-hop"].strip()
			prefix = elem.fields["prefix"].strip()
			if target_as not in PrefijosAnunciados.keys():
				PrefijosAnunciados[target_as] = set()
			if PrefijosAnunciados[target_as] is None:
				PrefijosAnunciados[target_as] = set()
			_set = PrefijosAnunciados[target_as]
			if prefix not in _set:								
				_set.add(prefix)				
			
			_as = AS(aspath, nextHop, prefix, obtenerNombre)
			ASs.append(_as)			
			#pprint.pprint(elem.fields)
	return ASs

def obtenerASName(target_as):	
	global ASNames

	if target_as not in ASNames.keys():    		
		driver = webdriver.Firefox()
		driver.get("https://bgp.he.net/AS" + str(target_as))	
		delay = 40
		time.sleep(delay)
		p_element = driver.find_element_by_xpath('/html/body/div[1]/h1/a')
		
		nombre = p_element.text
		_as_len = len("AS" + str(target_as))
		ASNames[target_as] = nombre[_as_len:].strip()

	return ASNames[target_as]

def mostrarRIB(ASs):
	print("Network \t Next Hop \t Weight Path")
	for i in range(0, len(ASs)):
		_as = ASs[i]
		_aspath = ''
		for j in range(0, len(_as._aspath)):
			_aspath += _as._aspath[j] + ' '		
		output = _as._prefix + "\t" + _as._nextHop + "\t" + _aspath.strip()
		print(output)	

def mostrarInformacion(ASs, target_as):
	proveedores = set()
	global ASNames
	global PrefijosAnunciados
	for k in range(0, len(ASs)):
		if ASs[k]._proveedor not in proveedores:
			proveedores.add(ASs[k]._proveedor)
		# Muestro los proveedores asociados
	for p in proveedores:
		print ("AS" + str(p) + ": " + ASNames[p])

	# Muestro los prefijos anunciados
	prefijos_anunciados = str(PrefijosAnunciados[target_as])
	prefijos_anunciados = prefijos_anunciados[6:]
	prefijos_anunciados = prefijos_anunciados.replace("'", "")
	prefijos_anunciados = prefijos_anunciados.replace("])", "")
	print ("Prefijos anunciados por AS" + str(target_as) + " " + prefijos_anunciados)
	
def punto2():
	time_init = '2015-07-05'
	time_end = '2015-07-05 00:02'
	rib_completa = obtenerRIB(time_init, time_end, colectores[0])
	print("Tamaño tabla sin agrupar: " + str(len(rib_completa)))
	s = set(map(lambda x:x._aspath[-1], rib_completa))
	as_origen = dict.fromkeys(s)	

	for entry in rib_completa:
		_as = entry._aspath[-1]
		if entry._prefix.find(':') > -1:
			continue # es una direccion IPv6
		if as_origen[_as] is None:
			as_origen[_as] = list()
		as_origen[_as].append(entry._prefix)
	tamanio_tabla = 0
	for k in as_origen.keys():
		if as_origen[k] == None:
			continue		
		as_origen[k] = cidr_merge(as_origen[k])
		tamanio_tabla += len(as_origen[k])
		
	print("Tamaño tabla con maxima agregacion: " + str(tamanio_tabla))		

def punto3():
	collector = 'route-views2'
	original = 43513
	impostor = 34434
	
	time_init = '2018-11-11 12:00'	
	time_end = '2018-11-11 12:20'
	ASs1 = obtenerRutas(original, time_init, time_end, collector, False)	
	prefijos_anunciados1 = set(map(lambda x:x._prefix, ASs1))
		
	ASs1 = obtenerRutas(impostor, time_init, time_end, collector, False)	
	prefijos_anunciados = set(map(lambda x:x._prefix, ASs1))

	prefijos_secuestrados = prefijos_anunciados.intersection(prefijos_anunciados1)

	print("Prefijos anunciados por ambos durante " + time_init + " a " + time_end + " : " + str(prefijos_secuestrados))

	time_init = '2018-11-11'	
	time_end = '2018-11-11 00:15'
	ASs1 = obtenerRutas(original, time_init, time_end, collector, False)	
	prefijos_antes_secuestro = set(map(lambda x:x._prefix, ASs1))
		
	ASs1 = obtenerRutas(impostor, time_init, time_end, collector, False)	
	prefijos_antes_secuestro1 = set(map(lambda x:x._prefix, ASs1))
	
	if len(prefijos_antes_secuestro.intersection(prefijos_secuestrados)) > 0:
		print(str(prefijos_secuestrados) + " originalmente pertenecia a " + str(original))
	else:
		print(str(prefijos_secuestrados) + " originalmente pertenecia a " + str(impostor))

	print("Prefijos anunciados por ambos durante " + time_init + " a " + time_end + " : " + str(prefijos_antes_secuestro1))


	time_init = '2018-11-12 08:00'	
	time_end = '2018-11-12 08:10'
	ASs1 = obtenerRutas(original, time_init, time_end, collector, False)	
	prefijos_anunciados = set(map(lambda x:x._prefix, ASs1))
	
	ASs1 = obtenerRutas(impostor, time_init, time_end, collector, False)	
	prefijos_anunciados1 = set(map(lambda x:x._prefix, ASs1))

	prefijos_secuestrados = prefijos_anunciados.intersection(prefijos_anunciados1)
	
	print("Prefijos anunciados por ambos durante " + time_init + " a " + time_end + " : " + str(prefijos_secuestrados))

def punto1(time_init, time_end):
	global colectores
	global ISP_as
	global target_as
	for i in range(0, len(colectores)):
		collector = colectores[i]
		print("Utilizando collector: " + collector)
		ASs1 = obtenerRutas(target_as, time_init, time_end, collector)
		print("Hay " + str(len(ASs1)) + " AS-PATHs diferentes")			

		ASs2 = obtenerRutas(ISP_as, time_init, time_end, collector)
		print("Hay " + str(len(ASs2)) + " AS-PATHs diferentes hacia el ISP")			

		mostrarInformacion(ASs1, target_as)
		mostrarInformacion(ASs2, ISP_as)	

if __name__ == "__main__":	
	time_init = '2017-03-01'
	time_end = '2017-03-01 00:15'

	if len(sys.argv) == 3:		
		time_init = sys.argv[1]  
		time_end = sys.argv[2]          

	ISP_as = 10481 # Fibertel
	target_as = 36917

	punto1(time_init, time_end)
	# Mismas consultas pero para el 2012
	punto1('2012-03-01', '2012-03-01 00:15')
	punto3()
	#mostrarRIB(rib_completa)

	



