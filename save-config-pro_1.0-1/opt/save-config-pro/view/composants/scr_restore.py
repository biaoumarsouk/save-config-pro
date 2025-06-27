import argparse
import os
import subprocess
from datetime import datetime
import psutil
import struct
import socket
import json

def get_local_ip_in_subnet(subnet_cidr):
    """Trouve l'IP locale dans un sous-réseau donné"""
    try:
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
    except Exception:
        return None
    return None

def get_default_local_ip():
    """Trouve une IP locale sans se baser sur les sous-réseaux"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return None

# Charger les sous-réseaux
networks_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files', 'networks.json')
subnets = []

try:
    if os.path.exists(networks_path) and os.path.getsize(networks_path) > 0:
        with open(networks_path, 'r') as f:
            subnets = json.load(f)
            if not isinstance(subnets, list):
                subnets = []
except (json.JSONDecodeError, Exception) as e:
    print(f"[AVERTISSEMENT] Erreur lors de la lecture de networks.json: {e}")
    subnets = []

# Trouver l'IP du serveur FTP
ftp_server_ip = None

# Essayer d'abord avec les sous-réseaux configurés
for subnet in subnets:
    ftp_server_ip = get_local_ip_in_subnet(subnet)
    if ftp_server_ip:
        break

# Si aucune IP n'a été trouvée via les sous-réseaux
if not ftp_server_ip:
    ftp_server_ip = get_default_local_ip()
    if ftp_server_ip:
        print(f"[INFO] Utilisation de l'IP locale par défaut: {ftp_server_ip}")
    else:
        # Demander à l'utilisateur de saisir l'IP manuellement
        try:
            ftp_server_ip = input("Veuillez entrer l'adresse IP du serveur FTP: ")
            if not ftp_server_ip:
                raise RuntimeError("Aucune adresse IP de serveur FTP fournie")
        except Exception:
            raise RuntimeError("""
Impossible de déterminer l'adresse IP du serveur FTP. Veuillez :
1. Vérifier que le fichier networks.json contient des sous-réseaux valides, ou
2. Configurer manuellement l'adresse IP du serveur FTP, ou
3. Vérifier que votre interface réseau est correctement configurée
""")

def generate_restore_files(config_file, ip, username, password, device_type, system="ios", enable_password=None):
    """Génère les fichiers et exécute le playbook Ansible pour la restauration"""
    composants_dir = os.path.dirname(os.path.abspath(__file__))
    projet_root = os.path.dirname(composants_dir)
    files_dir = os.path.join(projet_root, 'files')
    restore_dir = os.path.join(files_dir, f'restore_{device_type.lower()}')
    os.makedirs(restore_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Configuration Ansible
    ansible_cfg = f"""# Configuration générée le {timestamp}
[defaults]
host_key_checking = False
"""

    become_line = ""
    if enable_password:
        become_line = f" ansible_become=yes ansible_become_method=enable ansible_become_password={enable_password}"

    # Traitement selon le type de périphérique
    if device_type.lower() == "cisco":
        if system.lower() == "asa":
            # Cisco ASA
            playbook_content = f"""---
- name: Restauration Cisco ASA depuis FTP
  hosts: all
  gather_facts: no
  vars:
    ftp_server: "{ftp_server_ip}"
    ftp_username: "ftpuser"
    ftp_password: "Marsouk57"
    config_file: "{config_file}"

  tasks:
    - name: Copier la configuration depuis FTP vers startup-config
      cisco.asa.asa_command:
        commands:
          - "copy /noconfirm ftp://{{{{ ftp_username }}}}:{{{{ ftp_password }}}}@{{{{ ftp_server }}}}/{{{{ config_file }}}} startup-config"
      register: copy_result
      ignore_errors: yes

    - name: Appliquer la configuration (startup-config vers running-config)
      cisco.asa.asa_command:
        commands:
          - "reload noconfirm"
      when: copy_result is not skipped
"""
            inventory_content = f"""# Fichier généré le {timestamp}
[all]
{ip} ansible_host={ip} ansible_user={username} ansible_ssh_pass={password} ansible_network_os=asa ansible_connection=network_cli{become_line}
"""

        else:
            # Cisco IOS
            ansible_cfg += """\n[network_cli]
timeout = 60
ssh_args = -o KexAlgorithms=+diffie-hellman-group14-sha1,diffie-hellman-group1-sha1 -o HostKeyAlgorithms=+ssh-rsa -o Ciphers=+aes128-cbc,aes192-cbc,aes256-cbc,3des-cbc
"""
            playbook_content = f"""---
- name: Restauration Cisco depuis FTP
  hosts: all
  gather_facts: yes
  vars:
    ftp_server: "{ftp_server_ip}"
    ftp_username: "ftpuser"
    ftp_password: "Marsouk57"
    config_file: "{config_file}"

  tasks:
    - name: Copier la configuration depuis FTP
      cisco.ios.ios_command:
        commands:
          - "copy ftp://{{{{ ftp_username }}}}:{{{{ ftp_password }}}}@{{{{ ftp_server }}}}/{{{{ config_file }}}} startup-config\\n\\n"
      register: result
      ignore_errors: yes

    - name: Appliquer la configuration
      cisco.ios.ios_command:
        commands:
          - "copy startup-config running-config\\n\\n"
      when: not result.failed
      ignore_errors: yes
"""
            inventory_content = f"""# Fichier généré le {timestamp}
[all]
{ip} ansible_host={ip} ansible_user={username} ansible_ssh_pass={password} ansible_network_os=ios ansible_connection=network_cli{become_line}
"""

    elif device_type.lower() == "mikrotik":
        ansible_cfg += """\n[persistent_connection]
connect_timeout = 60
command_timeout = 300
"""
        playbook_content = f"""---
- name: Restauration MikroTik depuis FTP
  hosts: all
  gather_facts: no
  vars:
    ftp_address: "{ftp_server_ip}"
    ftp_user: "ftpuser"
    ftp_password: "Marsouk57"
    rsc_file_name: "{config_file}"

  tasks:
    - name: Télécharger le fichier RSC
      community.routeros.command:
        commands:
          - >
            /tool fetch address={{{{ ftp_address }}}}
            src-path={{{{ rsc_file_name }}}}
            user={{{{ ftp_user }}}}
            password={{{{ ftp_password }}}}
            mode=ftp
            dst-path={{{{ rsc_file_name }}}}
            upload=no
      register: fetch_result
      retries: 3
      delay: 5

    - name: Importer la configuration
      community.routeros.command:
        commands:
          - /import file-name={{{{ rsc_file_name }}}}
      register: import_result
"""
        inventory_content = f"""# Fichier généré le {timestamp}
[all]
{ip} ansible_host={ip} ansible_user={username} ansible_ssh_pass={password} ansible_network_os=routeros ansible_connection=network_cli{become_line}
"""

    else:
        print(f"[✖] Type d'équipement non pris en charge : {device_type}")
        return

    # Création des fichiers
    files_to_create = {
        "ansible.cfg": ansible_cfg,
        f"restore_{device_type.lower()}_ftp.yml": playbook_content,
        "inventory.ini": inventory_content
    }

    for filename, content in files_to_create.items():
        filepath = os.path.join(restore_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"[✔] Fichiers générés dans '{restore_dir}'")

    # Exécution du playbook
    playbook_path = os.path.join(restore_dir, f"restore_{device_type.lower()}_ftp.yml")
    inventory_path = os.path.join(restore_dir, "inventory.ini")

    print(f"\n[⚡] Exécution du playbook Ansible pour {device_type} ({system})...")
    try:
        subprocess.run([
            "ansible-playbook",
            "-i", inventory_path,
            playbook_path
        ], check=True, cwd=restore_dir)
        print("[✔] Playbook exécuté avec succès")
    except subprocess.CalledProcessError as e:
        print(f"[✖] Erreur lors de l'exécution du playbook: {e}")
    except Exception as e:
        print(f"[✖] Erreur inattendue: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Génère et exécute les playbooks de restauration')
    parser.add_argument('--config_file', required=True, help='Nom du fichier de configuration')
    parser.add_argument('--ip', required=True, help='Adresse IP de l\'équipement')
    parser.add_argument('--username', required=True, help='Nom d\'utilisateur')
    parser.add_argument('--password', required=True, help='Mot de passe')
    parser.add_argument('--device_type', required=True, choices=['cisco', 'mikrotik'], help='Type d\'équipement')
    parser.add_argument('--system', default='ios', help='Sous-type (ios ou asa pour Cisco)')
    parser.add_argument('--enable_password', help='Mot de passe enable (si requis)', default=None)

    args = parser.parse_args()

    generate_restore_files(
        config_file=args.config_file,
        ip=args.ip,
        username=args.username,
        password=args.password,
        device_type=args.device_type,
        system=args.system,
        enable_password=args.enable_password
    )