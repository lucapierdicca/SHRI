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
#===========================================================================
debug = False

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

def inputframe_suc(args):
	curr_input = args[0]
	successors_list = args[1]
	FSA = args[2]
	state = args[3]

	frames = []
	for i in args[1]:
		if i['in'] not in frames and i['in'] != '':
			frames.append(i['in'])

	tint_url = "http://localhost:8012/tint?"
	response = requests.get(tint_url+'text='+curr_input+'&format=json')
	annotations = json.loads(response.text)
	original_annotations = annotations

	if debug:
		print(curr_input)
	#============================== STEP 1 - FRAME CLASSIFICATION =================================

	#retrieve all keywords l.u.s (verbs and nouns) in the sentence
	pos_verb = ['V','V+PC','VM']
	pos_nouns = ['S','A']
	verbs = [[token['lemma'],token['index']] for token in annotations['sentences'][0]['tokens'] if token['pos'] in pos_verb]
	#nouns = [[token['lemma'],token['index']] if for token in annotations['sentences'][0]['tokens'] if token['pos'] in pos_nouns]


	nouns = []
	for token in annotations['sentences'][0]['tokens']:
		succeded = False
		if token['pos'] in pos_nouns:
			if 'features' in token:
				if 'Number'in token['features']:
					succeded = True
					if token['features']['Number'][0] == 'Plur':
						nouns.append([token['lemma'],token['index']])
					else:
						nouns.append([token['word'],token['index']])
			if not succeded:
				nouns.append([token['word'],token['index']])
	if debug:
		print()
		print(nouns)

	#map verb -> frame
	frame_to_verb = {}
	for v in verbs:
		for f in frames:
			if v[0] in f['lu_v']:
				frame_to_verb[f['name']] = [v]

	#map noun -> frame
	frame_to_nouns = {}
	for n in nouns:
		for f in frames:
			for lu in f['lu_s']:
				if n[0] in lu:
					index_in_lu = lu.split().index(n[0])
					n_aug = n+[index_in_lu]
					if f['name'] not in frame_to_nouns:
						frame_to_nouns[f['name']] = {lu:[n_aug]}
					else:
						if lu not in frame_to_nouns[f['name']]:
							frame_to_nouns[f['name']][lu] = [n_aug]
						else:
							frame_to_nouns[f['name']][lu].append(n_aug)

	#resolve multi word-match
	for f,n in frame_to_nouns.items():
		for lu,m in n.items():
			if len(m) > 1:
				for i in range(len(m)):
					for j in range(i+1,len(m)):
						if (m[i][1]-m[j][1]) == (m[i][2]-m[j][2]):
							n[lu] = [[lu.split()[0], (m[i][1],m[j][1]),(m[i][2],m[j][2]),FSA_config.menulbllemma_to_id[lu]]]


	#resolve partial match
	pm = {}
	for f,n in frame_to_nouns.items():
		for lu,m in n.items():
			for i in m:
				if i[0] not in pm:
					pm[i[0]] = 1
				else:
					pm[i[0]] +=1

	#final mapping
	surface_to_frame = {k:{'verb':v} for k,v in frame_to_verb.items()}
	for f,n in frame_to_nouns.items():
		if f not in surface_to_frame:
			surface_to_frame[f] = {'nouns':[]}
		else:
			surface_to_frame[f]['nouns'] = []
		for k,v in n.items():
			surface_to_frame[f]['nouns'].append(tuple(v[0]+[pm[v[0][0]]]))
		surface_to_frame[f]['nouns'] = list(set(surface_to_frame[f]['nouns']))

	#lu list
	keywords = {}
	for k,v in surface_to_frame.items():
		if 'verb' in v and 'nouns' in v:
			keywords[v['verb'][0][0]] = {'type':'v','info':v['verb'][0][1]}
			for n in v['nouns']:
				keywords[n[0]] = {'type':'n', 'info':(n[1],n[2],n[3])}
	if debug:
		print()
		pprint(frame_to_verb)
		print()
		pprint(frame_to_nouns)
		print()
		pprint(surface_to_frame)
		print()
		print('K',keywords)

	#===============================================================================================
	#============================== STEP 2 - CORE ELEMENTS MAPPING =================================
	import numpy as np

	original_list = []
	pos_det = ['N','RD','RI','D']

	for index,token in enumerate(original_annotations['sentences'][0]['tokens']):
		succeded = False
		if token['pos'] in pos_nouns:
			if 'features' in token:
				if 'Number'in token['features']:
					succeded = True
					if token['features']['Number'][0] == 'Plur':
						original_list.append(token['lemma'])
					else:
						original_list.append(token['word'])
			if not succeded:
				original_list.append(token['word'])
		elif token['pos'] in pos_verb:
			original_list.append(token['lemma'])
		elif token['pos'] in pos_det:
			original_list.append(token['word']+'_'+token['pos'])
		else:
			original_list.append(token['word']+'_'+token['pos'])

		if original_list[index] in keywords:
			original_list[index]+='_'+keywords[original_list[index]]['type']
		elif '_' not in original_list[index]:
			original_list[index]+='_u'


	#create artificial list multi-word to one-word
	forbidden_intervals = []
	for k_values in keywords.values():
		if k_values['type'] == 'n':
			if type(k_values['info'][0]) is tuple:
				forbidden_intervals.append(k_values['info'][0])
	
	artificial_list = []
	for index,t in enumerate(original_list):
		allowed=True
		for inter in forbidden_intervals:
			if index in range(inter[0]+1,inter[1]):
				allowed=False
		if t[t.find('_')+1:] in ['n','v']+pos_det and allowed:
			artificial_list.append(t)


	#add commas to artificial list
	artificial_list_commas = []
	for t in artificial_list:
		artificial_list_commas.append(t[:t.find('_')])
		if t[t.find('_')+1:] == 'n':
			artificial_list_commas.append(',')

	artificial_list_commas = artificial_list_commas[:-1]

	if debug:
		print()
		print('OL',original_list)
		print()
		print('AL',artificial_list)
		print()
		print('ALC', artificial_list_commas)

	#quantity
	quantity_to_token = {1:[',','un','uno','una','gli','il','i'],
						 2:['due'],
						 3:['tre'],
						 4:['quattro']}

	token_to_quantity = {t:k for k,v in quantity_to_token.items() for t in v}

	#final mapped frames quantity augmented
	mapped_frame = []
	for k,v in surface_to_frame.items():
		if 'verb' in v and 'nouns' in v:
			for n in v['nouns']:
				if artificial_list_commas[artificial_list_commas.index(n[0])-1] in token_to_quantity:
					q = token_to_quantity[artificial_list_commas[artificial_list_commas.index(n[0])-1]]
				else:
					q=1
				mapped_frame.append([k,q,n])
	if debug:
		print()
		print('MF',mapped_frame)

	#successors
	applicable_successors = []
	for f in mapped_frame:
		for s in successors_list:
			if state_entails(s,state) and f[0] in s['name']:
				for i in range(f[1]):
					applicable_successors.append({'name':s['name'],
												  'input':f[2],
												  'priority':FSA[s['name']]['priority']})						

	
	if len(applicable_successors) == 0:
		applicable_successors.append({'name':successors_list[-1]['name'],
									  'priority':FSA[successors_list[-1]['name']]['priority']})

	return applicable_successors

#TODO
def prenotazione1_exe(args):
	menu_utils.print_menu(FSA_config.menu)

#TODO
def pagamento1_tur():
	turn = ''
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
		turn += [str(v),FSA_config.id_to_menulbl[k],',']
	turn = turn[:-1]
	turn.insert(0,'Hai ordinato')

	turn = ' '.join(turn)+'. Arriviamo subito!'

	return turn

#TODO
def tr_oggetto_tur():
	print('trasporto')

#TODO
def informazione_tur():
	print('info')