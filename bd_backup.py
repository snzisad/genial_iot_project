import os
import time

'''
    mongo backup by python
    developrt: mr-exception
    github: mr-exception
'''

# configs:
interval_m = 5
outputs_dir = './database'

host = "NA" # if host is your local machine leave it NA
port = "NA" # if mongo is on default port (37017) leave in NA

username = "NA" # if there is no username set, leave it in NA
password = "NA" # if there is no password set, leave it in NA

def render_output_locations():
  return outputs_dir + time.strftime("%d-%m-%Y-%H:%M:%S")

def run_backup():
  command = "mongodump"
  if host != 'NA':
    command += " --host " + host
  if port != 'NA':
    command += " --port " + port
  if username != 'NA':
    command += " --username " + username
  if password != 'NA':
    command += " --password " + password
  
  command += " --out " + render_output_locations()
  
  os.system(command)

print("mongo backup progress started")
print("I will backup your mongo db every {0} minutes".format(interval_m))

while True:
  time.sleep(interval_m * 60)
  run_backup()