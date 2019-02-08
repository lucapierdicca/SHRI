from pynput import keyboard
import speech_recognition as sr
import pyaudio
import wave
import threading



def worker():
	def on_press(key):
		global start
		start = True

	def on_release(key):
		global start
		start = False
		return False

	with keyboard.Listener(on_press=on_press,on_release=on_release) as listener:
		listener.join()

t = threading.Thread(target=worker)
t.start()


CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "output.wav"

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

start = False
frames = []

while True:
	if start:
		data = stream.read(CHUNK)
		frames.append(data)
		if not start:
			break

print("* done recording")
stream.stop_stream()
stream.close()
p.terminate()

wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()


r = sr.Recognizer()
with sr.AudioFile(WAVE_OUTPUT_FILENAME) as source:
	audio = r.record(source)


try:
	text = r.recognize_google(audio, language='it-IT')
except sr.UnknownValueError:
    print('Google Cloud Speech could not understand audio')
except sr.RequestError as e:
    print('Could not request results from Google Cloud Speech service; {0}'.format(e))

print(text)
