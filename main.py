from FSA_config import FSA,world_state

def update_world_state(curr_state):
	if 'eff' in curr_state:
		for i in range(len(curr_state['eff'])):
			if curr_state['eff'][i] != '*':
				world_state[i] = curr_state['eff'][i]

def write_memory(curr_state_dict,curr_state):
	if 'memory' in curr_state:
		process_f(curr_state['memory'],args=[curr_state_dict])

def text_to_speech(curr_state_dict,curr_state):
	turn = ''
	if 'turn' in curr_state:
		turn = curr_state['turn']
		if callable(curr_state['turn']):
			turn = process_f(curr_state['turn'],args=[curr_state_dict['input']])
	
		if debug:
			print(turn)
		else:
			speak(turn)

#TODO
def speak(turn):
	return 0

def speech_to_text(curr_state):
	if 'input' in curr_state:
		if not debug:
			if curr_state['input'] == '':
				return hear()
			elif callable(curr_state['input']):
				return process_f(curr_state['input'])
		else:
			return input('Scrivi: ')

#TODO
def hear():
	return 0

def retrieve_successors(curr_input,curr_state):
	if 'successors_f' in curr_state:
		successors = process_f(curr_state['successors_f'], args=[curr_input,curr_state['successors'],FSA,world_state])
	else:
		successors = [{'name':curr_state['successors'][0]['name'],
					  'priority':FSA[curr_state['successors'][0]['name']]['priority']}]
	return successors


def generic_action_exec(curr_state):
	if 'exec' in curr_state:
		process_f(curr_state['exec'])

def process_f(callback,args=[]):
	return callback(args)

def priority_sort_frontier():
	frontier.sort(key=lambda x: x['priority'], reverse=True)


#=====================================================================================


debug = True

frontier = []
curr_state_dict = {'name':'ATTESA','priority':FSA['ATTESA']['priority']}
frontier.append(curr_state_dict)


def main():

	global frontier

	while True:

		priority_sort_frontier()
		if debug: print(frontier)
		
		curr_state_dict = frontier.pop(0)
		curr_state = FSA[curr_state_dict['name']]

		update_world_state(curr_state)
		if debug: print(''.join(world_state),curr_state['name'])

		write_memory(curr_state_dict,curr_state)

		text_to_speech(curr_state_dict,curr_state)

		generic_action_exec(curr_state)

		curr_input = speech_to_text(curr_state)

		successors = retrieve_successors(curr_input,curr_state)

		frontier += [s for s in successors if s not in frontier]



main()

# def speech_to_text(curr_state, robot_hears, debug=True):
	
# 	text, o_text, p_text = '','',''
# 	global info_memory
	
# 	if curr_state['input']: 
# 		if not debug:
# 			with sr.Microphone() as source:
# 				print('In ascolto...')
# 				audio = robot_hears.listen(source, timeout=60)
# 		try:
# 			if not debug:
# 				o_text = robot_hears.recognize_google(audio, language='it-IT')
# 			else:
# 				o_text = input('Scrivi...\n')
			
# 			text = o_text
			
# 			if curr_state['preprocessing']:
# 				p_text = preprocess(text, menu)
# 				text = p_text

# 			print('Utente_o: ' + o_text)
# 			print('Utente_p: ' + p_text)

# 		except sr.UnknownValueError:
# 		    print('Google Cloud Speech could not understand audio')
# 		except sr.RequestError as e:
# 		    print('Could not request results from Google Cloud Speech service; {0}'.format(e))

# 		info_memory['original_text'] = o_text

# 	info_memory['curr_state_name'] = curr_state['name']

# 	return text.lower()