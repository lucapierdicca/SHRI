import xml.etree.ElementTree

def load_menu(path):
	root = xml.etree.ElementTree.parse(path).getroot()

	portate = ['antipasti','primi','secondi','dolci','bevande']
	menu = {}
	
	for i in portate:
		for e in root.findall('./'+i+'/'):
			nome = e.find('nome').text
			prezzo = float(e.find('prezzo').text)

			menu[nome] = {'tipo':i,
						  'nome':nome,
						  'prezzo':prezzo}
	return menu


def print_menu(menu):

	reverse = {}
	portate = ['antipasti','primi','secondi','dolci','bevande']

	for v in menu.values():
		if v['tipo'] not in reverse:
			reverse[v['tipo']] = {'nome':[v['nome']],
						 		'prezzo':[v['prezzo']]}
		else:
			reverse[v['tipo']]['nome'].append(v['nome'])
			reverse[v['tipo']]['prezzo'].append(v['prezzo'])

	print('--------MENU-------')
	for i in portate:
		print(i.upper())
		for nome,prezzo in zip(reverse[i]['nome'],reverse[i]['prezzo']):
			print("\t"+nome)
			print("\t%.2f €" % prezzo)
