import boto3
import paramiko

# AWS configuration
region_name = 'us-east-1'
ec2 = boto3.resource('ec2', region_name=region_name)
volume_size = 100  # in GB
volume_type = 'gp2'

# MySQL configuration
mysql_username = 'user'
mysql_password = 'password'
mysql_database = 'database_name'
mysql_host = 'localhost'
mysql_port = '3306'

# SSH configuration
ssh_key_path = '/path/to/ssh/key'
ssh_username = 'ec2-user'
ssh_host = 'ec2-instance-public-ip'

# Disk usage threshold
disk_usage_threshold = 80  # in percentage

# Connect to EC2 instance via SSH
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(hostname=ssh_host, username=ssh_username, key_filename=ssh_key_path)

# Get the current disk usage
stdin, stdout, stderr = ssh_client.exec_command("df -h /var/lib/mysql | awk '{print $5}' | tail -1")
disk_usage = int(stdout.read().decode('utf-8').strip().replace('%', ''))

# If disk usage exceeds the threshold, provision a new EBS volume and attach it to the EC2 instance
if disk_usage > disk_usage_threshold:
    # Create a new EBS volume
    volume = ec2.create_volume(Size=volume_size, VolumeType=volume_type, AvailabilityZone=ssh_client.get_transport().remote_version[0].split('-')[0]+'b')

    # Attach the new volume to the EC2 instance
    instance_id = ssh_client.get_transport().remote_version[0].split('-')[1]
    device = '/dev/xvdf'
    ec2_volume = ec2.Volume(volume.id)
    ec2_volume.attach_to_instance(InstanceId=instance_id, Device=device)

    # Wait for the new volume to be available
    ec2_volume.wait_until_available()

    # Format and mount the new volume
    stdin, stdout, stderr = ssh_client.exec_command(f"sudo mkfs -t ext4 {device}")
    stdin, stdout, stderr = ssh_client.exec_command(f"sudo mkdir /mnt/data{ec2_volume.id}")
    stdin, stdout, stderr = ssh_client.exec_command(f"sudo mount {device} /mnt/data{ec2_volume.id}")
    stdin, stdout, stderr = ssh_client.exec_command(f"sudo chown -R mysql:mysql /mnt/data{ec2_volume.id}")

    # Update the MySQL configuration to include the new volume
    mysql_config_file = '/etc/mysql/my.cnf'
    ssh_client.exec_command(f"sudo sed -i 's|datadir.*|datadir = /mnt/data{ec2_volume.id}/mysql|' {mysql_config_file}")

    # Restart the MySQL service
    ssh_client.exec_command("sudo systemctl restart mysql")

# Close the SSH connection
ssh_client.close()
