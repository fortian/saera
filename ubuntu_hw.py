#! /usr/bin/end python

import os, sys
import email
import subprocess
import sqlite3
import gtk
import gobject
import appindicator
import pyjulius
import time
import Queue

try:
	import keybinder # requires package python-keybinder
except:
	keybinder = None

global app
app = None

if sys.version < '3':
	import codecs
	def u(x):
		# return codecs.unicode_escape_decode(x)[0]
		return x.encode('utf-8')
else:
	def u(x):
		return x

if sys.version_info[0]==3:
	raw_input = input

memory_path = os.getenv('HOME')+'/.saera_memory.db'
if not os.path.exists(memory_path):
	conn = sqlite3.connect(memory_path)
	conn.row_factory = sqlite3.Row
	cur = conn.cursor()
	cur.execute('CREATE TABLE Variables (Id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, VarName TEXT NOT NULL, Value TEXT NOT NULL, UpdateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
	cur.execute('CREATE TABLE Locations (Id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, LocName TEXT NOT NULL COLLATE NOCASE, Zip TEXT, Latitude REAL, Longitude REAL, Timezone REAL, UpdateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
	cur.execute('CREATE TABLE People (Id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, Name TEXT NOT NULL COLLATE NOCASE, Description TEXT, Born DATE, Died DATE, Gender TEXT, Profession TEXT)')

	cur.execute('INSERT INTO Locations (LocName, Zip, Latitude, Longitude, Timezone) VALUES ("Tokyo", "", 35.6833, 139.6833, 9)')
	cur.execute('INSERT INTO Locations (LocName, Zip, Latitude, Longitude, Timezone) VALUES ("Shanghai", "", 31.2, 121.5, 8)')
	cur.execute('INSERT INTO Locations (LocName, Zip, Latitude, Longitude, Timezone) VALUES ("New York", "10001", 40.7127, -74.0059, -5)')
	cur.execute('INSERT INTO Locations (LocName, Zip, Latitude, Longitude, Timezone) VALUES ("Mexico City", "08619", 19.433, -99.133, -6)')
	cur.execute('INSERT INTO Locations (LocName, Zip, Latitude, Longitude, Timezone) VALUES ("Moscow", "101", 55.75, 37.6167, 3)')
	cur.execute('INSERT INTO Locations (LocName, Zip, Latitude, Longitude, Timezone) VALUES ("Los Angeles", "90001", 34.05, -118.25, -8)')

	conn.commit()
else:
	conn = sqlite3.connect(memory_path)
	conn.row_factory = sqlite3.Row
	cur = conn.cursor()

subprocess.Popen(['julius/julius -module -gram julius/saera -h julius/hmmdefs -input mic'],shell=True,stdout=subprocess.PIPE)
client = pyjulius.Client('localhost',10500)
print ('Connecting to pyjulius server')
while True:
	try:
		client.connect()
		break
	except pyjulius.ConnectionError:
		sys.stdout.write('.')
		time.sleep(2)
sys.stdout.write('\n')
client.start()

def set_alarm(time, message = "alarm"):
	# TODO
	pass

def set_reminder(time, message, location=None):
	os.system("echo 'echo \""+message.replace('"','\\"').replace("'","\\'")+"\" | wall' | at "+time.strftime("%H:%M"))

def run_text(t):
	return app.execute_text(t)

def open_text_input(widget):
	message = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
	message.set_markup("An example error popup.")
	message.run()

def pulse(onoff):
	ind.set_status([appindicator.STATUS_ACTIVE,appindicator.STATUS_ATTENTION][onoff])
	# gobject.timeout_add(500,pulse, not onoff)

def getSpeech(widget=None,data=None):
	ind.set_status(appindicator.STATUS_ATTENTION)
	subprocess.Popen(['canberra-gtk-play --file=/usr/share/sounds/ubuntu/notifications/Slick.ogg'],shell=True,stdout=subprocess.PIPE)
	print "Listening..."
	time.sleep(0.5)
	# Clear queue
	client.results.get(False)
	pulse(True)
	while 1:
		pulse(int(time.time()*2)%2==0)
		try:
			result = client.results.get(False)
			print repr(result)
			if isinstance(result,pyjulius.Sentence):
				print "SENTENCE"
				print dir(result), " ".join([i.word for i in result.words]), result.score
				break
		except Queue.Empty:
			continue
	ind.set_status(appindicator.STATUS_ACTIVE)
	result = run_text(" ".join([i.word.lower() for i in result.words]))
	try:
		is_string = isinstance(result,basestring)
	except NameError:
		is_string = isinstance(result,str)
	if is_string:
		subprocess.Popen(['notify-send',result])
		print (result)
		speak(result)
	else:
		for i in result:
			subprocess.Popen(['notify-send',i[0]])
			print (i[0])
			speak (result)
	gobject.timeout_add(1000,getTrigger)

def getTrigger():
	while True:
		try:
			result = client.results.get(True,0.7)
			if isinstance(result,pyjulius.Sentence) and len(result.words)==1 and result.words[0].word=="SAERA" and result.words[0].confidence>0.7:
				getSpeech()
				return
		except Queue.Empty:
			gobject.timeout_add(1000,getTrigger)
			return

def getText(widget=None,data=None):
	def responseToDialog(entry, dialog, response):
	    dialog.response(response)
	dialog = gtk.MessageDialog(
		None,
		gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
		gtk.MESSAGE_QUESTION,
		gtk.BUTTONS_OK,
		None)
	dialog.set_markup('Enter text')
	entry = gtk.Entry()
	entry.connect("activate", responseToDialog, dialog, gtk.RESPONSE_OK)
	hbox = gtk.HBox()
	hbox.pack_start(gtk.Label(""), False, 5, 5)
	hbox.pack_end(entry)
	dialog.format_secondary_markup("How may I help you?")
	dialog.vbox.pack_end(hbox, True, True, 0)
	dialog.show_all()
	dialog.run()
	text = entry.get_text()
	dialog.destroy()

	result = run_text(text)
	try:
		is_string = isinstance(result,basestring)
	except NameError:
		is_string = isinstance(result,str)
	if is_string:
		subprocess.Popen(['notify-send',result])
		print (result)
		speak(result)
	else:
		for i in result:
			subprocess.Popen(['notify-send',i[0]])
			print (i[0])
			speak (result)
	return text

def run_app(s):
	global app
	app = s

	global ind
	ind = appindicator.Indicator("new-gmail-indicator",
                                           "xfce4-mixer-record",
                                           appindicator.CATEGORY_APPLICATION_STATUS)
	ind.set_attention_icon("xfce4-mixer-no-record")
	ind.set_status(appindicator.STATUS_ACTIVE)

	menu = gtk.Menu()
	speech_item = gtk.MenuItem("Speak")
	speech_item.connect("activate", getSpeech)
	speech_item.show()
	enter_item = gtk.MenuItem("Enter text")
	enter_item.connect("activate", getText)
	enter_item.show()
	quit_item = gtk.MenuItem("Quit")
	quit_item.connect("activate", lambda x: (client.stop(),client.disconnect(),sys.exit()))
	quit_item.show()
	menu.append(speech_item)
	menu.append(enter_item)
	menu.append(quit_item)
	ind.set_menu(menu)
	if keybinder is not None:
		keybinder.bind("<Shift>F3",getText,"")
		keybinder.bind("F3",getSpeech,"")
	try:
		gobject.timeout_add(1000,getTrigger)
		gtk.main()
	except Exception as e:
		print "Error: ",e.message
	finally:
		client.stop()

def is_playing():
	return False


def pause():
	pass

def play():
	pass

def call_phone(num):
	pass

def get_unread_email():
	return []

class MailFolder:
	def __init__(self):
		self.messages = {}
	def check(self):
		for i in os.listdir(os.getenv("HOME")+"/.qmf/mail/"):
			if not i in self.messages and not "part" in i:
				self.messages[i] = email.message_from_file(open(os.getenv("HOME")+"/.qmf/mail/"+i))

def speak(string):
	os.system('espeak -v +f2 "' + u(string).replace(":00"," o'clock").replace("\n",". ") + '"')
	return string

def quit():
	print ("Bye!")
	conn.close()
	client.stop()
	client.disconnect()
	sys.exit(0)