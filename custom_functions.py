import FSA_config 
import requests
import json
from pprint import pprint
import menu_utils
import random

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
	
	orig_sen_aug_ann_list = json.loads(response.text)

	e_index = [i['index'] for i in orig_sen_aug_ann_list['sentences'][0]['tokens'] if i['pos'] == 'CC']

	orig_sen_words_list = [i['word'] if i['index'] not in e_index else i['word']+'_*' for i in orig_sen_aug_ann_list['sentences'][0]['tokens']]

	#una lista vuota che verrà riempita solo in caso di terminazione senza errori di questa funzione
	mapped_frame = []

	# ====================VERBI - FRAME CLASSIFICATION PRELIMINARE===================
	
	#tramite pos raccolgo tutti i verbi
	pos_verb = ['V','V+PC','VM']
	verbs = [[token['word'],token['lemma'],token['index']] for token in orig_sen_aug_ann_list['sentences'][0]['tokens'] if token['pos'] in pos_verb]

	#se non ce ne sono -> error
	if len(verbs) < 1:
		if debug:
			print('Non ci sono verbi')
		return mapped_frame

	#altrimenti
	#tramite dep graph trovo la root
	for i in orig_sen_aug_ann_list['sentences'][0]['basic-dependencies']:
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
	orig_sen_aug_ann_list['sentences'][0]['basic-dependencies'].sort(key=lambda x: x['dependent'])

	for index,i in enumerate(orig_sen_aug_ann_list['sentences'][0]['basic-dependencies']):
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


def tavola_frame_mapping(orig_sen_words_string,frames):

	tint_url = "http://localhost:8012/tint?"
	response = requests.get(tint_url+'text='+orig_sen_words_string+'&format=json')
	
	orig_sen_aug_ann_list = json.loads(response.text)

	e_index = [i['index'] for i in orig_sen_aug_ann_list['sentences'][0]['tokens'] if i['pos'] == 'CC']

	orig_sen_words_list = [i['word'] if i['index'] not in e_index else i['word']+'_*' for i in orig_sen_aug_ann_list['sentences'][0]['tokens']]

	#una lista vuota che verrà riempita solo in caso di terminazione senza errori di questa funzione
	mapped_frame = []

	# ====================VERBI - FRAME CLASSIFICATION PRELIMINARE===================
	
	#tramite pos raccolgo tutti i verbi
	pos_verb = ['V','V+PC','VM']
	verbs = [[token['word'],token['lemma'],token['index']] for token in orig_sen_aug_ann_list['sentences'][0]['tokens'] if token['pos'] in pos_verb]

	#se non ce ne sono -> error
	if len(verbs) < 1:
		if debug:
			print('Non ci sono verbi')
		return mapped_frame

	#altrimenti
	#tramite dep graph trovo la root
	for i in orig_sen_aug_ann_list['sentences'][0]['basic-dependencies']:
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
	frame_to_verb['NOIN'] = verbs[0]
	for v in verbs:
		for f in frames:
			if v[1] in f['lu_v']:
				frame_to_verb[f['name']] = v


	# if len(frame_to_verb) == 0:
	# 	if debug:
	# 		print('La root non è in lu_v di nessun frame')
	# 	return mapped_frame

	if debug:
		pprint(frame_to_verb)

	
	#=====================SOSTANTIVI - CORE ELEMENTS MAPPING CON FRAME CLASSIFICATION DEFINITIVA========================
	
	#preprocessa la frase originale
	if list(frame_to_verb)[0] == 'ORDINAZIONE':
		standard_root = 'portami '
	else:
		standard_root = frame_to_verb[list(frame_to_verb)[0]][1]+' '

	prep_sen_words_string = preprocess(orig_sen_words_string,standard_root)
	
	
	if debug:
		#dep_VIZ('0',prep_sen_words_string)
		print(prep_sen_words_string)


	# dizionario aumentato della frase
	prep_sen_ann_list = augment_annotations(prep_sen_words_string)

	#trovo gli indici di tutti i det o nummod
	start = [['',0,'',0]]

	for index,i in enumerate(prep_sen_ann_list):
		if i['dep'] == 'det' or i['dep'] == 'nummod':
			if i['governorGloss'] == start[-1][2]:
				start[-1] = [i['dep'],i['dependentGloss'],i['dependent'],i['governorGloss'],i['dependent']-i['governor']]
			else:
				start.append([i['dep'],i['dependentGloss'],i['dependent'],i['governorGloss'],i['dependent']-i['governor']])

	start.append(['','',index+2,'',0])
	start = start[1:]
	if debug: print(start)
	
	#se non c'è alcun det o nummod -> error
	# if len(start) == 1:
	# 	if debug:
	# 		print('Errore articoli')
	# 	return mapped_frame
	
	#altrimenti
    #trova la root
	root=''
	for i in prep_sen_ann_list:
		if i["dep"] == "ROOT":
			root = i["dependentGloss"]
			print("root --> ", root)

	if root=='':
		print('Errore root preprocessed !!!!!!')
		return 0


    # cerca il dobj
	obj_lemma = ''
	for i in prep_sen_ann_list:
		if (i["governorGloss"] == root and (i["dep"] == "dobj" or i["dep"] == "xcomp")):
			obj = i["dependentGloss"]
			obj_lemma = i["lemma"]
			obj_sen_index = i["dependent"]
			print("obj ->", obj,  "-- lemma ->", obj_lemma)
    
    # se non c'è il dobj -> error                     
	if obj_lemma is '':
		if debug:
			print("Errore dobj")
		return mapped_frame


    # altrimenti
   	#creo la struttura per l'intero lessico
	struct = {s:[[0]*len(s.split(' ')),f['name']] for f in frames for s in f['lu_s'] }
                
    #aggiorno la struttura in caso di SWE
	for x in struct.keys():
		hp_menu_sentence_dict = augment_annotations(standard_root+' un '+x)
		for numi, i in enumerate(hp_menu_sentence_dict):
			if numi>1 and i["lemma"] == obj_lemma and i["dep"] != "case" and i["dep"] != "conj":
				struct[x][0][numi-2] +=1

	if debug:
		print('\n'+str(1))
		pprint(struct)         
        
	#aggiorno la struttura in caso di MWE elastiche che rispettano l'ordine 
	raccogli = [k for k,v in struct.items() if len(v)>1 and v[0][0] == 1 and v[0][-1] != 1]

	for k in raccogli:
		fake_sen_ann_list = augment_annotations(standard_root+' un '+k)[3:]
		fake_len = len(fake_sen_ann_list)+1
		fake_sen_ann_list = [i for i in fake_sen_ann_list if i['dep'] != 'case' and i['dep'] != 'det']
		sliced_prep_sen_ann_list = [i for i in prep_sen_ann_list[obj_sen_index:] if i['dep'] != 'case' and i['dep'] != 'det']

		if len(sliced_prep_sen_ann_list)>0:
			if fake_sen_ann_list[0]['lemma'] == sliced_prep_sen_ann_list[0]['lemma']:
				struct[k][0][fake_len-1] = 1

    
	if debug:
		print('\n'+str(2))
		pprint(struct)   

    #aggiorno la struttura in caso di MWE elastiche che non rispettano l'ordine
	dep_check(struct,obj_sen_index,prep_sen_ann_list)

	if debug:
		print('\n'+str(3))
		pprint(struct)   


	internal_words_check = 0
	for k,v in struct.items():
		internal_words_check += sum(v[0])
	
	frame_to_nouns = {}
	if internal_words_check>0:
		for k,v in struct.items():
			if len(v[0])>1:
				if sum(v[0])>1:
					if v[1] not in frame_to_nouns:
						frame_to_nouns[v[1]] = [[start[0][1],k]]
					else:
						frame_to_nouns[v[1]].append([start[0][1],k])
				elif sum(v[0])==1:
					if v[1]+'_CONFERMA' not in frame_to_nouns:
						frame_to_nouns[v[1]+'_CONFERMA'] = [[start[0][1],k]]
					else:
						frame_to_nouns[v[1]+'_CONFERMA'].append([start[0][1],k])
			else:
				if v[0][0] == 1:
					if v[1] not in frame_to_nouns:
						frame_to_nouns[v[1]] = [[start[0][1],k]]
					else:
						frame_to_nouns[v[1]].append([start[0][1],k])
	else:
		frame_to_nouns['NOIN'] = [[start[0][1],obj]]


	# if len(frame_to_nouns) == 0:
	# 	frame_to_nouns['*'] = [obj]
	# 	if debug:
	# 		print('Non ci sono internal words')
	# 	return mapped_frame
	

	if debug:
		pprint(frame_to_nouns)

	quantity_to_token_ord = {1:['un',"un'",'uno','una','il','la','lo',"l'",'gli','i','le'],
						 	2:['due'],
						 	3:['tre'],
						 	4:['quattro']}

	quantity_to_token_tr = {1:['un',"un'",'uno','una','il','la','lo',"l'"],
							2:['due'],
							3:['tre'],
							4:['quattro']}

	token_to_quantity_ord = {t:k for k,v in quantity_to_token_ord.items() for t in v}
	token_to_quantity_tr = {t:k for k,v in quantity_to_token_tr.items() for t in v}

	for k,v in frame_to_nouns.items():
		if k == 'ORDINAZIONE' or k == 'ORDINAZIONE_CONFERMA' or k=='INFORMAZIONE' or k=='NOIN':
			t = token_to_quantity_ord
		elif k == 'TR_OGGETTO':
			t = token_to_quantity_tr
		for i in v:
			if i[0] in t:
				i[0] = t[i[0]]
			else:
				i[0] = -1

	#incrocio frame_to_verbs e frame_to_nouns
	#e ottengo il matching finale tra i verbi e le internal words
	#riempio finalmente mapped_frame
	for k1 in frame_to_verb.keys():
		for k2 in frame_to_nouns.keys():
			if k1 in k2:
				mapped_frame.append([k2,frame_to_verb[k1][1],frame_to_nouns[k2]])

	ordinazione_check = False
	for i in mapped_frame:
		if i[0] == 'ORDINAZIONE':
			ordinazione_check=True
	
	if ordinazione_check:
		mapped_frame=[i for i in mapped_frame if i[0] != 'ORDINAZIONE_CONFERMA']


	if debug:
		pprint(mapped_frame)


	return mapped_frame


def dep_check(struct,obj_index,augm_annotations):


    #forb_dep = ['case','conj','det']
    #path = [i['dependentGloss'] for i in list_dict if i['governorGloss'] == obj and i['dep'] not in forb_dep]

    path = []
    dfs(augm_annotations[obj_index-1],augm_annotations,path)
    path = [i['lemma'] for i in path if i['dep'] != 'case']

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
                    'own_index':j,
                    'lemma':ult_dict[j]['lemma']})
		ult_dict[i]['succ'] = list(succ)

	return ult_dict


def preprocess(text,standard_root):

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


def tavola_suc(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	frames = []
	for i in args[1]:
		if i['in'] not in frames and i['in'] != '':
			frames.append(i['in'])

	mapped_frame = tavola_frame_mapping(curr_input,frames)
	
	applicable_successors = []

	for f in mapped_frame:
		this_input = [f[1],f[2]]
		for s in successors_list:
			if state_entails(s,state) and f[0] in s['name']:
				applicable_successors.append({'name':s['name'],
											  'input':this_input,
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

#TODO
def tr_oggetto_tur(args):
	client_request = args[0]
	turn=''
	return turn

#TODO
def informazione_tur(args):
	print('informazione')

#TODO
def ord_iter_tur(args):
	turns = ['Sì, poi?','Ok, poi?','Sì certo, poi?']
	index = random.randint(0,len(turns)-1)

	return turns[index]

#TODO
def ord_iter_frame_mapping(orig_sen_words_string,frames):

	orig_sen_words_string = curr_input
	orig_sen_aug_ann_list = augment_annotations(orig_sen_words_string)

	mapped_frame = []

	for i in orig_sen_aug_ann_list:
		if i['dep']=='ROOT':
			root = i['dependentGloss']
			root_index = i['dependent']
			root_pos = i['pos']
		if i['dep']=='dobj':
			dobj = i['dependentGloss']
			dobj_index = i['dependent'] 

	standard_root = 'portami '

	if root_pos == 'V':
		prep_sen_words_string = preprocess(orig_sen_words_string,standard_root)
	else:
		det = ''
		for i in orig_sen_aug_ann_list:
			if i['dep'] == 'nummod' or i['dep'] == 'det':
				if i['governorGloss'] == root:
					det = i['dependentGloss']
		
		if det == '': det='un'

		internal_word,internal_word_index = '',0
		for i in orig_sen_aug_ann_list:
			if i['dep'] != 'case' and i['dep'] != 'det':
				for f in frames:
					for l in f['lu_s']:
						if i['lemma'] in ' '.join([i['lemma'] for i in augment_annotations('portami un '+l)]):
							internal_word=i['dependentGloss']
							internal_word_index=i['dependent']


		prep_sen_words_string = standard_root+det+' '



def ord_iter_succ(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	frames = []
	for i in args[1]:
		if i['in'] not in frames and i['in'] != '':
			frames.append(i['in'])

	mapped_frame = ord_iter_frame_mapping(curr_input,frames)
	
	applicable_successors = []

	for f in mapped_frame:
		this_input = [f[1],f[2]]
		for s in successors_list:
			if state_entails(s,state) and f[0] in s['name']:
				applicable_successors.append({'name':s['name'],
											  'input':this_input,
											  'priority':FSA[s['name']]['priority']})
	if len(applicable_successors) == 0:
		applicable_successors.append({'name':successors_list[-1]['name'],
									  'priority':FSA[successors_list[-1]['name']]['priority']})

	return applicable_successors

#TODO
def ord_conf_tur(args):
	return 0

#TODO
def ord_conf_succ(args):
	return 0

#TODO
def help_succ(args):
	return 0

def benvenuto_succ(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	orig_sen_words_string = curr_input
	orig_sen_aug_ann_list = augment_annotations(orig_sen_words_string)

	lex = {'uno':1,'solo':1,'due':2,'tre':3,'quattro':4}
	orig_sen_aug_ann_list.sort(key=lambda x:x['dependent'])

	tokens = [i for i in orig_sen_aug_ann_list if i['pos'] == 'N' or i['dep'] == 'advmod']
	tokens.sort(key=lambda x:x['dependent'])
	
	this_input,case,in_lex,is_num = '',False,False,0

	if len(tokens) > 0:
		for i in tokens:
			if i['dependentGloss'] in lex: in_lex,this_input=True,lex[i['dependentGloss']]
			if i['pos']=='N': is_num=True

	if in_lex: case=1
	elif is_num: case=2

	applicable_successors = []
	for s in successors_list:
		if state_entails(s,state) and case == s['in']:
			applicable_successors.append({'name':s['name'],
										  'input':this_input,
										  'priority':FSA[s['name']]['priority']})
	
	if len(applicable_successors) == 0:
		applicable_successors.append({'name':successors_list[-1]['name'],
									  'priority':FSA[successors_list[-1]['name']]['priority']})

	return applicable_successors


def prenotazione1_tur(args):
	this_input = args[0]

	if this_input == 1:
		turn = 'Prego il tavolo 1 è libero. Questo è il nostro menù, quando sarai pronto chiamami.'
	else:
		turn = 'Prego il tavolo 1 è libero. Questo è il nostro menù, quando sarete pronti chiamatemi.'

	return turn


def noin_tur(args):
	this_input = args[0]

	verb = this_input[0]
	qty = this_input[1][0][0]
	obj = this_input[1][0][1]
	
	if qty >=1:
		turn = 'Mi dispiace ma non posso '+verb+' '+str(qty)+' '+obj
	else:
		urn = 'Mi dispiace ma non posso '+verb+' '+obj

	return turn