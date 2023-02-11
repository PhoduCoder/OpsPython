import subprocess
import re
import pandas as pd
import paramiko
from datetime import datetime
import csv

def get_patch_info(os_type, ssh_client):
    if os_type == 'ubuntu':
        cmd = "apt list --upgradable"
    elif os_type == 'centos':
        cmd = "yum check-update"
    else:
        return None
    
    try:
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode("utf-8")
        lines = output.split("\n")
        packages = []
        for line in lines:
            if "security" in line:
                package_info = re.search("(\S+)\s+(\S+)\s+(.*)", line)
                package_name = package_info.group(1)
                package_version = package_info.group(2)
                packages.append([package_name, package_version, os_type])
        return packages
    except Exception as e:
        print(e)
        return None

def generate_report(servers, key_file):
    report_data = []
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for server in servers:
        os_type = server[0]
        hostname = server[1]
        ip = server[2]
        try:
            ssh_client.connect(hostname=ip, username='root', key_filename=key_file)
            info = get_patch_info(os_type, ssh_client)
            if info:
                report_data.extend([[hostname] + i for i in info])
            ssh_client.close()
        except Exception as e:
            print("Error connecting to {}: {}".format(hostname, e))
    df = pd.DataFrame(report_data, columns=["Server", "Package", "Version", "OS"])
    df.to_csv("security_patch_report_{}.csv".format(datetime.now().strftime("%Y%m%d")), index=False)
    print("Report generated successfully!")

def read_servers_from_csv(file_name):
    servers = []
    with open(file_name, 'r') as f:
        reader = csv.reader(f)
        next(reader) # Skip the header row
        for row in reader:
            servers.append(row)
    return servers

# Read the server list from a CSV file
servers = read_servers_from_csv('servers.csv')

# Example key file
key_file = "/home/user/.ssh/id_rsa"

generate_report(servers, key_file)
