import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import platform
import subprocess
from .composants.loading import run_with_loading
from datetime import datetime

class DetailsSaveRestaurationFrame(tk.Toplevel):
    fenetre_ouverte = False  # contrôle unique pour empêcher plusieurs fenêtres

    def __init__(self, parent, details, theme_manager,current_user=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.title("Détails de l'équipement")
        self.geometry("700x500")
        self.resizable(False, False)
        self.configure(bg=self.theme_manager.bg_main)
        self.theme_manager.register_widget(self, 'bg_main')
        self.nom_equipement = details[0]
        self.ip_equipement = details[1]
        self.type_equipement = details[2]
        self.dossier_sauvegarde = "/home/ftpuser"
        self.open_file_window = None
        self.current_user = current_user  # Nouvel attribut pour stocker l'utilisateur

        # JSON path
        fichiers = {
            "MikroTik": "mikrotik_save.json",
            "Cisco": "cisco_save.json",
            "Huawei": "huawei_save.json",
            "Juniper": "juniper_save.json",
            "Fortinet": "fortinet_save.json"
        }
        base_path = os.path.join(os.path.dirname(__file__), 'files')
        filename = fichiers.get(self.type_equipement)
        json_path = os.path.join(base_path, filename) if filename else None

        self.credentials_data = self.charger_donnees_json(json_path)
        self.infos = self.trouver_infos_equipement()
        self.mac = self.infos.get("mac", "inconnu")

        self.columnconfigure(0, weight=1)

        # Titre
        title_frame = tk.Frame(self)
        title_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        title_frame.columnconfigure(0, weight=1)

        title_label = tk.Label(title_frame, text="Status", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, sticky="w")

        self.status_dot = tk.Canvas(title_frame, width=16, height=16, highlightthickness=0)
        self.status_dot.grid(row=0, column=1, sticky="e")
        self.mettre_a_jour_statut()

        # Informations
        info_frame = tk.Frame(self)
        info_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        labels = ["Nom", "Adresse IP", "Type", "MAC", "Nom d'utilisateur", "Mot de passe"]
        values = [
            self.nom_equipement,
            self.ip_equipement,
            self.type_equipement,
            self.mac,
            self.infos.get("credentials", {}).get("username", "Inconnu"),
            self.infos.get("credentials", {}).get("password", "Inconnu")
        ]

        self.mdp_var = tk.StringVar(value=values[-1])
        self.mdp_visible = False

        for i in range(0, len(labels), 2):
            for j in range(2):
                index = i + j
                if index < len(values):
                    label = tk.Label(info_frame, text=f"{labels[index]} :", font=("Arial", 11),
                                   fg=self.theme_manager.fg_main, bg=self.theme_manager.bg_main)
                    label.grid(row=i//2, column=2*j, sticky="w", padx=(0, 5), pady=2)

                    if labels[index] == "Mot de passe":
                        mdp_frame = tk.Frame(info_frame)
                        mdp_frame.grid(row=i//2, column=2*j+1, sticky="w", pady=2)
                        self.mdp_entry = tk.Entry(mdp_frame, textvariable=self.mdp_var,
                                                font=("Arial", 11, "bold"), show="*",
                                                relief="flat", width=20,
                                                fg=self.theme_manager.fg_main,
                                                bg=self.theme_manager.bg_main,
                                                readonlybackground=self.theme_manager.bg_main,
                                                state="readonly")
                        self.mdp_entry.pack(side="left")
                        self.eye_btn = tk.Button(mdp_frame, text="🔒", font=("Arial", 10),
                                               relief="flat", fg=self.theme_manager.fg_main,
                                               bg=self.theme_manager.bg_main,
                                               command=self.toggle_mdp_visibility)
                        self.eye_btn.pack(side="left", padx=5)
                    else:
                        value = tk.Label(info_frame, text=values[index], font=("Arial", 11, "bold"),
                                       bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main)
                        value.grid(row=i//2, column=2*j+1, sticky="w", pady=2)

        for col in range(4):
            info_frame.columnconfigure(col, weight=1)

        ttk.Separator(self, orient="horizontal").grid(row=3, column=0, sticky="ew", padx=10, pady=10)

        tk.Label(self, text="Fichiers de sauvegarde :", font=("Arial", 12, "bold"),
                fg=self.theme_manager.fg_main, bg=self.theme_manager.bg_main).grid(row=4, column=0, padx=10, sticky="ew")

        self.file_listbox = tk.Listbox(self, height=10)
        self.file_listbox.grid(row=5, column=0, padx=20, pady=5, sticky="nsew")
        self.file_listbox.bind("<Double-Button-1>", self.ouvrir_contenu_fichier)
        self.rowconfigure(5, weight=1)
        
        self.theme_manager.register_widget(mdp_frame, 'bg_main', 'fg_main','bg_hover')
        self.theme_manager.register_widget(title_label, 'bg_main', 'fg_main')
        self.theme_manager.register_widget(title_frame, 'bg_main')
        self.theme_manager.register_widget(info_frame, 'bg_main')
        self.theme_manager.register_widget(self.status_dot, 'bg_main')
        self.theme_manager.register_widget(self.file_listbox, 'bg_secondary', 'fg_main')

        self.charger_fichiers()
        self.transient(parent)
        self.update()
        self.grab_set()
        self.focus()


    def toggle_mdp_visibility(self):
        self.mdp_visible = not self.mdp_visible
        self.mdp_entry.config(show="" if self.mdp_visible else "*")
        self.eye_btn.config(text="🔓" if self.mdp_visible else "🔒")

    def charger_fichiers(self):
        """Charge les fichiers de sauvegarde liés à la MAC adresse"""
        self.file_listbox.delete(0, tk.END)
        if not self.mac or not os.path.exists(self.dossier_sauvegarde):
            self.file_listbox.insert(tk.END, "Aucun fichier trouvé.")
            return

        try:
            fichiers = os.listdir(self.dossier_sauvegarde)
            fichiers_associes = [f for f in fichiers if self.mac.replace(":", "-").upper() in f]
            fichiers_associes.sort(key=lambda x: os.path.getmtime(os.path.join(self.dossier_sauvegarde, x)), reverse=True)

            for fichier in fichiers_associes:
                # Récupérer la date de modification du fichier
                timestamp = os.path.getmtime(os.path.join(self.dossier_sauvegarde, fichier))
                date_modif = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                self.file_listbox.insert(tk.END, f"{date_modif}    |    {fichier}")

            if not fichiers_associes:
                self.file_listbox.insert(tk.END, "Aucun fichier trouvé pour cet équipement.")
        except Exception as e:
            self.file_listbox.insert(tk.END, f"Erreur : {e}")
    
    def ouvrir_contenu_fichier(self, event):
        if self.open_file_window is not None and self.open_file_window.winfo_exists():
            messagebox.showinfo("Fenêtre déjà ouverte", "Veuillez fermer la fenêtre actuelle d'abord.")
            return

        selection = self.file_listbox.curselection()
        if not selection:
            return

        line = self.file_listbox.get(selection[0])
        filename = line.split("|")[-1].strip()
        filepath = os.path.join(self.dossier_sauvegarde, filename)

        if not os.path.exists(filepath):
            messagebox.showerror("Erreur", "Fichier introuvable.")
            return

        self.open_file_window = tk.Toplevel(self)
        self.open_file_window.title(f"Contenu de {filename}")
        self.open_file_window.geometry("600x400")
        self.open_file_window.configure(bg=self.theme_manager.bg_main)
        self.theme_manager.register_widget(self.open_file_window, 'bg_main')

        # Utilisation de grid pour avoir une meilleure maîtrise
        self.open_file_window.rowconfigure(0, weight=1)
        self.open_file_window.rowconfigure(1, weight=0)
        self.open_file_window.columnconfigure(0, weight=1)

        # Zone texte avec scrollbar
        text_frame = tk.Frame(self.open_file_window, bg=self.theme_manager.bg_main)
        text_frame.grid(row=0, column=0, sticky="nsew")

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        text_area = tk.Text(text_frame, wrap="word",
                          bg=self.theme_manager.bg_main,
                          fg=self.theme_manager.fg_main,
                          yscrollcommand=scrollbar.set)
        text_area.pack(side="left", expand=True, fill="both")
        scrollbar.config(command=text_area.yview)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                text_area.insert("1.0", content)
        except Exception as e:
            messagebox.showerror("Erreur de lecture", f"Impossible de lire le fichier : {e}")
            return

        # Zone bouton visible en bas
        bouton_frame = tk.Frame(self.open_file_window, bg=self.theme_manager.bg_main, height=50)
        bouton_frame.grid(row=1, column=0, sticky="ew")
        bouton_frame.grid_propagate(False)  # Empêche le rétrécissement automatique

        # Frame pour les boutons (côte à côte)
        button_container = tk.Frame(bouton_frame, bg=self.theme_manager.bg_main)
        button_container.pack(expand=True, fill="both", pady=5)

        # Bouton Restaurer
        bouton_restauration = tk.Button(
            button_container,
            text="Restaurer",
            font=("Arial", 11, "bold"),
            fg=self.theme_manager.fg_main,
            bg=self.theme_manager.bg_secondary,
            command=lambda: self.executer_restauration(
                filename=filename,
                ip=self.ip_equipement,
                username=self.infos.get("credentials", {}).get("username", ""),
                password=self.infos.get("credentials", {}).get("password", ""),
                enable_password=self.infos.get("credentials", {}).get("enable_password", ""),
                type_equipement=self.type_equipement,
                system=self.infos.get("system", "inconnu"),  
            )
        )
        bouton_restauration.pack(side="left", expand=True, fill="both", padx=5)

        # Bouton Supprimer
        bouton_suppression = tk.Button(
            button_container,
            text="Supprimer",
            font=("Arial", 11, "bold"),
            bg="#AAAAAA", fg="black",  
            command=lambda: self.supprimer_fichier(filepath)
        )
        bouton_suppression.pack(side="left", expand=True, fill="both", padx=5)

        self.theme_manager.register_widget(bouton_restauration, 'bg_secondary', 'fg_main', 'bg_hover')

        def on_close():
            self.open_file_window.destroy()
            self.open_file_window = None

        self.open_file_window.protocol("WM_DELETE_WINDOW", on_close)

    def supprimer_fichier(self, filepath):
        """Supprime le fichier sélectionné"""
        confirmation = messagebox.askyesno(
            "Confirmation",
            f"Êtes-vous sûr de vouloir supprimer le fichier {os.path.basename(filepath)} ?",
            parent=self.open_file_window
        )
        
        if confirmation:
            try:
                os.remove(filepath)
                messagebox.showinfo(
                    "Succès",
                    "Le fichier a été supprimé avec succès.",
                    parent=self.open_file_window
                )
                self.charger_fichiers()  # Recharger la liste des fichiers
                self.open_file_window.destroy()
                self.open_file_window = None
            except Exception as e:
                messagebox.showerror(
                    "Erreur",
                    f"Une erreur est survenue lors de la suppression : {str(e)}",
                    parent=self.open_file_window
                )

    def executer_restauration(self, filename, ip, username, password, enable_password, type_equipement, system="ios"):
        """Exécute le script de restauration et enregistre les détails dans restauration.json"""
        try:
            from .composants.scr_restore import generate_restore_files
            import json
            from datetime import datetime
            import os

            # Mapping des types d'équipements vers les noms normalisés
            type_normalisation = {
                "cisco": "cisco",
                "mikrotik": "mikrotik",
                "huawei": "huawei",
                "juniper": "juniper",
                "fortinet": "fortinet",
                "asa": "cisco",  # Cisco ASA
                "ios": "cisco",  # Cisco IOS
                "routeros": "mikrotik",
                "fortigate": "fortinet"
            }

            # Normalisation du type d'équipement
            device_type = None
            for key, value in type_normalisation.items():
                if key in type_equipement.lower():
                    device_type = value
                    break
            
            if device_type is None:
                raise ValueError(f"Type d'équipement non reconnu: {type_equipement}")

            # Mapping des fichiers JSON par type d'équipement
            json_file_map = {
                "cisco": "cisco_save.json",
                "mikrotik": "mikrotik_save.json",
                "huawei": "huawei_save.json",
                "juniper": "juniper_save.json",
                "fortinet": "fortinet_save.json"
            }

            base_path = os.path.join(os.path.dirname(__file__), 'files')
            json_file = json_file_map.get(device_type)
            json_path = os.path.join(base_path, json_file) if json_file else None

            # Récupérer les informations de l'équipement
            device_info = {
                "mac": "inconnu",
                "name": "inconnu",
                "ip": ip,
                "type": type_equipement,
                "system": system
            }

            if json_path and os.path.exists(json_path):
                try:
                    with open(json_path, "r") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            device = next((item for item in data if item.get("ip") == ip), None)
                            if device:
                                device_info.update({
                                    "mac": device.get("mac", "inconnu"),
                                    "name": device.get("name", "inconnu"),
                                    "system": device.get("system", system)
                                })
                except Exception as e:
                    print(f"Erreur lecture fichier équipement: {str(e)}")

            # Exécuter la restauration
            generate_restore_files(
                config_file=filename,
                ip=ip,
                username=username,
                password=password,
                device_type=device_type,
                system=device_info["system"],  # Utilise le système de l'appareil si trouvé
                enable_password=enable_password
            )

            # Enregistrement dans restauration.json
            log_entry = {
                "equipement": {
                    "mac": device_info["mac"],
                    "name": device_info["name"],
                    "ip": device_info["ip"],
                    "type": device_info["type"],
                    "system": device_info["system"]
                },
                "fichiers_utilises": filename,
                "date_execution": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "username": self.current_user,
                "type_operation": "restauration",
                "status": "succès"
            }

            restauration_path = os.path.join(base_path, 'restauration.json')
            
            # Lire les entrées existantes ou créer un nouveau fichier
            existing_data = []
            if os.path.exists(restauration_path):
                try:
                    with open(restauration_path, 'r') as f:
                        existing_data = json.load(f)
                        if not isinstance(existing_data, list):
                            existing_data = []
                except (json.JSONDecodeError, Exception):
                    existing_data = []

            # Ajouter la nouvelle entrée
            existing_data.append(log_entry)

            # Écrire le fichier
            with open(restauration_path, 'w') as f:
                json.dump(existing_data, f, indent=4)

            messagebox.showinfo("Succès", 
                f"Restauration {device_type} ({device_info['system']}) effectuée avec succès\n"
                f"Équipement: {device_info['name']} ({ip})\n"
                f"Fichier: {filename}")
                
        except Exception as e:
            # Enregistrer l'échec dans le log
            error_log = {
                "equipement": {
                    "ip": ip,
                    "type": type_equipement,
                    "error": str(e)
                },
                "date_execution": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "username": self.current_user,
                "type_operation": "restauration",
                "status": "échec"
            }
            
            if 'restauration_path' in locals():
                try:
                    with open(restauration_path, 'r') as f:
                        existing_data = json.load(f)
                        if not isinstance(existing_data, list):
                            existing_data = []
                except (json.JSONDecodeError, Exception):
                    existing_data = []
                
                existing_data.append(error_log)
                
                with open(restauration_path, 'w') as f:
                    json.dump(existing_data, f, indent=4)

            messagebox.showerror("Erreur", f"Une erreur est survenue: {str(e)}")
    def charger_donnees_json(self, chemin):
        if not chemin or not os.path.exists(chemin):
            return []
        try:
            with open(chemin, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def trouver_infos_equipement(self):
        for equipement in self.credentials_data:
            if equipement.get("name") == self.nom_equipement and equipement.get("ip") == self.ip_equipement:
                return equipement
        return {}

    def mettre_a_jour_statut(self):
        try:
            result = subprocess.run(["ping", "-c", "1", "-W", "1", self.ip_equipement], stdout=subprocess.DEVNULL)
            color = "green" if result.returncode == 0 else "red"
        except Exception:
            color = "red"
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 14, 14, fill=color, outline=color)




class SaveRestauration(tk.Frame):
    def __init__(self, parent, theme_manager):
        super().__init__(parent, bg=theme_manager.bg_main)
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main')  # <-- nécessaire
        self.parent = parent
        self.base_path = os.path.join(os.path.dirname(__file__), 'files')
        self.details_window = None
        
        # Initialisation des variables
        self.device_count_var = tk.StringVar()
        self.device_count_var.set("Appareils détectés : 0")
        
        # Création des widgets
        self.create_widgets()
        self.load_data_with_loading()

    def set_current_user(self, username):
        """Définit l'utilisateur actuellement connecté"""
        self.current_user = username
   
    def create_widgets(self):
        """Crée les widgets principaux avec layout grid responsive"""

        # Configuration du layout principal
        self.grid_rowconfigure(0, weight=0)  # Titre + mode
        self.grid_rowconfigure(1, weight=1)  # Tableau extensible
        self.grid_rowconfigure(2, weight=0)  # Statut
        self.grid_columnconfigure(0, weight=1)

        # === Top : titre + mode
        top_frame = tk.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", pady=(10, 0))
        top_frame.grid_columnconfigure(0, weight=1)
        self.theme_manager.register_widget(top_frame, 'bg_main')

        center_frame = tk.Frame(top_frame)
        center_frame.grid(row=0, column=0)
        self.theme_manager.register_widget(center_frame, 'bg_main')

        title = tk.Label(
            center_frame,
            text="\U0001F4BB Système de Gestion des Configurations Réseaux Informatiques",
            font=("Helvetica", 16, "bold")
        )
        title.pack()
        self.theme_manager.register_widget(title, 'bg_main', 'fg_main')

        self.mode_label = tk.Label(
            center_frame,
            text="Tous les sauvegardes",
            font=("Helvetica", 14, "bold")
        )
        self.mode_label.pack(pady=5)
        self.theme_manager.register_widget(self.mode_label, 'bg_main', 'fg_main')

        # === Tableau
        self.table_frame = tk.Frame(self)
        self.table_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.theme_manager.register_widget(self.table_frame, 'bg_main')

        self.columns = ("Nom", "Adresse IP", "Types", "En sauvegarde")
        self.tree = ttk.Treeview(self.table_frame, columns=self.columns, show="headings")
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", stretch=True)

        self.scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Double-1>", self.on_select)
        self.tree.bind("<Configure>", self.adjust_column_widths)

        # === Statut
        self.status_frame = tk.Frame(self)
        self.status_frame.grid(row=2, column=0, sticky="ew", pady=10)
        self.theme_manager.register_widget(self.status_frame, 'bg_main')

        inner_status = tk.Frame(self.status_frame)
        inner_status.pack(anchor="center")
        self.theme_manager.register_widget(inner_status, 'bg_main')

        self.device_count_var = tk.StringVar(value="Appareils détectés : 0")

        count_label = tk.Label(
            inner_status,
            textvariable=self.device_count_var,
            font=("Helvetica", 14, "bold")
        )
        count_label.pack(side="left", padx=20)
        self.theme_manager.register_widget(count_label, 'bg_main', 'fg_main')

        status_label = tk.Label(
            inner_status,
            text="État du système : OK",
            font=("Helvetica", 14, "bold")
        )
        status_label.pack(side="left", padx=20)
        self.theme_manager.register_widget(status_label, 'bg_main', 'fg_success')

        # === Bouton export en haut à droite (hors layout principal)
        export_button = tk.Button(
            self,
            text="🖨️",
            background=self.theme_manager.bg_main,
            foreground=self.theme_manager.fg_main,
            activebackground=self.theme_manager.bg_hover,
            activeforeground=self.theme_manager.fg_main,
            relief="raised",
            cursor="hand2",
            command=self.export_to_json
        )
        export_button.place(relx=1.0, rely=0.0, anchor="ne", x=-20, y=10)
        self.theme_manager.register_widget(export_button, 'bg_main', 'fg_main', 'bg_hover')


    def adjust_column_widths(self, event):
        total_width = event.width
        col_count = len(self.columns)
        if col_count > 0:
            for col in self.columns:
                self.tree.column(col, width=total_width // col_count)



    def is_alive(self, ip):
        param = "-n" if platform.system().lower() == "windows" else "-c"
        try:
            result = subprocess.run(["ping", param, "1", ip],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        except Exception:
            return False

    def load_data_with_loading(self):
        def task(update_progress):
            update_progress(10, "Initialisation...")

            # Dictionnaire des fichiers de configuration
            fichiers = {
                "MikroTik": "mikrotik_save.json",
                "Cisco": "cisco_save.json", 
                "Huawei": "huawei_save.json",
                "Juniper": "juniper_save.json",
                "Fortinet": "fortinet_save.json"
            }

            # Dictionnaire pour stocker les MACs par ftp_server et type d'équipement
            inventory_data = {}

            # 1. Parcourir tous les dossiers de backup pour construire l'inventaire
            update_progress(20, "Analyse des sauvegardes...")
            for eq_type in fichiers.keys():
                parent_dir = os.path.join(self.base_path, f"backup_{eq_type.lower()}")
                
                if not os.path.exists(parent_dir):
                    continue
                    
                # Parcourir les sous-dossiers (backup_<type>_<ip_ftp>)
                for backup_dir in os.listdir(parent_dir):
                    full_path = os.path.join(parent_dir, backup_dir)
                    
                    if not os.path.isdir(full_path):
                        continue
                        
                    # Extraire l'IP FTP du nom du dossier
                    try:
                        ftp_ip = backup_dir.split('_')[-1].replace('_', '.')
                    except:
                        continue
                    
                    # Lire l'inventory.ini
                    inventory_path = os.path.join(full_path, "inventory.ini")
                    if os.path.exists(inventory_path):
                        with open(inventory_path, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#') and not line.startswith('['):
                                    parts = line.split()
                                    if len(parts) > 0:
                                        mac = parts[0].replace('-', ':').upper()
                                        ip = parts[1].split('=')[1] if 'ansible_host=' in line else "N/A"
                                        
                                        if ftp_ip not in inventory_data:
                                            inventory_data[ftp_ip] = {}
                                        if eq_type not in inventory_data[ftp_ip]:
                                            inventory_data[ftp_ip][eq_type] = set()
                                            
                                        inventory_data[ftp_ip][eq_type].add((mac, ip))

            # 2. Parcourir les équipements et vérifier leur statut
            rows = []
            update_progress(40, "Vérification des équipements...")
            
            for i, (eq_type, filename) in enumerate(fichiers.items()):
                file_path = os.path.join(self.base_path, filename)
                if not os.path.exists(file_path):
                    continue
                    
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        
                        for eq in data:
                            if not eq.get("status", False):
                                continue
                                
                            name = eq.get("name", "Inconnu")
                            ip = eq.get("ip", "N/A")
                            mac = eq.get("mac", "").replace('-', ':').upper()
                            ftp_server = eq.get("ftp_server", "")
                            
                            # Vérifier si l'équipement est dans le bon inventaire
                            is_in_inventory = False
                            if ftp_server in inventory_data:
                                if eq_type in inventory_data[ftp_server]:
                                    for (stored_mac, stored_ip) in inventory_data[ftp_server][eq_type]:
                                        if stored_mac == mac:
                                            is_in_inventory = True
                                            break
                            
                            # Vérifier si l'équipement est joignable
                            is_up = self.is_alive(ip)
                            
                            # Déterminer le statut
                            if not is_in_inventory:
                                sauvegarde_status = "❌"
                            elif not is_up:
                                sauvegarde_status = "❌"
                            else:
                                sauvegarde_status = "✔️"
                            
                            rows.append((name, ip, eq_type, sauvegarde_status))
                            
                except json.JSONDecodeError:
                    print(f"Erreur de lecture JSON dans : {filename}")
                
                update_progress(40 + (i+1)*12, f"Traitement {eq_type}...")

            return rows

        def callback(rows):
            self.tree.delete(*self.tree.get_children())
            for row in rows:
                self.tree.insert("", "end", values=row)
            self.device_count_var.set(f"Appareils détectés : {len(rows)}")

        run_with_loading(
            content_frame=self.parent,
            task_function=task,
            callback=callback,
            theme_manager=self.theme_manager
        )


    def on_select(self, event):
        selected_item = self.tree.selection()
        if selected_item:
            item_values = self.tree.item(selected_item)["values"]
            if self.details_window and self.details_window.winfo_exists():
                return
            
            self.details_window = DetailsSaveRestaurationFrame(
                self, 
                item_values, 
                self.theme_manager,
                current_user=self.current_user  # Passage de l'utilisateur connecté
            )
            self.details_window.protocol("WM_DELETE_WINDOW", self.on_details_window_close)

    def on_details_window_close(self):
        if self.details_window:
            self.details_window.destroy()
            self.details_window = None

    def export_to_json(self):
        confirm = messagebox.askyesno("Export JSON", "Voulez-vous exporter les données affichées en JSON ?")
        if not confirm:
            return

        data = []
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id)["values"]
            status = "connecté" if values[3] == "En sauvegarde" else "Pas en sauvegarde"
            data.append({
                "nom": values[0],
                "ip": values[1],
                "type": values[2],
                "status": status
            })

        export_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Fichier JSON", "*.json")],
            title="Enregistrer sous",
            initialfile="export_sauvegardes.json"
        )

        if not export_path:
            return

        try:
            with open(export_path, "w") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Export réussi", f"Export effectué avec succès dans :\n{export_path}")
        except Exception as e:
            messagebox.showerror("Erreur export", f"Une erreur est survenue lors de l'export :\n{e}")




