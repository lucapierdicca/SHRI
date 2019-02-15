import requests
import json
from pprint import pprint
from graphviz import Digraph
from PIL import Image
from menu_utils import load_menu
from FSA_config import inputframe_suc

menu = load_menu('menu.xml')

lexicon_O = [v['nome'].lower() for v in menu.values()]

menulbl_to_id = {t:i for i,t in enumerate(lexicon_O)}
id_to_menulbl = {v:k for k,v in menulbl_to_id.items()}
id_to_prezzo = {i:v['prezzo'] for i,v in enumerate(menu.values())}

tint_url = "http://localhost:8012/tint?"
for index,t in enumerate(lexicon_O):
	response = requests.get(tint_url+'text='+'un '+t+'&format=json')
	annotations = json.loads(response.text)
	lemmatized = []
	for i in annotations['sentences'][0]['tokens'][1:]:
		lemmatized.append(i['lemma'])
	
	lexicon_O[index] = ' '.join(lemmatized)

menulbllemma_to_id = {t:i for i,t in enumerate(lexicon_O)}

lexicon_TO = ['menu']
lexicon_I = ['antipasto','primo','secondo','dolce','antipasti','primi','secondi','dolci']
lexicon_P = ['conto']
lexicon_B = ['tavolo','posto','tavoli','posti']

frames = [{'in':{'name':'ORDINAZIONE','lu_v':['mangiare','ordinare','volere','chiedere','portare','prendere'],'lu_s':lexicon_O,'ce':['entity']}},
	   	  {'in':{'name':'TR_OGGETTO','lu_v':['portare'],'lu_s':lexicon_TO,'ce':['theme']}},
	   	  {'in':{'name':'INFORMAZIONE','lu_v':['elencare','essere','avere','dire'],'lu_s':lexicon_I,'ce':['content']}},
	   	  {'in':{'name':'PAGAMENTO','lu_v':['portare','pagare','saldare'],'lu_s':lexicon_P,'ce':['good']}},
	   	  {'in':{'name':'PRENOTAZIONE','lu_v':['essere','prenotare'],'lu_s':lexicon_B,'ce':['services']}}]

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



def frame_mapping(orig_sen_words_string):

	tint_url = "http://localhost:8012/tint?"
	response = requests.get(tint_url+'text='+orig_sen_words_string+'&format=json')
	
	orig_sen_annotations_list = json.loads(response.text)

	e_index = [i['index'] for i in orig_sen_annotations_list['sentences'][0]['tokens'] if i['pos'] == 'CC']

	orig_sen_words_list = [i['word'] if i['index'] not in e_index else i['word']+'_*' for i in orig_sen_annotations_list['sentences'][0]['tokens']]

	
	# ====================VERBI - FRAME CLASSIFICATION PRELIMINARE===================
	
	#tramite pos raccolgo tutti i verbi
	pos_verb = ['V','V+PC','VM']
	verbs = [[token['word'],token['lemma'],token['index']] for token in orig_sen_annotations_list['sentences'][0]['tokens'] if token['pos'] in pos_verb]

	#se non ce ne sono -> error
	if len(verbs) < 1:
		print('Non ci sono verbi')
		return 1,''

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
		return 1,''

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
		return 1,''

	#altrimenti
	#mappo root -> frame [tramite lu_v]
	frame_to_verb = {}
	frame_to_verb['*'] = verbs[0]
	for v in verbs:
		for f in frames:
			if v[1] in f['lu_v']:
				frame_to_verb[f['name']] = v


	if len(frame_to_verb) == 0:
		print('La root non è in lu_v di nessun frame')
		return 1,''

	pprint(frame_to_verb)

	
	#=====================SOSTANTIVI - CORE ELEMENTS MAPPING CON FRAME CLASSIFICATION DEFINITIVA========================

	#trovo gli indici di tutti i det o nummod
	start = [['',0,'',0]]
	orig_sen_annotations_list['sentences'][0]['basic-dependencies'].sort(key=lambda x: x['dependent'])

	for index,i in enumerate(orig_sen_annotations_list['sentences'][0]['basic-dependencies']):
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
		return 2,''

	#altrimenti
	#estraggo dalla frase tutto ciò che è compreso tra gli index dei det/nummod consecutivamente fino alla fine
	#le possibili MWE o anche SWE
	segment_ranges = [(start[i][1],start[i+1][1])for i in range(len(start)-1)]

	segment_lists = [orig_sen_words_list[i[0]-1:i[1]-1] for i in segment_ranges]


	#mappo MWE (non unite) o SWE -> frame [tramite lu_s]
	frame_to_nouns = {'*':[]}
	for seg in segment_lists:
		check = False
		internal_words_list = [word for index,word in enumerate(seg) if index != 0 and '_*' not in word]
		internal_words_string = ' '.join(internal_words_list)

		
		#lemmatization-------------------------
		for index,t in enumerate([internal_words_string]):
			response = requests.get(tint_url+'text='+'un '+t+'&format=json')
			annotations = json.loads(response.text)
			lemmatized = []
			for i in annotations['sentences'][0]['tokens'][1:]:
				lemmatized.append(i['lemma'])
			
			internal_words_string_lemma = ' '.join(lemmatized)
		#--------------------------------------

		for f in frames:
			for lex in f['lu_s']:
				if internal_words_string_lemma == lex:
					check=True
					if f['name'] not in frame_to_nouns:
						frame_to_nouns[f['name']] = [[seg[0],internal_words_string]]
					else:
						frame_to_nouns[f['name']].append([seg[0],internal_words_string])
					break
				break

		if not check:
			frame_to_nouns['*'].append([seg[0],internal_words_string])

	if len(frame_to_nouns) == 1 and len(frame_to_nouns['*']) == 0:
		print('Non ci sono internal words')
		return 2,''

	pprint(frame_to_nouns)


	quantity_to_token = {1:[',','un','uno','una','gli','il','i','le','la'],
						 2:['due'],
						 3:['tre'],
						 4:['quattro']}

	token_to_quantity = {t:k for k,v in quantity_to_token.items() for t in v}

	#incrocio frame_to_verbs e frame_to_nouns
	#e ottengo il matching finale tra i verbi e le internal words
	mapped_frame = []
	for k1 in frame_to_verb.keys():
		for k2 in frame_to_nouns.keys():
			if k1 == k2:
				for n in frame_to_nouns[k2]:
					mapped_frame.append([k1,frame_to_verb[k1][1],token_to_quantity[n[0]],n[1]])

	pprint(mapped_frame)


	return 0,mapped_frame


def inputframe_suc(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	frames = []
	for i in args[1]:
		if i['in'] not in frames and i['in'] != '':
			frames.append(i['in'])

	result,mapped_frame = frame_mapping(curr_input)
	
	applicable_successors = []
	if result > 0:
		applicable_successors.append({'name':successors_list[-1]['name'],
							  'priority':FSA[successors_list[-1]['name']]['priority']})
	else:
		for f in mapped_frame:
			for s in successors_list:
				if state_entails(s,state) and f[0] in s['name']:
					for i in range(f[2]):
						applicable_successors.append({'name':s['name'],
													  'input':f,
													  'priority':FSA[s['name']]['priority']})	



			


#potresti portarmi due piatti di spaghetti alla amatriciana due bruschette al pomodoro e un piatto di tonnarelli alla cacio e pep

sentence = "potresti portarmi due piatti di spaghetti alla amatriciana due bruschette con pomodoro e un piatto di tonnarelli alla cacio e pepe"

dep_VIZ('0',sentence)

addition(sentence)
