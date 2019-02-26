import FSA_config 
import requests
import json
from pprint import pprint
import menu_utils
import random
import re
import os,signal
import time

def state_entails(action,state):
	if action['pre'] != '':
		for i,j in zip(action['pre'],state):
			if i != j and i != '*':
				return False
	return True


#===========================================================================
#===========================================================================

debug = False

menu_check = False

comanda_mod = 0


def attesa_suc(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	applicable_successors = []
	for s in successors_list:
		if state_entails(s,state) and curr_input == s['in']:
			applicable_successors.append({'name':s['name'],
										  'input':curr_input,
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
	qty = [['',0,'',0]]
	orig_sen_aug_ann_list['sentences'][0]['basic-dependencies'].sort(key=lambda x: x['dependent'])

	for index,i in enumerate(orig_sen_aug_ann_list['sentences'][0]['basic-dependencies']):
		if i['dep'] == 'det' or i['dep'] == 'nummod':
			if i['governorGloss'] == qty[-1][2]:
				qty[-1] = [i['dependentGloss'],i['dependent'],i['governorGloss'],i['dependent']-i['governor']]
			else:
				qty.append([i['dependentGloss'],i['dependent'],i['governorGloss'],i['dependent']-i['governor']])

	qty.append(['',index+2,'',0])
	qty = qty[1:]

	#se non c'è alcun det o nummod -> error
	if len(qty) == 1:
		if debug:
			print('Errore articoli')
		return mapped_frame

	#altrimenti
	#estraggo dalla frase tutto ciò che è compreso tra gli index dei det/nummod consecutivamente fino alla fine
	#le possibili MWE o anche SWE
	segment_ranges = [(qty[i][1],qty[i+1][1])for i in range(len(qty)-1)]

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

	#lista delle mappature 
	mapped_frame = []

	#se l'input è vuoto -> error
	if orig_sen_words_string == '' or orig_sen_words_string == None:
		return mapped_frame

	if re.search('(^no$|^no .*|^basta($| così.*)|puoi andare.*|^niente.*)',orig_sen_words_string) != None:
		mapped_frame.append(['RIEPILOGO','',''])
		return mapped_frame


	#altrimenti fai tutto il resto
	orig_sen_ann_list = augment_annotations(orig_sen_words_string)
	if orig_sen_ann_list == 1:
		return mapped_frame


	# ====================VERBI - FRAME CLASSIFICATION PRELIMINARE===================
	
	#tramite pos raccolgo tutti i verbi
	pos_verb = ['V','V+PC','VM']
	verbs = [[token['dependentGloss'],token['lemma'],token['dependent']] for token in orig_sen_ann_list if token['pos'] in pos_verb]

	#se non ce ne sono -> error
	if len(verbs) < 1:
		if debug:
			print('Non ci sono verbi')
		return mapped_frame

	#altrimenti
	#tramite dep graph trovo la root
	for i in orig_sen_ann_list:
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


	if debug:
		pprint(frame_to_verb)

	
	#=====================SOSTANTIVI - CORE ELEMENTS MAPPING CON FRAME CLASSIFICATION DEFINITIVA========================
	
	# #preprocesso la frase originale
	# if list(frame_to_verb)[-1] == 'ORDINAZIONE':
	# 	standard_root = 'portami '
	# else:
	# 	standard_root = frame_to_verb[list(frame_to_verb)[0]][1]+' '
	# prep_sen_words_string = preprocess(orig_sen_words_string,standard_root)
	
	
	# if debug: print(prep_sen_words_string)

	#annoto la nuova frase preprocessata
	standard_root = frame_to_verb[list(frame_to_verb)[0]][1]
	prep_sen_ann_list = orig_sen_ann_list#augment_annotations(prep_sen_words_string)


	#trovo gli indici di tutti i det o nummod
	qty = [['','',0,'',0]]
	for index,i in enumerate(prep_sen_ann_list):
		if i['dep'] == 'det' or i['dep'] == 'nummod':
			if i['governorGloss'] == qty[-1][3]:
				qty[-1] = [i['dep'],i['dependentGloss'],i['dependent'],i['governorGloss'],i['dependent']-i['governor']]
			else:
				qty.append([i['dep'],i['dependentGloss'],i['dependent'],i['governorGloss'],i['dependent']-i['governor']])

	qty.append(['','',index+2,'',0])
	qty = qty[1:]
	if debug: print(qty)
	

	#se c'è un nummod e questo non è nelle allowed qty -> error (QTY)
	if qty[0][0] == 'nummod':
		allowed_qty = ['uno','una','due','tre','quattro']
		if qty[0][1] not in allowed_qty:
			if debug: print('Errore quantità')
			mapped_frame.append(['QTY','',''])
			return mapped_frame
	

	#altrimenti
    #trova la root
	root=''
	for i in prep_sen_ann_list:
		if i["dep"] == "ROOT":
			root = i["dependentGloss"]
			


	#se la root non c'è allora -> error
	if root=='':
		if debug: print('Non esiste una preprocessed root ... ATTENTO')
		return mapped_frame

	#altrimenti
    # cerca il dobj
	obj_lemma = ''
	for i in prep_sen_ann_list:
		if (i["governorGloss"] == root and (i["dep"] == "dobj" or i["dep"] == "xcomp")):
			obj = i["dependentGloss"]
			obj_lemma = i["lemma"]
			obj_sen_index = i["dependent"]
    
    # se non c'è il dobj -> error                     
	if obj_lemma is '':
		if debug: print("Errore dobj")
		return mapped_frame


	if debug: print("root: %s - obj: %s - obj_lemma: %s" % (root,obj,obj_lemma))

    # altrimenti
   	#creo la struttura per l'intero lessico
	struct = {s:[[0]*len(s.split(' ')),['']*len(s.split(' ')),f['name']] for f in frames for s in f['lu_s'] }
                
    #aggiorno la struttura in caso di SWE
	for x in struct.keys():
		hp_menu_sentence_dict = augment_annotations(standard_root+' un '+x)
		for numi, i in enumerate(hp_menu_sentence_dict):
			if numi>1 and i["lemma"] == obj_lemma and i["dep"] != "case" and i["dep"] != "conj":
				struct[x][0][numi-2] +=1
				struct[x][1][numi-2] = obj

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
				struct[k][1][fake_len-1] = sliced_prep_sen_ann_list[0]['dependentGloss']

	if debug:
		print('\n'+str(2))
		pprint(struct)   

    #aggiorno la struttura in caso di MWE elastiche che non rispettano l'ordine
	dep_check(struct,obj_sen_index,prep_sen_ann_list)

	if debug:
		print('\n'+str(3))
		pprint(struct)   

	#check sull'effettiva presenza di internal words
	internal_words_check = 0
	for k,v in struct.items():
		internal_words_check += sum(v[0])
	
	frame_to_nouns = {}
	#popolo frame_to_nouns nel modo opportuno in funzione del check fatto prima
	qty_lbl = qty[0][1]
	menu_lbl = ''
	utt_lbl = obj
	if internal_words_check>0:
		for k,v in struct.items():
			menu_lbl = k
			utt_lbl = v[1][0]
			if len(v[0])>1:
				if sum(v[0])>1:
					if v[2] not in frame_to_nouns:
						frame_to_nouns[v[2]] = [[qty_lbl,menu_lbl,utt_lbl]]
					else:
						frame_to_nouns[v[2]].append([qty_lbl,menu_lbl,utt_lbl])
				elif sum(v[0])==1:
					if v[2]+'_CONFERMA' not in frame_to_nouns:
						frame_to_nouns[v[2]+'_CONFERMA'] = [[qty_lbl,menu_lbl,utt_lbl]]
					else:
						frame_to_nouns[v[2]+'_CONFERMA'].append([qty_lbl,menu_lbl,utt_lbl])
			else:
				if v[0][0] == 1:
					if v[2] not in frame_to_nouns:
						frame_to_nouns[v[2]] = [[qty_lbl,menu_lbl,utt_lbl]]
					else:
						frame_to_nouns[v[2]].append([qty_lbl,menu_lbl,utt_lbl])
	else:
		frame_to_nouns['NOIN'] = [[qty_lbl,menu_lbl,utt_lbl]]


	if debug:
		pprint(frame_to_nouns)



	#occupiamoci di quantità/articoli gestiti in modo diverso in funzione del frame
	quantity_to_token_ord = {1:['un',"un'",'uno','una','il','la','lo',"l'",'gli','i','le',''],
						 	2:['due'],
						 	3:['tre'],
						 	4:['quattro']}

	quantity_to_token_tr = {1:['un',"un'",'uno','una','il','la','lo',"l'"],
							2:['due'],
							3:['tre'],
							4:['quattro']}
	
	quantity_to_token_pa = {1:['il']}

	quantity_to_token_in = {1:['i']}

	token_to_quantity_ord = {t:k for k,v in quantity_to_token_ord.items() for t in v}
	token_to_quantity_tr = {t:k for k,v in quantity_to_token_tr.items() for t in v}
	token_to_quantity_pa = {t:k for k,v in quantity_to_token_pa.items() for t in v}
	token_to_quantity_in = {t:k for k,v in quantity_to_token_in.items() for t in v}

	for k,v in frame_to_nouns.items():
		if k == 'ORDINAZIONE' or k == 'ORDINAZIONE_CONFERMA' or k=='NOIN':
			t = token_to_quantity_ord
		elif k == 'TR_OGGETTO':
			t = token_to_quantity_tr
		elif k == 'PAGAMENTO':
			t = token_to_quantity_pa
		elif k == 'INFORMAZIONE':
			t = token_to_quantity_in
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
			if k1 in k2 and frame_to_nouns[k2][0][0] != -1: #se qtà pari a -1 non verrà inserito in mapped_frame -> probabile error
				mapped_frame.append([k2,frame_to_verb[k1][1],frame_to_nouns[k2]])

	
	# se 'ORDINAZIONE' e 'ORDINAZIONE_CONFERMA' sono presenti contemporaneamente in mapped_frame, vince sempre 'ORDINAZIONE'
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
	try:
		dicti = json.loads(r.text)
	except:
		return 1
    
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
		this_input = [f[1],f[2],f[0]]
		for s in successors_list:
			if state_entails(s,state) and f[0] == s['name']:
				applicable_successors.append({'name':s['name'],
											  'input':this_input,
											  'priority':FSA[s['name']]['priority']})
	if len(applicable_successors) == 0:
		applicable_successors.append({'name':successors_list[-1]['name'],
									  'priority':FSA[successors_list[-1]['name']]['priority']})

	return applicable_successors


def prenotazione1_exe(args):

	global menu_check

	menu_check = True
	wid=''
	os.system('display menu.png &')
	time.sleep(0.5)
	out = os.popen('wmctrl -l').read()
	for line in out.splitlines():
		if 'menu.png' in line:
			wid = line.split()[0]
	os.system('wmctrl -i -r '+wid+' -e 0,1100,80,-1,-1')
			
	
	# pil_im = Image.open('menu.png', 'r')
	# pil_im.show()
	
	#menu_utils.print_menu(FSA_config.menu)


def pagamento_tur(args):

	if len(FSA_config.long_term)==0:
		turn = 'Non hai ordinato nulla, il totale da pagare è pari a 0. Grazie e arrivederci!'
		return turn

	count = {}
	for ordine in FSA_config.long_term:
		qty = ordine[0]
		menu_lbl = ordine[1]
		if menu_lbl not in count:
			count[menu_lbl] = qty
		else:
			count[menu_lbl]+= qty

	conto = 0
	for k,v in count.items():
		conto += FSA_config.menu[k]['prezzo'] * v

	turn = 'Ecco a te. Puoi pagare direttamente alla cassa. Grazie e arrivederci!\nTOTALE: '+str(conto)+' euro' 
	return turn


def pagamento_exe(args):
	#resetta la long term
	del FSA_config.long_term[:]


def ordinazione_mem(args):
	this_input = args[0]

	qty = this_input[1][0][0]
	menu_lbl = this_input[1][0][1]
	frame = this_input[2]

	FSA_config.short_term.append([qty,menu_lbl,frame])
	#FSA_config.long_term.append([qty,menu_lbl,frame])

def ordinazione_long_mem(args):
	FSA_config.long_term += FSA_config.short_term
	del FSA_config.short_term[:]


def riepilogo_mem(args):
	#elimina tutte le ordinazione_conferma
	FSA_config.short_term = [i for i in FSA_config.short_term if i[-1]!='ORDINAZIONE_CONFERMA']


def riepilogo_tur(args):

	if len(FSA_config.short_term) != 0:
		count = {}
		for ordine in FSA_config.short_term:
			qty = ordine[0]
			menu_lbl = ordine[1]
			if menu_lbl not in count:
				count[menu_lbl] = qty
			else:
				count[menu_lbl]+= qty

		turn = []
		for k,v in count.items():
			turn += [str(v),k,',']
		turn = turn[:-1]
		turn.insert(0,'Hai ordinato')

		turn = ' '.join(turn)+'. Confermi?'
	else:
		turn = ''

	return turn


def riepilogo_succ(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	orig_sen_words_string = curr_input

	applicable_successors = []

	#se l'input è vuoto -> error
	if orig_sen_words_string == '' or orig_sen_words_string == None:
		applicable_successors.append({'name':successors_list[-1]['name'],
							  		  'priority':FSA[successors_list[-1]['name']]['priority']})
		return applicable_successors
	

	if re.search('(^si.*)',orig_sen_words_string) != None:
		applicable_successors.append({'name':'R_SI',
								  	  'input':orig_sen_words_string,
								  	  'priority':FSA['R_SI']['priority']})

		return applicable_successors


	if re.search('(^no.*)',orig_sen_words_string) != None:
		applicable_successors.append({'name':'R_NO_1',
								  	  'input':orig_sen_words_string,
								  	  'priority':FSA['R_NO_1']['priority']})

		return applicable_successors


	applicable_successors.append({'name':successors_list[-1]['name'],
						  		  'priority':FSA[successors_list[-1]['name']]['priority']})
	
	return applicable_successors	


def r_si_exe(args):

	#chiudi il menu
	global menu_check
	menu_check = False
	out = os.popen('ps -A').read()
	for line in out.splitlines():
		if 'display' in line:
			pid = int(line.split(None, 1)[0])
			os.kill(pid, signal.SIGKILL)


def r_no_1_tur(args):
	turn = '\n'.join([i[1] for i in FSA_config.short_term])+'.\nCosa vuoi modificare?'
	return turn


def r_no_1_succ(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	comanda = [i[1] for i in FSA_config.short_term]

	orig_sen_words_string = curr_input

	applicable_successors = []

	#se l'input è vuoto -> error
	if orig_sen_words_string == '' or orig_sen_words_string == None:
		applicable_successors.append({'name':successors_list[-1]['name'],
							  		  'priority':FSA[successors_list[-1]['name']]['priority']})
		return applicable_successors
	

	if orig_sen_words_string in comanda:
		
		global comanda_mod
		
		for i in comanda:
			if orig_sen_words_string == i:
				comanda_mod = i
		
		applicable_successors.append({'name':'R_NO_2',
								  	  'input':orig_sen_words_string,
								  	  'priority':FSA['R_NO_2']['priority']})

		return applicable_successors


	else:
		applicable_successors.append({'name':'R_NO_1_UNK',
								  	  'input':orig_sen_words_string,
								  	  'priority':FSA['R_NO_1_UNK']['priority']})

		return applicable_successors
	

def r_no_2_succ(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	orig_sen_words_string = curr_input

	applicable_successors = []

	#se l'input è vuoto -> error
	if orig_sen_words_string == '' or orig_sen_words_string == None:
		applicable_successors.append({'name':successors_list[-1]['name'],
							  		  'priority':FSA[successors_list[-1]['name']]['priority']})
		return applicable_successors
	

	if orig_sen_words_string in list(FSA_config.menu.keys()):
				
		for i in FSA_config.short_term:
			if i[1] == comanda_mod:
				i[1] = orig_sen_words_string
		
		applicable_successors.append({'name':'RIEPILOGO',
								  	  'input':orig_sen_words_string,
								  	  'priority':FSA['RIEPILOGO']['priority']})

		return applicable_successors


	else:
		applicable_successors.append({'name':'R_NO_2_UNK',
								  	  'input':orig_sen_words_string,
								  	  'priority':FSA['R_NO_2_UNK']['priority']})

		return applicable_successors


def tr_oggetto_tur(args):
	this_input = args[0]

	qty = this_input[1][0][0]
	obj = this_input[1][0][2]

	global menu_check
	
	wid=''
	if obj == 'menu':
		if menu_check == False:
			turn='Ecco '+'il'+' '+obj
			os.system('display menu.png &')
			time.sleep(0.5)
			out = os.popen('wmctrl -l').read()
			for line in out.splitlines():
				if 'menu.png' in line:
					wid = line.split()[0]
			os.system('wmctrl -i -r '+wid+' -e 0,1100,80,-1,-1')
			menu_check = True
		else:
			turn = 'Ho solo un menu, mi dispiace'
	else:
		turn='Ecco '+str(qty)+' '+obj
	
	return turn


def informazione_tur(args):
	this_input = args[0]

	portata = this_input[1][0][1]
	turn=''
	for k in FSA_config.portata_to_menulbl.keys():
		if portata == augment_annotations('i '+k)[1]['lemma']:
			turn = 'I '+k+' sono '+', '.join(FSA_config.portata_to_menulbl[k][:-1])+' e '+FSA_config.portata_to_menulbl[k][-1]
	
	return turn


def ord_conf_mem(args):
	this_input = args[0]

	menu_lbls = this_input[1]
	frame = this_input[2]
	FSA_config.short_term.append([menu_lbls,frame])


def ord_conf_tur(args):
	#mi serve l'appoggio sulla short term memory per questo turn
	#perchè l'utente potrebbe sbagliarsi nelle conferme
	#cosa che comporta il cambiamento di this_input
	#è sempre l'ultimo elemento di short_term
	this_input = FSA_config.short_term[-1]  

	menu_lbls = [i[1] for i in this_input[0]]

	if len(menu_lbls) == 1:
		turn = "Abbiamo {}, va bene?".format(menu_lbls[0])
	else:
		turn = "Abbiamo\n{}\nQuale preferisci?".format('\n'.join(menu_lbls))

	return turn


def ord_conf_succ(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]
	this_input_from_shterm = FSA_config.short_term[-1]

	orig_sen_words_string = curr_input

	applicable_successors = []

	#se l'input è vuoto -> error
	if orig_sen_words_string == '' or orig_sen_words_string == None:
		applicable_successors.append({'name':successors_list[-1]['name'],
							  		  'priority':FSA[successors_list[-1]['name']]['priority']})
		return applicable_successors

	#se non va bene nessuna proposta -> error ALT
	if re.search('(no.*|nessun(o|a).*|niente.*)',orig_sen_words_string) != None:
		applicable_successors.append({'name':'ALT',
								  	  'input':orig_sen_words_string,
								  	  'priority':FSA['ALT']['priority']})

		return applicable_successors


	num_alternative = len(this_input_from_shterm[0])

	if num_alternative == 1:
		if re.search('(^si($| .*)|^perfetto( .*|$)|^va (bene|benissimo))',orig_sen_words_string) != None:
			applicable_successors.append({'name':'ORDINAZIONE',
										  'input':['portare']+[this_input_from_shterm[0],successors_list[0]['name']],
										  'priority':FSA[successors_list[0]['name']]['priority']})
			return applicable_successors

	else:
		for i in this_input_from_shterm[0]:
			if orig_sen_words_string == i[1]:
				applicable_successors.append({'name':'ORDINAZIONE',
											  'input':['portare']+[[i],successors_list[0]['name']],
											  'priority':FSA[successors_list[0]['name']]['priority']})

				return applicable_successors


	applicable_successors.append({'name':successors_list[-1]['name'],
							  	  'priority':FSA[successors_list[-1]['name']]['priority']})
	
	return applicable_successors


def modifica_succ(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	orig_sen_words_string = curr_input
	
	applicable_successors = []

	#se l'input è vuoto -> error
	if orig_sen_words_string == '' or orig_sen_words_string == None:
		applicable_successors.append({'name':successors_list[-1]['name'],
							  'priority':FSA[successors_list[-1]['name']]['priority']})
		return applicable_successors


	#altrimenti fai tutto il resto
	for s in successors_list:
		if s['in'] != '':
			if state_entails(s,state) and re.search(s['in']['regex'],curr_input ) != None:
				applicable_successors.append({'name':s['name'],
											  'input':orig_sen_words_string,
											  'priority':FSA[s['name']]['priority']})
	if len(applicable_successors) == 0:
		applicable_successors.append({'name':successors_list[-1]['name'],
									  'priority':FSA[successors_list[-1]['name']]['priority']})

	return applicable_successors


def benvenuto_succ(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	orig_sen_words_string = curr_input

	applicable_successors = []


	#se l'input è vuoto -> error
	if orig_sen_words_string == '' or orig_sen_words_string == None:
		applicable_successors.append({'name':successors_list[-1]['name'],
							  'priority':FSA[successors_list[-1]['name']]['priority']})
		return applicable_successors

	#altrimenti fai tutto il resto
	orig_sen_ann_list = augment_annotations(orig_sen_words_string)

	lex = {'uno':1,'solo':1,'due':2,'tre':3,'quattro':4}
	orig_sen_ann_list.sort(key=lambda x:x['dependent'])

	tokens = [i for i in orig_sen_ann_list if i['pos'] == 'N' or i['dep'] == 'advmod']
	tokens.sort(key=lambda x:x['dependent'])
	
	this_input,case,in_lex,is_num = '',False,False,0

	if len(tokens) > 0:
		for i in tokens:
			if i['dependentGloss'] in lex: in_lex,this_input=True,lex[i['dependentGloss']]
			if i['pos']=='N': is_num=True

	if in_lex: case=1
	elif is_num: case=2


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
	obj = this_input[1][0][2]

	verb_ann = augment_annotations(verb)

	person = 2

	if 'features' in verb_ann[0] and 'person' in verb_ann[0]['features'] and verb_ann[0]['lemma'] != 'volere':
		person = verb_ann[0]['features']['person']

	if int(person) == 1:
		turn = 'Non so cosa dovrei fare, scusa...'
	else:
		if verb_ann[0]['lemma'] == 'volere': verb = 'portare'
		if qty >=1:
			turn = 'Mi dispiace ma non posso '+verb+' '+str(qty)+' '+obj
		else:
			urn = 'Mi dispiace ma non posso '+verb+' '+obj

	return turn


def tavola_tur(args):
	prev_state_input = args[0]

	if prev_state_input == 'T':
		turn = 'Dimmi pure'
	else:
		turns = ["Cos'altro desideri?",'Che altro posso fare?']
		index = random.randint(0,len(turns)-1)
		turn = turns[index]

	return turn