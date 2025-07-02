import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import json
import weakref
import sys
from view.composants.scriptrunner import ScriptRunner
import time
import shutil
from datetime import datetime

class BackupSchedulerManager:
    _instance = None
    CONFIG_FILE = "files/sauvegarde.json"  # Nom du fichier de configuration

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_once()
            cls._instance._load_config()  # Charger la configuration au démarrage
        return cls._instance

    def _init_once(self):
        self.running = False
        self.remaining_seconds = 0
        self.days = 0
        self.hours = 0
        self.minutes = 0
        self.seconds = 0
        self.interval_seconds = 0
        self.timer_thread = None
        self.backup_thread = None
        self.callbacks = []
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.lock = threading.Lock()
        self.backup_in_progress = False
        self.last_start_time = None
        self.current_user = None  # Nouvel attribut pour stocker l'utilisateur

    def set_current_user(self, username):
        """Définit l'utilisateur actuel pour le journal des sauvegardes"""
        self.current_user = username


    def _load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        config_path = os.path.join(self.base_dir, self.CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.running = config.get('running', False)
                    self.days = config.get('days', 0)
                    self.hours = config.get('hours', 0)
                    self.minutes = config.get('minutes', 0)
                    self.seconds = config.get('seconds', 0)
                    self.interval_seconds = config.get('interval_seconds', 0)
                    self.last_start_time = config.get('last_start_time')
                    
                    if self.running and self.last_start_time:
                        # Calculer le temps écoulé depuis le dernier démarrage
                        elapsed = time.time() - self.last_start_time
                        self.remaining_seconds = max(0, self.interval_seconds - int(elapsed % self.interval_seconds))
                    else:
                        self.remaining_seconds = self.interval_seconds
                        
            except Exception as e:
                print(f"Erreur lors du chargement de la configuration: {e}")

    def _save_config(self):
        """Sauvegarde la configuration dans le fichier JSON"""
        config = {
            'running': self.running,
            'days': self.days,
            'hours': self.hours,
            'minutes': self.minutes,
            'seconds': self.seconds,
            'interval_seconds': self.interval_seconds,
            'last_start_time': self.last_start_time if self.running else None
        }
        
        config_path = os.path.join(self.base_dir, self.CONFIG_FILE)
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de la configuration: {e}")

    def set_duration(self, days, hours, minutes, seconds):
        with self.lock:
            self.days = days
            self.hours = hours
            self.minutes = minutes
            self.seconds = seconds
            total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
            self.remaining_seconds = total_seconds
            self.interval_seconds = total_seconds
            self._save_config()  # Sauvegarder après modification

    def start(self):
        with self.lock:
            # Validation des entrées
            if self.interval_seconds <= 0:
                raise ValueError("La durée doit être supérieure à 0")
            if self.running:
                return

            # Récupération des équipements actifs
            active_equipments = self._get_active_macs()
            
            # Vérification s'il y a des équipements à sauvegarder
            if not active_equipments:
                messagebox.showwarning(
                    "Aucun équipement", 
                    "Aucun équipement sélectionné pour la sauvegarde.\n"
                    "Veuillez d'abord créer une sauvegarde valide."
                )
                return

            # Chemin du fichier de log
            log_path = os.path.join(self.base_dir, "files", "operation_sauvegarde.json")
            
            # Initialisation du log
            log_data = []
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r') as f:
                        log_data = json.load(f)
                        if not isinstance(log_data, list):
                            log_data = []
                except Exception as e:
                    print(f"⚠️ Erreur lecture log: {e} - Nouveau fichier créé")

            # Conversion correcte de l'intervalle total (pas du temps restant)
            total_seconds = self.interval_seconds
            days = total_seconds // 86400
            remaining = total_seconds % 86400
            hours = remaining // 3600
            remaining %= 3600
            minutes = remaining // 60
            seconds = remaining % 60
            interval_str = f"{days}j {hours}h {minutes}m {seconds}s"

            # Nouvelle entrée de log
            new_entry = {
                "date_debut": time.strftime("%Y-%m-%d %H:%M:%S"),
                "date_fin": None,
                "equipements": active_equipments,
                "status": "en_cours",
                "utilisateur": self.current_user if self.current_user else "system",
                "intervalle": interval_str,
                "intervalle_secondes": self.interval_seconds
            }
            log_data.append(new_entry)

            # Sauvegarde du log
            try:
                with open(log_path, 'w') as f:
                    json.dump(log_data, f, indent=2)
            except Exception as e:
                print(f"⚠️ Erreur écriture log: {e}")

            # Démarrage du processus
            self.running = True
            self.backup_in_progress = False
            self.last_start_time = time.time()
            self._save_config()

        self._start_countdown()
        self._schedule_backup()
    def _update_backup_log(self, success=True):
        """Met à jour le statut de la dernière sauvegarde"""
        log_path = os.path.join(self.base_dir, "files", "operation_sauvegarde.json")
        if not os.path.exists(log_path):
            return
            
        try:
            with open(log_path, 'r+') as f:
                log_data = json.load(f)
                if log_data and log_data[-1]["status"] == "en_cours":
                    log_data[-1].update({
                        "status": "succes" if success else "echec"
                    })
                    f.seek(0)
                    json.dump(log_data, f, indent=2)
                    f.truncate()
        except Exception as e:
            print(f"⚠️ Erreur mise à jour log: {e}")

    def _get_active_macs(self):
        """Récupère les MAC et noms des équipements actifs"""
        active_equipments = []
        equipment_files = {
            "cisco": "cisco_save.json",
            "mikrotik": "mikrotik_save.json", 
            "fortinet": "fortinet_save.json"
        }
        
        for filename in equipment_files.values():
            filepath = os.path.join(self.base_dir, "files", filename)
            if not os.path.exists(filepath):
                continue
                
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    active_equipments.extend(
                        {"mac": eq["mac"], "name": eq.get("name", "Inconnu")}
                        for eq in data
                        if eq.get("status") and "mac" in eq
                    )
            except Exception as e:
                print(f"⚠️ Erreur lecture {filename}: {e}")
        
        return active_equipments

    def stop(self):
        with self.lock:
            self.running = False
            self.backup_in_progress = False
            self.last_start_time = None
            self._save_config()

        if self.timer_thread:
            self.timer_thread.cancel()
            self.timer_thread = None

        if self.backup_thread and self.backup_thread.is_alive():
            self.backup_thread.join(timeout=1.0)

        # Nettoyer les dossiers de backup et réinitialiser les status
        self._cleanup_backup_folders()
        self.update_last_date_fin()
        self._reset_equipment_status()

    def _reset_equipment_status(self):
        """Réinitialise tous les status d'équipement à false"""
        equipment_files = [
            os.path.join(self.base_dir, "files", "mikrotik_save.json"),
            os.path.join(self.base_dir, "files", "cisco_save.json"),
            os.path.join(self.base_dir, "files", "fortinet_save.json")
        ]

        for file_path in equipment_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r+') as f:
                        data = json.load(f)
                        for item in data:
                            item["sauvegarde"] = False
                        f.seek(0)
                        json.dump(data, f, indent=2)
                        f.truncate()
                    print(f"✅ Confirmation d'arrêt dans {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"❌ Erreur réinitialisation {file_path}: {str(e)}")

    def update_last_date_fin(self):
        """Met à jour uniquement la date_fin du dernier enregistrement si elle est null/None"""
        log_path = os.path.join(self.base_dir, "files", "operation_sauvegarde.json")
        
        if not os.path.exists(log_path):
            return

        try:
            with open(log_path, 'r+') as f:
                try:
                    log_data = json.load(f)
                    if not isinstance(log_data, list):  # Vérification du format
                        raise ValueError("Format de log invalide")
                except (json.JSONDecodeError, ValueError):
                    return

                if log_data:
                    last_entry = log_data[-1]
                    
                    # Vérifie si date_fin est null/None ou n'existe pas
                    if last_entry.get("date_fin") is None:
                        # Mise à jour conditionnelle
                        last_entry["date_fin"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Réécriture complète du fichier
                        f.seek(0)
                        json.dump(log_data, f, indent=2)
                        f.truncate()

        except PermissionError:
            print("[ERREUR] Permission refusée pour le fichier de log")
        except Exception as e:
            print(f"[ERREUR] Échec mise à jour date_fin: {str(e)}")

    def _cleanup_backup_folders(self):
        """Supprime tous les dossiers de configuration Ansible/backup"""
        backup_folders = [
            os.path.join(self.base_dir, "files", "backup_mikrotik"),
            os.path.join(self.base_dir, "files", "backup_cisco"),
            os.path.join(self.base_dir, "files", "backup_fortinet")
        ]

        for folder in backup_folders:
            if os.path.exists(folder):
                try:
                    for item in os.listdir(folder):
                        item_path = os.path.join(folder, item)
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.unlink(item_path)
                    print(f"✅ Dossier {folder} nettoyé")
                except Exception as e:
                    print(f"❌ Erreur nettoyage {folder}: {str(e)}")

    def _run_backup_task(self):
        try:
            with self.lock:
                if self.backup_in_progress:
                    return
                self.backup_in_progress = True

            for folder_name in ["backup_mikrotik", "backup_cisco", "backup_fortinet"]:
                parent_dir = os.path.join(self.base_dir, "files", folder_name)
                
                # Vérifier si le dossier parent existe
                if not os.path.exists(parent_dir):
                    print(f"⚠️ Dossier {folder_name} non trouvé, skipping...")
                    continue
                
                # Parcourir tous les sous-dossiers dans le dossier parent
                for backup_subdir in os.listdir(parent_dir):
                    backup_dir = os.path.join(parent_dir, backup_subdir)
                    
                    # Vérifier que c'est bien un dossier
                    if not os.path.isdir(backup_dir):
                        continue
                    
                    playbook_file = f"{folder_name}_ftp.yml"
                    inventory_file = os.path.join(backup_dir, "inventory.ini")
                    playbook_path = os.path.join(backup_dir, playbook_file)
                    
                    # Vérifier que les fichiers nécessaires existent
                    if not all([os.path.exists(inventory_file), os.path.exists(playbook_path)]):
                        print(f"⚠️ Fichiers manquants dans {backup_subdir}, skipping...")
                        continue
                    
                    # Construire la commande
                    command = [
                        "ansible-playbook",
                        "-i", "inventory.ini",
                        playbook_file
                    ]
                    
                    print(f"\n🔧 Début de sauvegarde dans {backup_subdir}...")
                    print(f"📁 Dossier: {backup_dir}")
                    print(f"🔄 Commande: {' '.join(command)}")
                    
                    try:
                        result = subprocess.run(
                            command,
                            cwd=backup_dir,
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=1800  # Timeout après 30 minutes
                        )
                        print(f"✅ {backup_subdir} - Sauvegarde terminée avec succès")
                        print(result.stdout)
                    except subprocess.TimeoutExpired:
                        print(f"⌛ {backup_subdir} - Timeout après 30 minutes")
                    except subprocess.CalledProcessError as e:
                        print(f"❌ {backup_subdir} - Erreur pendant l'exécution:")
                        print(e.stdout)
                        print(e.stderr, file=sys.stderr)
                    except Exception as e:
                        print(f"❌ {backup_subdir} - Erreur inattendue: {str(e)}", file=sys.stderr)

                self._update_backup_log(success=True)
        
        except Exception as e:
            print(f"❌ Erreur pendant la sauvegarde: {e}")
            self._update_backup_log(success=False)
            raise
            
        finally:
            with self.lock:
                self.backup_in_progress = False

    def _schedule_backup(self):
        with self.lock:
            if not self.running:
                return

            if self.timer_thread:
                self.timer_thread.cancel()

        self.backup_thread = threading.Thread(target=self._run_backup_task, daemon=True)
        self.backup_thread.start()

        with self.lock:
            if self.running:
                self.timer_thread = threading.Timer(
                    self.interval_seconds,
                    self._schedule_backup
                )
                self.timer_thread.daemon = True
                self.timer_thread.start()

    def _safe_exec_callback(self, callback):
        try:
            cb = callback() if isinstance(callback, (weakref.ref, weakref.WeakMethod)) else callback
            if cb is not None:
                cb()
            return True
        except (tk.TclError, ReferenceError, AttributeError):
            return False
        except Exception as e:
            print(f"Erreur callback : {e}")
            return False

    def _start_countdown(self):
        def countdown():
            with self.lock:
                if not self.running:
                    return

                if self.remaining_seconds <= 0:
                    self.remaining_seconds = self.interval_seconds
                else:
                    self.remaining_seconds -= 1

            self.callbacks = [cb for cb in self.callbacks if self._safe_exec_callback(cb)]

            if self.running:
                threading.Timer(1, countdown).start()

        countdown()

    def get_time(self):
        with self.lock:
            rem = self.remaining_seconds
        days = rem // 86400
        hours = (rem % 86400) // 3600
        minutes = (rem % 3600) // 60
        seconds = rem % 60
        return days, hours, minutes, seconds

    def cleanup(self):
        self.stop()
        self.callbacks.clear()

    
    def register_callback(self, callback):
        """Register a callback to be notified when the timer updates"""
        with self.lock:
            # Use weakref to avoid keeping objects alive unnecessarily
            try:
                if hasattr(callback, '__self__'):  # Method
                    self.callbacks.append(weakref.WeakMethod(callback))
                else:  # Function
                    self.callbacks.append(weakref.ref(callback))
            except (TypeError, AttributeError):
                self.callbacks.append(callback)  # Fallback for non-weakref-able objects



class BackupScheduler(tk.Frame):
    fichiers = {
        "MikroTik": "mikrotik_save.json",
        "Cisco": "cisco_save.json",
        "Huawei": "huawei_save.json",
        "Juniper": "juniper_save.json",
        "Fortinet": "fortinet_save.json"
    }

    def __init__(self, parent, theme_manager):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main')
        self.manager = BackupSchedulerManager()
        
        # Initialisation des variables
        self._init_variables()
        
        # Création de l'interface
        self._create_widgets()
        
        # Configuration initiale
        self._setup_initial_state()
        
        # Chargement des données
        self.load_equipment_data()
        self.actualiser_frame_sauvegarde()

    def _init_variables(self):
        """Initialise les variables du gestionnaire"""
        self.days_var = tk.IntVar(value=self.manager.days)
        self.hours_var = tk.IntVar(value=self.manager.hours)
        self.minutes_var = tk.IntVar(value=self.manager.minutes)
        self.seconds_var = tk.IntVar(value=self.manager.seconds)
        
        # Variables d'animation
        self.size = 200
        self.pulse_margin = 10
        self.pulse_max = 10
        self.canvas_size = self.size + 2 * (self.pulse_margin + self.pulse_max)
        self.center = self.canvas_size // 2
        self.pulse_scale = 0
        self.pulse_direction = 1
        self.pulse_animation_id = None


    def _create_widgets(self):
        """Crée tous les widgets de l'interface"""
        # Configuration du grid principal
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=10)
        self.grid_columnconfigure(0, weight=1)
        
        # Frame supérieur
        self.top_frame = tk.Frame(self, padx=10, pady=10)
        self.top_frame.grid(row=0, column=0, sticky="nsew")
        self.theme_manager.register_widget(self.top_frame, 'bg_main')
        
        # Configuration des colonnes du top_frame avec largeurs égales
        for i in range(4):
            self.top_frame.grid_columnconfigure(i, weight=1, uniform="top_frames")
        
        # Frame inférieur
        self.bottom_frame = tk.Frame(self)
        self.bottom_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        self.theme_manager.register_widget(self.bottom_frame, 'bg_main')
        
        # Création des widgets
        self._create_equipement_frame()      # Colonne 0
        self._create_planning_frame()        # Colonne 1
        self._create_form_frame()            # Colonne 2
        self._create_countdown_frame()       # Colonne 3
        self._create_animated_button()       # Bouton central
        self._create_equipements_frame()     # Bas gauche
        self._create_equi_save_frame()       # Bas droit

    def _create_countdown_frame(self):
        """Crée le frame du compte à rebours"""
        self.countdown_frame = tk.LabelFrame(
            self.top_frame,
            text="Prochaines sauvegardes",
            font=("Arial", 12, "bold"),
            highlightthickness=0,
            bd=2,
            relief="groove",
            labelanchor="n"
        )
        self.countdown_frame.grid(row=0, column=3, sticky="nsew", padx=5, pady=5, ipadx=5, ipady=5)
        self.theme_manager.register_widget(self.countdown_frame, 'bg_main', 'fg_main')

        # Conteneur interne avec grid pour un meilleur contrôle
        inner_frame = tk.Frame(self.countdown_frame)
        inner_frame.pack(expand=True, fill='both')
        self.theme_manager.register_widget(inner_frame, 'bg_main')

        # Configuration des colonnes
        for i in range(4):
            inner_frame.grid_columnconfigure(i, weight=1, uniform="countdown_cols")

        # Labels titres
        labels_texts = ["JJ", "HH", "MN", "SC"]
        self.labels = []
        for i, txt in enumerate(labels_texts):
            lbl = tk.Label(inner_frame, text=txt, font=("Courier", 12, "bold"))
            lbl.grid(row=0, column=i, sticky="", pady=(10,0))
            self.theme_manager.register_widget(lbl, 'bg_main', 'fg_main')
            self.labels.append(lbl)

        # Labels valeurs
        self.days_label = tk.Label(inner_frame, text="00", font=("Courier", 20, "bold"), fg="red")
        self.days_label.grid(row=1, column=0, pady=(0,10))
        self.theme_manager.register_widget(self.days_label, 'bg_main')

        self.hours_label = tk.Label(inner_frame, text="00", font=("Courier", 20, "bold"), fg="red")
        self.hours_label.grid(row=1, column=1, pady=(0,10))
        self.theme_manager.register_widget(self.hours_label, 'bg_main')

        self.minutes_label = tk.Label(inner_frame, text="00", font=("Courier", 20, "bold"), fg="red")
        self.minutes_label.grid(row=1, column=2, pady=(0,10))
        self.theme_manager.register_widget(self.minutes_label, 'bg_main')

        self.seconds_label = tk.Label(inner_frame, text="00", font=("Courier", 20, "bold"), fg="red")
        self.seconds_label.grid(row=1, column=3, pady=(0,10))
        self.theme_manager.register_widget(self.seconds_label, 'bg_main')

    def _create_equipement_frame(self):
        """Crée le frame d'équipement"""
        self.equipement_frame = tk.LabelFrame(
            self.top_frame,
            text="Equipements en sauvegarde",
            font=("Arial", 12, "bold"),
            highlightthickness=0,
            bd=2,
            relief="groove",
            labelanchor="n"
        )
        self.equipement_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5, ipadx=5, ipady=5)
        self.theme_manager.register_widget(self.equipement_frame, 'bg_main', 'fg_main')

        # Conteneur pour centrer le contenu et placer les 3 labels
        container = tk.Frame(self.equipement_frame)
        container.pack(expand=True, fill='both')
        self.theme_manager.register_widget(container, 'bg_main')

        # créer un frame centré dans container
        center_frame = tk.Frame(container, bg=self.theme_manager.bg_main)
        center_frame.pack(expand=True)
        self.theme_manager.register_widget(center_frame, 'bg_main', 'fg_main')

        # maintenant pack les 3 widgets dans center_frame sans expand ni fill
        self.equip_saved_label = tk.Label(center_frame, text="0", font=("Arial", 40, "bold"))
        self.equip_saved_label.pack(side="left", padx=(0, 2))
        self.theme_manager.register_widget(self.equip_saved_label, 'bg_main', 'fg_main')

        self.slash_canvas = tk.Canvas(center_frame, width=40, height=80, bg=self.theme_manager.bg_main, highlightthickness=0)
        self.slash_canvas.pack(side="left", padx=0)
        self.slash_canvas.create_line(5, 75, 35, 5, width=8, fill="green", capstyle='round')
        self.theme_manager.register_widget(self.slash_canvas, 'bg_main', 'fg_main')

        self.equip_total_label = tk.Label(center_frame, text="0", font=("Arial", 40, "bold"))
        self.equip_total_label.pack(side="left", padx=(2, 0))
        self.theme_manager.register_widget(self.equip_total_label, 'bg_main', 'fg_main')

    def _create_planning_frame(self):
        """Crée le frame de planification"""
        self.planning_frame = tk.LabelFrame(
            self.top_frame,
            text="Création de sauvegarde",
            font=("Arial", 12, "bold"),
            highlightthickness=0,
            bd=2,
            relief="groove",
            labelanchor="n"
        )
        self.planning_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5, ipadx=5, ipady=5)
        self.theme_manager.register_widget(self.planning_frame, 'bg_main', 'fg_main')
        
        # Conteneur pour centrer le contenu
        container = tk.Frame(self.planning_frame)
        container.pack(expand=True, fill='both')
        self.theme_manager.register_widget(container, 'bg_main')
        
        self.planning_label = tk.Label(container, text="📌", font=("Arial", 55, "bold"), foreground=self.theme_manager.fg_main)
        self.planning_label.pack(expand=True)
        self.theme_manager.register_widget(self.planning_label, 'bg_main', 'fg_main')
        
        # Liaison des événements
        container.bind("<Button-1>", lambda event: self.creer_sauvegarde())
        self.planning_label.bind("<Button-1>", lambda event: self.creer_sauvegarde())

    def _create_form_frame(self):
        """Crée le frame du formulaire"""
        self.form_frame = tk.LabelFrame(
            self.top_frame,
            text="Programmer",
            font=("Arial", 12, "bold"),
            padx=10,
            pady=10,
            bd=2, 
            relief="groove",
            labelanchor="n"
        )
        self.form_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5, ipadx=5, ipady=5)
        self.theme_manager.register_widget(self.form_frame, 'bg_main', 'fg_main')

        # Conteneur principal
        main_container = tk.Frame(self.form_frame)
        main_container.pack(expand=True, fill='both')
        self.theme_manager.register_widget(main_container, 'bg_main')

        # Configuration des colonnes pour les spinboxes
        for i in range(4):
            main_container.grid_columnconfigure(i, weight=1, uniform="form_cols")

        self.spinboxes = []
        self.spinbox_vars = []

        for idx, (label, var_name, max_val) in enumerate([
            ("Jours", "days_var", 99),
            ("Heures", "hours_var", 23),
            ("Minutes", "minutes_var", 59),
            ("Secondes", "seconds_var", 59)
        ]):
            # Frame pour chaque spinbox
            frame = tk.Frame(main_container)
            frame.grid(row=0, column=idx, sticky="nsew", padx=5)
            self.theme_manager.register_widget(frame, 'bg_main')

            # Label
            lbl = tk.Label(frame, text=label)
            lbl.pack(pady=(0,5))
            self.theme_manager.register_widget(lbl, 'bg_main', 'fg_main')

            # Spinbox
            var = tk.StringVar(value="0")
            setattr(self, var_name, var)
            self.spinbox_vars.append(var)

            sp = tk.Spinbox(
                frame,
                from_=0, to=max_val,
                textvariable=var,
                width=6,
                justify="center",
                relief="groove",
                borderwidth=2
            )
            sp.pack()
            
            # Configuration du style
            sp.configure(
                bg=getattr(self.theme_manager, 'bg_main'),
                fg=getattr(self.theme_manager, 'fg_main'),
                insertbackground=getattr(self.theme_manager, 'fg_main'),
                selectbackground=getattr(self.theme_manager, 'bg_hover'),
                selectforeground=getattr(self.theme_manager, 'fg_main')
            )
            
            # Gestion des événements
            sp.bind("<FocusIn>", lambda event, v=var: event.widget.delete(0, "end") if v.get() == "0" else None)
            sp.bind("<FocusOut>", lambda event, v=var: v.set("0") if v.get() == "" else None)
            
            self.spinboxes.append(sp)
            self.theme_manager.register_widget(sp, 'bg_main', 'fg_main')

        # Boutons de contrôle
        self.button_frame = tk.Frame(main_container)
        self.button_frame.grid(row=1, column=0, columnspan=4, pady=(10,0), sticky="nsew")
        self.theme_manager.register_widget(self.button_frame, 'bg_main', 'fg_main')

        # Configuration des colonnes pour les boutons
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)

        self.start_btn = tk.Button(
            self.button_frame,
            text="Démarrer",
            command=self.on_start_clicked
        )
        self.start_btn.grid(row=0, column=0, padx=5, sticky="ew")
        self.theme_manager.register_widget(self.start_btn, 'bg_main', 'fg_main', 'bg_hover')

        self.stop_btn = tk.Button(
            self.button_frame,
            text="Arrêter",
            command=self.on_stop_clicked
        )
        self.stop_btn.grid(row=0, column=1, padx=5, sticky="ew")
        self.theme_manager.register_widget(self.stop_btn, 'bg_main', 'fg_main', 'bg_hover')

    def _setup_initial_state(self):
        """Configure l'état initial de l'interface"""
        if self.manager.running:
            self.update_countdown()
            self.update_animated_button()
            self.animate_pulse()
        
        self.manager.register_callback(self.update_countdown)


    def _create_animated_button(self):
        """Crée le bouton animé"""
        self.animated_canvas = tk.Canvas(self, width=self.canvas_size, height=self.canvas_size, highlightthickness=0)
        self.animated_canvas.place(relx=0.5, rely=0.5, anchor="center")

        offset = (self.canvas_size - self.size) // 2
        padding = 20
        
        self.button = self.animated_canvas.create_oval(
            offset + padding, offset + padding,
            offset + self.size - padding, offset + self.size - padding,
            fill="red", outline="white", width=6
        )
        
        self.text = self.animated_canvas.create_text(
            self.center, self.center, text="DEMARRER", fill="white", font=("Arial", 18, "bold")
        )
        
        self.pulse_circle = self.animated_canvas.create_oval(
            offset + self.pulse_margin, offset + self.pulse_margin,
            offset + self.size - self.pulse_margin, offset + self.size - self.pulse_margin,
            outline="red", width=3
        )
        
        self.theme_manager.register_widget(self.animated_canvas, 'bg_main', 'fg_main')


    def _create_equipements_frame(self):
        """Crée le frame de la liste des équipements"""
        self.equipements_frame = tk.LabelFrame(
            self,
            text="Liste des équipements",
            font=("Arial", 12, "bold"),
            highlightthickness=0,
            bd=2,
            relief="groove",
            labelanchor="n"
        )
        self.equipements_frame.place(x=20, y=190, width=340, height=500)
        self.theme_manager.register_widget(self.equipements_frame, 'bg_main', 'fg_main')

        # Scrollbar
        scrollbar = tk.Scrollbar(self.equipements_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        # Treeview
        self.equipements_tree = ttk.Treeview(
            self.equipements_frame,
            columns=("Nom", "IP"),
            show="headings",
            yscrollcommand=scrollbar.set
        )
        self.equipements_tree.heading("Nom", text="Nom", anchor="center")
        self.equipements_tree.heading("IP", text="Adresse IP", anchor="center")
        self.equipements_tree.column("Nom", width=150, anchor="center")
        self.equipements_tree.column("IP", width=150, anchor="center")
        self.equipements_tree.pack(fill="both", expand=True, padx=5, pady=5)

        scrollbar.config(command=self.equipements_tree.yview)

    def _create_equi_save_frame(self):
        """Crée le frame des équipements sauvegardés"""
        self.equi_save_frame = tk.LabelFrame(
            self,
            text="Équipements en sauvegarde",
            font=("Arial", 12, "bold"),
            highlightthickness=0,
            bd=2,
            relief="groove",
            labelanchor="n"
        )
        self.equi_save_frame.place(relx=1.0, y=190, x=-20, width=340, height=500, anchor="ne")
        self.theme_manager.register_widget(self.equi_save_frame, 'bg_main', 'fg_main')

        # Scrollbar
        scrollbar = tk.Scrollbar(self.equi_save_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        # Treeview
        self.save_tree = ttk.Treeview(
            self.equi_save_frame,
            columns=("Nom", "IP"),
            show="headings",
            yscrollcommand=scrollbar.set
        )
        self.save_tree.heading("Nom", text="Nom", anchor="center")
        self.save_tree.heading("IP", text="Adresse IP", anchor="center")
        self.save_tree.column("Nom", width=150, anchor="center")
        self.save_tree.column("IP", width=150, anchor="center")
        self.save_tree.pack(fill="both", expand=True, padx=5, pady=5)

        scrollbar.config(command=self.save_tree.yview)

    def load_equipment_data(self):
        """Charge les données des équipements"""
        base_path = os.path.join(os.path.dirname(__file__), 'files')

        for nom_famille, filename in self.fichiers.items():
            json_path = os.path.join(base_path, filename)
            if os.path.isfile(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for equip in data:
                            name = equip.get("name", "N/A")
                            ip = equip.get("ip", "N/A")
                            self.equipements_tree.insert("", "end", values=(name, ip))
                except Exception as e:
                    print(f"Erreur lecture {json_path}: {e}")
        
        self.update_total_equipements()

    def actualiser_frame_sauvegarde(self):
        """Met à jour le frame des sauvegardes"""
        self.save_tree.delete(*self.save_tree.get_children())
        base_path = os.path.join(os.path.dirname(__file__), 'files')

        for nom_famille, filename in self.fichiers.items():
            json_path = os.path.join(base_path, filename)
            if os.path.isfile(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for equip in data:
                            if equip.get("sauvegarde", False):
                                name = equip.get("name", "N/A")
                                ip = equip.get("ip", "N/A")
                                self.save_tree.insert("", "end", values=(name, ip))
                except Exception as e:
                    print(f"Erreur lecture {json_path}: {e}")

        # Mise à jour de l'interface
        self.update_animated_button()
        if self.manager.running:
            self.animate_pulse()

    def set_spinboxes_state(self, state: str):
        """Définit l'état des spinboxes"""
        for sp in self.spinboxes:
            sp.config(state=state)

    def on_start_clicked(self):
        """Gère le clic sur le bouton Démarrer"""
        if messagebox.askyesno("Confirmation", "Voulez-vous démarrer la planification ?"):
            self.start_schedule()

    def on_stop_clicked(self):
        """Gère le clic sur le bouton Arrêter"""
        if messagebox.askyesno("Confirmation", "Voulez-vous arrêter la planification ?"):
            self.stop_schedule()

    def start_schedule(self):
        """Démarre la planification"""
        try:
            days = int(self.days_var.get())
            hours = int(self.hours_var.get())
            minutes = int(self.minutes_var.get())
            seconds = int(self.seconds_var.get())
            
            self.manager.set_duration(days, hours, minutes, seconds)
            self.manager.start()
            self.update_animated_button()
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez saisir des valeurs numériques valides.")

    def stop_schedule(self):
        """Arrête la planification"""
        self.manager.stop()
        self.days_label.config(text="00")
        self.hours_label.config(text="00")
        self.minutes_label.config(text="00")
        self.seconds_label.config(text="00")
        self.update_animated_button()
        self.actualiser_frame_sauvegarde()
        self.update_total_equipements()

    def update_countdown(self):
        """Met à jour le compte à rebours"""
        days, hours, minutes, seconds = self.manager.get_time()
        self.days_label.config(text=f"{days:02}")
        self.hours_label.config(text=f"{hours:02}")
        self.minutes_label.config(text=f"{minutes:02}")
        self.seconds_label.config(text=f"{seconds:02}")

    def update_total_equipements(self):
        """Met à jour le nombre total d'équipements"""
        base_path = os.path.join(os.path.dirname(__file__), 'files')
        total = 0
        total_sauvegarde = 0
        for nom, filename in self.fichiers.items():
            json_path = os.path.join(base_path, filename)
            if os.path.isfile(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        total += len(data)
                        for equip in data:
                            if equip.get("sauvegarde", False):
                                total_sauvegarde += 1
                except Exception as e:
                    print(f"Erreur lecture {json_path}: {e}")
        self.equip_saved_label.config(text=str(total_sauvegarde))
        self.equip_total_label.config(text=str(total))   
        self.equip_saved_label.update_idletasks()
        self.equip_total_label.update_idletasks()     


    def animate_pulse(self):
        """Animation du bouton pulsant"""
        if self.manager.running:
            self.pulse_scale += self.pulse_direction * 0.5
            if self.pulse_scale > self.pulse_max or self.pulse_scale < 0:
                self.pulse_direction *= -1

            offset = (self.canvas_size - self.size) // 2
            base_margin = self.pulse_margin
            x0 = offset + base_margin - self.pulse_scale
            y0 = offset + base_margin - self.pulse_scale
            x1 = offset + self.size - base_margin + self.pulse_scale
            y1 = offset + self.size - base_margin + self.pulse_scale

            self.animated_canvas.coords(self.pulse_circle, x0, y0, x1, y1)
            self.animated_canvas.itemconfig(self.pulse_circle, outline="#00ff00")
            self.pulse_animation_id = self.after(50, self.animate_pulse)
        else:
            if self.pulse_animation_id:
                self.after_cancel(self.pulse_animation_id)
                self.pulse_animation_id = None

            offset = (self.canvas_size - self.size) // 2
            margin = self.pulse_margin
            self.animated_canvas.coords(
                self.pulse_circle,
                offset + margin, offset + margin,
                offset + self.size - margin, offset + self.size - margin
            )

    def update_animated_button(self):
        """Met à jour l'état du bouton animé"""
        if self.manager.running:
            self.animated_canvas.itemconfig(self.button, fill="green")
            self.animated_canvas.itemconfig(self.text, text="EN COURS")
            self.set_spinboxes_state('disabled')
            self.animate_pulse()
            self.animated_canvas.bind("<Button-1>", lambda event: self.on_stop_clicked())
        else:
            self.animated_canvas.itemconfig(self.button, fill="red")
            self.animated_canvas.itemconfig(self.text, text="DEMARRER")
            self.set_spinboxes_state('normal')
            if self.pulse_animation_id:
                self.after_cancel(self.pulse_animation_id)
                self.pulse_animation_id = None

            offset = (self.canvas_size - self.size) // 2
            margin = self.pulse_margin
            self.animated_canvas.coords(
                self.pulse_circle,
                offset + margin, offset + margin,
                offset + self.size - margin, offset + self.size - margin
            )
            self.animated_canvas.itemconfig(self.pulse_circle, outline="red")
            self.animated_canvas.bind("<Button-1>", lambda event: self.on_start_clicked())

    def creer_sauvegarde(self):
        """Crée une sauvegarde des équipements"""
        if messagebox.askyesno(
            "Confirmation",
            "Voulez-vous générer la sauvegarde de tous les équipements enregistrés ?\n"
            "Sinon, supprimez les équipements depuis le réseau scanné."
        ):
            self.stop_schedule()
            runner = ScriptRunner()

            # Exécution des scripts de sauvegarde
            results = [
                runner.run("scr_backup_cisco.py"),
                runner.run("scr_backup_mikrotik.py"),
                runner.run("scr_backup_fortinet.py")
            ]

            if all(code == 0 for code, _, _ in results):
                messagebox.showinfo("Succès", "✔️ Sauvegarde générée avec succès.")
            else:
                errors = []
                for i, (code, _, err) in enumerate(results):
                    if code != 0:
                        equip_name = ["Cisco", "MikroTik", "Fortinet"][i]
                        errors.append(f"{equip_name}: {err.strip() or 'Erreur inconnue'}")
                
                message = "❌ Une erreur s'est produite lors de la sauvegarde.\n" + "\n".join(errors)
                messagebox.showerror("Erreur", message)
        self.actualiser_frame_sauvegarde()
        self.update_total_equipements()