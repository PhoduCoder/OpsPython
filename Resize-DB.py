import boto3
import paramiko
import os
import time

# Define constants for the script
INSTANCE_ID = '<YOUR_INSTANCE_ID>'
REGION = '<YOUR_REGION>'
NEW_VOLUME_SIZE = 100 # GB
MOUNT_POINT = '/mnt/mysql_data_new'

# Connect to EC2
ec2 = boto3.resource('ec2', region_name=REGION)
instance = ec2.Instance(INSTANCE_ID)

# Create a new EBS volume
volume = ec2.create_volume(Size=NEW_VOLUME_SIZE, AvailabilityZone=instance.placement['AvailabilityZone'])

# Wait for the new volume to be available
while volume.state != 'available':
    volume.reload()
    time.sleep(5)

# Attach the new volume to the instance
device_name = '/dev/xvdg'
response = instance.attach_volume(Device=device_name, VolumeId=volume.id)

# Wait for the volume to be attached
while not os.path.exists(device_name):
    time.sleep(5)

# Use SSH to copy the data to the new volume
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(instance.public_ip_address, username='ec2-user')

# Stop the MySQL service on the EC2 instance
stdin, stdout, stderr = ssh.exec_command('sudo systemctl stop mysqld')

# Copy the data from the old data directory to the new volume
stdin, stdout, stderr = ssh.exec_command('sudo rsync -av /var/lib/mysql/ {} --exclude="*.pid"'.format(MOUNT_POINT))
stdout.channel.recv_exit_status()

# Check for errors during the rsync process
if stderr.read().decode("utf-8"):
    print('Error occurred while copying data')
    response = instance.detach_volume(Device=device_name)
    volume.delete()
    exit()

# Verify that the data was copied correctly
stdin, stdout, stderr = ssh.exec_command('sudo diff -r /var/lib/mysql {} --exclude="*.pid"'.format(MOUNT_POINT))

# Check for errors during the diff process
if stdout.read().decode("utf-8"):
    print('Error: Data copied is not identical to original data')
    response = instance.detach_volume(Device=device_name)
    volume.delete()
    exit()

# Update the MySQL configuration file to use the new data directory
stdin, stdout, stderr = ssh.exec_command('sudo sed -i "s#/var/lib/mysql#{0}#" /etc/my.cnf'.format(MOUNT_POINT))

# Start the MySQL service on the EC2 instance
stdin, stdout, stderr = ssh.exec_command('sudo systemctl start mysqld')

# Check for errors during the MySQL service start process
if stderr.read().decode("utf-8"):
    print('Error occurred while starting MySQL service')
    response = instance.detach_volume(Device=device_name)
    volume.delete()
    exit()

# Close the SSH connection
ssh.close()

# Print success message
print('New volume created and attached successfully')
