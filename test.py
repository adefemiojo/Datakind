
 
import RPi.GPIO as GPIO
import time
import serial
import time
from datetime import datetime
import picamera
import picamera.array
import subprocess

def takepic(camera,output):
	horz = 256
	vert = 192
	camera.resolution = (horz,vert)
	camera.capture(output,format='yuv')
	count = 0

	for i in range(0,len(output.array)):
		for j in range(0,len(output.array[i])):
			count = count + output.array[i][j][0]
	if count/(horz*vert)>50:
		camera.capture('/mnt/usb/Fridge_data/Fridgepics/image'+
				timestamp()+'.jpg')
	return None

def poll(byte_2,byte_3,byte_4):

	byte_1 = 0xA5

	check_sum = 0x0100 - ((byte_1 + byte_2 + byte_3 + byte_4) & 0xFF)

	return bytearray([byte_1,byte_2,byte_3,byte_4,check_sum])

def temp_on_poll():
	return poll(0x11,0x00,0x00)

def temp_off_poll():
	return poll(0x10,0x00,0x00)

def power_poll():
	return poll(0x93,0x00,0x00)

def temp_poll():
	return poll(0x8E,0x00,0x00)

def change_power(Power):
	high, low = divmod(Power*1000,0x100)
	return poll(0x91,low,high)

def set_thermo_mode():
	return poll(0x82,0x02,0x00)

def set_temp_on(Temp):
	high, low = divmod(int(Temp*100),0x100)
	return poll(0x0F,low,high)

def set_temp_off(Temp):
	high, low = divmod(int(Temp*100),0x100)
	return poll(0x0E,low,high)

def respond(Arr,Expected_string,dividing_factor,ser):
	ser.flushInput()
	ser.write(Arr)
	response = ser.read(5)
	char_response = list(response)

	if ord(char_response[0]) != 90:
		error_write(timestamp(),"Incorrect framing error")

	if ord(char_response[1]) != int(Expected_string,16):
		error_write(timestamp(),"Unexpected response error")

	r_check_sum = ( 0x0100 - ((ord(char_response[0]) +
				ord(char_response[1]) +
				ord(char_response[2]) +
				ord(char_response[3]) ) & 0xFF) & 0xFF )

	if ord(char_response[4]) != r_check_sum:
		error_write(timestamp(),"Check sum error")

	return float((256*ord(char_response[3])+ord(char_response[2])))/dividing_factor

def timestamp():
	now = time.time()
	return datetime.fromtimestamp(now).strftime('%d-%m-%Y %H_%M_%S')

def usb_setup():
	bashCommand = ''
	counter = 96
	while counter < 122:
		counter = counter + 1
		try:
			bashCommand = 'sudo mount /dev/sd'+chr(counter)+'1 /mnt/usb'
			processTest = subprocess.check_output(bashCommand.split())
		except subprocess.CalledProcessError:
			pass
		else:
			process = subprocess.Popen(bashCommand.split())
			break
	if counter == 122:
		error_write(timestamp(),'Insert USB')	
	return None

def setup(ser,ON,OFF):
	Thermo_mode = respond(set_thermo_mode(),'0x82',1,ser)
	Power = 16
	Power_set_Point = respond(change_power(Power),'0x91',1000,ser)
	time.sleep(0.01)
	time.sleep(0.01)
	temp_on = respond(temp_on_poll(),'0x11',100,ser)
	temp_off = respond(temp_off_poll(),'0x11',100,ser)
	temp_on = ON
	Temp_on_set = respond(set_temp_on(temp_on),'0x0F',100,ser)
	time.sleep(0.01)
	temp_off = OFF
	Temp_off_set = respond(set_temp_off(temp_off),'0x0E',100,ser)
	time.sleep(0.01)
	return None

def data_retrieve():
	Power = respond(power_poll(),'0x93',1000,ser)
	time.sleep(0.01)
	Temp = respond(temp_poll(),'0x8E',100,ser)
	time.sleep(0.01)
	return Power,Temp

def write(file,string):
	with open(file,'a') as f:
		f.write(string)
	return None	

def file_write(Power,Temp,Time):
	string = Time + ',' + str(Power) + ',' + str(Temp) + '\n'
	write('/mnt/usb/Fridge_data/Fridge_data_2.txt',string)
	return None

def error_write(Time,error):
	string = Time + ',' + error + '\n'
	write('/home/pi/Documents/Fridge/ErrorLogger.txt',string)
	try:
		write('/mnt/usb/Fridge_data/ErrorLogger.txt',string)
	except:
		pass
	return None

def kill_kill_kill():
	remove = 'rm test.txt'
	remove_process = subprocess.Popen(remove.split())
	create = 'touch test.txt'
	create_process = subprocess.Popen(create.split())
	bashCommand = 'ps -ef '
	processTest = subprocess.check_output(bashCommand.split())
	write('/home/pi/Documents/Fridge/test.txt',processTest)
	with open('/home/pi/Documents/Fridge/test.txt','r') as file:
		processes = []
		for line in file:
			if line.find('python') != -1:
				processes.append(line.strip())
	arr = []
	for p in range(0,len(processes)):
		arr.append(processes[p].split())
	del_array = []
	for i in range(0,len(arr)):
		del_array.append(arr[i][1])
	for d in range(0,len(del_array)-1):
		kill = 'kill -9 '+str(del_array[d])
		process = subprocess.Popen(kill.split())
	return None

def serial_port(port):
	return serial.Serial(
			port = port,
			baudrate = 9600,
			parity=serial.PARITY_NONE,
			stopbits=serial.STOPBITS_ONE,
			bytesize=serial.EIGHTBITS,
			timeout=1
			)

port1 = '/dev/ttyUSB0'
port2 = '/dev/ttyUSB1'
port3 = '/dev/ttyUSB2'
port4 = '/dev/ttyUSB3'


def try_Serial_port():

	try:
		try:
			try:
				ser = serial_port(port1)
			except:
				ser = serial_port(port2)
		except:
			ser = serial_port(port3)
	except:
		ser = serial_port(port4)

	return ser

ON = 9.7
OFF = 9.3

def setup_with_exceptions(ON,OFF):

	try:
		setup(try_Serial_port(),ON,OFF)
	except IOError, e:
		if str(e).find('mnt') != -1:
			try:
				print(str(e))
				usb_setup()
			except:
				if str(e).find('ermission') != -1:
					error_write(timestamp(),'Permission exception')
				else:
					error_write(timestamp(),'Insert USB')
				time.sleep(1)
		elif str(e).find('tty') != -1:
			error_write(timestamp(),"Lost serial port contact")
			time.sleep(1)
	except IndexError, I:
		error_write(timestamp(),"Fridge is turned off or not connected to power source")
		time.sleep(1)
	except MemoryError, m:
		error_write(timestamp(),"SD card is full, replace with new SD card")
		time.sleep(1)
	except R:
		error_write(timestamp(),str(R))
	return None

setup_with_exceptions(ON,OFF)
usb_setup()

while True:
	try:
		ser = try_Serial_port()
		Power,Temp = data_retrieve()
		file_write(Power,Temp,timestamp())
		with picamera.PiCamera() as camera:
			with picamera.array.PiYUVArray(camera) as output:
				try:
					take_pic(camera,output)
				finally:
					camera.close()
	except IOError, e:
		E_string = str(e)
		if E_string.find("mnt") != -1:
			try:
                if E_string.find('ermission') != -1:
					error_write(timestamp(),'Permission denied')
                #print(str(e))
				usb_setup()
			except:
					error_write(timestamp(),'Insert USB')
		elif E_string.find('tty') != -1:
			error_write(timestamp(),"Lost serial port contact")
		time.sleep(1)
	except IndexError, I:
		error_write(timestamp(),"Fridge is turned off or not connected to power source")
		time.sleep(1)
	except picamera.exc.PiCameraMMALError, M:
		kill_kill_kill()
		time.sleep(1)
		error_write(timestamp(),"Picamera is being weird")
	except MemoryError, m:
		error_write(timestamp(),"USB is full, replace with new usb")
		break
	except :
		error_write(timestamp(),'Unexpected error')
		time.sleep(1)
		kamikazi()
