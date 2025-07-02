import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
from tkinter import ttk
import sys

class MenuUniversel(tk.Frame):
    def __init__(self, root, theme_manager):
        super().__init__(root, width=220)  # On retire le bg car il sera géré par le theme_manager
        self.root = root
        self.theme_manager = theme_manager
        self.submenus = {}
        
        # Enregistrer ce frame dans le theme_manager
        self.theme_manager.register_widget(self, 'bg_secondary')
        
        self.pack_propagate(False)  # empêche le frame de rétrécir

        # Structure du menu
        self.menu_structure = {
            "Gérer le serveur": {
                "Redémarrer le serveur": self.restart_server,
                "Réinstaller le serveur": self.reinstal_server,
                "Désinstaller le serveur": self.desinstall_server,
                "Supprimer les sauvegardes": self.efface_sauvegarde,
            },
            "Gérer Ansible": {
                "Mettre à jour ansible": self.install_ansible,
                "Désinstaller ansible": self.desintall_ansible
            }
        }

        # Création des éléments du menu
        self.create_menu_widgets()

    def create_menu_widgets(self):
        # Labels et séparateur
        self.title_label = tk.Label(self)
        self.theme_manager.register_widget(self.title_label, 'bg_secondary', 'fg_main')
        self.title_label.pack(pady=2)
        
        self.menu_title = tk.Label(self, text=" Outils systèmes", font=("Helvetica", 12, "bold"), anchor="center")
        self.theme_manager.register_widget(self.menu_title, 'bg_secondary', 'fg_main')
        self.menu_title.pack(pady=2)

        self.separator = tk.Frame(self, height=0.1, bg=self.theme_manager.separator)
        self.separator.pack(fill='x')
        self.theme_manager.register_widget(self.separator, 'separator')

        # Création des groupes de menu
        for group, actions in self.menu_structure.items():
            self.create_menu_group(group, actions)

    def create_menu_group(self, group_name, actions_dict):
        group_container = tk.Frame(self)
        self.theme_manager.register_widget(group_container, 'bg_secondary')
        group_container.pack(fill="x", anchor="w")

        submenu_frame = tk.Frame(self)
        self.theme_manager.register_widget(submenu_frame, 'bg_secondary')

        def toggle_submenu():
            visible = self.submenus.get(group_name, False)
            if visible:
                submenu_frame.pack_forget()
                btn.config(text=f"{group_name}  ▶")
            else:
                submenu_frame.pack(after=group_container, fill="x", anchor="w")
                btn.config(text=f"{group_name}  ▼")
            self.submenus[group_name] = not visible

        btn = tk.Button(
            group_container,
            text=f"{group_name}  ▶",
            anchor="w",
            command=toggle_submenu,
            font=("Helvetica", 11, "bold"),
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=20,
            pady=6,
            width=27
        )
        self.theme_manager.register_widget(btn, 'bg_secondary', 'fg_main','bg_hover')
        btn.config(
            activebackground=self.theme_manager.bg_hover
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=self.theme_manager.bg_hover))
        btn.bind("<Leave>", lambda e: btn.config(bg=self.theme_manager.bg_secondary))
        btn.pack(fill="x")

        for label, cmd in actions_dict.items():
            sub_btn = tk.Button(
                submenu_frame,
                text=f" • {label}",
                command=cmd,
                font=("Helvetica", 11),
                relief="flat",
                anchor="w",
                padx=30,
                pady=4,
                bd=0,
                highlightthickness=0
            )
            self.theme_manager.register_widget(sub_btn, 'bg_secondary', 'fg_main','bg_hover')
            sub_btn.config(
                activebackground=self.theme_manager.bg_hover
            )
            sub_btn.bind("<Enter>", lambda e, b=sub_btn: b.config(bg=self.theme_manager.bg_hover))
            sub_btn.bind("<Leave>", lambda e, b=sub_btn: b.config(bg=self.theme_manager.bg_secondary))
            sub_btn.pack(fill="x")


    def restart_server(self):
        """Action pour redémarrer le serveur (exemple avec un message)"""
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer cet équipement ?"):
            def run_1():
                try:
                    subprocess.run(["sudo", "systemctl", "start", "vsftpd"], check=True)
                    messagebox.showinfo("Action", "Le serveur a été redémarré.")
                except subprocess.CalledProcessError as e:
                    messagebox.showerror("Erreur", f"Échec du redémarrage : {e}")
            
            threading.Thread(target=run_1).start()


   

    def reinstal_server(self):
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment réinstaller le serveur sans perdre vos données ?"):
            def run_command(command, check=True):
                try:
                    subprocess.run(command, check=check)
                except subprocess.CalledProcessError as e:
                    print(f"Erreur lors de l'exécution : {' '.join(command)}\n{e}")

            def update_vsftpd_conf():
                print("Mise à jour de la configuration de vsftpd...")
                config_path = "/etc/vsftpd.conf"
                options = {
                    "write_enable": "YES",
                    "local_umask": "022",
                    "local_enable": "YES",
                    "chroot_local_user": "YES",
                    "allow_writeable_chroot": "YES"
                }

                # Lire et modifier le fichier si nécessaire
                with open(config_path, 'r') as file:
                    lines = file.readlines()

                updated_lines = []
                for line in lines:
                    key_found = False
                    for key in options:
                        if line.strip().startswith(key):
                            updated_lines.append(f"{key}={options[key]}\n")
                            key_found = True
                            break
                    if not key_found:
                        updated_lines.append(line)

                # Ajouter les options manquantes
                for key, value in options.items():
                    if not any(l.strip().startswith(key) for l in updated_lines):
                        updated_lines.append(f"{key}={value}\n")

                # Écrire la nouvelle config
                with open(config_path, 'w') as file:
                    file.writelines(updated_lines)

            def install_vsftpd():
                print("Installation de vsftpd...")
                run_command(['sudo', 'apt', 'update'])
                run_command(['sudo', 'apt', 'install', '-y', 'vsftpd'])

                update_vsftpd_conf()

                print("Activation et redémarrage de vsftpd...")
                run_command(['sudo', 'systemctl', 'enable', 'vsftpd'])
                run_command(['sudo', 'systemctl', 'restart', 'vsftpd'])

            def create_ftp_user():
                username = "ftpuser"
                password = "Ftpuser57"

                print(f"Création de l'utilisateur FTP : {username}")
                try:
                    subprocess.run(['sudo', 'useradd', '-m', username], check=True)
                except subprocess.CalledProcessError:
                    print(f"L'utilisateur {username} existe déjà.")

                print("Définition du mot de passe...")
                subprocess.run(f"echo '{username}:{password}' | sudo chpasswd", shell=True, check=True)

                print("Création et configuration du répertoire personnel...")
                run_command(['sudo', 'mkdir', '-p', f"/home/{username}"])
                run_command(['sudo', 'chown', f"{username}:{username}", f"/home/{username}"])
                run_command(['sudo', 'chmod', '755', f"/home/{username}"])
                run_command(['sudo', 'usermod', '-d', f"/home/{username}", username])

            def main():
                install_vsftpd()
                create_ftp_user()
                print("✅ Serveur FTP prêt. Essayez : ftp localhost")
                messagebox.showinfo("Succès", "Le serveur FTP a été réinstallé avec succès.")
            threading.Thread(target=main).start()

    def desinstall_server(self):
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment désinstaller le serveur et perdre vos données ?"):
            def run_2():
                try:
                    # Désinstaller vsftpd
                    print("Désinstallation de vsftpd...")
                    subprocess.run(['sudo', 'apt', 'remove', '--purge', 'vsftpd', '-y'], check=True)

                    # Supprimer les fichiers de configuration
                    print("Suppression des fichiers de configuration de vsftpd...")
                    subprocess.run(['sudo', 'rm', '-rf', '/etc/vsftpd.conf', '/etc/vsftpd*'], check=True)

                    # Supprimer l'utilisateur FTP
                    username = "ftpuser"
                    print(f"Suppression de l'utilisateur FTP : {username}")
                    subprocess.run(['sudo', 'userdel', '-r', username], check=True)

                    # Tenter d'arrêter le service vsftpd (sans check)
                    print("Arrêt du service vsftpd...")
                    subprocess.run(['sudo', 'systemctl', 'stop', 'vsftpd'])

                    # Désactivation au démarrage (sans check non plus pour éviter l'erreur si le service est absent)
                    print("Désactivation de vsftpd au démarrage...")
                    subprocess.run(['sudo', 'systemctl', 'disable', 'vsftpd'])

                    print("✅ Suppression de vsftpd terminée avec succès.")
                    messagebox.showinfo("Succès", "Le serveur FTP a été désinstallé avec succès.")

                except subprocess.CalledProcessError as e:
                    print(f"Erreur lors de la suppression de vsftpd : {e}")
                    messagebox.showerror("Erreur critique", f"Une erreur est survenue pendant la désinstallation :\n{e}")

            threading.Thread(target=run_2).start()


    def desintall_ansible(self):
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment réinstaller le serveur sans perdre vos données ?"):
            def is_ansible_installed():
                try:
                    # Vérifier si Ansible est installé en utilisant `which`
                    subprocess.check_call(["which", "ansible"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    return True
                except subprocess.CalledProcessError:
                    return False

            def uninstall_ansible():
                if not is_ansible_installed():
                    messagebox.showinfo("Succès", "Ansible n'est pas installé sur ce système.")
                    print("Ansible n'est pas installé sur ce système.")
                    return  # Si Ansible n'est pas installé, on arrête le script.

                try:
                    # Désinstallation d'Ansible
                    print("Désinstallation d'Ansible...")
                    subprocess.check_call(["sudo", "apt", "remove", "-y", "ansible"])

                    # Suppression des fichiers de configuration
                    print("Suppression des fichiers de configuration...")
                    subprocess.check_call(["sudo", "apt", "purge", "-y", "ansible"])

                    # Suppression des dépendances inutilisées
                    print("Suppression des dépendances inutilisées...")
                    subprocess.check_call(["sudo", "apt", "autoremove", "-y"])

                    print("Ansible a été désinstallé avec succès!")
                    messagebox.showinfo("Succès", "Ansible a été bien désinstallé")
                    # Vérification que Ansible a bien été désinstallé
                    if not is_ansible_installed():
                        print("Ansible a bien été désinstallé.")
                    else:
                        print("Erreur : Ansible est toujours installé.")
                    
                except subprocess.CalledProcessError as e:
                    print(f"Erreur lors de la désinstallation : {e}")
                    sys.exit(1)

            threading.Thread(target=uninstall_ansible).start()

    def install_ansible(self):
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment réinstaller le serveur sans perdre vos données ?"):
            def inst_ansible():
                try:
                    # Mise à jour des paquets système
                    print("Mise à jour des paquets système...")
                    subprocess.check_call(["sudo", "apt", "update", "-y"])
                    subprocess.check_call(["sudo", "apt", "upgrade", "-y"])

                    # Installer les dépendances nécessaires
                    print("Installation des dépendances...")
                    subprocess.check_call(["sudo", "apt", "install", "-y", "software-properties-common"])

                    # Ajouter le dépôt d'Ansible
                    print("Ajout du dépôt d'Ansible...")
                    subprocess.check_call(["sudo", "add-apt-repository", "--yes", "ppa:ansible/ansible"])

                    # Mettre à jour après ajout du dépôt
                    print("Mise à jour des paquets après ajout du dépôt...")
                    subprocess.check_call(["sudo", "apt", "update", "-y"])

                    # Installer Ansible
                    print("Installation d'Ansible...")
                    subprocess.check_call(["sudo", "apt", "install", "-y", "ansible"])

                    # Vérification de l'installation d'Ansible
                    print("Vérification de l'installation d'Ansible...")
                    subprocess.check_call(["ansible", "--version"])

                    print("Ansible a été installé avec succès!")
                    messagebox.showinfo("Succès", "Ansible a été mis à jour avec succès")
                except subprocess.CalledProcessError as e:
                    print(f"Erreur lors de l'installation : {e}")
                    sys.exit(1)
            threading.Thread(target=inst_ansible).start()


    def efface_sauvegarde(self):
        """Supprime tous les fichiers .cfg et .rsc du dossier /home/ftpuser avec sudo"""
        if messagebox.askyesno(
            "Confirmation", 
            "Voulez-vous vraiment supprimer toutes les sauvegardes?\n"
            "Cette action est irréversible !"
        ):

            def run_delete():
                try:
                    # Récupération de la liste des fichiers
                    result = subprocess.run(
                        ["sudo", "find", "/home/ftpuser", "-name", "*.cfg", "-o", "-name", "*.rsc"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    fichiers = result.stdout.splitlines()
                    
                    if not fichiers:
                        messagebox.showinfo("Information", "Aucun fichier de sauvegarde à supprimer.")
                        return
                    
                    # Suppression avec sudo
                    for fichier in fichiers:
                        subprocess.run(["sudo", "rm", fichier], check=True)
                    
                    # Rafraîchir après suppression
                    if hasattr(self.root, 'dashboard') and self.root.dashboard:
                        self.root.after(100, lambda: self.root.dashboard.remplir_fichiers_ftp())
                        self.root.after(100, lambda: self.root.dashboard.update_section(2))
                    messagebox.showinfo(
                        "Succès", 
                        f"{len(fichiers)} sauvegardes ont été supprimées avec succès."
                    )
                    
                except subprocess.CalledProcessError as e:
                    messagebox.showerror(
                        "Erreur", 
                        f"Échec de la suppression : {e.stderr or 'Permission refusée ou erreur système'}"
                    )
                except Exception as e:
                    messagebox.showerror("Erreur inattendue", f"Une erreur est survenue : {str(e)}")
            
            # Lancement dans un thread séparé
            threading.Thread(target=run_delete).start()