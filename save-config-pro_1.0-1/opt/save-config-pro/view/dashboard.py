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
from datetime import datetime
import time
import threading
import shutil
import pwd

class Dashboard(tk.Frame):
    def __init__(self, parent, controller, theme_manager):
        super().__init__(parent)
        self.controller = controller
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main')

        # --- Variables d'état ---

        self.saved_networks = self.load_saved_networks()
        self.is_updating = False
        self.sauvegarde_count = 0
        self.pannes_count = 0
        
        # --- Variables pour une fermeture propre ---

        self.is_closing = False
        self.after_id_clock = None
        self.after_id_10s = None

        # --- Construction de l'interface ---

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # Conteneur principal

        self.main_container = tk.Frame(self)
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self.theme_manager.register_widget(self.main_container, 'bg_main')
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=2)
        self.main_container.grid_rowconfigure(0, weight=1)

        # Zone du graphique

        self.chart_frame = tk.Frame(self.main_container)
        self.chart_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.theme_manager.register_widget(self.chart_frame, 'bg_main')
        self.chart_frame.grid_rowconfigure(0, weight=1)
        self.chart_frame.grid_rowconfigure(1, weight=0)
        self.chart_frame.grid_columnconfigure(0, weight=1)

        self.chart_canvas_frame = tk.Frame(self.chart_frame)
        self.chart_canvas_frame.grid(row=0, column=0, sticky="nsew")
        self.theme_manager.register_widget(self.chart_canvas_frame, 'bg_main')

        # Horloge

        self.clock_frame = tk.Frame(self.chart_frame)
        self.clock_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.theme_manager.register_widget(self.clock_frame, 'bg_main')
        self.clock_inner_frame = tk.Frame(self.clock_frame)
        self.clock_inner_frame.pack(expand=True, anchor="center")
        self.theme_manager.register_widget(self.clock_inner_frame, 'bg_main')
        self.clock_label = tk.Label(self.clock_inner_frame, text="Prochaine sauvegarde:", font=("Arial", 10, "bold"))
        self.clock_label.pack()
        self.theme_manager.register_widget(self.clock_label, 'bg_main', 'fg_main')
        self.clock_value = tk.Label(self.clock_inner_frame, text="", font=("Arial", 14))
        self.clock_value.pack()
        self.theme_manager.register_widget(self.clock_value, 'bg_main', 'fg_main')
        
        # Le reste de l'UI

        self.right_container = tk.Frame(self.main_container)
        self.right_container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.theme_manager.register_widget(self.right_container, 'bg_main')
        self.right_container.grid_rowconfigure(0, weight=3); self.right_container.grid_rowconfigure(1, weight=0); self.right_container.grid_rowconfigure(2, weight=2)
        self.right_container.grid_columnconfigure(0, weight=1)
        
        # La table des etats des equipements

        self.table_frame = tk.Frame(self.right_container)
        self.table_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.theme_manager.register_widget(self.table_frame, 'bg_main')
        self.table_frame.grid_rowconfigure(0, weight=1); self.table_frame.grid_columnconfigure(0, weight=1)
        self.columns = ("Equipements", "Mac", "Type", "Etat")
        self.tree = ttk.Treeview(self.table_frame, columns=self.columns, show="headings", height=7)
        for col in self.columns: self.tree.heading(col, text=col); self.tree.column(col, anchor="center", width=230)
        self.scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew"); self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<Double-1>", self.on_select)
        

        # Frame des services

        self.services_frame = tk.Frame(self.right_container)
        self.services_frame.grid(row=1, column=0, sticky="ew", pady=10)
        self.theme_manager.register_widget(self.services_frame, 'bg_main')
        for i in range(3): self.services_frame.grid_columnconfigure(i, weight=1)

        # État du serveur FTP

        self.ftp_frame = tk.LabelFrame(self.services_frame, text="État du serveur FTP", font=("Arial", 10, "bold"), bd=2, relief="groove")
        self.ftp_frame.grid(row=0, column=0, sticky="nsew", padx=5)
        self.theme_manager.register_widget(self.ftp_frame, 'bg_main', 'fg_main')
        self.ftp_status = tk.Label(self.ftp_frame, text="❌", font=("Arial", 24)); self.ftp_status.pack(pady=10)
        self.theme_manager.register_widget(self.ftp_status, 'bg_main', 'fg_main')
        self.ftp_label = tk.Label(self.ftp_frame, text="Serveur FTP non actif"); self.ftp_label.pack()
        self.theme_manager.register_widget(self.ftp_label, 'bg_main', 'fg_main')

        # État d'Ansible

        self.ansible_frame = tk.LabelFrame(self.services_frame, text="État d'Ansible", font=("Arial", 10, "bold"), bd=2, relief="groove")
        self.ansible_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        self.theme_manager.register_widget(self.ansible_frame, 'bg_main', 'fg_main')
        self.ansible_status = tk.Label(self.ansible_frame, text="❌", font=("Arial", 24)); self.ansible_status.pack(pady=10)
        self.theme_manager.register_widget(self.ansible_status, 'bg_main', 'fg_main')
        self.ansible_label = tk.Label(self.ansible_frame, text="Ansible non configuré"); self.ansible_label.pack()
        self.theme_manager.register_widget(self.ansible_label, 'bg_main', 'fg_main')

        # Stockage total

        self.stock_frame = tk.LabelFrame(self.services_frame, text="Stockage total", font=("Arial", 10, "bold"), bd=2, relief="groove")
        self.stock_frame.grid(row=0, column=2, sticky="nsew", padx=5)
        self.theme_manager.register_widget(self.stock_frame, 'bg_main', 'fg_main')
        self.stock_valeur = tk.Label(self.stock_frame, text="", font=("Arial", 24)); self.stock_valeur.pack(pady=10)
        self.theme_manager.register_widget(self.stock_valeur, 'bg_main', 'fg_main')

        # Tables des Fichiers sauvegardés 

        self.ftp_table_frame = tk.Frame(self.right_container)
        self.ftp_table_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        self.theme_manager.register_widget(self.ftp_table_frame, 'bg_main')
        self.ftp_table_frame.grid_rowconfigure(0, weight=1); self.ftp_table_frame.grid_columnconfigure(0, weight=1)
        self.ftp_tree = ttk.Treeview(self.ftp_table_frame, columns=("Nom", "Taille", "Heure"), show="headings", height=5)
        scrollbar_ftp = ttk.Scrollbar(self.ftp_table_frame, orient="vertical", command=self.ftp_tree.yview)
        self.ftp_tree.configure(yscrollcommand=scrollbar_ftp.set)
        for col in ("Nom", "Taille", "Heure"): self.ftp_tree.heading(col, text=col); self.ftp_tree.column(col, anchor="center")
        self.ftp_tree.grid(row=0, column=0, sticky="nsew"); scrollbar_ftp.grid(row=0, column=1, sticky="ns")
        
        # Les boutons statistiques

        self.bottom_stats_frame = tk.Frame(self)
        self.bottom_stats_frame.grid(row=1, column=0, sticky="ew", pady=10)
        self.theme_manager.register_widget(self.bottom_stats_frame, 'bg_main')
        for i in range(3): self.bottom_stats_frame.grid_columnconfigure(i, weight=1)
        self.sections = [
            {"title": "Réseau disponible", "count_func": self.count_reseau_disponible, "callback": self.controller.scann},
            {"title": "Réseau enregistrés", "count_func": self.count_reseau_enregistres, "callback": self.controller.show_sous_reseaux_enregistres},
            {"title": "Fichiers sauvegardés", "count_func": self.count_fichiers_sauvegardes, "callback": self.controller.show_saverestauration},
            {"title": "Appareils enrégistrés", "count_func": self.count_appareils_enr, "callback": self.controller.show_schedule},
            {"title": "Appareil en sauvegarde", "count_func": self.count_appareil_en_sauv, "callback": self.controller.show_saverestauration},
            {"title": "Pannes enregistrées", "count_func": self.count_pannes, "callback": self.controller.show_saverestauration},
        ]
        self.section_widgets = []
        self.create_stats_sections()

        # --- Démarrage des boucles et tâches après construction complète ---
        self.after(100, self.start_background_tasks)

    def start_background_tasks(self):
        """Lance toutes les tâches de fond une fois l'UI construite."""
        self.create_charts()
        self.update_clock()
        self.start_10s_timer()

   
    def prepare_for_close(self):
        """Détruit et nettoie proprement tous les processus en cours du Dashboard."""
        print("[INFO] Préparation à la fermeture du dashboard...")
        self.is_closing = True
        print("[INFO] Signal d'arrêt pour les threads activé.")

        if self.after_id_clock:
            try: self.after_cancel(self.after_id_clock)
            except tk.TclError: pass
            self.after_id_clock = None
            print("[INFO] Timer de l'horloge annulé.")

        if self.after_id_10s:
            try: self.after_cancel(self.after_id_10s)
            except tk.TclError: pass
            self.after_id_10s = None
            print("[INFO] Timer de 10s annulé.")
        
        print("[INFO] Nettoyage des ressources Matplotlib...")
        try:
            plt.close('all')
        except Exception as e:
            print(f"[AVERTISSEMENT] Erreur lors du nettoyage de Matplotlib: {e}")


    # Creation de la section des stats (les boutons du bas)
    def create_stats_sections(self):
        for i, section in enumerate(self.sections):
            row, col = divmod(i, 3)
            frame = tk.LabelFrame(self.bottom_stats_frame, text=section["title"], font=("Arial", 12, "bold"), bd=2, relief="groove", labelanchor="n")
            frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.theme_manager.register_widget(frame, 'bg_main', 'fg_main')
            lbl = tk.Label(frame, text=str(section["count_func"]()), font=("Arial", 30, "bold"), fg=self.theme_manager.fg_main)
            lbl.pack(expand=True)
            self.theme_manager.register_widget(lbl, 'bg_main', 'fg_main')
            frame.bind("<Button-1>", lambda e, cb=section["callback"]: cb())
            lbl.bind("<Button-1>", lambda e, cb=section["callback"]: cb())
            self.section_widgets.append({"frame": frame, "label": lbl, "title": section["title"], "callback": section["callback"]})


    # Mise à jour de certaines interfaces apres 10s
    def start_10s_timer(self):
        if not self.winfo_exists() or self.is_closing: return
        self.remplir_fichiers_ftp()
        self.update_section(2)
        self.remplir_treeview()
        self.after_id_10s = self.after(10000, self.start_10s_timer)


    # Compte à rebours prochaine sauvegarde

    def update_clock(self):
        if not self.winfo_exists() or self.is_closing: return
        try:
            config_path = os.path.abspath(os.path.join("view", "files", "sauvegarde.json"))
            with open(config_path, "r") as f: config = json.load(f)
            running = config.get("running", False); interval = config.get("interval_seconds", 0); last_start_time = config.get("last_start_time")
            if running and last_start_time:
                elapsed = time.time() - last_start_time
                remaining = max(0, int(interval - (elapsed % interval)))
                days, rem = divmod(remaining, 86400); hours, rem = divmod(rem, 3600); minutes, seconds = divmod(rem, 60)
                self.clock_value.config(text=f"{days}j:{hours:02}:{minutes:02}:{seconds:02}")
            else: self.clock_value.config(text="0j:00:00:00")
        except Exception: self.clock_value.config(text="Erreur")
        self.after_id_clock = self.after(1000, self.update_clock)

    
    # Mise à jours des etats des equipements et lister

    def _worker_update_devices(self):
        fichiers = {"cisco": "cisco_save.json", "mikrotik": "mikrotik_save.json", "huawei": "huawei_save.json", "juniper": "juniper_save.json", "fortinet": "fortinet_save.json"}
        tree_data, sauvegarde_count_local, pannes_count_local = [], 0, 0
        for type_eq, filename in fichiers.items():
            if self.is_closing: print("[INFO] Worker: Signal d'arrêt détecté (avant fichier)."); self.is_updating = False; return
            file_path = os.path.join(os.path.dirname(__file__), 'files', filename)
            if not os.path.exists(file_path): continue
            try:
                with open(file_path, 'r') as f: data = json.load(f)
                if not data: continue
            except (json.JSONDecodeError, IOError): continue
            for equipement in data:
                if self.is_closing: print("[INFO] Worker: Signal d'arrêt détecté (pendant traitement)."); self.is_updating = False; return
                if not equipement: continue
                etat = self.tester_etat_reel(equipement.get("ip", ""), equipement.get("credentials", {}).get("username", ""), equipement.get("credentials", {}).get("password", ""))
                tree_data.append((equipement.get("name", "Inconnu"), equipement.get("mac", "N/A"), type_eq, etat))
                if etat == "✔️": sauvegarde_count_local += 1
                else: pannes_count_local += 1
        final_results = {"tree_data": tree_data, "sauvegarde_count": sauvegarde_count_local, "pannes_count": pannes_count_local}
        
        if self.is_closing:
            print("[INFO] Worker: Arrêt avant de poster le résultat.")
            self.is_updating = False; return
        try:
            self.after(0, self._update_gui_from_worker, final_results)
        except tk.TclError:
            print("[INFO] Worker: La fenêtre a été détruite juste avant la mise à jour.")
            self.is_updating = False

    def _update_gui_from_worker(self, results):
        if not self.winfo_exists() or self.is_closing:
            self.is_updating = False; return
        self.sauvegarde_count = results["sauvegarde_count"]
        self.pannes_count = results["pannes_count"]
        for item in self.tree.get_children(): self.tree.delete(item)
        if not results["tree_data"]: self.tree.insert("", "end", values=("Aucun équipement enregistré", "", "", ""))
        else:
            for row_data in results["tree_data"]: self.tree.insert("", "end", values=row_data)
        self.refresh_all_stats()
        self.is_updating = False


    # Mettre à jour toutes les sections
    def refresh_all_stats(self):
        if not self.winfo_exists() or self.is_closing: return
        for i in range(len(self.section_widgets)): self.update_section(i)


    # Mettre à jour une section spécifique

    def update_section(self, section_index):
        if not self.winfo_exists() or self.is_closing: return
        if 0 <= section_index < len(self.section_widgets):
            try: self.section_widgets[section_index]["label"].config(text=str(self.sections[section_index]["count_func"]()))
            except Exception as e: print(f"Erreur mise à jour section {section_index}: {e}")


    # Création du chart

    def create_charts(self):
        if not self.winfo_exists() or self.is_closing: return
        try:
            counts = {k: v for k, v in self.count_equipments_by_type().items() if v > 0}
            fig, ax = plt.subplots(figsize=(7, 5), dpi=100)
            fig.patch.set_facecolor(self.theme_manager.bg_main)
            ax.set_facecolor(self.theme_manager.bg_main)
            if not counts: ax.text(0.5, 0.5, "Aucun équipement enregistré", ha='center', va='center', color=self.theme_manager.fg_main, fontsize=12); ax.axis('off')
            else:
                ax.pie(counts.values(), labels=counts.keys(), autopct='%1.1f%%', startangle=90, textprops={'color': self.theme_manager.fg_main, 'fontsize': 10}, wedgeprops={'linewidth': 1, 'edgecolor': self.theme_manager.bg_main})
                ax.set_title("Répartition des équipements enrégistrées", color=self.theme_manager.fg_main, fontsize=12)
            plt.tight_layout()
            if hasattr(self, 'canvas'): self.canvas.get_tk_widget().destroy()
            self.canvas = FigureCanvasTkAgg(fig, master=self.chart_canvas_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        except Exception as e: print(f"Erreur création graphique: {e}")


    # Chargement des fichiers depuis le serveur ftp pour remplir le ftp_tree
            
    def remplir_fichiers_ftp(self):
        if not self.winfo_exists() or self.is_closing: return
        ftp_dir = os.path.expanduser("/home/ftpuser")
        if os.path.exists(ftp_dir):
            try:
                fichiers = [f for f in os.listdir(ftp_dir) if os.path.isfile(os.path.join(ftp_dir, f)) and f.lower().endswith(('.cfg', '.rsc'))]
                self.ftp_tree.delete(*self.ftp_tree.get_children())
                taille_totale = 0
                if fichiers:
                    for f in fichiers:
                        chemin = os.path.join(ftp_dir, f); taille = os.path.getsize(chemin); taille_totale += taille
                        modif_str = datetime.fromtimestamp(os.path.getmtime(chemin)).strftime("%d/%m/%Y %H:%M:%S")
                        self.ftp_tree.insert("", "end", values=(f, f"{taille / 1024:.1f} KB", modif_str))
                else: self.ftp_tree.insert("", "end", values=("Aucun fichier sauvegardé", "", ""), tags=("empty",))
                if taille_totale < 10_000: taille_str = f"{taille_totale / 1024:.1f} KB"
                elif taille_totale < 100_000_000: taille_str = f"{taille_totale / (1024**2):.1f} MB"
                else: taille_str = f"{taille_totale / (1024**3):.2f} GB"
                self.stock_valeur.config(text=taille_str)
            except Exception as e: print(f"Erreur remplissage FTP: {e}")
        else:
            self.stock_valeur.config(text="0 KB")
            self.ftp_tree.delete(*self.ftp_tree.get_children())
            self.ftp_tree.insert("", "end", values=("Aucun fichier sauvegardé", "", ""), tags=("empty",))
        self.check_services_status()


    # Vérification des services comme le serveur ftp et ansible
    def check_services_status(self):
        if not self.winfo_exists() or self.is_closing: return
        if self.check_ftp_service(): self.ftp_status.config(text="✔️"); self.ftp_label.config(text="Serveur FTP actif")
        else: self.ftp_status.config(text="❌"); self.ftp_label.config(text="Serveur FTP non actif")
        if self.check_ansible_config(): self.ansible_status.config(text="✔️"); self.ansible_label.config(text="Ansible configuré")
        else: self.ansible_status.config(text="❌"); self.ansible_label.config(text="Ansible non configuré")
    

    def load_saved_networks(self):
        networks_file = os.path.join(os.path.dirname(__file__), 'files', 'networks.json')
        if os.path.exists(networks_file):
            try:
                with open(networks_file, 'r') as f: return json.load(f)
            except json.JSONDecodeError: return []
        return []
    


    def check_ftp_service(self):
        try:
            if subprocess.run(['systemctl', 'is-active', '--quiet', 'vsftpd'], check=False).returncode != 0: return False
            user_info = pwd.getpwnam('ftpuser')
            if not os.path.isdir(user_info.pw_dir): return False
        except (FileNotFoundError, KeyError, Exception): return False
        return True

    def check_ansible_config(self): return shutil.which('ansible') is not None


    #------Les methoses pour faire les comptes
    def count_appareils_enr(self):
        total = 0; fichiers = ["cisco_save.json", "mikrotik_save.json", "huawei_save.json", "juniper_save.json", "fortinet_save.json"]
        for filename in fichiers:
            file_path = os.path.join(os.path.dirname(__file__), 'files', filename)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f: total += len(json.load(f))
                except (json.JSONDecodeError, TypeError): continue
        return total
    

    def count_reseau_enregistres(self): return len(self.saved_networks)
    def on_select(self, event): print("select")

    # Verification des etats ping et ssh
    def ping(self, ip):
        try: return subprocess.run(['ping', '-c', '1', '-W', '1', ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        except Exception: return False
    def test_ssh_connection(self, ip, username, password, timeout=3):
        try:
            client = paramiko.SSHClient(); client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, username=username, password=password, timeout=timeout, allow_agent=False, look_for_keys=False)
            client.close(); return True
        except Exception: return False
    def tester_etat_reel(self, ip, username, password):
        ping_ok = self.ping(ip)
        return "✔️" if ping_ok and self.test_ssh_connection(ip, username, password) else ("⚠️" if ping_ok else "❌")
    

    def count_reseau_disponible(self):
        count = 0
        for _, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family.name == 'AF_INET' and addr.address != '127.0.0.1':
                    try: ipaddress.IPv4Interface(f"{addr.address}/{addr.netmask}"); count += 1
                    except Exception: pass
        return count
    

    def count_fichiers_sauvegardes(self):
        if not self.winfo_exists(): return 0
        return sum(1 for item in self.ftp_tree.get_children() if "empty" not in self.ftp_tree.item(item, "tags"))
    

    def count_equipments_by_type(self):
        types = {"cisco": "cisco_save.json", "mikrotik": "mikrotik_save.json", "fortinet": "fortinet_save.json"}
        counts = {}
        for eq_type, filename in types.items():
            file_path = os.path.join(os.path.dirname(__file__), 'files', filename)
            counts[eq_type] = 0
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f: data = json.load(f)
                    if isinstance(data, list): counts[eq_type] = len(data)
                except (json.JSONDecodeError, TypeError): continue
        return counts
    

    def count_appareil_en_sauv(self): return self.sauvegarde_count


    def count_pannes(self): return self.pannes_count


    def remplir_treeview(self):
        if self.is_updating: return
        self.is_updating = True
        thread = threading.Thread(target=self._worker_update_devices, daemon=True)
        thread.start()