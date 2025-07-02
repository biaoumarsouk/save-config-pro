import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import json
import subprocess
import socket
import paramiko
import ipaddress
import psutil
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

class Dashboard(tk.Frame):
    def __init__(self, parent, controller, theme_manager):
        super().__init__(parent)
        self.controller = controller
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main')

        # Charger les réseaux enregistrés
        self.saved_networks = self.load_saved_networks()

        # Configuration du grid principal
        self.grid_rowconfigure(0, weight=1)  # Contenu principal
        self.grid_rowconfigure(1, weight=0)  # Statistiques (hauteur fixe)
        self.grid_columnconfigure(0, weight=1)

        # Conteneur principal
        self.main_container = tk.Frame(self)
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.theme_manager.register_widget(self.main_container, 'bg_main')

        # Configuration des colonnes (graphique à gauche, contenu à droite)
        self.main_container.grid_columnconfigure(0, weight=1)  # Graphique
        self.main_container.grid_columnconfigure(1, weight=2)  # Contenu
        self.main_container.grid_rowconfigure(0, weight=1)

        # Zone du graphique (colonne de gauche)
        self.chart_frame = tk.Frame(self.main_container)
        self.chart_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.theme_manager.register_widget(self.chart_frame, 'bg_main')
        
        # Configuration du grid pour chart_frame
        self.chart_frame.grid_rowconfigure(0, weight=1)  # Graphique
        self.chart_frame.grid_rowconfigure(1, weight=0)  # Horloge (hauteur fixe)
        self.chart_frame.grid_columnconfigure(0, weight=1)

        # Frame pour le canvas Matplotlib
        self.chart_canvas_frame = tk.Frame(self.chart_frame)
        self.chart_canvas_frame.grid(row=0, column=0, sticky="nsew")
        self.theme_manager.register_widget(self.chart_canvas_frame, 'bg_main')

        # Horloge centrée sous le graphique
        self.clock_frame = tk.Frame(self.chart_frame)
        self.clock_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.theme_manager.register_widget(self.clock_frame, 'bg_main')

        # Conteneur interne pour centrer les labels
        self.clock_inner_frame = tk.Frame(self.clock_frame)
        self.clock_inner_frame.pack(expand=True, anchor="center")
        self.theme_manager.register_widget(self.clock_inner_frame, 'bg_main')

        self.clock_label = tk.Label(self.clock_inner_frame, 
                                  text="Prochaine sauvegarde:",
                                  font=("Arial", 10, "bold"))
        self.clock_label.pack()
        self.theme_manager.register_widget(self.clock_label, 'bg_main', 'fg_main')

        self.clock_value = tk.Label(self.clock_inner_frame, 
                                  text="", 
                                  font=("Arial", 14))
        self.clock_value.pack()
        self.theme_manager.register_widget(self.clock_value, 'bg_main', 'fg_main')

        # Créer le graphique
        self.after(100, self.create_charts)
        self.update_clock()


        # Conteneur droit (tableaux et services)
        self.right_container = tk.Frame(self.main_container)
        self.right_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.theme_manager.register_widget(self.right_container, 'bg_main')

        # Configuration du grid pour right_container
        self.right_container.grid_rowconfigure(0, weight=3)  # Tableau équipements
        self.right_container.grid_rowconfigure(1, weight=0)  # Services
        self.right_container.grid_rowconfigure(2, weight=2)  # Tableau FTP
        self.right_container.grid_columnconfigure(0, weight=1)

        # Tableau principal des équipements
        self.table_frame = tk.Frame(self.right_container)
        self.table_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.theme_manager.register_widget(self.table_frame, 'bg_main')

        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        # Treeview avec scrollbar
        self.columns = ("Equipements", "Mac", "Type", "Etat")
        self.tree = ttk.Treeview(self.table_frame, columns=self.columns, show="headings", height=7)
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=230)

        self.scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Double-1>", self.on_select)
        self.remplir_treeview()

        # Frame des services (FTP, Ansible, Stockage)
        self.services_frame = tk.Frame(self.right_container)
        self.services_frame.grid(row=1, column=0, sticky="ew", pady=10)
        self.theme_manager.register_widget(self.services_frame, 'bg_main')

        # Configuration 3 colonnes égales
        for i in range(3):
            self.services_frame.grid_columnconfigure(i, weight=1)

        # Serveur FTP
        self.ftp_frame = tk.LabelFrame(self.services_frame, text="État du serveur FTP",
                                     font=("Arial", 10, "bold"),
                                     bd=2, relief="groove")
        self.ftp_frame.grid(row=0, column=0, sticky="nsew", padx=5)
        self.theme_manager.register_widget(self.ftp_frame, 'bg_main', 'fg_main')

        self.ftp_status = tk.Label(self.ftp_frame, text="❌", font=("Arial", 24))
        self.ftp_status.pack(pady=10)
        self.theme_manager.register_widget(self.ftp_status, 'bg_main', 'fg_main')

        self.ftp_label = tk.Label(self.ftp_frame, text="Serveur FTP non actif")
        self.ftp_label.pack()
        self.theme_manager.register_widget(self.ftp_label, 'bg_main', 'fg_main')

        # Ansible
        self.ansible_frame = tk.LabelFrame(self.services_frame, text="État d'Ansible",
                                        font=("Arial", 10, "bold"),
                                        bd=2, relief="groove")
        self.ansible_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        self.theme_manager.register_widget(self.ansible_frame, 'bg_main', 'fg_main')

        self.ansible_status = tk.Label(self.ansible_frame, text="❌", font=("Arial", 24))
        self.ansible_status.pack(pady=10)
        self.theme_manager.register_widget(self.ansible_status, 'bg_main', 'fg_main')

        self.ansible_label = tk.Label(self.ansible_frame, text="Ansible non configuré")
        self.ansible_label.pack()
        self.theme_manager.register_widget(self.ansible_label, 'bg_main', 'fg_main')

        # Stockage total
        self.stock_frame = tk.LabelFrame(self.services_frame, text="Stockage total",
                                       font=("Arial", 10, "bold"),
                                       bd=2, relief="groove")
        self.stock_frame.grid(row=0, column=2, sticky="nsew", padx=5)
        self.theme_manager.register_widget(self.stock_frame, 'bg_main', 'fg_main')

        self.stock_valeur = tk.Label(self.stock_frame, text="", font=("Arial", 24))
        self.stock_valeur.pack(pady=10)
        self.theme_manager.register_widget(self.stock_valeur, 'bg_main', 'fg_main')

        # Tableau FTP
        self.ftp_table_frame = tk.Frame(self.right_container)
        self.ftp_table_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        self.theme_manager.register_widget(self.ftp_table_frame, 'bg_main')

        self.ftp_table_frame.grid_rowconfigure(0, weight=1)
        self.ftp_table_frame.grid_columnconfigure(0, weight=1)

        self.ftp_tree = ttk.Treeview(
            self.ftp_table_frame,
            columns=("Nom", "Taille", "Heure"),
            show="headings",
            height=5
        )
        
        scrollbar = ttk.Scrollbar(self.ftp_table_frame, orient="vertical", command=self.ftp_tree.yview)
        self.ftp_tree.configure(yscrollcommand=scrollbar.set)

        for col in ("Nom", "Taille", "Heure"):
            self.ftp_tree.heading(col, text=col)
            self.ftp_tree.column(col, anchor="center")

        self.ftp_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.remplir_fichiers_ftp()
        self.check_services_status()

        # Statistiques en bas
        self.bottom_stats_frame = tk.Frame(self)
        self.bottom_stats_frame.grid(row=1, column=0, sticky="ew", pady=10)
        self.theme_manager.register_widget(self.bottom_stats_frame, 'bg_main')

        # Configuration 3 colonnes égales
        for i in range(3):
            self.bottom_stats_frame.grid_columnconfigure(i, weight=1)

        # Sections des statistiques
        self.sections = [
            {"title": "Réseau disponible", "count_func": self.count_reseau_disponible, "callback": self.controller.scann},
            {"title": "Réseau enregistrés", "count_func": self.count_reseau_enregistres, "callback": self.controller.show_sous_reseaux_enregistres},
            {"title": "Fichiers sauvegardés", "count_func": self.count_fichiers_sauvegardes, "callback": self.controller.show_saverestauration},
            {"title": "Appareils enrégistrés", "count_func": self.count_appareils_enr, "callback": self.controller.show_schedule},
            {"title": "Appareil en sauvegarde", "count_func": self.count_appareil_en_sauv, "callback": self.controller.show_saverestauration},
            {"title": "Pannes enregistrées", "count_func": self.count_pannes, "callback": self.controller.show_saverestauration},
        ]
        
        self.section_widgets = []  # Liste pour stocker les références des widgets
        
        # Création des statistiques
        self.create_stats_sections()
        self.start_10s_timer()  # Démarrer le timer séparé

    def create_stats_sections(self):
        """Crée les sections de statistiques"""
        for i, section in enumerate(self.sections):
            row, col = divmod(i, 3)
            
            # Création du frame
            frame = tk.LabelFrame(
                self.bottom_stats_frame,
                text=section["title"],
                font=("Arial", 12, "bold"),
                bd=2,
                relief="groove",
                labelanchor="n"
            )
            frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.theme_manager.register_widget(frame, 'bg_main', 'fg_main')

            # Label pour le compteur
            lbl = tk.Label(
                frame,
                text=str(section["count_func"]()),
                font=("Arial", 30, "bold"),
                fg=self.theme_manager.fg_main
            )
            lbl.pack(expand=True)
            self.theme_manager.register_widget(lbl, 'bg_main', 'fg_main')

            # Gestion des événements
            frame.bind("<Button-1>", lambda e, cb=section["callback"]: cb())
            lbl.bind("<Button-1>", lambda e, cb=section["callback"]: cb())
            
            # Stockage des références
            self.section_widgets.append({
                "frame": frame,
                "label": lbl,
                "title": section["title"],
                "callback": section["callback"]
            })


    def start_10s_timer(self):
        self.remplir_fichiers_ftp()
        self.update_section(2)
        self.remplir_treeview()
        self.after(10000, self.start_10s_timer) 

    def update_section(self, section_index):
        """Met à jour une section spécifique"""
        if 0 <= section_index < len(self.section_widgets):
            section = self.section_widgets[section_index]
            try:
                new_count = self.sections[section_index]["count_func"]()
                section["label"].config(text=str(new_count))
                section["frame"].config(text=f"{section['title']}")
            except Exception as e:
                print(f"Erreur mise à jour section {section_index}: {e}")

    def refresh_all_stats(self):
        """Rafraîchit toutes les sections"""
        for i in range(len(self.section_widgets)):
            self.update_section(i)

    def create_charts(self):
        """Crée le graphique avec une taille agrandie"""
        try:
            counts = {k: v for k, v in self.count_equipments_by_type().items() if v > 0}
            
            fig, ax = plt.subplots(figsize=(7, 5), dpi=100)
            fig.patch.set_facecolor(self.theme_manager.bg_main)
            ax.set_facecolor(self.theme_manager.bg_main)

            if not counts:
                ax.text(0.5, 0.5, "Aucun équipement enregistré", 
                       ha='center', va='center', 
                       color=self.theme_manager.fg_main,
                       fontsize=12)
                ax.axis('off')
            else:
                ax.pie(
                    counts.values(), 
                    labels=counts.keys(), 
                    autopct='%1.1f%%', 
                    startangle=90,
                    textprops={'color': self.theme_manager.fg_main, 'fontsize': 10},
                    wedgeprops={'linewidth': 1, 'edgecolor': self.theme_manager.bg_main}
                )
                ax.set_title("Répartition des équipements enrégistrées", 
                           color=self.theme_manager.fg_main,
                           fontsize=12)

            plt.tight_layout()

            if hasattr(self, 'canvas'):
                self.canvas.get_tk_widget().destroy()

            self.canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        except Exception as e:
            print(f"Erreur création graphique: {e}")

    def update_chart_colors(self):
        """Met à jour les couleurs du diagramme en fonction du thème actuel"""
        if hasattr(self, "canvas"):
            self.canvas.get_tk_widget().destroy()

        # Recalcul des données
        counts = self.count_equipments_by_type()
        labels = list(counts.keys())
        values = list(counts.values())

        # Nouvelle figure avec couleurs mises à jour
        fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
        fig.patch.set_facecolor(self.theme_manager.bg_main)
        ax.set_facecolor(self.theme_manager.bg_main)

        ax.pie(
            values,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            textprops={'color': self.theme_manager.fg_main},
            wedgeprops={'linewidth': 1, 'edgecolor': self.theme_manager.bg_main}
        )
        ax.set_title("Répartition des équipements enrégistrés", color=self.theme_manager.fg_main)

        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)




    def update_clock(self):
        try:
            # Chemin absolu vers le fichier de config partagé
            config_path = os.path.abspath(os.path.join("view", "files", "sauvegarde.json"))

            with open(config_path, "r") as f:
                config = json.load(f)

            running = config.get("running", False)
            interval = config.get("interval_seconds", 0)
            last_start_time = config.get("last_start_time")

            if running and last_start_time:
                elapsed = time.time() - last_start_time
                remaining = max(0, int(interval - (elapsed % interval)))

                # Convertir en Jours:Heures:Minutes:Secondes
                days, rem = divmod(remaining, 86400)
                hours, rem = divmod(rem, 3600)
                minutes, seconds = divmod(rem, 60)

                countdown = f"{days}j:{hours:02}:{minutes:02}:{seconds:02}"
                self.clock_value.config(text=countdown)
            else:
                self.clock_value.config(text="0j:00:00:00")

        except Exception as e:
            print("Erreur de lecture de la configuration :", e)
            self.clock_value.config(text="Erreur")

        # Relancer la mise à jour dans 1 seconde (réagit au changement de running)
        if self.clock_value.winfo_exists():
            self.clock_value.after(1000, self.update_clock)

        
    def count_equipments_by_type(self):
        """Compte les équipements par type à partir des fichiers JSON"""
        types = {
            "cisco": "cisco_save.json",
            "mikrotik": "mikrotik_save.json",
            "fortinet": "fortinet_save.json"
        }
        
        counts = {}
        for eq_type, filename in types.items():
            file_path = os.path.join(os.path.dirname(__file__), 'files', filename)
            counts[eq_type] = 0  # Valeur par défaut
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, list):  # Vérifie si c'est une liste
                            counts[eq_type] = len(data)
                except (json.JSONDecodeError, TypeError):
                    counts[eq_type] = 0
        
        # Retourne le dictionnaire (correction de la faute de frappe: 'count' -> 'counts')
        return counts

    # Fonction pour remplir les fichiers FTP avec heure, taille, nom
    def remplir_fichiers_ftp(self):
        ftp_dir = os.path.expanduser("/home/ftpuser")
        if os.path.exists(ftp_dir):
            # ⬇️ Filtrer uniquement les fichiers .cfg ou .rsc
            fichiers = [
                f for f in os.listdir(ftp_dir)
                if os.path.isfile(os.path.join(ftp_dir, f)) and f.lower().endswith(('.cfg', '.rsc'))
            ]

            self.ftp_tree.delete(*self.ftp_tree.get_children())

            taille_totale = 0  # Initialiser la taille totale

            if fichiers:
                for f in fichiers:
                    chemin = os.path.join(ftp_dir, f)
                    taille = os.path.getsize(chemin)
                    taille_totale += taille
                    heure_modif = os.path.getmtime(chemin)
                    from datetime import datetime
                    modif_str = datetime.fromtimestamp(heure_modif).strftime("%d/%m/%Y %H:%M:%S")
                    taille_kb = f"{taille / 1024:.1f} KB"
                    self.ftp_tree.insert("", "end", values=(f, taille_kb, modif_str))
            else:
                self.ftp_tree.insert("", "end", values=("Aucun fichier sauvegardé", "", ""), tags=("empty",))

            # Mettre à jour le Label "Stockage total"
            if taille_totale < 10_000:  # < 10 000 KB
                taille_str = f"{taille_totale / 1024:.1f} KB"
            elif taille_totale < 100_000_000:  # < 100 000 MB = 100 GB
                taille_str = f"{taille_totale / (1024**2):.1f} MB"
            else:
                taille_str = f"{taille_totale / (1024**3):.2f} GB"

            self.stock_valeur.config(text=taille_str)

        else:
            self.stock_valeur.config(text="0 KB")
            self.ftp_tree.delete(*self.ftp_tree.get_children())
            self.ftp_tree.insert("", "end", values=("Aucun fichier sauvegardé", "", ""), tags=("empty",))

        # Vérifier l'état des services
        self.check_services_status()



    def on_select(self, event):
        print("select")

    def load_saved_networks(self):
        networks_file = os.path.join(os.path.dirname(__file__), 'files', 'networks.json')
        if os.path.exists(networks_file):
            with open(networks_file, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def check_services_status(self):
        # Vérifier l'état du serveur FTP
        ftp_active = self.check_ftp_service()
        if ftp_active:
            self.ftp_status.config(text="✔️")
            self.ftp_label.config(text="Serveur FTP actif")
        else:
            self.ftp_status.config(text="❌")
            self.ftp_label.config(text="Serveur FTP non actif")

        # Vérifier l'état d'Ansible
        ansible_configured = self.check_ansible_config()
        if ansible_configured:
            self.ansible_status.config(text="✔️")
            self.ansible_label.config(text="Ansible configuré")
        else:
            self.ansible_status.config(text="❌")
            self.ansible_label.config(text="Ansible non configuré")

    def check_ftp_service(self):
        """Vérifie si le service FTP est actif"""
        try:
            # Vérifier si le processus vsftpd est en cours d'exécution
            result = subprocess.run(['pgrep', 'vsftpd'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False

    def check_ansible_config(self):
        """Vérifie si Ansible est correctement configuré"""
        try:
            # Vérifier si on peut exécuter une commande Ansible simple
            result = subprocess.run(['ansible', '--version'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False

    def count_reseau_disponible(self):
        interfaces = psutil.net_if_addrs()
        count = 0

        for interface_name, addrs in interfaces.items():
            for addr in addrs:
                if addr.family.name == 'AF_INET' and addr.address != '127.0.0.1':
                    try:
                        ip_obj = ipaddress.IPv4Interface(f"{addr.address}/{addr.netmask}")
                        count += 1
                    except Exception:
                        pass
        return count

    def count_reseau_enregistres(self):
        return len(self.saved_networks)

    def count_fichiers_sauvegardes(self):
        all_items = self.ftp_tree.get_children()
        count = 0
        for item in all_items:
            if "empty" not in self.ftp_tree.item(item, "tags"):
                count += 1
        return count


    def count_appareils_enr(self):
        fichiers = {
            "cisco": "cisco_save.json",
            "mikrotik": "mikrotik_save.json",
            "huawei": "huawei_save.json",
            "juniper": "juniper_save.json",
            "fortinet":"fortinet_save.json"
        }
        
        total = 0
        for type_eq, filename in fichiers.items():
            file_path = os.path.join(os.path.dirname(__file__), 'files', filename)
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    try:
                        data = json.load(f)
                        total += len(data)
                    except json.JSONDecodeError:
                        continue
        return total

    def count_appareil_en_sauv(self):
        fichiers = {
            "cisco": "cisco_save.json",
            "mikrotik": "mikrotik_save.json",
            "huawei": "huawei_save.json",
            "juniper": "juniper_save.json",
            "fortinet":"fortinet_save.json"
        }

        count = 0
        for type_eq, filename in fichiers.items():
            file_path = os.path.join(os.path.dirname(__file__), 'files', filename)
            if not os.path.exists(file_path):
                continue

            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    continue

            for equipement in data:
                ip = equipement.get("ip", "")
                credentials = equipement.get("credentials", {})
                username = credentials.get("username", "")
                password = credentials.get("password", "")
                status = equipement.get("status", False)

                ping_ok = self.ping(ip)
                ssh_ok = self.test_ssh_connection(ip, username, password)

                if status and ping_ok and ssh_ok:
                    count += 1

        return count


    def count_pannes(self):
        fichiers = {
            "cisco": "cisco_save.json",
            "mikrotik": "mikrotik_save.json",
            "huawei": "huawei_save.json",
            "juniper": "juniper_save.json",
            "fortinet":"fortinet_save.json"
        }
        
        count = 0
        for type_eq, filename in fichiers.items():
            file_path = os.path.join(os.path.dirname(__file__), 'files', filename)
            if not os.path.exists(file_path):
                continue

            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    continue

            for equipement in data:
                ip = equipement.get("ip", "")
                credentials = equipement.get("credentials", {})
                username = credentials.get("username", "")
                password = credentials.get("password", "")

                ping_ok = self.ping(ip)
                ssh_ok = self.test_ssh_connection(ip, username, password)
                
                if not ping_ok or not ssh_ok:
                    count += 1
        return count

    def remplir_treeview(self):
        # Vider le treeview actuel
        for item in self.tree.get_children():
            self.tree.delete(item)

        fichiers = {
            "cisco": "cisco_save.json",
            "mikrotik": "mikrotik_save.json",
            "huawei": "huawei_save.json",
            "juniper": "juniper_save.json",
            "fortinet": "fortinet_save.json"
        }

        equipements_trouves = False

        for type_eq, filename in fichiers.items():
            file_path = os.path.join(os.path.dirname(__file__), 'files', filename)

            if not os.path.exists(file_path):
                continue

            with open(file_path, 'r') as f:
                try:
                    data = json.load(f)
                except (json.JSONDecodeError, IOError):
                    continue

            if not data:  # Fichier vide
                continue

            for equipement in data:
                if not equipement:  # Équipement vide
                    continue

                name = equipement.get("name", "Inconnu")
                mac = equipement.get("mac", "N/A")
                ip = equipement.get("ip", "")

                credentials = equipement.get("credentials", {})
                username = credentials.get("username", "")
                password = credentials.get("password", "")

                etat = self.tester_etat_reel(ip, username, password)

                self.tree.insert("", "end", values=(name, mac, type_eq, etat))
                equipements_trouves = True

        if not equipements_trouves:
            # Afficher un message si aucun équipement n'a été trouvé
            self.tree.insert("", "end", values=("Aucun équipement enregistré", "", "", ""))

    def ping(self, ip):
        try:
            output = subprocess.run(['ping', '-c', '1', '-W', '1', ip],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            return output.returncode == 0
        except Exception:
            return False

    def test_ssh_connection(self, ip, username, password, timeout=3):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            client.connect(ip, username=username, password=password, timeout=timeout, allow_agent=False, look_for_keys=False)
            client.close()
            return True
        except (paramiko.ssh_exception.AuthenticationException,
                paramiko.ssh_exception.SSHException,
                socket.error):
            return False

    def tester_etat_reel(self, ip, username, password):
        ping_ok = self.ping(ip)
        ssh_ok = self.test_ssh_connection(ip, username, password)

        if ping_ok and ssh_ok:
            return "✔️"
        elif ping_ok and not ssh_ok:
            return "⚠️"
        else:
            return "❌"
