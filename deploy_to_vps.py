import paramiko
import os
import time

host = "157.173.101.159"
port = 22
username = "user247"
password = "Z9K!@R7Q"
target_port = 8247
local_dir = "dashboard"
remote_dir = "dashboard"

try:
    print(f"Connecting to {host}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port, username, password)

    print("Creating remote directory...")
    ssh.exec_command(f"mkdir -p {remote_dir}")

    sftp = ssh.open_sftp()
    
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        if os.path.isfile(local_path):
            remote_path = f"{remote_dir}/{item}"
            print(f"Uploading {local_path} to {remote_path}...")
            sftp.put(local_path, remote_path)
    
    sftp.close()

    print(f"Starting Python HTTP server on port {target_port}...")
    ssh.exec_command(f"fuser -k {target_port}/tcp")
    ssh.exec_command(f"cd {remote_dir} && nohup python3 -m http.server {target_port} --bind 0.0.0.0 > server.log 2>&1 &")
    
    time.sleep(2)
    stdin, stdout, stderr = ssh.exec_command(f'curl -s http://localhost:{target_port}/ > /dev/null && echo OK || echo FAIL')
    print('CURL TEST:', stdout.read().decode().strip())

    print(f"Deployment complete! Dashboard is hosted at http://{host}:{target_port}/")
    ssh.close()

except Exception as e:
    print(f"Failed to deploy: {e}")
