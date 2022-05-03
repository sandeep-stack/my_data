import math
import os
import shutil
import sys
import time
import multiprocessing
from getpass import getpass
from configparser import ConfigParser
import paramiko
import pandas as pd
from multiprocessing import Process, Manager, Queue
import namednodes
import socket
import csv
from datetime import datetime
from paramiko.buffered_pipe import PipeTimeout

## inits
BASE_TEST_PATH="stress_automation/tests.csv"
BASE_PATH="C:\Stress"
CSV_PATH =  os.path.join(BASE_PATH,"tests.csv")

def logging(comb):
	#combination number?
	#comb = math.ceil(test_num/5)
	# create the log folder
	logPath = os.path.join(BASE_PATH, 'logs', 'Combination' + str(comb))
	scandumpTag = 'Combination' + str(comb)
	print(" =========== In LOGGING function =========== ")
	os.chdir(logPath)
	logName = "PythonSV.log"
	log(r"{0}".format(logName))
	sv.gfxcard0.tiles.gfx.gtgp.force_wake=0x10001
	sv.gfxcard0.tiles.gfx.gtgp.driver_render_fwake=0x10001
	print(
		"\n++++++++++++++++++++++++++++++++++++++++++++++++++LOGGING - IPEHR++++++++++++++++++++++++++++++++++++++++++++\n")
	sv.gfxcard0.tiles.gfx.gtgp.showsearch("ipehr")
	print(
		"\n++++++++++++++++++++++++++++++++++++++++++++++++++LOGGING - INSTDONE+++++++++++++++++++++++++++++++++++++++++\n")
	sv.gfxcard0.tiles.gfx.gtgp.showsearch("instdone_ccs")
	print(
		"\n++++++++++++++++++++++++++++++++++++++++++++++++++LOGGING - GTSTATUS+++++++++++++++++++++++++++++++++++++++++\n")
	import pontevecchio.debug.domains.gfx.gt.gtStatus as gs
	gs.status()
	print(
		"\n++++++++++++++++++++++++++++++++++++++++++++++++++LOGGING - SOC LOG++++++++++++++++++++++++++++++++++++++++++\n")
	import pontevecchio.fv.ras.error_logging_modules.soc_error_log as soc
	soc.soc_error_log()
	nolog()

	if sv.gfxcard0.tile0.taps.pvc_gdt0.debugid and sv.gfxcard0.tile1.taps.pvc_gdt0.debugid == 0:
		time.sleep(300)

	if sv.gfxcard0.tile0.taps.pvc_gdt0.debugid and sv.gfxcard0.tile1.taps.pvc_gdt0.debugid != 0:
		from pontevecchio.debug.domains.gfx.tools.scandump import pvcgfxscanAFD as pvcgfxscanAFD
		pvcgfxscanAFD.gtScandump(name=scandumpTag)
		time.sleep(60)
	else:
		print("TAP debugid is not proper. Skipping Scandump.")

def checkTarget():
	TIMEOUT = 500
	while TIMEOUT > 0:
		t = os.system('ping -n 4 {0} | find "bytes=32" > nul'.format(target))
		if t == 0:
			print("Target is UP")
			return t
		else:
			print("Trying to reach the target IP address")
			time.sleep(1)
			TIMEOUT=TIMEOUT-1
	return t

## boot system
def reset():
	MODE = "driver"
	import toolext.bootscript.boot as b
	b.clean_up_vars()
	status = exec(boot)

	#execute post boot sequence
	exec(post_boot)

	print(f"Exited with status = {status}")
	print(" =========== PythonSV based boot finished =========== ")

	status = checkTarget()
	if status == 0:
		time.sleep(120)
		sshRun(MODE)
	else:
		print("System is unreachable. Please check.")
		sys.exit(1)

	#delay after driver load
	time.sleep(120)

	#apply post driver load values
	exec(post_driver)

## get the csv to understand #tests; create the logs folder on target
def sshRun(MODE):
	global testsAvailable

	try:
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.connect(target, 22, user, password)
	except paramiko.AuthenticationException:
		print("Authentication failed, please verify your credentials")
		result_flag = False
	except paramiko.SSHException as sshException:
		print("Could not establish SSH connection: %s" % sshException)
		result_flag = False
	except socket.timeout as e:
		print("Connection timed out")
		result_flag = False
	except Exception as e:
		print("Exception in connecting to the server")
		print("PYTHON SAYS:",e)
		result_flag = False
		ssh.close()
	else:
		result_flag = True
	
	if result_flag:	
		if MODE == "setup":
			# get the test file
			sftp=ssh.open_sftp()
			sftp.get(BASE_TEST_PATH,'tests.csv')
			sftp.close()
			
			# get number of tests and setup log folder
			list = pd.read_csv('tests.csv',encoding='cp1252')
			rows = len(list.index)
			testsAvailable = int(rows/6)
		elif MODE == "driver":
			stdin, stdout, stderr = ssh.exec_command('sudo modprobe i915 enable_rc6=1 rc6_ignore_steppings=1 enable_iaf=0 reset=0 enable_hangcheck=0 enable_rps=1;if lsmod | grep i915; then echo "Module Loaded"; echo 300 | sudo tee /sys/class/drm/card1/gt/gt0/rps_min_freq_mhz; echo 300 | sudo tee /sys/class/drm/card1/gt/gt1/rps_min_freq_mhz; for i in /sys/class/drm/card*/engine/*/heartbeat_interval_ms; do echo 0 | sudo tee $i; done; for i in /sys/class/drm/card*/engine/*/preempt_timeout_ms; do echo 0 | sudo tee $i; done; for i in /sys/class/drm/card*/engine/*/max_busywait_duration_ns; do echo 0 | sudo tee $i; done; for i in /sys/class/drm/card*/engine/*/stop_timeout_ms; do echo 0 | sudo tee $i; done; else echo "Module Not Loaded"; while :; do echo "Hit CTRL+C to stop  "; sleep 1; done; fi',get_pty=True)
			stdin.write(password)
			stdin.write("\n")
			stdin.flush()
		elif MODE == "driver_version":
			stdin, stdout, stderr = ssh.exec_command('uname -a; sudo dpkg -l | grep intel',get_pty=True)
			stdin.write(password)
			stdin.write("\n")
			stdin.flush()
			#for line in iter(stdout.readline, ""):
			#	logging.debug(line)
		elif MODE == "dmesg":
			stdin, stdout, stderr = ssh.exec_command('dmesg -wT',get_pty=True)
			with open('dmesg.log','a') as o:
				orig_stdout = sys.stdout
				sys.stdout = o
				for line in iter(stdout.readline,""):
					print(line.strip('\n'))
				sys.stdout = orig_stdout
				o.close()
	else:
		os._exit(1)

def targetLog(q,test_num,args):
	#combination number?
	comb = math.ceil(test_num/6)
	#create the log folder
	logPath=os.path.join(BASE_PATH,'logs','Combination'+str(comb))
	if not os.path.isdir(logPath):
		os.makedirs(logPath)

	os.chdir(logPath)

	while q.empty():
		MODE = "dmesg"
		sshRun(MODE)

def runTimer(q,args):
	##calculate timeout in seconds
	timeout = args[3]

	while timeout >= 0:
		time.sleep(1)
		timeout = timeout - 1
	q.put(1)
	print("In timer, hit exit flag, exiting")
	os._exit(1)

def create_resultsCsv():
	if os.path.exists('results.csv'):
		os.remove('results.csv')
	header = ['combination','testnumber', 'time', 'folder', 'command', 'iteration', 'status']
	with open('results.csv', 'w') as f:
		# create the csv writer
		writer = csv.writer(f)
		# write a row to the csv file
		writer.writerow(header)
		f.close()

def copy_to_excel(line):
	li = line.split(",")
	if(li[0]=='TEST_RESULT'):
		del li[0]
		li = [x.replace("\r\n","") for x in li]
		with open('results.csv', 'a+') as f:
		# create the csv writer
			writer = csv.writer(f)
		# write a row to the csv file
			writer.writerow(li)
			f.close()

def runTests(q,test_num,args,MODE=None):
	target = args[0]
	user = args[1]
	password = args[2]

	try:
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.connect(target, 22, user, password)
	except paramiko.AuthenticationException:
		print("Authentication failed, please verify your credentials")
		result_flag = False
	except paramiko.SSHException as sshException:
		print("Could not establish SSH connection: %s" % sshException)
		result_flag = False
	except socket.timeout as e:
		print("Connection timed out")
		result_flag = False
	except Exception as e:
		print("Exception in connecting to the server")
		print("PYTHON SAYS:",e)
		result_flag = False
		ssh.close()
	else:
		result_flag = True

	# get number of tests and setup log folder
	df = pd.read_csv(CSV_PATH,encoding='cp1252')
	combination = df['combination'][test_num-1]
	folder = df['folder'][test_num-1]
	command_line = df['command_line'][test_num-1]
	index = df['testnumber'][test_num-1]
	run_status = df['runstatus'][test_num-1]

	if result_flag:
		if run_status != "#":
			logPath = os.path.join(BASE_PATH, 'logs', 'Combination' + str(combination))
			os.chdir(logPath)
			logFile = 'Test' + str(test_num) + ".log"
			if MODE == "dmesg":
				while q.empty():
					stdin, stdout, stderr = ssh.exec_command('dmesg -wT',get_pty=True)
					with open('dmesg.log','a') as o:
						orig_stdout = sys.stdout
						sys.stdout = o
						for line in iter(stdout.readline,""):
							print(line.strip('\n'))
						sys.stdout = orig_stdout
						o.close()
			else:
				count = 1
				while q.empty():
					timestamp = str(datetime.now())
					result = "TEST STARTED"
					print("Combination: %s Test number: %s Time: %s Command: %s Iteration: %s Status: %s" % (combination,test_num,timestamp,command_line,count,result))
					try:
						if folder.find('binocle') != -1:
							stdin, stdout, stderr = ssh.exec_command('export UseDrmVirtualEnginesForCcs=0; cd {0};{1}'.format(folder, command_line), timeout=900, get_pty=True)
						elif folder.find('OpenCV') != -1:
							stdin, stdout, stderr = ssh.exec_command('cd {0}; export LD_LIBRARY_PATH=$PWD; {1}'.format(folder, command_line), timeout=900, get_pty=True)
						elif folder.find('HCPBench') != -1:
							stdin, stdout, stderr = ssh.exec_command('cd {0}; cd ../HCPBenchSYCLlib; export LD_LIBRARY_PATH=$PWD; cd {1}; {2}'.format(folder, folder, command_line), timeout=900, get_pty = True)
						else:
							stdin, stdout, stderr = ssh.exec_command('cd {0};{1}'.format(folder, command_line), timeout=900, get_pty=True)
						copy_to_excel("TEST_RESULT," + str(combination) + "," + str(test_num) + "," + timestamp + "," + folder + "," + command_line + "," + str(count) + "," + result + "")
						with open(logFile, 'a') as o:
							orig_stdout = sys.stdout
							sys.stdout = o
							for line in iter(stdout.readline,""):
								print(line.strip('\n'))
							value = stdout.channel.recv_exit_status()
							if value != 0:
								result = "TEST FAILED"
							else:
								result = "TEST PASSED"
							print("Combination: %s Test number: %s Time: %s Command: %s Iteration: %s Status: %s" % (combination,test_num,timestamp,command_line,count,result))
							sys.stdout = orig_stdout
							o.close()
							timestamp = str(datetime.now())
							print("Combination: %s Test number: %s Time: %s Command: %s Iteration: %s Status: %s" % (combination,test_num,timestamp,command_line,count,result))
							copy_to_excel("TEST_RESULT," + str(combination) + "," + str(test_num) + "," + timestamp + "," + folder + "," + command_line + "," + str(count) + "," + result + "")
					except socket.timeout as e:
						sys.stdout = orig_stdout
						print("Connection timed out")
						os._exit(1)
					except PipeTimeout:
						sys.stdout = orig_stdout
						print("Connection timed out")
						os._exit(1)
					except Exception as e:
						sys.stdout = orig_stdout
						print("Exception in execute command")
						print("PYTHON SAYS:", e)
						os._exit(1)
					count += 1
	os._exit(1)

def run():
	global comb_from
	global comb_to
	args = [target,user,password,totalTime]
	processes = []

	reset()
	
	list = pd.read_csv(CSV_PATH,encoding='cp1252')
	rows = len(list.index)
	testsAvailable = int(rows/6)

	q = multiprocessing.Queue()

	if (comb_to >= comb_from) and (comb_to <= testsAvailable):
		while comb_from <= comb_to:
			test_num = comb_from*6 - 5
			test_to = comb_from*6
			#cleanup combination logs
			logPath = os.path.join(BASE_PATH, 'logs', 'Combination' + str(comb_from))
			if os.path.exists(logPath):
				shutil.rmtree(logPath)

			os.makedirs(logPath)
			os.chdir(logPath)
			create_resultsCsv()

			for i in range(test_num,test_to+1):
				startTest = multiprocessing.Process(target=runTests,args=(q,i,args))
				startTest.start()
				processes.append(startTest)

			#MODE = "dmesg"
			#startLog = multiprocessing.Process(target=runTests, args=(q, test_num, args, MODE))
			#startLog.start()

			startTimer = multiprocessing.Process(target=runTimer,args=(q,args))
			startTimer.start()

			#startLog.join()
			for startTest in processes:
				startTest.join()
			startTimer.join()

			# check if the IP is reachable
			status = checkTarget()
			if status != 0:
				logging(comb_from)
				reset()
			
			print("Waiting for 5 mins before taking logs")
			time.sleep(300)
			logging(comb_from)

			#terminate
			#startLog.terminate()
			startTimer.terminate()
			for startTest in processes:
				startTest.terminate()
			reset()
			comb_from +=1

			#clear queue
			while not q.empty():
				q.get()
	else:
		print("Please check test combinations in config.ini file")

if __name__ == "__main__":
	# instantiate
	config = ConfigParser()

	# parse existing file
	config.read('config.ini')

	# read contents of config.ini
	dict = {}

	for sec in config.sections():
		for item in config.items(sec):
			dict[item[0]] = item[1]

	# read values from a section
	target = config.get('SYSTEM-INFO', 'target')
	user = config.get('SYSTEM-INFO', 'user')
	project = config.get('SYSTEM-INFO', 'project')
	hours = config.getint('TEST-PARAMS', 'hour')
	minutes = config.getint('TEST-PARAMS', 'minute')
	comb_from = config.getint('TEST-PARAMS', 'comb_from')
	comb_to = config.getint('TEST-PARAMS', 'comb_to')
	boot = dict.get('boot').strip('\n')
	post_boot = dict.get('post_boot').strip('\n')
	post_driver = dict.get('post_driver').strip('\n')

	print("Target:", target)
	print("User:", user)
	print("Project:", project)
	print("Hours:", hours)
	print("Minutes:", minutes)
	print("Test from:", comb_from)
	print("Test to:", comb_to)

	input = input("Is this configuration OK to proceed (Y/N)?")

	if input == "Y" or input == "y":
		print("Configuration is OK to proceed. Continuing.")
	else:
		print("Invalid input. Please try again!")
		sys.exit(1)

	##calculate timeout in seconds
	totalTime = (hours * 3600) + (minutes * 60)

	password = getpass(prompt='Input your target password: ')

	# TODO: read from config
	PYSV_PROJECT = 'pontevecchio'
	PYSV_REPO = fr"C:\pythonsv\{PYSV_PROJECT}"
	sys.path.append(PYSV_REPO)
	os.chdir(PYSV_REPO)
	from startpvc import *
	from common import baseaccess

	if baseaccess.getaccess() != 'tssa':
		import itpii

		itp = itpii.baseaccess()

	itp.unlock()

	import startpvc_auto

	startpvc_auto.auto_main()

	run()
	sys.exit(0)
