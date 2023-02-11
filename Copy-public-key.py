import csv
import subprocess

servers = []
key_file = '/path/to/id_rsa.pub'

with open('servers.csv', 'r') as file:
    reader = csv.reader(file)
    for row in reader:
        servers.append(row[0])

for server in servers:
    subprocess.run(['ssh-copy-id', '-i', key_file, 'root@' + server])
