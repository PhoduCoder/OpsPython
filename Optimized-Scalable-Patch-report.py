import csv
import paramiko

def get_patch_status(server, key_file):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(server, key_filename=key_file)
    stdin, stdout, stderr = ssh.exec_command("apt-get update && apt list --upgradable")
    output = stdout.read().decode("utf-8")
    ssh.close()
    return output

def patch_report_generator(servers, key_file):
    for server in servers:
        patch_status = get_patch_status(server, key_file)
        yield f"Server: {server}\nPatch status:\n{patch_status}"

def write_patch_report(report_file, servers, key_file):
    with open(report_file, "w") as file:
        for report in patch_report_generator(servers, key_file):
            file.write(report + "\n")

def main():
    servers = []
    key_file = "/path/to/id_rsa"
    report_file = "patch_report.txt"

    with open("servers.csv", "r") as file:
        reader = csv.reader(file)
        for row in reader:
            servers.append(row[0])

    write_patch_report(report_file, servers, key_file)

if __name__ == "__main__":
    main()