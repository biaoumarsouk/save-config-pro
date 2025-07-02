import os
import shutil
import json
import subprocess
from datetime import datetime
import platform
import psutil
import struct
import socket
import paramiko


def get_local_ip_in_subnet(subnet_cidr):
    subnet_ip, subnet_mask = subnet_cidr.split('/')
    subnet_int = struct.unpack("!I", socket.inet_aton(subnet_ip))[0]
    mask_int = (0xFFFFFFFF << (32 - int(subnet_mask))) & 0xFFFFFFFF

    def ip_to_int(ip):
        return struct.unpack("!I", socket.inet_aton(ip))[0]

    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip_int = ip_to_int(addr.address)
                if (ip_int & mask_int) == (subnet_int & mask_int):
                    return addr.address
    return None

def is_reachable(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        result = subprocess.run(['ping', param, '1', ip],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False
    
def test_ssh_connection(ip, username, password, timeout=3):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            hostname=ip,
            username=username,
            password=password,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False
        )
        client.close()
        return True
    except (paramiko.ssh_exception.AuthenticationException,
            paramiko.ssh_exception.SSHException,
            socket.error):
        return False

def get_mac_from_arp(ip):
    try:
        if platform.system().lower() == "windows":
            output = subprocess.check_output(f"arp -a {ip}", shell=True, text=True)
            for line in output.splitlines():
                if ip in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1].replace("-", ":").lower()
        else:
            output = subprocess.check_output(f"arp -n {ip}", shell=True, text=True)
            for line in output.splitlines():
                if ip in line:
                    parts = line.split()
                    for part in parts:
                        if ':' in part and len(part) == 17:
                            return part.lower()
            if not output.strip():
                output = subprocess.check_output(f"ip neigh show {ip}", shell=True, text=True)
                for line in output.splitlines():
                    if ip in line:
                        parts = line.split()
                        for part in parts:
                            if ':' in part and len(part) == 17:
                                return part.lower()
    except Exception:
        pass
    return None

def get_ftp_server_for_ip(ip, subnets_ftp_mapping):
    for subnet, ftp_server in subnets_ftp_mapping.items():
        subnet_ip, subnet_mask = subnet.split('/')
        subnet_int = struct.unpack("!I", socket.inet_aton(subnet_ip))[0]
        mask_int = (0xFFFFFFFF << (32 - int(subnet_mask))) & 0xFFFFFFFF
        ip_int = struct.unpack("!I", socket.inet_aton(ip))[0]
        
        if (ip_int & mask_int) == (subnet_int & mask_int):
            return ftp_server
    return None

# Charger les sous-réseaux et les serveurs FTP correspondants
networks_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files', 'networks.json')
with open(networks_path, 'r') as f:
    subnets = json.load(f)

# Créer un mapping sous-réseau -> serveur FTP
subnets_ftp_mapping = {}
for subnet in subnets:
    ftp_server_ip = get_local_ip_in_subnet(subnet)
    if ftp_server_ip:
        subnets_ftp_mapping[subnet] = ftp_server_ip

if not subnets_ftp_mapping:
    raise RuntimeError("Impossible de détecter les adresses IP locales dans les sous-réseaux fournis.")

# Charger la liste des équipements Fortinet
json_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'files', 'fortinet_save.json'))
with open(json_file, 'r') as f:
    equipments = json.load(f)

# Organiser les équipements par serveur FTP
ftp_equipments = {ftp_ip: [] for ftp_ip in subnets_ftp_mapping.values()}

reachable_equipments = []
for eq in equipments:
    ip = eq['ip']
    username = eq['credentials']['username']
    password = eq['credentials']['password']
    expected_mac = eq['mac'].lower()
    subprocess.run(f"ssh-keygen -R {ip}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if is_reachable(ip):
        real_mac = get_mac_from_arp(ip)
        if real_mac and real_mac == expected_mac:
            if test_ssh_connection(ip, username, password):
                eq['status'] = True
                eq['sauvegarde'] = True

                # Trouver le subnet et le serveur FTP correspondant
                for subnet, ftp_server in subnets_ftp_mapping.items():
                    subnet_ip, subnet_mask = subnet.split('/')
                    subnet_int = struct.unpack("!I", socket.inet_aton(subnet_ip))[0]
                    mask_int = (0xFFFFFFFF << (32 - int(subnet_mask))) & 0xFFFFFFFF
                    ip_int = struct.unpack("!I", socket.inet_aton(ip))[0]

                    if (ip_int & mask_int) == (subnet_int & mask_int):
                        eq["subnet"] = subnet
                        eq["ftp_server"] = ftp_server
                        ftp_equipments[ftp_server].append(eq)
                        break

                reachable_equipments.append(eq)
            else:
                eq['sauvegarde'] = False
        else:
            eq['sauvegarde'] = False
    else:
        eq['sauvegarde'] = False


if not reachable_equipments:
    print("❌ Aucun équipement FortiGate joignable avec MAC correspondante.")
    exit()

# Mettre à jour le JSON
with open(json_file, 'w') as f:
    json.dump(equipments, f, indent=4)

# Répertoire parent pour tous les backups
parent_backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files', 'backup_fortinet')
current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Réinitialiser le répertoire parent
if os.path.exists(parent_backup_dir):
    shutil.rmtree(parent_backup_dir)
os.makedirs(parent_backup_dir)

# Créer un backup pour chaque serveur FTP
for ftp_server_ip, eq_list in ftp_equipments.items():
    if not eq_list:
        continue
        
    # Créer le répertoire spécifique pour ce serveur FTP
    backup_dir = os.path.join(parent_backup_dir, f'backup_fortinet_{ftp_server_ip}')
    os.makedirs(backup_dir)

    # Générer inventory.ini (avec ansible_connection=ssh)
    inventory_file = os.path.join(backup_dir, 'inventory.ini')
    with open(inventory_file, 'w') as f:
        f.write(f"# Fichier généré le {current_date}\n[fortinet]\n")
        for eq in eq_list:
            f.write(
                f"{eq['mac'].replace(':', '-')} ansible_host={eq['ip']} "
                f"ansible_user={eq['credentials']['username']} "
                f"ansible_ssh_pass={eq['credentials']['password']} "
                "ansible_connection=ssh\n"
            )

    # Générer ansible.cfg
    ansible_cfg_file = os.path.join(backup_dir, 'ansible.cfg')
    with open(ansible_cfg_file, 'w') as f:
        f.write(f"# Configuration générée le {current_date}\n")
        f.write("[defaults]\n")
        f.write("inventory = inventory.ini\n")
        f.write("host_key_checking = False\n")
        f.write("timeout = 60\n")
        f.write("gathering = explicit\n")
        f.write("deprecation_warnings = False\n\n")
        f.write("[ssh_connection]\n")
        f.write("ssh_args = -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa\n")

    # Générer le playbook avec raw
    playbook_path = os.path.join(backup_dir, 'backup_fortinet_ftp.yml')
    with open(playbook_path, 'w') as f:
        f.write(f"""---
# Playbook FortiGate - Généré le {current_date}
- name: Sauvegarder la configuration FortiGate via FTP
  hosts: fortinet
  gather_facts: no
  tasks:
    - name: Backup config via raw command
      ansible.builtin.raw: >
        execute backup config ftp fortinet_{{{{ inventory_hostname }}}}_{{{{ lookup('pipe', 'date +%Y-%m-%d_%H-%M-%S') }}}}.cfg
        {ftp_server_ip}
        ftpuser
        Ftpuser57
""")

    print(f"✅ Sauvegarde générée pour le serveur FTP {ftp_server_ip} dans : {backup_dir}")
    print("▶️ Pour exécuter le playbook :")
    print(f"ansible-playbook -i {inventory_file} {playbook_path}\n")