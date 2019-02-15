import requests
import json
from pprint import pprint
from graphviz import Digraph
from PIL import Image
from menu_utils import load_menu
from FSA_config import inputframe_suc

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

def dep_VIZ(file_id,text):
	
	# parser server url
	tint_url = "http://localhost:8012/tint?"
	response = requests.get(tint_url+'text='+text+'&format=json')
	annotations = json.loads(response.text)

	#pprint(annotations['sentences'][0]['basic-dependencies'])
	# pprint(annotations['sentences'][0]['tokens'])

	f = Digraph(file_id, format='png')

	for token in annotations['sentences'][0]['tokens']:
		f.node(token['word']+'_'+str(token['index']))

	for edge in annotations['sentences'][0]['basic-dependencies']:
		if edge['dep'] != 'ROOT':
			f.edge(edge['governorGloss']+'_'+str(edge['governor']),
					edge['dependentGloss']+'_'+str(edge['dependent']),
					label=edge['dep']+'_'+str(edge['dependent']-edge['governor']),
					fontsize="11",
					ldistance="3.0")

	f.attr(label='\n'+text)
	f.render(cleanup=True,)
	pil_im = Image.open(file_id+'.gv.png', 'r')
	pil_im.show()


text = ["potresti portarmi due piatti di spaghetti alla amatriciana due bruschette al pomodoro e un tiramisu alla nutella"]
text_list = text[0].split()

# for i in range(1,len(text_list)):
# 	dep_VIZ(str(i),' '.join(text_list[0:i]))

#args = [sentence[0],frames]

#if_successors(args)



def dfs(node):
	global augm_annotations,n_iter,predicate_path

	curr_succs = []
	if 'succ' in node:
		if node['dep'] == 'ROOT':
			try:
				curr_succs = [s for s in node['succ'] if s['dep'] == 'dobj']
			except:
				print('no dobj')
		else:
			curr_succs = [s for s in node['succ']]

		for s in curr_succs: 
			predicate_path.append(s)
			dfs(augm_annotations[s['own_index']])

#potresti portarmi due piatti di spaghetti alla amatriciana due bruschette al pomodoro e un tiramisu alla nutella
sentence = ["potresti portarmi due piatti di spaghetti, due bruschette, un tiramisu"]

dep_VIZ('0',sentence[0])

while True:

	tint_url = "http://localhost:8012/tint?"
	response = requests.get(tint_url+'text='+sentence[0]+'&format=json')
	annotations = json.loads(response.text)

	orig_sen_list = [{'dependentGloss':i['dependentGloss'],'sent_index':i['dependent']} for i in annotations['sentences'][0]['basic-dependencies']]
	orig_sen_list.sort(key=lambda x: x['sent_index'])

	augm_annotations = list(annotations['sentences'][0]['basic-dependencies'])

	for i in range(len(augm_annotations)):
		succ = []
		curr_element = augm_annotations[i]['dependentGloss'] 
		for j in range(len(augm_annotations)):
			curr_token_parent = augm_annotations[j]['governorGloss']
			if curr_token_parent == curr_element:
				succ.append({'childGloss':augm_annotations[j]['dependentGloss'],'dep':augm_annotations[j]['dep'],'sent_index':augm_annotations[j]['dependent'],'own_index':j})
		augm_annotations[i]['succ'] = list(succ)


	predicate_path = [{'childGloss':augm_annotations[0]['dependentGloss'],'sent_index':augm_annotations[0]['dependent'],'own_index':0}]
	n_iter = 0

	dfs(augm_annotations[0])

	predicate_path.sort(key=lambda x: x['sent_index'])

	print()
	pprint(predicate_path)

	token_to_remove = [i['sent_index'] for i in predicate_path[1:]]
	sentence_list = [i['dependentGloss'] for i in orig_sen_list if i['sent_index'] not in token_to_remove]
	sentence = [' '.join(sentence_list)]

	print()
	print(sentence[0])

	if len(predicate_path) == 1:
		break




