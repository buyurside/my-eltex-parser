#!/usr/bin/env python3

import paramiko
import yaml
import subprocess
import filecmp
from time import sleep
from sys import exit
import argparse
from datetime import datetime
from pathlib import Path
from os import listdir, path, mkdir, access, chmod, W_OK, R_OK, X_OK


path_to_conf =  "./."

debug        = False

delay        = 300
dir_mode     = 0o744
port         = 22
username     = ""
password     = ""
working_dir  = "./."


def get_timestamp():
    return f'{datetime.now().strftime("%d-%m-%Y_%H:%M:%S")}'

def print_debug(str):
    if debug:
        print(f"[DEBUG]: {str}")

def print_err(str):
    if debug:
        print(f"[ERROR]: {str}")

def print_info(str):
    print(f"[INFO]: {str}")

def print_fatal(str):
    print(f"[FATAL]: {str}. Aborting...")
    exit(1488)

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--config', type=str, default="./.")
args = parser.parse_args()

if args.config:
    path_to_conf = args.config

    with open(path_to_conf) as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
    ### всегда абортирует...
    #try:
    #    with open("config.yml") as f:
    #        cfg = yaml.load(f, Loader=yaml.FullLoader)
    #except:
    #    with open("config.yml") as f:
    #        cfg = yaml.load(f, Loader=yaml.FullLoader)
    #finally:
    #    print("No config file was found in this directory. Aborting...")
    #    exit(1488)


hosts = cfg['hosts']
for host in hosts:
    if host['ip'] == "":
        print_fatal("IP address is empty")
    if host['hostname'] == "" and host['dir'] == "":
        print_fatal("Hostname parameter is empty")

username = cfg['username']
if username == "":
    print_fatal('Username parameter is empty')

try:
    password = cfg['password']
except:
    pass
try:
    working_dir = cfg['working_dir']
except:
    pass
try:
    delay = cfg['delay']
except:
    pass


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

while True:
    for host in hosts:
        #hostname = host["hostname"]
        if host['hostname'] == "" and host['dir'] != "":
            hostname = host['dir']
            dir = working_dir + '/' + hostname
        elif host['hostname'] != "" and host['dir'] == "":
            hostname = host['hostname']
            dir = working_dir + '/' + host['hostname']
        else:
            hostname = host['hostname']
            dir = working_dir + '/' + host['dir']


        try:
            port = host['port']
        except:
            pass

        client.connect(host["ip"], port, username, password)

        ssh_stdin, ssh_stdout, ssh_stderr = client.exec_command("show running-config")
        
        decoded_stdout = str(ssh_stdout.read().decode().strip())
        
        print_info(f'HOST: {hostname} \n\tIP:   {host["ip"]}')

        if ssh_stderr != "":
            print_debug(f"stderr:\n{ssh_stderr.read().decode()}")
        try:
            config_start = decoded_stdout.index("hostname ")
        except ValueError:
            print_info("Substring not found. Check user permissions on remote host. Skipping...")
            continue
        except:
            print_err("Unknown error. Skipping...")
            continue

        decoded_stdout = decoded_stdout[config_start:]
        print_debug(f"stdout:\n{decoded_stdout}")
    
        client.close()
        
        if not path.isdir(f'{dir}'):
            mkdir(dir, dir_mode)
        elif not access(f'{dir}', W_OK) or not access(f'{dir}', R_OK):
           print_info("Found incorrect permissions. Start fixing...")
           #
           ### ПЕРЕДЕЛАТЬ ###
           # добавить валидацию на успешное выполнение операции ниже
           #
           chmod(f'{dir}', dir_mode)
           print_info("Success.")
    
        conf_path = f'{dir}/{hostname}_{get_timestamp()}.conf'
        confs = [f for f in listdir(path=f'{dir}/.')]
        if len(confs) > 0:
            with open(f'{dir}/{confs[-1]}', 'r') as f:
                last_config = f.read().strip()
            f.close()
                
            if last_config == decoded_stdout:
                print_info("No changes in config.")
                continue
            
        #hostname = host["hostname"]
    
        with open(f'{conf_path}', 'w') as conf:
            conf.write(decoded_stdout)
        conf.close()
        print_info("Got new version of config.")

    sleep(delay)
