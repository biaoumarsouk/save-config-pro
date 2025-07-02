import os
import shutil
import json
import platform
import subprocess
from datetime import datetime
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


# Charger les sous-réseaux
networks_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files', 'networks.json')
with open(networks_path, 'r') as f:
    subnets = json.load(f)

subnet_ftp_map = {}
for subnet in subnets:
    ftp_ip = get_local_ip_in_subnet(subnet)
    if ftp_ip:
        subnet_ftp_map[subnet] = ftp_ip

if not subnet_ftp_map:
    raise RuntimeError("Impossible de détecter les adresses IP locales dans les sous-réseaux fournis.")

def is_reachable(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        result = subprocess.run(["ping", param, "1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        arp_result = subprocess.check_output(["arp", "-n", ip], universal_newlines=True)
        for line in arp_result.splitlines():
            if ip in line:
                parts = line.split()
                for part in parts:
                    if len(part) == 17 and part.count(":") == 5:
                        return part.upper()
    except Exception:
        pass
    return None

def get_subnet_for_ip(ip, subnets):
    ip_int = struct.unpack("!I", socket.inet_aton(ip))[0]
    for subnet in subnets:
        subnet_ip, subnet_mask = subnet.split('/')
        subnet_int = struct.unpack("!I", socket.inet_aton(subnet_ip))[0]
        mask_int = (0xFFFFFFFF << (32 - int(subnet_mask))) & 0xFFFFFFFF
        if (ip_int & mask_int) == (subnet_int & mask_int):
            return subnet
    return None

backup_parent_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files', 'backup_cisco')
if os.path.exists(backup_parent_dir):
    shutil.rmtree(backup_parent_dir)

has_valid_equipments = False
current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

json_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files', 'cisco_save.json')
with open(json_file, 'r') as f:
    equipments = json.load(f)

equipments_by_subnet = {subnet: [] for subnet in subnet_ftp_map}
equipments_by_subnet["unknown"] = []

for equipment in equipments:
    ip = equipment.get('ip')
    if ip:
        subnet = get_subnet_for_ip(ip, subnets)
        if subnet in equipments_by_subnet:
            equipments_by_subnet[subnet].append(equipment)
        else:
            equipments_by_subnet["unknown"].append(equipment)
    else:
        equipments_by_subnet["unknown"].append(equipment)

def process_subnet(subnet, ftp_ip, equipments):
    global has_valid_equipments
    inventory = []
    groupes = {"IOS": [], "ASA": []}

    inventory.append(f"# Fichier généré le {current_date}")
    inventory.append(f"# Sous-réseau: {subnet}")
    inventory.append(f"# Serveur FTP: {ftp_ip}\n")

    for equipment in equipments:
        equip_type = equipment.get("system", "").upper()
        ip = equipment.get('ip')
        username = equipment['credentials']['username']
        password = equipment['credentials']['password']
        expected_mac = equipment.get('mac', '').upper().replace("-", ":")

        if is_reachable(ip):
            actual_mac = get_mac_from_arp(ip)
            if actual_mac and actual_mac == expected_mac:
                if test_ssh_connection(ip, username, password):
                    mac = expected_mac.replace(":", "-")
                    username = equipment['credentials']['username']
                    password = equipment['credentials']['password']
                    enable_pwd = equipment['credentials'].get('enable_password')
                    if equip_type == "IOS":
                        line = f"{mac} ansible_host={ip} ansible_user={username} ansible_ssh_pass={password} ansible_network_os=cisco.ios.ios ansible_connection=network_cli"
                    elif equip_type == "ASA":
                        line = f"{mac} ansible_host={ip} ansible_user={username} ansible_ssh_pass={password} ansible_network_os=cisco.asa.asa ansible_connection=network_cli"
                    else:
                        continue
                    if enable_pwd:
                        line += f" ansible_become=yes ansible_become_method=enable ansible_become_password={enable_pwd}"
                    groupes[equip_type].append(line)
                    equipment['status'] = True
                    equipment['sauvegarde'] = True
                    equipment['subnet'] = subnet
                    equipment['ftp_server'] = ftp_ip
                    has_valid_equipments = True
                else:
                    equipment['sauvegarde'] = False
            else:
                equipment['sauvegarde'] = False
        else:
            equipment['sauvegarde'] = False


    if groupes["IOS"]:
        inventory.append("\n[ciscoios]")
        inventory.extend(groupes["IOS"])
    if groupes["ASA"]:
        inventory.append("\n[ciscoasa]")
        inventory.extend(groupes["ASA"])

    if groupes["IOS"] or groupes["ASA"]:
        subnet_dir = os.path.join(backup_parent_dir, f'backup_cisco_{ftp_ip}' if subnet != "unknown" else 'backup_cisco_unknown')
        os.makedirs(subnet_dir, exist_ok=True)

        with open(os.path.join(subnet_dir, 'inventory.ini'), 'w') as f:
            f.write("\n".join(inventory))

        with open(os.path.join(subnet_dir, 'ansible.cfg'), 'w') as f:
            f.write(f"# Configuration générée le {current_date}\n")
            f.write(f"# Pour le sous-réseau: {subnet}\n")
            f.write("[defaults]\n")
            f.write("ssh_args = -o KexAlgorithms=+diffie-hellman-group14-sha1,diffie-hellman-group1-sha1 -o HostKeyAlgorithms=+ssh-rsa -o Ciphers=+aes128-cbc,aes192-cbc,aes256-cbc,3des-cbc\n")
            f.write("host_key_checking = False\n")
            f.write("\n[network_cli]\n")
            f.write("timeout = 60\n")

        playbook_path = os.path.join(subnet_dir, 'backup_cisco_ftp.yml')
        with open(playbook_path, 'w') as f:
            f.write(f"""---
# Playbook généré le {current_date}
# Pour le sous-réseau: {subnet}
# Serveur FTP: {ftp_ip}

- name: Sauvegarde des configurations Cisco via FTP
  hosts: ciscoios
  gather_facts: yes
  vars:
    ftp_server: "{ftp_ip}"
    ftp_username: "ftpuser"
    ftp_password: "Ftpuser57"
    current_date: "{{{{ lookup('pipe', 'date +\\\"%Y-%m-%d_%H-%M-%S\\\"') }}}}"
  tasks:
    - name: Copier la configuration vers le serveur FTP
      cisco.ios.ios_command:
        commands:
          - "copy running-config ftp://{{{{ ftp_username }}}}:{{{{ ftp_password }}}}@{{{{ ftp_server }}}}/cisco_ios_{{{{ inventory_hostname }}}}_{{{{ current_date }}}}.cfg\\n\\n"
      register: result
      ignore_errors: yes

- name: Sauvegarde automatique de la configuration Cisco ASA vers FTP
  hosts: ciscoasa
  gather_facts: no
  connection: network_cli
  vars:
    ftp_server: "{ftp_ip}"
    ftp_username: "ftpuser"
    ftp_password: "Ftpuser57"
    backup_filename: "cisco_asa_{{{{ inventory_hostname_short }}}}_{{{{ lookup('pipe', 'date +\\\"%Y-%m-%d_%H-%M-%S\\\"') }}}}.cfg"
  tasks:
    - name: Exécuter la sauvegarde vers FTP
      ansible.netcommon.cli_command:
        command: |
          copy /noconfirm running-config ftp://{{{{ ftp_username }}}}:{{{{ ftp_password }}}}@{{{{ ftp_server }}}}/{{{{ backup_filename }}}}
        check_all: False
      register: backup_result
      retries: 3
      delay: 10
      ignore_errors: yes

    - name: Vérifier le résultat de la sauvegarde
      assert:
        that:
          - "'bytes copied' in backup_result.stdout"
        fail_msg: "Échec de la sauvegarde FTP"
        success_msg: "Sauvegarde réussie vers FTP"
      when: backup_result is not skipped

    - name: Afficher les détails de la sauvegarde
      debug:
        var: backup_result.stdout_lines
      when: backup_result is not skipped
""")

# Traiter tous les sous-réseaux détectés
for subnet, ftp_ip in subnet_ftp_map.items():
    process_subnet(subnet, ftp_ip, equipments_by_subnet[subnet])

# Traiter les équipements au sous-réseau inconnu
if equipments_by_subnet["unknown"]:
    process_subnet("unknown", "0.0.0.0", equipments_by_subnet["unknown"])

# Supprimer tout si rien n'a été généré
if not has_valid_equipments and os.path.exists(backup_parent_dir):
    shutil.rmtree(backup_parent_dir)

# Sauvegarder les statuts
with open(json_file, 'w') as f:
    json.dump(equipments, f, indent=4)

if has_valid_equipments:
    print(f"Fichiers créés avec succès dans les répertoires sous {backup_parent_dir}")
else:
    print("Aucun équipement valide trouvé - aucun fichier créé")
