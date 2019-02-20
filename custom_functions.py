import FSA_config 
import requests
import json
from pprint import pprint
import menu_utils


def state_entails(action,state):
	if action['pre'] != '':
		for i,j in zip(action['pre'],state):
			if i != j and i != '*':
				return False
	return True


#===========================================================================
debug = True

def attesa_suc(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	applicable_successors = []
	for s in successors_list:
		if state_entails(s,state) and curr_input == s['in']:
			applicable_successors.append({'name':s['name'],
										  'priority':FSA[s['name']]['priority']})
	
	if len(applicable_successors) == 0:
		applicable_successors.append({'name':successors_list[-1]['name'],
									  'priority':FSA[successors_list[-1]['name']]['priority']})

	return applicable_successors


def mapping(orig_sen_words_string,frames):

	tint_url = "http://localhost:8012/tint?"
	response = requests.get(tint_url+'text='+orig_sen_words_string+'&format=json')
	
	orig_sen_annotations_list = json.loads(response.text)

	e_index = [i['index'] for i in orig_sen_annotations_list['sentences'][0]['tokens'] if i['pos'] == 'CC']

	orig_sen_words_list = [i['word'] if i['index'] not in e_index else i['word']+'_*' for i in orig_sen_annotations_list['sentences'][0]['tokens']]

	#una lista vuota che verrà riempita solo in caso di terminazione senza errori di questa funzione
	mapped_frame = []

	# ====================VERBI - FRAME CLASSIFICATION PRELIMINARE===================
	
	#tramite pos raccolgo tutti i verbi
	pos_verb = ['V','V+PC','VM']
	verbs = [[token['word'],token['lemma'],token['index']] for token in orig_sen_annotations_list['sentences'][0]['tokens'] if token['pos'] in pos_verb]

	#se non ce ne sono -> error
	if len(verbs) < 1:
		if debug:
			print('Non ci sono verbi')
		return mapped_frame

	#altrimenti
	#tramite dep graph trovo la root
	for i in orig_sen_annotations_list['sentences'][0]['basic-dependencies']:
		root = ''
		if i['dep'] == 'ROOT':
			root = i['dependentGloss']
			break

	#se nn la trovo (possibile?) -> error
	if root == '':
		if debug:
			print('Non esiste una root')
		return mapped_frame

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
		if debug:
			print('La root non è un verbo')
		return mapped_frame

	#altrimenti
	#mappo root -> frame [tramite lu_v]
	frame_to_verb = {}
	frame_to_verb['*'] = verbs[0]
	for v in verbs:
		for f in frames:
			if v[1] in f['lu_v']:
				frame_to_verb[f['name']] = v


	if len(frame_to_verb) == 0:
		if debug:
			print('La root non è in lu_v di nessun frame')
		return mapped_frame

	if debug:
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
		if debug:
			print('Errore articoli')
		return mapped_frame

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

		if not check:
			frame_to_nouns['*'].append([seg[0],internal_words_string])

	if len(frame_to_nouns) == 1 and len(frame_to_nouns['*']) == 0:
		if debug:
			print('Non ci sono internal words')
		return mapped_frame
	
	if debug:
		pprint(frame_to_nouns)


	quantity_to_token = {1:[',','un',"un'",'uno','una','gli','il','i','le','la'],
						 2:['due'],
						 3:['tre'],
						 4:['quattro']}

	token_to_quantity = {t:k for k,v in quantity_to_token.items() for t in v}

	#incrocio frame_to_verbs e frame_to_nouns
	#e ottengo il matching finale tra i verbi e le internal words
	#riempio finalmente mapped_frame
	for k1 in frame_to_verb.keys():
		for k2 in frame_to_nouns.keys():
			if k1 == k2:
				for n in frame_to_nouns[k2]:
					mapped_frame.append([k1,frame_to_verb[k1][1],token_to_quantity[n[0]],n[1]])

	if debug:
		pprint(mapped_frame)


	return mapped_frame


def frame_mapping(orig_sen_words_string,frames):

	tint_url = "http://localhost:8012/tint?"
	response = requests.get(tint_url+'text='+orig_sen_words_string+'&format=json')
	
	orig_sen_annotations_list = json.loads(response.text)

	e_index = [i['index'] for i in orig_sen_annotations_list['sentences'][0]['tokens'] if i['pos'] == 'CC']

	orig_sen_words_list = [i['word'] if i['index'] not in e_index else i['word']+'_*' for i in orig_sen_annotations_list['sentences'][0]['tokens']]

	#una lista vuota che verrà riempita solo in caso di terminazione senza errori di questa funzione
	mapped_frame = []

	# ====================VERBI - FRAME CLASSIFICATION PRELIMINARE===================
	
	#tramite pos raccolgo tutti i verbi
	pos_verb = ['V','V+PC','VM']
	verbs = [[token['word'],token['lemma'],token['index']] for token in orig_sen_annotations_list['sentences'][0]['tokens'] if token['pos'] in pos_verb]

	#se non ce ne sono -> error
	if len(verbs) < 1:
		if debug:
			print('Non ci sono verbi')
		return mapped_frame

	#altrimenti
	#tramite dep graph trovo la root
	for i in orig_sen_annotations_list['sentences'][0]['basic-dependencies']:
		root = ''
		if i['dep'] == 'ROOT':
			root = i['dependentGloss']
			break

	#se nn la trovo (possibile?) -> error
	if root == '':
		if debug:
			print('Non esiste una root')
		return mapped_frame

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
		if debug:
			print('La root non è un verbo')
		return mapped_frame

	#altrimenti
	#mappo root -> frame [tramite lu_v]
	frame_to_verb = {}
	frame_to_verb['*'] = verbs[0]
	for v in verbs:
		for f in frames:
			if v[1] in f['lu_v']:
				frame_to_verb[f['name']] = v


	if len(frame_to_verb) == 0:
		if debug:
			print('La root non è in lu_v di nessun frame')
		return mapped_frame

	if debug:
		pprint(frame_to_verb)

	
	#=====================SOSTANTIVI - CORE ELEMENTS MAPPING CON FRAME CLASSIFICATION DEFINITIVA========================
	
	#preprocessa la frase originale
	standard_root = frame_to_verb[list(frame_to_verb)[1]][1]+' '
	prep_sen_words_string = preprocessing(orig_sen_words_string,standard_root)
	if debug:
		print(prep_sen_words_string)

	# dizionario aumentato della frase
	dict_list = augment_annotations(prep_sen_words_string)

	#trovo gli indici di tutti i det o nummod
	start = [['',0,'',0]]

	for index,i in enumerate(dict_list):
		if i['dep'] == 'det' or i['dep'] == 'nummod':
			if i['governorGloss'] == start[-1][2]:
				start[-1] = [i['dependentGloss'],i['dependent'],i['governorGloss'],i['dependent']-i['governor']]
			else:
				start.append([i['dependentGloss'],i['dependent'],i['governorGloss'],i['dependent']-i['governor']])

	start.append(['',index+2,'',0])
	start = start[1:]

	#se non c'è alcun det o nummod -> error
	if len(start) == 1:
		if debug:
			print('Errore articoli')
		return mapped_frame
	
	#altrimenti
    #trova la root
	root=''
	for i in dict_list:
		if i["dep"] == "ROOT":
			root = i["dependentGloss"]
			print("root --> ", root)

	if root=='':
		print('Errore root preprocessed !!!!!!')
		return 0


    # cerca il dobj
	obj_lemma = ''
	for i in dict_list:
		if (i["governorGloss"] == root and (i["dep"] == "dobj" or i["dep"] == "xcomp")):
			obj = i["dependentGloss"]
			obj_lemma = i["lemma"]
			obj_index = i["dependent"]
			print("obj ->", obj,  "-- lemma ->", obj_lemma)
    
    # se non c'è il dobj -> error                     
	if obj_lemma is '':
		if debug:
			print("Errore dobj")
		return mapped_frame


    # altrimenti
   	#creo la struttura per l'intero lessico
	struct = {s:[[0]*len(s.split(' ')),f['name']] for s in f['lu_s'] for f in frames}
                        
    #aggiorno la struttura in caso di SWE
	for x in struct.keys():
		hp_menu_sentence_dict = augment_annotations(standard_root+' un '+x)
		for numi, i in enumerate(hp_menu_sentence_dict):
			if numi>1 and i["lemma"] == obj_lemma and i["dep"] != "case" and i["dep"] != "conj":
				struct[x][0][numi-2] +=1

	if debug:
		print('\n'+str(1))
		pprint(struct)         
        

    #aggiorno la struttura in caso di MWE rispettata
	for k,v in struct.items():
		if len(v)>1 and v[0][-1] != 1 and v[0][0] == 1:
			inp = augment_annotations(standard_root+' un '+k)
			temp = {i['lemma']:i['dep'] for i in inp}
			for numr, r in enumerate(temp):
				if numr > 2 and temp[r] != 'case':
					indice_da_controllare = (obj_index -1 + numr -2)
					for k1,v1 in struct.items():
						for numi, i in enumerate(augment_annotations(standard_root+' un '+k1)):
							if numi>1 and i["lemma"] == dict_list[indice_da_controllare]["lemma"] :
								print(i["lemma"],dict_list[indice_da_controllare]["lemma"])
								v1[0][numi-2] +=1

    
	if debug:
		print('\n'+str(2))
		pprint(struct)   

    #aggiorno la struttura in caso di MWE non rispettata
	dep_check(struct,obj,dict_list)

	if debug:
		print('\n'+str(3))
		pprint(struct)   


	#mappo MWE (non unite) o SWE -> frame [tramite lu_s]
	frame_to_nouns = {'*':[]}
	for k,v in struct.items():
		if len(v[0])>1:
			if sum(v[0])>1:
				if v[1] not in frame_to_nouns:
					frame_to_nouns[v[1]] = [k]
				else:
					frame_to_nouns[v[1]].append(k)
			else:
				if 'CONFERMA' not in frame_to_nouns:
					frame_to_nouns['CONFERMA'] = [k]
				else:
					frame_to_nouns['CONFERMA'].append(k)
		else:
			if v[0][0] == 1:
				if v[1] not in frame_to_nouns:
					frame_to_nouns[v[1]] = [k]
				else:
					frame_to_nouns[v[1]].append(k)


	if len(frame_to_nouns) == 1 and len(frame_to_nouns['*']) == 0:
		if debug:
			print('Non ci sono internal words')
		return mapped_frame
	

	if debug:
		pprint(frame_to_nouns)


	# quantity_to_token = {1:[',','un',"un'",'uno','una','gli','il','i','le','la'],
	# 					 2:['due'],
	# 					 3:['tre'],
	# 					 4:['quattro']}

	# token_to_quantity = {t:k for k,v in quantity_to_token.items() for t in v}

	# #incrocio frame_to_verbs e frame_to_nouns
	# #e ottengo il matching finale tra i verbi e le internal words
	# #riempio finalmente mapped_frame
	# for k1 in frame_to_verb.keys():
	# 	for k2 in frame_to_nouns.keys():
	# 		if k1 == k2:
	# 			for n in frame_to_nouns[k2]:
	# 				mapped_frame.append([k1,frame_to_verb[k1][1],token_to_quantity[n[0]],n[1]])

	if debug:
		pprint(mapped_frame)


	return mapped_frame


def dep_check(struct,obj,list_dict):

    forb_dep = ['case','conj','det']
    path = [i['dependentGloss'] for i in list_dict if i['governorGloss'] == obj and i['dep'] not in forb_dep]

    for k,v in struct.items():
        for i in path:
            if i in k.split():
                v[0][k.split().index(i)] = 1    
        

def dfs(node,augm_annotations,path):
    curr_succs = []
    if 'succ' in node:
        curr_succs = [s for s in node['succ']]
        for s in curr_succs: 
            path.append(s)
            dfs(augm_annotations[s['own_index']],augm_annotations,path)


def augment_annotations(t):
    
	ult_dict = []
	path = "http://localhost:8012/tint?text=" + t + "&format=json"
	r=requests.get(path)
	dicti = json.loads(r.text)
    
	dependencies_list = ["dependentGloss", "dep", "governorGloss", "dependent",'governor']
	tokens_list = ["lemma", "features", "pos"]
    
	dicti["sentences"][0]["basic-dependencies"].sort(key=lambda x: x["dependent"])
            
	for numi, i in enumerate(dicti["sentences"][0]["basic-dependencies"]):
		ult_dict.append(dict())
		for elem in dicti["sentences"][0]["basic-dependencies"][numi]:
			if elem in dependencies_list:
				ult_dict[numi][elem] = dicti["sentences"][0]["basic-dependencies"][numi].get(elem)
			for token_elem in dicti["sentences"][0]["tokens"][numi]:
				if token_elem in tokens_list:
					ult_dict[numi][token_elem] = dicti["sentences"][0]["tokens"][numi].get(token_elem)
    
	for i in range(len(ult_dict)):
		succ = []
		curr_element = ult_dict[i]['dependentGloss'] 
		for j in range(len(ult_dict)):
			curr_token_parent = ult_dict[j]['governorGloss']
			if curr_token_parent == curr_element:
				succ.append({'dependentGloss':ult_dict[j]['dependentGloss'],
                    'dep':ult_dict[j]['dep'],
                    'dependent':ult_dict[j]['dependent'],
                    'own_index':j})
		ult_dict[i]['succ'] = list(succ)

	return ult_dict

def preprocessing(text,standard_root):

	#dizionario aumentato della frase
	augm = augment_annotations(text)

	#lista degli indici delle parole da rimuovere
	to_be_removed = []

	#trova 
	root,root_index = '',0
	dobj,dobj_index = '',0

	for i in augm:
		if i['dep'] == 'ROOT':
			root = i['dependentGloss']
			root_index = i['dependent']
			to_be_removed+=[i for i in range(1,root_index+1)]
		if i['dep'] == 'dobj':
 			dobj = i['lemma']
 			dobj_index = i['dependent']
            
	#controlla pop
	path = []
	if dobj == 'piatto' or dobj == 'porzione':
		dfs(augm[dobj_index-1],augm,path)

		path.append(augm[dobj_index-1])
		path.sort(key=lambda x: x["dependent"])

	for i in path:
		if i['dep'] == 'case':
			if i['dependent'] == dobj_index+1:
				to_be_removed+=[dobj_index,i['dependent']]


	#rimuovi tutto temp che c'è da rimuovere
	art_sentence = [i['dependentGloss'] for i in augm if i['dependent'] not in to_be_removed]


	return standard_root+' '.join(art_sentence)





































def inputframe_suc(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	frames = []
	for i in args[1]:
		if i['in'] not in frames and i['in'] != '':
			frames.append(i['in'])

	mapped_frame = frame_mapping(curr_input,frames)
	
	applicable_successors = []

	for f in mapped_frame:
		if f[0] != '*':
			for s in successors_list:
				if state_entails(s,state) and f[0] in s['name']:
					for i in range(f[2]):
						applicable_successors.append({'name':s['name'],
													  'input':f,
													  'priority':FSA[s['name']]['priority']})
	if len(applicable_successors) == 0:
		applicable_successors.append({'name':successors_list[-1]['name'],
									  'priority':FSA[successors_list[-1]['name']]['priority']})

	return applicable_successors


def prenotazione1_exe(args):
	menu_utils.print_menu(FSA_config.menu)

#TODO
def pagamento1_tur(args):
	turn = 'calcola il conto'
	return turn

def ordinazione_mem(args):
	curr_state_dict = args[0]
	FSA_config.short_term.append(curr_state_dict)
	FSA_config.long_term.append(curr_state_dict)

def riepilogo_tur(args):
	count = {}
	for state_dict in FSA_config.short_term:
		if state_dict['input'][3] not in count:
			count[state_dict['input'][3]] = 1
		else:
			count[state_dict['input'][3]]+= 1

	turn = []
	for k,v in count.items():
		turn += [str(v),k,',']
	turn = turn[:-1]
	turn.insert(0,'Hai ordinato')

	turn = ' '.join(turn)+'. Arriviamo subito!'

	return turn


def tr_oggetto_tur(args):
	count = {}
	for state_dict in FSA_config.short_term:
		if state_dict['input'][3] not in count:
			count[state_dict['input'][3]] = 1
		else:
			count[state_dict['input'][3]]+= 1

	turn = []
	for k,v in count.items():
		turn += [str(v),k,',']
	turn = turn[:-1]
	turn.insert(0,'Ecco a te, ')

	turn = ' '.join(turn)

	return turn

#TODO
def informazione_tur(args):
	print('informazione')