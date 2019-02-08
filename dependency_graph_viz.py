import requests
import json
from pprint import pprint
from graphviz import Digraph
from PIL import Image
from menu_utils import load_menu
from frames import if_successors

menu = load_menu('menu.xml')

lexicon_O = [v['nome'].lower() for v in menu.values()]

tint_url = "http://localhost:8012/tint?"

for index,t in enumerate(lexicon_O):
	response = requests.get(tint_url+'text='+t+'&format=json')
	annotations = json.loads(response.text)
	splitted = t.split()
	for i in annotations['sentences'][0]['tokens']:
		if 'features' in i:
			if 'Number'in i['features']:
				if i['features']['Number'][0] == 'Plur':
					splitted[i['index']-1] = i['lemma']
					lexicon_O[index] = ' '.join(splitted)


lexicon_TO = ['menu']
lexicon_I = ['antipasto','primo','secondo','dolce']
lexicon_P = ['conto']
lexicon_B = ['tavolo','posto']

frames = [{'in':{'name':'ORDINAZIONE','lu_v':['ordinare','volere','chiedere','portare','prendere'],'lu_s':lexicon_O,'ce':['entity']}},
	   	  {'in':{'name':'TR_OGGETTO','lu_v':['portare'],'lu_s':lexicon_TO,'ce':['theme']}},
	   	  {'in':{'name':'INFORMAZIONE','lu_v':['essere','avere'],'lu_s':lexicon_I,'ce':['content']}},
	   	  {'in':{'name':'PAGAMENTO','lu_v':['portare','pagare','saldare'],'lu_s':lexicon_P,'ce':['good']}},
	   	  {'in':{'name':'PRENOTAZIONE','lu_v':['essere','prenotare'],'lu_s':lexicon_B,'ce':['services']}}]


def dep_viz(file_id,text,annotations):
	
	# parser server url
	# tint_url = "http://localhost:8012/tint?"
	# response = requests.get(tint_url+'text='+text+'&format=json')
	# annotations = json.loads(response.text)

	# pprint(annotations['sentences'][0]['basic-dependencies'])
	# pprint(annotations['sentences'][0]['tokens'])

	f = Digraph(file_id, format='png')

	for token in annotations['sentences'][0]['tokens']:
		f.node(token['word'])

	for edge in annotations['sentences'][0]['basic-dependencies']:
		if edge['dep'] != 'ROOT':
			f.edge(edge['governorGloss'],edge['dependentGloss'],label=edge['dep'],fontsize="11",ldistance="3.0")

	f.attr(label='\n'+text)
	f.render(cleanup=True,)
	pil_im = Image.open(file_id+'.gv.png', 'r')
	pil_im.show()

def dep_VIZ(file_id,text):
	
	# parser server url
	tint_url = "http://localhost:8012/tint?"
	response = requests.get(tint_url+'text='+text+'&format=json')
	annotations = json.loads(response.text)

	# pprint(annotations['sentences'][0]['basic-dependencies'])
	# pprint(annotations['sentences'][0]['tokens'])

	f = Digraph(file_id, format='png')

	for token in annotations['sentences'][0]['tokens']:
		f.node(token['word'])

	for edge in annotations['sentences'][0]['basic-dependencies']:
		if edge['dep'] != 'ROOT':
			f.edge(edge['governorGloss'],edge['dependentGloss'],label=edge['dep'],fontsize="11",ldistance="3.0")

	f.attr(label='\n'+text)
	f.render(cleanup=True,)
	pil_im = Image.open(file_id+'.gv.png', 'r')
	pil_im.show()



sentence = ["vorrei tre bruschette due crocchette e gli spaghetti alla carbonara"]

# for index,i in enumerate(sentence):
# 	dep_VIZ(str(index),i)

args = [sentence[0],frames]

if_successors(args)























'''
response = requests.get(tint_url+'text='+' '.join(artificial_list_commas)+'&format=json')
annotations = json.loads(response.text)

dep_VIZ('0',' '.join(artificial_list_commas))



def get_path(depGloss,path):
	if depGloss == 'ROOT':
		return 0
	else:
		for i in annotations['sentences'][0]['basic-dependencies']:
			if i['dependentGloss'] == depGloss:
				path.insert(0,i['dependentGloss'])
				path.insert(0,i['dep'])
				get_path(i['governorGloss'],path)

paths = []
for k,v in surface_to_frame.items():
	if 'nouns' in v and 'verb' in v:
		for n in v['nouns']:
			path = []
			get_path(n[0],path)
			paths.append(path)
print()	
print(paths)
'''

# #handling partial matches-------------
# response = requests.get(tint_url+'text='+lu+'&format=json')
# annotations = json.loads(response.text)
# pprint(annotations['sentences'][0]['tokens'])
# lu_subs = [[token['lemma'],token['index']] for token in annotations['sentences'][0]['tokens'] if token['pos'] != 'E+RD' or token['pos'] != 'E']

# print(n[0],lu,lu_subs)

# prop = 1.0/len(lu_subs)
# lu_index = 0
# for i in lu_subs:
# 	if i[0] == n[0]:
# 		lu_index = i[1]
# s_aug = n+[prop,lu_index]
# #--------------------------------------


#pprint(annotations['sentences'][0]['tokens'])

