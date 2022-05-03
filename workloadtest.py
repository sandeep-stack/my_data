import sys
import multiprocessing
import os
import logging
import time
import pandas as pd
import csv
import subprocess
from multiprocessing import Process, Manager, Value

RESULT_FILE_PATH="Workload_results.csv"
INPUT_FILE_PATH="Workload_test.csv"
LOG_FOLDER="WORKLOAD"




if sys.argv[1] == '-h':
    hour_time = int(sys.argv[2])

if sys.argv[3] == '-m':
    minute_time = int(sys.argv[4])    

def copy_to_excel(line):

    li = list(line.split(","))
    if(li[0]=='TEST_RESULT'):
        del li[0]
        li = [x.replace("\r\n","") for x in li]
        with open(RESULT_FILE_PATH, 'a') as f:
        # create the csv writer
            writer = csv.writer(f)
        # write a row to the csv file
            print("Before writing to csv :",li)
            writer.writerow(li)
            f.close()


def timeoutfun(timeoutmin,exit_flag):

    while exit_flag[0]!=1 and timeoutmin>0:
        time.sleep(1)
        timeoutmin=timeoutmin-1;
    exit_flag[0]=1;
            

def run_command(test_folder,test_command,exit_flag):
    os.system("echo -------------------"+test_folder+" Test Started---------------------")
    print("-------------------"+test_folder+" Test Started---------------------")
    os.chdir(envPath)
    path=os.path.join(envPath,LOG_FOLDER,"Workloadlogs"+str(exit_flag[1])+".txt")
    fileopen=open(path,"w")
    print("path",path)
    exit_flag[1]=exit_flag[1]+1;
    os.chdir(test_folder)
    os.system("pwd")
    #run infinite times
    while exit_flag[0]!=1:
        fileopen.write("\n["+test_folder+","+test_command+" Test Started]\n")
        #value=subprocess.call(""+test_command+" && echo $?",stdout=fileopen, shell=True)
        value=subprocess.call(""+test_command+" && echo $?", shell=True)
        output0 = os.popen(test_command)
        out0 = output0.read()
        fileopen.write(out0)
        print('output is',out0)
        if value !=0:
                print("Test Fail")
                value = "Fail"
            #os.system('echo Test Fail')
        else:
                print("Test Pass")
                value = "pass"
        fileopen.write("\n[TEST_RESULT,"+test_folder+","+test_command+","+value+"]\n")
        fileopen.write("\n["+test_folder+","+test_command+" Test ended]\n")
        print("\n-------------------"+test_command+" Test ended---------------------")
        os.chdir(envPath)
        copy_to_excel("TEST_RESULT,"+test_folder+","+test_command+","+value+"")
        os.chdir(test_folder)
            #os.system('echo Test Pass')
        #os.system("echo TEST_RESULT,"+test_folder+","+test_command+","+value+"")
    fileopen.close()
    os.chdir(envPath)   


def add_process(test_folder,test_command,exit_flag):         
    p = Process(target=run_command, args=(test_folder,test_command,exit_flag))
    p.start()
    p.join() 
    p.terminate()
   

def create_testresultcsv():
    if os.path.exists(RESULT_FILE_PATH):
        os.remove(RESULT_FILE_PATH)
    header = ['folder','command','status']
    with open(RESULT_FILE_PATH, 'w') as f:
    # create the csv writer
        writer = csv.writer(f)
    # write a row to the csv file
        writer.writerow(header)
        f.close()

def set_and_run(test_folder,test_command,exit_flag):
    os.chdir(envPath)
    os.system("echo =====================STARTING TESTS=========================")

    if test_folder == 'dldt/dldt':
        os.chdir('dldt/dldt/lib/')
        env_direc_new1 = os.getcwd()
        os.chdir(envPath)
        os.chdir('dldt/dldt/tbb/lib/')
        env_direc_new2 = os.getcwd()
        os.chdir(envPath)
        os.chdir('dldt/dldt/opencv/lib/')
        env_direc_new3 = os.getcwd()
        os.chdir(envPath)
        os.chdir(test_folder)
        os.environ['LD_LIBRARY_PATH'] = env_direc_new1+":"+env_direc_new2+":"+env_direc_new3    
        add_process(test_folder,test_command,exit_flag)

    elif test_folder == 'HCPBench' or test_folder == 'HCPBenchOpenCL':
        os.chdir('HCPBenchSYCLlib')
        env_direc_new = os.getcwd()
        os.chdir(envPath)
        os.chdir(test_folder)
        os.environ['LD_LIBRARY_PATH'] = env_direc_new
        add_process(test_folder,test_command,exit_flag)                 
        
    elif test_folder == 'OpenCV' or test_folder == 'BlackScholes' or test_folder == 'Resnet' or test_folder == 'spmv/ocl' or test_folder == 'Resnet/inference' or \
    test_folder == 'OCL_Bins':
        os.chdir(test_folder)
        env_direc_new = os.getcwd()
        os.environ['LD_LIBRARY_PATH'] = env_direc_new
        add_process(test_folder,test_command,exit_flag)

    elif test_folder == 'Binocle':  
        if(test_command.find("compubench")!=-1):
            compubench_cmd,Binocle_cmd =test_command.split("+")
            os.chdir(envPath)
            os.chdir("CompuBenchCL157Desktop/64bit")
            env_direc_new = os.getcwd()
            os.environ['LD_LIBRARY_PATH'] = env_direc_new
            add_process("CompuBenchCL157Desktop/64bit",compubench_cmd,exit_flag)
            os.chdir(envPath)
            os.chdir(test_folder)
            env_direc_new = os.getcwd()
            os.environ['LD_LIBRARY_PATH'] = env_direc_new
            add_process(test_folder,Binocle_cmd,exit_flag) 
        else:
            os.chdir(envPath)
            os.chdir(test_folder)
            env_direc_new = os.getcwd()
            os.environ['LD_LIBRARY_PATH'] = env_direc_new
            add_process(test_folder,test_command,exit_flag)

    else:
        add_process(test_folder,test_command,exit_flag)



def all_test_execute(exit_flag): #Running all tests
    df = pd.read_csv(INPUT_FILE_PATH, encoding = 'unicode_escape')
    # iterate over each line as a ordered dictionary and print only few column by column Number
    for index, row in df.iterrows():
        p = multiprocessing.Process(target=set_and_run,args=(row['folder'],row['command_line'],exit_flag))
        p.start()



def main():
    global envPath
    envPath=os.getcwd()
    try: 
            os.mkdir(LOG_FOLDER) 
    except OSError as error: 
            print(error)
    manager = Manager()
    exit_flag = manager.list(range(2))
    create_testresultcsv()
    totaltime=(hour_time*3600)+(minute_time*60)
    timer_process = multiprocessing.Process(target=timeoutfun,args=(totaltime,exit_flag))
    timer_process.start()
    

    start_test = multiprocessing.Process(target=all_test_execute,args=(exit_flag,))
    start_test.start()
    timer_process.join()
    start_test.join()
    print("_____ALL TEST COMPLETED_______")



       
                        
if __name__=="__main__": 

    main()

    exit()  
