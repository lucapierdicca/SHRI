from FSA_config import FSA,world_state
import os
import speech_recognition as sr
from gtts import gTTS
import time
import subprocess
from ctypes import *
from contextlib import contextmanager
import pyaudio

ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)

def py_error_handler(filename, line, function, err, fmt):
    pass

c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

@contextmanager
def noalsaerr():
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(c_error_handler)
    yield
    asound.snd_lib_error_set_handler(None)



def update_world_state(curr_state_dict):
	curr_state = FSA[curr_state_dict['name']]
	if 'eff' in curr_state:
		for i in range(len(curr_state['eff'])):
			if curr_state['eff'][i] != '*':
				world_state[i] = curr_state['eff'][i]

def write_memory(curr_state_dict):
	curr_state = FSA[curr_state_dict['name']]
	if 'memory' in curr_state:
		process_f(curr_state['memory'],args=[curr_state_dict['input']])

def text_to_speech(curr_state_dict):
	curr_state = FSA[curr_state_dict['name']]
	turn = ''
	if 'turn' in curr_state:
		if curr_state['name'] != 'ATTESA':
			turn = curr_state['turn']
			if callable(curr_state['turn']):
				turn = process_f(curr_state['turn'],args=[curr_state_dict['input']])
		
			if debug:
				print(turn)
			else:
				speak(turn)
		else:
			print(curr_state['turn'])

#TODO
def speak(turn):
	#c = "gtts-cli \""+turn+"\" -l \"it\" | mpg123 -"
	tts = gTTS(turn,'it')
	tts.save('turn.mp3')
	#time.sleep(1)
	print('\033[92mEnnio: '+turn+'\033[0m')
	#os.system('mpg123 -q /home/luca/Desktop/SHRI/turn.mp3')
	subprocess.call('mpg123 -q /home/luca/Desktop/SHRI/turn.mp3', 
					shell=True,
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE)
			

def speech_to_text(curr_state_dict):
	curr_state = FSA[curr_state_dict['name']]
	if 'input' in curr_state:
		if curr_state['name'] != 'ATTESA':
			if not debug:
				if curr_state['input'] == '':
					return hear()
				elif callable(curr_state['input']):
					return process_f(curr_state['input'])
			else:
				return input('Scrivi: ')
		else:
			return input('Scrivi: ')

#TODO
def hear():
	r = sr.Recognizer()
	r.energy_threshold = 200
	
	err = True
	while err:
		input("Premi 'Invio' per avviare la registrazione")

		with noalsaerr() as n, sr.Microphone() as source:
			print("In ascolto...")
			audio = r.listen(source)
			print("Fine registrazione")
			try:
				err = False
				text = r.recognize_google(audio, language="it-IT")
			except sr.UnknownValueError:
			    err = True#print("Google Cloud Speech could not understand audio")
			except sr.RequestError as e:
			    err = True#print("Could not request results from Google Cloud Speech service; {0}".format(e))
	print('\033[94mTu: '+text.lower()+'\033[0m')
	return text.lower()

def retrieve_successors(curr_input,curr_state_dict):
	curr_state = FSA[curr_state_dict['name']]

	if 'successors_f' in curr_state:
		successors = process_f(curr_state['successors_f'], args=[curr_input,curr_state['successors'],FSA,world_state])
	else:
		successors = [{'name':curr_state['successors'][0]['name'],
						'input':'',
					  	'priority':FSA[curr_state['successors'][0]['name']]['priority']}]
	return successors


def generic_action_exec(curr_state_dict):
	curr_state = FSA[curr_state_dict['name']]
	if 'exec' in curr_state:
		process_f(curr_state['exec'])

def process_f(callback,args=[]):
	return callback(args)

def priority_sort_frontier():
	frontier.sort(key=lambda x: x['priority'], reverse=True)


#=====================================================================================


debug = True
debug_frontier = False

frontier = []
curr_state_dict = {'name':'ATTESA','priority':FSA['ATTESA']['priority']}
frontier.append(curr_state_dict)


def main():

	global frontier

	while True:

		priority_sort_frontier()
		if debug_frontier: print(frontier)
		
		curr_state_dict = frontier.pop(0)
		#curr_state = FSA[curr_state_dict['name']]

		update_world_state(curr_state_dict)
		if debug: print(''.join(world_state),curr_state_dict['name'])

		write_memory(curr_state_dict)

		text_to_speech(curr_state_dict)

		generic_action_exec(curr_state_dict)

		curr_input = speech_to_text(curr_state_dict)

		successors = retrieve_successors(curr_input,curr_state_dict)

		frontier += [s for s in successors if s not in frontier]



main()

