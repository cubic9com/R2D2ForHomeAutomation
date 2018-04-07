"""R2-D2 for Home Automation.

This module builds on SimpleHTTPServer by implementing the standard GET
and HEAD requests to json data for irMagician.

"""


__version__ = "0.1"

__all__ = ["R2D2ForHomeAutomationRequestHandler"]

import BaseHTTPServer
import SimpleHTTPServer
import serial
import json
import subprocess
import random
import base64
import time
from neopixel import *
import RPi.GPIO as GPIO
import signal
import sys
import threading
import urllib2
from R2D2ForHomeAutomationConst import *

# LED strip configuration:
LED_COUNT      = 6       # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 5       # DMA channel to use for generating signal (try 5)
#LED_BRIGHTNESS = 63     # Set to 0 for darkest and 255 for brightest
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)

# server configuraion:
PORT = 8000
AUTH_KEY = 'foohoge:barpiyo'

# BRAVIA configuration:
BRAVIA_MAC_ADDRESS = '00:00:5E:00:53:00'
BRAVIA_IP_ADDRESS = '192.0.2.100'

key = ''
servo = ''

ser = serial.Serial('/dev/ttyACM0', 9600, timeout = 1)
ser.readline()

class R2D2ForHomeAutomationRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
	''' Main class to present webpages and authentication. '''
	def do_HEAD(self):
		print 'send header'
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()

	def do_AUTHHEAD(self):
		print 'send header'
		self.send_response(401)
		self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
		self.send_header('Content-type', 'text/html')
		self.end_headers()

	def do_GET(self):
		global key
		''' Present frontpage with user authentication. '''
		if self.headers.getheader('Authorization') == None:
			self.do_AUTHHEAD()
			self.wfile.write('no auth header received')
			pass
		elif self.headers.getheader('Authorization') == 'Basic '+key:
			r = random.randint(1, 3)
			subprocess.Popen(['paplay', '/home/pi/r2d2_' + str(r) + '.wav'],
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				shell=False)
			time.sleep(0.8)
			th_rotate = RotateThread()
			th_rotate.start()
			blink_led(strip)
			print(self.path)
			if self.path == '/':
				self.do_HEAD()
				pass
			elif self.path == '/ircc/PowerOn':
				subprocess.Popen(['etherwake', BRAVIA_MAC_ADDRESS],
					stdin=subprocess.PIPE,
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE,
					shell=False)	 
			elif self.path.startswith('/ircc/'):
				soap_send(self.path.lstrip('/ircc/'))
				print 'send header'
				self.send_response(200)
				self.send_header('Content-type', 'text/html')
				self.end_headers()
			else:
				f = self.send_head()
				if f:
					ir_play(f)
					f.close()
			self.wfile.write('\r\n')
			blink_led(strip)
			turnoff_led(strip)
			pass
		else:
			self.do_AUTHHEAD()
			self.wfile.write(self.headers.getheader('Authorization'))
			self.wfile.write('not authenticated')
			pass

class RotateThread(threading.Thread):
	def __init__(self):
		super(RotateThread, self).__init__()

	def run(self):
		rotate()

def soap_send(f):
	prefix = '<?xml version="1.0" encoding="utf-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1"><IRCCCode>'
	suffix = '</IRCCCode></u:X_SendIRCC></s:Body></s:Envelope>'
	data = prefix + ircccode[f] + suffix
	request = urllib2.Request('http://' + BRAVIA_IP_ADDRESS + '/sony/IRCC', data)
	try:
		response = urllib2.urlopen(request)
	except Exception:
		print "Exception"

def ir_play(f):
	json_data = json.load(f)

	recNumber = len(json_data['data'])
	rawX = json_data['data']

	ser.write('n,%d\r\n' % recNumber)
	ser.readline()

	postScale = json_data['postscale']
	ser.write('k,%d\r\n' % postScale)
	ser.readline()

	for n in range(recNumber):
		bank = n / 64
		pos = n % 64
		if (pos == 0):
			ser.write('b,%d\r\n' % bank)

		ser.write('w,%d,%d\n\r' % (pos, rawX[n]))

	ser.write('p\r\n')
	ser.readline()

def randblue():
	b = random.randint(80, 127)
	return Color(0, 0, b)

def randcolor():
	r = random.randint(0, 31)
	g = random.randint(0, 31)
	b = random.randint(0, 31)
	return Color(r, g, b)

def blink_led(strip, wait_ms=100, iterations=10):
	for i in range(10):
		strip.setPixelColor(0, randblue())
		strip.setPixelColor(1, randblue())
		if i == 0:
			strip.setPixelColor(2, Color(110, 31, 31))
		if i == 0:
			strip.setPixelColor(3, Color(31, 127, 31))
		if i == 9:
			strip.setPixelColor(2, Color(31, 31, 127))
		if i == 9:
			strip.setPixelColor(3, Color(95, 95, 31))
		strip.setPixelColor(4, randcolor())
		strip.setPixelColor(5, randcolor())
		strip.show()
		time.sleep(wait_ms/1000.0)

def turnoff_led(strip, wait_ms=100, iterations=10):
	for q in range(strip.numPixels()):
		strip.setPixelColor(q, 0)
	strip.show()

def rotate():
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(gp_out, GPIO.OUT)
	servo = GPIO.PWM(gp_out, 50)
	servo.start(5.5)
	servo.ChangeDutyCycle(0.1)
     	time.sleep(0.7)
	servo.ChangeDutyCycle(11.9)
     	time.sleep(0.7)
        servo.ChangeDutyCycle(5.5)
	time.sleep(0.5)
	servo.stop()
	GPIO.cleanup()
        time.sleep(0.8)

def exit_handler(signal, frame):
	# servo motor
	servo.ChangeDutyCycle(4.0)
	time.sleep(0.5)
	servo.stop()
	GPIO.cleanup()

	# led
	for q in range(strip.numPixels()):
		strip.setPixelColor(q, 0)
	strip.show()

	sys.exit(0)

def test(HandlerClass = R2D2ForHomeAutomationRequestHandler,
		 ServerClass = BaseHTTPServer.HTTPServer):
	BaseHTTPServer.HTTPServer(('', PORT), R2D2ForHomeAutomationRequestHandler).serve_forever()

if __name__ == '__main__':
	signal.signal(signal.SIGINT, exit_handler)

	# servo motor
	gp_out = 24

	# led
	strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
	strip.begin()

	key = base64.b64encode(AUTH_KEY)
	test()
