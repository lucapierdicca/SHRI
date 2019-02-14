import requests
import json
from pprint import pprint
from graphviz import Digraph
from PIL import Image
from menu_utils import load_menu
from FSA_config import inputframe_suc

menu = load_menu('menu.xml')

lexicon_O = [v['nome'].lower() for v in menu.values()]
lexicon_TO = ['menu']
lexicon_I = ['antipasto','primo','secondo','dolce','antipasti','primi','secondi','dolci']
lexicon_P = ['conto']
lexicon_B = ['tavolo','posto','tavoli','posti']

frames = [{'name':'ORDINAZIONE','lu_v':['mangiare','ordinare','volere','chiedere','portare','prendere'],'lu_s':lexicon_O,'ce':['entity']},
	   	  {'name':'TR_OGGETTO','lu_v':['portare'],'lu_s':lexicon_TO,'ce':['theme']},
	   	  {'name':'INFORMAZIONE','lu_v':['essere','avere','dire'],'lu_s':lexicon_I,'ce':['content']},
	   	  {'name':'PAGAMENTO','lu_v':['portare','pagare','saldare'],'lu_s':lexicon_P,'ce':['good']},
	   	  {'name':'PRENOTAZIONE','lu_v':['essere','prenotare'],'lu_s':lexicon_B,'ce':['services']}]

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

def dfs(node,augm_annotations,path):

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
			path.append(s)
			dfs(augm_annotations[s['own_index']])



def addition(orig_sen_words_string):
	tint_url = "http://localhost:8012/tint?"
	response = requests.get(tint_url+'text='+orig_sen_words_string+'&format=json')
	
	orig_sen_annotations_list = json.loads(response.text)

	orig_sen_words_list = [i['word'] for i in orig_sen_annotations_list['sentences'][0]['tokens']]

	
	# ====================VERBI - FRAME CLASSIFICATION PRELIMINARE===================
	
	#tramite pos raccolgo tutti i verbi
	pos_verb = ['V','V+PC','VM']
	verbs = [[token['word'],token['lemma'],token['index']] for token in orig_sen_annotations_list['sentences'][0]['tokens'] if token['pos'] in pos_verb]

	#se non ce ne sono -> error
	if len(verbs) < 1:
		print('Non ci sono verbi')
		return 1

	#altrimenti
	#tramite dep graph trovo la root
	for i in orig_sen_annotations_list['sentences'][0]['basic-dependencies']:
		root = ''
		if i['dep'] == 'ROOT':
			root = i['dependentGloss']
			break

	#se nn la trovo (possibile?) -> error
	if root == '':
		print('Non esiste una root')
		return 1

	#altrimenti
	#cerco la root all'interno della lista dei verbi
	for v in verbs:
		if v[0] == root:
			v.append(1)
		else:
			v.append(0)

	#elimino tutti i verbi tranne la root
	verbs = [i[:-1] for i in verbs if i[-1] != 0]

	#se non c'è più nulla nella lista dei verbi -> error
	if len(verbs) == 0:
		print('La root non è un verbo')
		return 1

	#altrimenti
	#mappo root -> frame [traimite lu_v]
	frame_to_verb = {}
	for v in verbs:
		for f in frames:
			if v[1] in f['lu_v']:
				frame_to_verb[f['name']] = v

	pprint(frame_to_verb)

	#=====================SOSTANTIVI - CORE ELEMENTS MAPPING CON FRAME CLASIFICATION DEFINITIVA========================

	orig_sen_annotations_dep_aug_list = list(orig_sen_annotations_list['sentences'][0]['basic-dependencies'])

	for i in range(len(orig_sen_annotations_dep_aug_list)):
		succ = []
		curr_element = orig_sen_annotations_dep_aug_list[i]['dependentGloss'] 
		for j in range(len(orig_sen_annotations_dep_aug_list)):
			curr_token_parent = orig_sen_annotations_dep_aug_list[j]['governorGloss']
			if curr_token_parent == curr_element:
				succ.append({'childGloss':orig_sen_annotations_dep_aug_list[j]['dependentGloss'],
							'dep':orig_sen_annotations_dep_aug_list[j]['dep'],
							'sent_index':orig_sen_annotations_dep_aug_list[j]['dependent'],
							'own_index':j})
		orig_sen_annotations_dep_aug_list[i]['succ'] = list(succ)


	#trovo gli indici di tutti i det o nummod
	start = [['',0,'',0]]
	orig_sen_annotations_dep_aug_list.sort(key=lambda x: x['dependent'])

	for index,i in enumerate(orig_sen_annotations_dep_aug_list):
		if i['dep'] == 'det' or i['dep'] == 'nummod':
			if i['governorGloss'] == start[-1][2]:
				start[-1] = [i['dependentGloss'],i['dependent'],i['governorGloss'],i['dependent']-i['governor']]
			else:
				start.append([i['dependentGloss'],i['dependent'],i['governorGloss'],i['dependent']-i['governor']])

	start.append(['',index+2,'',0])
	start = start[1:]

	#se non c'è alcun det o nummod -> error
	if len(start) == 1:
		print('Errore articoli')
		return 2

	#altrimenti
	#estraggo dalla frase tutto ciò che è compreso tra gli index dei det/nummod consecutivamente fino alla fine
	#le possibili MWE o anche SWE
	segment_ranges = [(start[i][1],start[i+1][1])for i in range(len(start)-1)]

	segment_strings = [[orig_sen_words_list[i[0]-1:i[1]-1]] for i in segment_ranges]

	print(segment_ranges)

	print(segment_strings)

	#mappo MWE (non unite) o SWE -> frame [tramite lu_s]
	#TODO




sentence = "potresti portarmi due piatti di spaghetti alla amatriciana due bruschette al pomodoro e un tiramisu alla nutella"

dep_VIZ('0',sentence)

addition(sentence)
