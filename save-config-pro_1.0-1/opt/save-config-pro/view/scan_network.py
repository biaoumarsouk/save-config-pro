import tkinter as tk
import subprocess
from concurrent.futures import ThreadPoolExecutor
import json
import os
import configparser 
from tkinter import ttk, messagebox, filedialog
from .composants.loading import run_with_loading
from .composants.menu_filtre import ToggleMenu
from itertools import chain
import time
import re

files_dir = os.path.join(os.path.dirname(__file__), 'files')
if not os.path.exists(files_dir):
    os.makedirs(files_dir)
class FunctionsScanner:
    def __init__(self, sudo_password=""):
        self.sudo_password = sudo_password
        self.equipment_list = []  # Liste globale pour tous les appareils de tous les réseaux

    def scan_network(self, network):
        """Scan un réseau spécifique et retourne les appareils trouvés"""
        try:
            command = ['sudo', '-S', 'nmap', '-sn', '-PR', '-T4', network]
            result = subprocess.check_output(
                command,
                input=self.sudo_password + "\n",
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            devices = []
            lines = result.splitlines()
            ip = None
            for line in lines:
                if 'Nmap scan report for' in line:
                    ip = line.split()[-1].strip("()")
                if 'MAC Address' in line:
                    parts = line.split()
                    mac = parts[2] if len(parts) > 2 else 'inconnu'
                    devices.append({
                        'name': '',
                        'ip': ip,
                        'mac': mac,
                        'network': network,  # Stocke le réseau d'origine
                        'credentials': {
                            'username': '',
                            'password': '',
                            'enable':''
                        },
                        'status':'',
                    })

            # Ajoute à la liste globale
            self.equipment_list.extend(devices)
            return devices
            
        except Exception as e:
            print(f"Erreur scan réseau {network}: {e}")
            return []

    def scan_multiple_networks(self, networks):
        """Scan plusieurs réseaux et retourne tous les appareils"""
        self.equipment_list = []  # Réinitialise la liste
        
        for network in networks:
            self.scan_network(network)
            
        return self.equipment_list

    def _scan_device(self, device, keywords):
        """Analyse un appareil spécifique pour détecter son type"""
        try:
            ip = device['ip']
            command = (
                f"echo {self.sudo_password} | sudo -S nmap -sV -T4 --version-light -p 23,80,443,22,161 {ip}"
            )
            result = subprocess.check_output(
                command,
                shell=True,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            if any(keyword in result for keyword in keywords):
                return device
        except Exception:
            pass
        return None

    def _filter_devices(self, keywords):
        """Filtre les appareils par mots-clés"""
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(lambda d: self._scan_device(d, keywords), self.equipment_list)
        return [device for device in results if device]

    def filter_cisco_ios_devices(self):
        return self._filter_devices(['Cisco', 'IOS'])

    def filter_mikrotik_devices(self):
        return self._filter_devices(['MikroTik'])

    def filter_huawei_devices(self):
        return self._filter_devices(['Huawei'])

    def filter_juniper_devices(self):
        return self._filter_devices(['Juniper'])
    
    def filter_fortinet_devices(self):
        return self._filter_devices(['fortigate', 'fortinet', 'forti'])

    def filter_all_devices_grouped(self):
        """Combine tous les appareils filtrés en évitant les doublons"""
        cisco = self.filter_cisco_ios_devices()
        mikrotik = self.filter_mikrotik_devices()
        huawei = self.filter_huawei_devices()
        juniper = self.filter_juniper_devices()
        fortinet = self.filter_fortinet_devices()

        merged = {d['ip']: d for d in chain(cisco, mikrotik, huawei, juniper, fortinet)}
        return list(merged.values())




class NetworkScanner(tk.Frame):
    def __init__(self, parent, networks, theme_manager):
        super().__init__(parent, bg=theme_manager.bg_main)
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main')  # <-- nécessaire
        self.parent = parent
        self.networks = networks if isinstance(networks, list) else [networks]
        self.displayed_devices = []
        self.current_mode = "tout"
        self.scanner = FunctionsScanner()
        
        # Création des widgets
        self.create_widgets()
        
        self.toggle_menu = ToggleMenu(
            root=self.parent,
            show_cisco=self.show_cisco,
            show_mikrotik=self.show_mikrotik,
            show_huawei=self.show_huawei,
            show_juniper=self.show_juniper,
            show_fortinet=self.show_fortinet,
            export_data=self.export_data,
            theme_manager=self.theme_manager
        )
    def create_widgets(self):
        """Widgets principaux avec grid pour un layout responsive verticalement"""

        # Configurer les lignes/colonnes du frame principal
        self.grid_rowconfigure(0, weight=0)  # Top (titre + mode) fixe
        self.grid_rowconfigure(1, weight=1)  # Milieu (Treeview) extensible
        self.grid_rowconfigure(2, weight=0)  # Bas (status) fixe
        self.grid_columnconfigure(0, weight=1)

        # === Top (titre + mode)
        top_frame = tk.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", pady=10)
        self.theme_manager.register_widget(top_frame, 'bg_main')

        title = tk.Label(
            top_frame,
            text="\U0001F4BB Système de Gestion des Configurations Réseaux Informatiques",
            font=("Arial", 16, "bold")
        )
        title.pack()
        self.theme_manager.register_widget(title, 'bg_main', 'fg_main')

        self.mode_label = tk.Label(
            top_frame,
            text="Tous les équipements",
            font=("Arial", 14, "bold")
        )
        self.mode_label.pack()
        self.theme_manager.register_widget(self.mode_label, 'bg_main', 'fg_main')

        # === Middle (Treeview) : extensible verticalement
        self.table_frame = tk.Frame(self)
        self.table_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.theme_manager.register_widget(self.table_frame, 'bg_main')

        self.columns = ("MAC", "Adresse IP", "État", "Enregistrer")
        self.tree = ttk.Treeview(self.table_frame, columns=self.columns, show="headings")
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", stretch=True)

        self.scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<Configure>", self.adjust_column_widths)
        self.tree.bind("<Double-1>", self.on_select)

        # === Bottom (status) — contenu centré horizontalement
        self.status_frame = tk.Frame(self)
        self.status_frame.grid(row=2, column=0, sticky="ew", pady=10)
        self.theme_manager.register_widget(self.status_frame, 'bg_main')

        inner_status = tk.Frame(self.status_frame)
        inner_status.pack(anchor="center")  # Centre horizontalement
        self.theme_manager.register_widget(inner_status, 'bg_main')

        self.device_count_var = tk.StringVar(value="Appareils détectés : 0")

        count_label = tk.Label(
            inner_status,
            textvariable=self.device_count_var,
            font=("Arial", 14, "bold")
        )
        count_label.pack(side="left", padx=20)
        self.theme_manager.register_widget(count_label, 'bg_main', 'fg_main')

        status_label = tk.Label(
            inner_status,
            text="État du système : OK",
            font=("Arial", 14, "bold")
        )
        status_label.pack(side="left", padx=20)
        self.theme_manager.register_widget(status_label, 'bg_main', 'fg_success')



    def adjust_column_widths(self, event):
        total_width = event.width
        col_count = len(self.columns)
        if col_count > 0:
            for col in self.columns:
                self.tree.column(col, width=total_width // col_count)

    def load_existing_data(self, source):
        filename = {
            "mikrotik": "mikrotik_save.json",
            "cisco": "cisco_save.json",
            "huawei": "huawei_save.json",
            "juniper": "juniper_save.json",
            "fortinet": "fortinet_save.json"
        }.get(source, "equipe_save.json")

        path = os.path.join(os.path.dirname(__file__),'files', filename)
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return []

    def update_table(self, new_list):
        self.displayed_devices = new_list[:]
        self.tree.delete(*self.tree.get_children())
        saved_list = self.load_existing_data(self.current_mode)

        for dev in self.displayed_devices:
            mac = dev.get('mac')
            ip = dev.get('ip')

            # Recherche dans la liste sauvegardée
            match = next((eq for eq in saved_list if eq['mac'] == mac), None)
            if match:
                if match.get('ip') == ip:
                    status = "✔️"   # Même MAC, même IP
                else:
                    status = "⚠️"   # Même MAC, IP différente
            else:
                status = "❌"       # MAC inconnu

            self.tree.insert("", "end", values=(mac, ip, "Connecté", status))

        self.device_count_var.set(f"Appareils détectés : {len(self.displayed_devices)}")


    def ask_credentials(self, equipment):
    

        filename = {
            "mikrotik": "mikrotik_save.json",
            "cisco": "cisco_save.json", 
            "huawei": "huawei_save.json",
            "juniper": "juniper_save.json",
            "fortinet": "fortinet_save.json"
        }.get(self.current_mode, "equipe_save.json")

        file_path = os.path.join(os.path.dirname(__file__), 'files', filename)
        cred_window = tk.Toplevel(self.parent, bg=self.theme_manager.bg_main)
        cred_window.title(f"Informations pour {equipment['ip']}")
        cred_window.geometry("300x400")
        cred_window.resizable(False, False)

        cred_window.transient(self.parent)
        cred_window.wait_visibility()
        cred_window.grab_set()

        label_style = {
            'bg': self.theme_manager.bg_main,
            'fg': self.theme_manager.fg_main
        }
        entry_style = {
            'bg': self.theme_manager.bg_secondary,
            'fg': self.theme_manager.fg_main,
            'insertbackground': self.theme_manager.fg_main
        }

        labels = [
            "Nom de l'équipement",
            "Nom d'utilisateur",
            "Mot de passe",
            "Mot de passe enable (optionnel)"
        ]
        entries = []

        for label in labels:
            tk.Label(cred_window, text=label, **label_style).pack(pady=2)
            entry = tk.Entry(cred_window, show="*" if "mot de passe" in label.lower() else None, **entry_style)
            entry.pack()
            entries.append(entry)

        current_list = self.load_existing_data(self.current_mode)
        existing_eq = next((eq for eq in current_list if eq['mac'] == equipment['mac']), None)

        tk.Label(cred_window, text="Système", **label_style).pack(pady=2)

        if self.current_mode == "cisco":
            system_options = ["IOS", "ASA"]
        else:
            system_options = sorted(set(eq.get("systeme", "default") for eq in current_list)) or ["default"]

        system_var = tk.StringVar()
        system_combobox = ttk.Combobox(cred_window, textvariable=system_var, values=system_options, state="readonly")
        system_combobox.pack()
        system_combobox.update_idletasks()
        system_combobox.event_generate('<Button-1>')
        cred_window.after(100, lambda: system_combobox.event_generate('<Escape>'))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=self.theme_manager.bg_main,
                        background=self.theme_manager.bg_main,
                        foreground=self.theme_manager.fg_main,
                        arrowcolor=self.theme_manager.fg_main,
                        bordercolor=self.theme_manager.bg_main,
                        lightcolor=self.theme_manager.bg_main,
                        darkcolor=self.theme_manager.bg_main,
                        relief="flat")

        if existing_eq:
            system_combobox.set(existing_eq.get("type", system_options[0]))
            entries[0].insert(0, existing_eq.get('name') or '')
            entries[1].insert(0, existing_eq.get('credentials', {}).get('username') or '')
            entries[2].insert(0, existing_eq.get('credentials', {}).get('password') or '')
            entries[3].insert(0, existing_eq.get('credentials', {}).get('enable_password') or '')
        else:
            system_combobox.set(system_options[0])

        def save_or_update():
            name, username, password, enable_password = [e.get() for e in entries]
            selected_type = system_var.get()

            if not name or not username or not password:
                messagebox.showerror("Erreur", "Tous les champs obligatoires doivent être remplis.")
                return

            ip = equipment.get('ip')
            mac = equipment.get('mac').replace(':', '-').upper()

            try:
                base_dir = os.path.join(os.path.dirname(__file__), 'files', f"backup_{self.current_mode.lower()}")
                if os.path.exists(base_dir):
                    for folder in os.listdir(base_dir):
                        full_path = os.path.join(base_dir, folder)
                        if os.path.isdir(full_path):
                            inventory_path = os.path.join(full_path, "inventory.ini")
                            if os.path.exists(inventory_path):
                                # Supprimer la ligne contenant la MAC
                                with open(inventory_path, 'r') as f:
                                    lines = f.readlines()

                                with open(inventory_path, 'w') as f:
                                    for line in lines:
                                        if not line.strip().startswith(mac):
                                            f.write(line)

                                # Supprimer les sections vides si besoin
                                with open(inventory_path, 'r') as f:
                                    content = f.read()

                                cleaned = re.sub(r'\[\w+\]\n(?=\[|\Z)', '', content, flags=re.MULTILINE)
                                with open(inventory_path, 'w') as f:
                                    f.write(cleaned)

                # Ajouter à l'inventory.ini de la machine actuelle
                current_backup_dir = os.path.join(base_dir, ip.replace('.', '_'))
                os.makedirs(current_backup_dir, exist_ok=True)
                current_inventory = os.path.join(current_backup_dir, "inventory.ini")

                line = (
                    f"{mac} ansible_host={ip} ansible_user={username} ansible_ssh_pass={password} "
                    f"ansible_network_os=cisco.ios.ios ansible_connection=network_cli "
                    f"ansible_become=yes ansible_become_method=enable ansible_become_password={enable_password}\n"
                )

                section_header = f"[{selected_type}]"

                # Ajouter proprement à la section
                if os.path.exists(current_inventory):
                    with open(current_inventory, 'r') as f:
                        content = f.read()
                else:
                    content = ""

                if section_header not in content:
                    content += f"\n{section_header}\n"

                # Éviter duplication
                content_lines = content.splitlines()
                content_lines = [l for l in content_lines if not l.strip().startswith(mac)]
                idx = content_lines.index(section_header) + 1 if section_header in content_lines else len(content_lines)
                content_lines.insert(idx, line.strip())

                with open(current_inventory, 'w') as f:
                    f.write('\n'.join(content_lines) + '\n')

            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la mise à jour de l'inventaire :\n{str(e)}")
                return

            # Mise à jour JSON
            equipment['name'] = name
            equipment['system'] = selected_type
            equipment['credentials'] = {
                'username': username,
                'password': password,
                'enable_password': enable_password if enable_password else None
            }
            equipment['status'] = False
            equipment['sauvegarde'] = False
            equipment['subnet'] = None
            equipment['ftp_server'] = None

            existing_eq = next((eq for eq in current_list if eq['mac'] == equipment['mac']), None)
            if existing_eq:
                for i, eq in enumerate(current_list):
                    if eq['mac'] == equipment['mac']:
                        current_list[i] = equipment
                        break
                action = "mis à jour"
            else:
                current_list.append(equipment)
                action = "enregistré"

            with open(file_path, 'w') as f:
                json.dump(current_list, f, indent=4)

            messagebox.showinfo("Succès", f"Équipement {action} dans :\n{filename}")
            cred_window.destroy()
            self.update_table(self.displayed_devices)


        def delete_equipment():
            if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer cet équipement ?"):
                return

            mac = equipment['mac'].replace(':', '-').upper()
            try:
                base_dir = os.path.join(os.path.dirname(__file__), 'files', f"backup_{self.current_mode.lower()}")
                if os.path.exists(base_dir):
                    for folder in os.listdir(base_dir):
                        full_path = os.path.join(base_dir, folder)
                        if os.path.isdir(full_path):
                            inventory_path = os.path.join(full_path, "inventory.ini")
                            if os.path.exists(inventory_path):
                                with open(inventory_path, 'r') as f:
                                    lines = f.readlines()

                                with open(inventory_path, 'w') as f:
                                    for line in lines:
                                        if not line.strip().startswith(mac):
                                            f.write(line)

                                # Nettoyage des sections vides
                                with open(inventory_path, 'r') as f:
                                    content = f.read()
                                cleaned = re.sub(r'\[\w+\]\n(?=\[|\Z)', '', content, flags=re.MULTILINE)
                                with open(inventory_path, 'w') as f:
                                    f.write(cleaned)

            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression dans inventory.ini:\n{str(e)}")
                return

            current_list = self.load_existing_data(self.current_mode)
            updated_list = [eq for eq in current_list if eq['mac'] != equipment['mac']]
            with open(file_path, 'w') as f:
                json.dump(updated_list, f, indent=4)

            cred_window.destroy()
            messagebox.showinfo("Supprimé", f"Équipement supprimé de :\n{filename}")
            self.update_table(self.displayed_devices)

        button_frame = tk.Frame(cred_window, bg=self.theme_manager.bg_main)
        button_frame.pack(pady=40)

        button_style = {
            'font': ("Arial", 10, "bold"),
            'width': 20,
            'activebackground': self.theme_manager.bg_hover,
            'activeforeground': self.theme_manager.fg_main
        }

        btn_label = "Mettre à jour" if existing_eq else "Enregistrer"
        tk.Button(
            button_frame, text=btn_label,
            command=save_or_update,
            bg="#0000FF",
            fg="white",
            **button_style
        ).grid(row=0, column=0, pady=2)

        if existing_eq:
            tk.Button(
                button_frame, text="Supprimer",
                command=delete_equipment,
                bg="#AAAAAA", fg="black",
                **button_style
            ).grid(row=1, column=0, pady=2)



    def show_all(self):
        """Affiche tous les appareils détectés"""
        self.current_mode = "tout"
        self.mode_label.config(text="Tous les équipements")
        self.update_table(self.scanner.equipment_list)

    def export_data(self):
        """Exporte les données au format JSON"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json")],
            title="Exporter les données"
        )
        if file_path:
            data = self.load_existing_data(self.current_mode)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            messagebox.showinfo("Succès", f"Données exportées vers:\n{file_path}")


    def show_cisco(self):
        self.current_mode = "cisco"
        self.current_mode_label = "Équipements Cisco"
        self.mode_label.config(text=self.current_mode_label)

        def task(update_progress):
            update_progress(20, "Filtrage...")
            return self.scanner.filter_cisco_ios_devices()

        def after_task(filtered):
            self.update_filtered_data(filtered, "🚫 Aucun équipement Cisco détecté")

        run_with_loading(
            content_frame=self.parent,
            task_function=task,
            callback=after_task,
            theme_manager=self.theme_manager
        )

    def show_mikrotik(self):
        self.current_mode = "mikrotik"
        self.current_mode_label = "Équipements MikroTik"
        self.mode_label.config(text=self.current_mode_label)

        def task(update_progress):
            update_progress(20, "Filtrage...")
            return self.scanner.filter_mikrotik_devices()

        def after_task(filtered):
            self.update_filtered_data(filtered, "🚫 Aucun équipement MikroTik détecté")

        run_with_loading(
            content_frame=self.parent,
            task_function=task,
            callback=after_task,
            theme_manager=self.theme_manager
        )

    def show_huawei(self):
        self.current_mode = "huawei"
        self.current_mode_label = "Équipements Huawei"
        self.mode_label.config(text=self.current_mode_label)

        def task(update_progress):
            update_progress(20, "Filtrage...")
            return self.scanner.filter_huawei_devices()

        def after_task(filtered):
            self.update_filtered_data(filtered, "🚫 Aucun équipement Huawei détecté")

        run_with_loading(
            content_frame=self.parent,
            task_function=task,
            callback=after_task,
            theme_manager=self.theme_manager
        )

    def show_juniper(self):
        self.current_mode = "juniper"
        self.current_mode_label = "Équipements Juniper"
        self.mode_label.config(text=self.current_mode_label)

        def task(update_progress):
            update_progress(20, "Filtrage...")
            return self.scanner.filter_juniper_devices()

        def after_task(filtered):
            self.update_filtered_data(filtered, "🚫 Aucun équipement Juniper détecté")

        run_with_loading(
            content_frame=self.parent,
            task_function=task,
            callback=after_task,
            theme_manager=self.theme_manager
        )

    def show_fortinet(self):
        self.current_mode = "fortinet"
        self.current_mode_label = "Équipements Fortinet"
        self.mode_label.config(text=self.current_mode_label)

        def task(update_progress):
            update_progress(20, "Filtrage...")
            return self.scanner.filter_fortinet_devices()

        def after_task(filtered):
            self.update_filtered_data(filtered, "🚫 Aucun équipement Fortinet détecté")

        run_with_loading(
            content_frame=self.parent,
            task_function=task,
            callback=after_task,
            theme_manager=self.theme_manager
        )

    def scan_network(self):
        """Lance le scan de tous les réseaux"""
        def task(update_progress):
            update_progress(10, "Démarrage du scan...")
            
            # Scan séquentiel de chaque réseau avec progression
            total_networks = len(self.networks)
            scanned_devices = []
            
            for i, network in enumerate(self.networks):
                update_progress(10 + (i * 80 // total_networks), 
                              f"Scan du réseau...")
                devices = self.scanner.scan_network(network)
                scanned_devices.extend(devices)
                time.sleep(0.5)  # Pause entre les scans
                
            update_progress(90, "Analyse des résultats...")
            return scanned_devices

        def after_task(equipment_list):
            self.displayed_devices = equipment_list
            self.update_table(equipment_list)
            self.mode_label.config(text="Résultats du scan")

        run_with_loading(
            content_frame=self.parent,
            task_function=task,
            callback=after_task,
            theme_manager=self.theme_manager
        )

    def export_data(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json")],
            title="Exporter les données"
        )
        if file_path:
            data = self.load_existing_data(self.current_mode)
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            messagebox.showinfo("Succès", f"Données exportées avec succès vers:\n{file_path}")

    def update_filtered_data(self, filtered, error_message):
        self.tree.delete(*self.tree.get_children())
        if hasattr(self.tree, "no_data_label"):
            self.tree.no_data_label.destroy()
            del self.tree.no_data_label

        if not filtered:
            lbl = tk.Label(
                self.tree,
                text=error_message,
                font=("Arial", 16, "bold"),
                fg="red", 
                bg=self.theme_manager.bg_secondary
            )
            lbl.place(relx=0.5, rely=0.5, anchor="center")
            self.tree.no_data_label = lbl
            self.device_count_var.set("Appareils détectés : 0")
        else:
            self.update_table(filtered)


    def on_select(self, event):
        """Gère le double-clic sur un élément du Treeview avec gestion des erreurs"""
        try:
            selection = self.tree.selection()
            if not selection:  # Si rien n'est sélectionné
                return
                
            item = selection[0]
            values = self.tree.item(item, 'values')
            
            if not values or len(values) < 3:  # Vérifie qu'on a assez de valeurs
                messagebox.showwarning("Avertissement", "Données d'équipement incomplètes")
                return
                
            equipment = {
                'mac': values[0],
                'ip': values[1],
                'status': values[2]
            }
            
            self.ask_credentials(equipment)
        except Exception as e:
            messagebox.showerror("Erreur", f"Une erreur est survenue : {str(e)}")