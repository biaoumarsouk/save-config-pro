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

# Charger les sous-réseaux
networks_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files', 'networks.json')
with open(networks_path, 'r') as f:
    subnets = json.load(f)

# Dictionnaire pour stocker les IPs des serveurs FTP par sous-réseau
subnet_ftp_servers = {}

# Trouver l'IP locale dans chaque sous-réseau
for subnet in subnets:
    ftp_ip = get_local_ip_in_subnet(subnet)
    if ftp_ip:
        subnet_ftp_servers[subnet] = ftp_ip

if not subnet_ftp_servers:
    raise RuntimeError("Impossible de détecter les adresses IP locales dans les sous-réseaux fournis.")

# Fonction pour déterminer à quel sous-réseau appartient une IP
def get_subnet_for_ip(ip):
    ip_int = struct.unpack("!I", socket.inet_aton(ip))[0]
    for subnet_cidr in subnet_ftp_servers.keys():
        subnet_ip, subnet_mask = subnet_cidr.split('/')
        subnet_int = struct.unpack("!I", socket.inet_aton(subnet_ip))[0]
        mask_int = (0xFFFFFFFF << (32 - int(subnet_mask))) & 0xFFFFFFFF
        if (ip_int & mask_int) == (subnet_int & mask_int):
            return subnet_cidr
    return None

# Fonction pour tester la connectivité avec ping
def is_reachable(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        result = subprocess.run(['ping', param, '1', ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

# Fonction pour récupérer la MAC correspondant à une IP via la table ARP locale
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

# Chemin vers mikrotik_save.json
json_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files', 'mikrotik_save.json')
json_file = os.path.abspath(json_file)

# Charger les équipements MikroTik
with open(json_file, 'r') as f:
    equipments = json.load(f)

# Répertoire parent de sauvegarde
parent_backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files', 'backup_mikrotik')
current_date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Vérifier s'il y a des équipements valides avant de créer le répertoire parent
has_valid_equipments = False

# Filtrage des équipements joignables et avec MAC correcte
reachable_equipments = []
for eq in equipments:
    ip = eq['ip']
    username = eq['credentials']['username']
    password = eq['credentials']['password']
    expected_mac = eq['mac'].lower()
    if is_reachable(ip):
        real_mac = get_mac_from_arp(ip)
        if real_mac is not None and real_mac == expected_mac:
            if test_ssh_connection(ip, username, password):
                eq['status'] = True
                eq['sauvegarde'] = True
                subnet_cidr = get_subnet_for_ip(ip)
                if subnet_cidr:
                    eq['subnet'] = subnet_cidr
                    eq['ftp_server'] = subnet_ftp_servers[subnet_cidr]
                    reachable_equipments.append(eq)
                    has_valid_equipments = True
            else:
                eq['sauvegarde'] = False
        else:
            eq['sauvegarde'] = False
    else:
        eq['sauvegarde'] = False

# Écriture du nouveau fichier mikrotik_save.json avec statuts mis à jour
with open(json_file, 'w') as f:
    json.dump(equipments, f, indent=4)

# Ne rien faire si aucun équipement joignable et validé MAC
if not has_valid_equipments:
    print("Aucun équipement MikroTik joignable avec MAC correspondante. Aucune sauvegarde générée.")
    exit()

# Supprimer le répertoire parent s'il existe déjà
if os.path.exists(parent_backup_dir):
    shutil.rmtree(parent_backup_dir)

# Créer le répertoire parent seulement si on a des équipements valides
os.makedirs(parent_backup_dir)

# Création des dossiers de sauvegarde par sous-réseau
backup_dirs = {}
for subnet_cidr, ftp_ip in subnet_ftp_servers.items():
    backup_dir_name = f"backup_mikrotik_{ftp_ip.replace('.', '.')}"
    backup_dir = os.path.join(parent_backup_dir, backup_dir_name)
    
    # Filtrer les équipements pour ce sous-réseau
    subnet_equipments = [eq for eq in reachable_equipments if eq.get('subnet') == subnet_cidr]
    
    if not subnet_equipments:
        continue  # Aucun équipement pour ce sous-réseau
    
    # Créer le répertoire
    os.makedirs(backup_dir)
    backup_dirs[subnet_cidr] = backup_dir

    # Génération du fichier inventory.ini
    inventory_file = os.path.join(backup_dir, 'inventory.ini')
    with open(inventory_file, 'w') as f:
        f.write(f"# Fichier généré le {current_date}\n[all]\n")
        for eq in subnet_equipments:
            f.write(
                f"{eq['mac'].replace(':', '-')} ansible_host={eq['ip']} "
                f"ansible_user={eq['credentials']['username']} "
                f"ansible_ssh_pass={eq['credentials']['password']} "
                "ansible_network_os=routeros ansible_connection=network_cli\n"
            )

    # Génération du fichier ansible.cfg
    ansible_cfg_file = os.path.join(backup_dir, 'ansible.cfg')
    with open(ansible_cfg_file, 'w') as f:
        f.write(f"# Configuration générée le {current_date}\n")
        f.write("[defaults]\n")
        f.write("host_key_checking = False\n")
        f.write("timeout = 60\n\n")
        f.write("[ssh_connection]\n")
        f.write("ssh_args = -o KexAlgorithms=+diffie-hellman-group14-sha1 -o HostKeyAlgorithms=+ssh-rsa\n")

    # Génération du fichier Playbook (.rsc)
    playbook_path = os.path.join(backup_dir, 'backup_mikrotik_ftp.yml')
    with open(playbook_path, 'w') as f:
        f.write(f"""---
# Playbook généré le {current_date}
- name: Export, upload FTP, and cleanup on MikroTik
  hosts: all
  gather_facts: no
  vars:
    ansible_network_timeout: 60
    export_file_name: "export_{{{{ inventory_hostname }}}}.rsc"
    ftp_address: "{ftp_ip}"
    ftp_user: "ftpuser"
    ftp_password: "Ftpuser57"
    ftp_dst_path: "/mikrotik_{{{{ inventory_hostname }}}}_{{{{ lookup('pipe', 'date +%Y-%m-%d_%H-%M-%S') }}}}.rsc"

  tasks:
    - name: Exporter la configuration MikroTik (.rsc)
      community.routeros.command:
        commands:
          - "/export file={{{{ export_file_name | regex_replace('.rsc$', '') }}}}"

    - name: Pause pour garantir que le fichier est créé
      pause:
        seconds: 3

    - name: Transférer l'export via FTP
      community.routeros.command:
        commands:
          - >
            /tool fetch address={{{{ ftp_address }}}}
            src-path={{{{ export_file_name }}}}
            user={{{{ ftp_user }}}}
            mode=ftp
            password={{{{ ftp_password }}}}
            dst-path={{{{ ftp_dst_path }}}}
            upload=yes
      register: ftp_upload
      retries: 3
      delay: 5
      until: ftp_upload is success

    - name: Supprimer le fichier local (.rsc)
      community.routeros.command:
        commands:
          - "/file remove {{{{ export_file_name }}}}"
      when: ftp_upload is succeeded
""")

    print(f"Fichiers créés avec succès pour le sous-réseau {subnet_cidr} dans le répertoire: {backup_dir}")

# Si aucun sous-réseau n'avait d'équipements valides (normalement impossible à ce stade)
if not backup_dirs:
    if os.path.exists(parent_backup_dir):
        shutil.rmtree(parent_backup_dir)
    print("Aucun équipement valide trouvé dans aucun sous-réseau. Aucun fichier créé.")