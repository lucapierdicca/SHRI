import requests
import json
from pprint import pprint
from graphviz import Digraph
from PIL import Image
from menu_utils import load_menu

menu = load_menu('menu.xml')

lexicon_O = [v['nome'].lower() for v in menu.values()]

# menulbl_to_id = {t:i for i,t in enumerate(lexicon_O)}
# id_to_menulbl = {v:k for k,v in menulbl_to_id.items()}
# id_to_prezzo = {i:v['prezzo'] for i,v in enumerate(menu.values())}

# tint_url = "http://localhost:8012/tint?"
# for index,t in enumerate(lexicon_O):
# 	response = requests.get(tint_url+'text='+'un '+t+'&format=json')
# 	annotations = json.loads(response.text)
# 	lemmatized = []
# 	for i in annotations['sentences'][0]['tokens'][1:]:
# 		lemmatized.append(i['lemma'])
	
# 	lexicon_O[index] = ' '.join(lemmatized)

# menulbllemma_to_id = {t:i for i,t in enumerate(lexicon_O)}

lexicon_TO = ['menu','forchetta','coltello','bicchiere']
lexicon_I = ['antipasto','primo','secondo','dolce']
lexicon_P = ['conto']
lexicon_B = ['tavolo','posto']

frames = [{'in':{'name':'ORDINAZIONE','lu_v':['mangiare','ordinare','volere','chiedere','portare','prendere'],'lu_s':lexicon_O,'ce':['entity']}},
	   	  {'in':{'name':'TR_OGGETTO','lu_v':['portare'],'lu_s':lexicon_TO,'ce':['theme']}},
	   	  {'in':{'name':'INFORMAZIONE','lu_v':['elencare','essere','avere','dire','sapere','suggerire','consigliare'],'lu_s':lexicon_I,'ce':['content']}},
	   	  {'in':{'name':'PAGAMENTO','lu_v':['portare','pagare','saldare'],'lu_s':lexicon_P,'ce':['good']}},
	   	  {'in':{'name':'PRENOTAZIONE','lu_v':['essere','prenotare'],'lu_s':lexicon_B,'ce':['services']}}]


debug = True

def dep_VIZ(file_id,text):
	
	ann_list = augment_annotations(text)

	f = Digraph(file_id, format='png')

	for token in ann_list:
		f.node(token['dependentGloss']+'_'+str(token['dependent']))

	for edge in ann_list:
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
			if i['pos'] == 'V':
				to_be_removed+=[i for i in range(1,root_index+1)]
			else:
				to_be_removed+=[i for i in range(1,root_index+1) if (augm[i]['dep'] != 'nummod' and augm[i]['dep'] != 'det') or augm[i]['lemma'] == 'piatto' or augm[i]['lemma']=='porzione']
				print(to_be_removed)
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



def frame_mapping(orig_sen_words_string,frames_out):

	frames = []
	for i in frames_out:
		if i['in'] not in frames and i['in'] != '':
			frames.append(i['in'])


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
	frame_to_verb['NOIN'] = verbs[0]
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
	if list(frame_to_verb)[0] == 'ORDINAZIONE':
		standard_root = 'portami '
	else:
		standard_root = frame_to_verb[list(frame_to_verb)[0]][1]+' '

	prep_sen_words_string = preprocessing(orig_sen_words_string,standard_root)
	
	
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

	start.append(['',index+2,'',0])
	start = start[1:]
	print(start)
	
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
	

		#fake_temp = {i['lemma']:i['dep'] for i in fake_sen_ann_list}
		#sliced_temp = {i['lemma']:i['dep'] for i in sliced_prep_sen_ann_list}
		
		# if len(sliced_prep_sen_ann_list)>=len(fake_sen_ann_list):
		# 	sliced_prep_sen_ann_list = sliced_prep_sen_ann_list[:len(fake_sen_ann_list)]
		# 	for index,(s,f) in enumerate(zip(sliced_prep_sen_ann_list,fake_sen_ann_list)):
		# 		if s['lemma'] == f['lemma']:
		# 			struct[k][0][index] = 1


	# for k,v in struct.items():
	# 	if len(v)>1 and v[0][-1] != 1 and v[0][0] == 1:
	# 		inp = augment_annotations(standard_root+' un '+k)
	# 		temp = {i['lemma']:i['dep'] for i in inp}
	# 		print(temp)
	# 		#if not (len(prep_sen_ann_list)<len(inp)):
	# 		for numr, r in enumerate(temp):
	# 			if numr > 2 and temp[r] != 'case':
	# 				indice_da_controllare = (obj_sen_index -1 + numr -2)
	# 				print(indice_da_controllare)
	# 				for k1,v1 in struct.items():
	# 					for numi, i in enumerate(augment_annotations(standard_root+' un '+k1)):
	# 						if numi>1 and i["lemma"] == prep_sen_ann_list[indice_da_controllare]["lemma"] :
	# 							print(i['lemma'],prep_sen_ann_list[indice_da_controllare]["lemma"] )
	# 							v1[0][numi-2] =1

    
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
		frame_to_nouns['NOIN'] = [['zero',obj]]





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



			

sentence = "basta cosi"

#pprint(augment_annotations(sentence))

#pprint(preprocess(sentence,'portami '))

#frame_mapping(sentence,frames)
#print()


dep_VIZ('0',sentence)