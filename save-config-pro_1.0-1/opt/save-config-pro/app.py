import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from view.scan_network import NetworkScanner
from view.saverestauration import SaveRestauration
from view.network_selection import SousReseaux
from view.network_enregistres import SousReseauxEnregistres
from view.plannification import BackupScheduler
from view.composants.menu_universel import MenuUniversel
from view.composants.menu_horizontal import BarreHaut
from view.composants.theme import ThemeManager
from view.composants.choix_menu import ChoiceMenu
from view.dashboard import Dashboard
from view.users import UsersManager
from view.historique_users import HistoriqueUsers
from view.deconnexion import Deconnexion
from view.fermer import Fermer
from view.auth import LoginFrame
from view.debut import AdminCreationFrame
from view.composants.loading import run_with_loading
import time
import os
import json


DOSSIER_PROFILS = os.path.join(os.path.dirname(__file__),'view', 'files', 'profils')

DOSSIER_FICHIERS = os.path.join(os.path.dirname(__file__),'view', 'files')
FICHIER_UTILISATEURS = os.path.join(DOSSIER_FICHIERS, 'users.json')

class NetworkConfigApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("\U0001F4BB Système de Gestion des Configurations Réseaux Informatiques")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Par exemple, utiliser 80% de la largeur et de la hauteur de l'écran
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)

        self.geometry(f"{window_width}x{window_height}")
        self.menu_visible = False  # Ou True selon l'état initial souhaité
        self.protocol("WM_DELETE_WINDOW", self.fermer)
        icon_path = "/usr/share/icons/hicolor/64x64/apps/save-config-pro.png"
        if os.path.exists(icon_path):
            self.iconphoto(False, tk.PhotoImage(file=icon_path))

        
        # Vérifier si un admin existe déjà
        if not self.check_admin_exists():
            self.show_admin_creation()
        else:
            self.show_login_screen()
    
    def check_admin_exists(self):
        users_file = os.path.join(os.path.dirname(__file__), 'view', 'files', 'users.json')
        if not os.path.exists(users_file):
            return False
            
        with open(users_file, 'r') as f:
            users = json.load(f)
            return any(user.get('role') == 'admin' for user in users.values())
    
    def show_admin_creation(self):
        """Affiche l'interface de création d'admin"""
        self.clear_window()
        self.admin_frame = AdminCreationFrame(
            self, 
            on_success=self.on_admin_created
        )
    
    def on_admin_created(self):
        """Callback appelé quand l'admin est créé"""
        self.show_login_screen()
        
    def show_login_screen(self):
        """Affiche l'interface de login"""
        self.clear_window()
        self.login_frame = LoginFrame(self, self.on_login_success)
        
    def on_login_success(self, username):
        """Callback appelé quand la connexion réussit"""
        self.nom_utilisateur = username
        self.setup_main_interface()
        
    def setup_main_interface(self):
        """Configure l'interface principale après connexion"""
        self.clear_window()
        # Initialisation du gestionnaire de thème
        self.theme_manager = ThemeManager(self)
        self.configure(bg=self.theme_manager.bg_main)
        self.setup_styles()
        
        # Création des widgets principaux
        self.create_main_widgets()
        self.scann()
    
    def clear_window(self):
        """Vide la fenêtre de tous ses widgets"""
        for widget in self.winfo_children():
            widget.destroy()

    def create_main_widgets(self):
        """Crée les widgets structurels principaux"""  
        self.barre_haut = BarreHaut(
            self,
            self.theme_manager,
            self.nom_utilisateur,
            DOSSIER_PROFILS
        )
        # Menu vertical
        self.vertical_menu = tk.Frame(self, width=60)
        self.vertical_menu.pack(side="left", fill="y")
        self.theme_manager.register_widget(self.vertical_menu, 'bg_secondary')
        # Boutons du menu vertical
        self.create_vertical_menu_buttons()
        # Menu universel
        self.menu_universel = MenuUniversel(self, self.theme_manager)

        # Séparateur
        self.separator_line = tk.Frame(self, width=1)
        self.separator_line.pack(side="left", fill="y")
        self.theme_manager.register_widget(self.separator_line, 'separator')
        
        # Contenu principal
        self.main_content = tk.Frame(self)
        self.main_content.pack(side="left", fill="both", expand=True)
        self.theme_manager.register_widget(self.main_content, 'bg_main')
        
        self.update_networks_from_json()  # Chargement initial

        

    def update_networks_from_json(self):
        """Recharge les sous-réseaux à partir du fichier JSON"""
        json_file_path = os.path.join(os.path.dirname(__file__), "view", "files", "networks.json")
        if os.path.exists(json_file_path):
            try:
                with open(json_file_path, "r") as f:
                    self.main_content.networks = json.load(f)
            except json.JSONDecodeError:
                self.main_content.networks = []
        else:
            self.main_content.networks = []

        # Réappliquer les thèmes si nécessaire
        self.theme_manager.register_widget(self.main_content, 'bg_main')


    def setup_styles(self):
        """Configure les styles ttk"""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Style Treeview
        self.style.configure("Treeview",
            background=self.theme_manager.bg_main,
            foreground=self.theme_manager.fg_main,
            fieldbackground=self.theme_manager.bg_main,
            rowheight=42,
            font=("Helvetica", 11)
        )
        self.style.configure("Treeview.Heading",
            background=self.theme_manager.bg_main,
            foreground=self.theme_manager.fg_main,
            font=("Helvetica", 11, "bold")
        )
        self.style.map('Treeview.Heading',
            background=[('active', self.theme_manager.bg_hover)],  # Couleur de fond quand cliqué
            foreground=[('active', self.theme_manager.highlight)]  # Couleur du texte quand cliqué
        )
        self.style.map('Treeview',
          background=[('selected', self.theme_manager.bg_hover)],  # Même couleur que le fond normal
          foreground=[('selected', self.theme_manager.fg_main)])
        
    def create_vertical_menu_buttons(self):
        role = self.get_user_role(self.nom_utilisateur)

        icons = [
            ("🏠", "Tableau de bord", self.show_dashboard),
            ("🖧", "Réseaux", self.open_scan_choice_window),
            ("🔍", "Scanner", self.init_scanner),
            ("📥", "Sauvegardes", self.show_saverestauration),
            ("⏰", "Planification", self.show_schedule),
            ("⚙️", "Paramètres", self.show_settings),
            # Le bouton utilisateurs ne sera ajouté que si admin
            *([("☺", "Utilisateurs", self.open_users_choice_window)] if role == "admin" else []),
            ("↩️", "Déconnecter", self.deconnect),
            ("🌓", "Thème", self.toggle_theme),
            ("▶", "Outils", self.toggle_menu_universel)
        ]

        # Configuration du tooltip
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.withdraw()
        tooltip_label = tk.Label(self.tooltip, font=("Helvetica", 10), bd=1, relief="solid")
        tooltip_label.pack()
        self.theme_manager.register_widget(tooltip_label, 'bg_secondary', 'fg_main')
        self.tooltip.label = tooltip_label

        for icon, label, cmd in icons:
            btn = tk.Button(
                self.vertical_menu,
                text=icon,
                font=("Helvetica", 18),
                relief="flat",
                bd=0,
                highlightthickness=0,
                width=2,
                height=2
            )
            # Enregistrement avec le gestionnaire de thème
            self.theme_manager.register_widget(
                btn,
                bg_prop='bg_secondary',
                fg_prop='fg_main',
                active_bg='bg_hover',
                active_fg='fg_main'
            )
            btn.config(command=cmd)
            btn.pack(pady=10)

            # Gestion des événements de souris
            btn.bind("<Enter>", lambda e, t=label: self.show_tooltip(e, t))
            btn.bind("<Leave>", lambda e: self.hide_tooltip())

        self.toggle_btn = self.vertical_menu.winfo_children()[-1]


    def get_user_role(self,username):
        if not os.path.exists(FICHIER_UTILISATEURS):
            return None
        with open(FICHIER_UTILISATEURS, "r") as f:
            users = json.load(f)
            user = users.get(username)
            return user.get("role") if user else None


    def show_tooltip(self, event, text):
        """Affiche le tooltip"""
        self.tooltip.label.config(text=text)
        self.tooltip.deiconify()
        self.tooltip.geometry(f"+{event.x_root+20}+{event.y_root+10}")

    def hide_tooltip(self):
        """Cache le tooltip"""
        self.tooltip.withdraw()

    def toggle_menu_universel(self):
        """Bascule l'affichage du menu universel"""
        if self.menu_visible:
            self.menu_universel.pack_forget()
            self.main_content.pack_forget()
            self.main_content.pack(side="left", fill="both", expand=True)
            self.menu_visible = False
            self.toggle_btn.config(text="▶")
        else:
            self.menu_universel.pack(side="left", fill="y")
            self.main_content.pack_forget()
            self.main_content.pack(side="left", fill="both", expand=True)
            self.menu_visible = True
            self.toggle_btn.config(text="◀")

    def clear_main_content(self):
        """Vide le contenu principal"""
        for widget in self.main_content.winfo_children():
            widget.destroy()


    def create_buttons(self):
        """Crée les boutons principaux"""
        self.button_frame = tk.Frame(self.main_content)
        self.button_frame.pack(fill="x", pady=10,padx=10)  # Remplir horizontalement
        self.theme_manager.register_widget(self.button_frame, 'bg_main', 'fg_success')

        button_configs = [
            ("🏠", "Tableau de bord", self.show_dashboard),
            ("🖧", "Réseaux", self.open_scan_choice_window),
            ("🔍", "Scanner", self.init_scanner),
            ("📥", "Sauvegardes", self.show_saverestauration),
            ("⏰", "Planification", self.show_schedule),
            ("⚙️", "Paramètres", self.show_settings),
        ]

        # Configuration responsive des colonnes
        for i in range(len(button_configs)):
            self.button_frame.grid_columnconfigure(i, weight=1)

        for i, (emoji, label, command) in enumerate(button_configs):
            frame = tk.Frame(self.button_frame, height=80, highlightbackground=self.theme_manager.fg_main,
                            highlightthickness=1, bd=0)
            frame.grid(row=0, column=i, padx=10, sticky="nsew")  # sticky pour l'étirement
            frame.pack_propagate(False)
            self.theme_manager.register_widget(frame, 'bg_main', highlight_prop='fg_main')

            emoji_label = tk.Label(frame, text=emoji, font=("Helvetica", 24))
            emoji_label.pack(pady=(10, 0))
            self.theme_manager.register_widget(emoji_label, 'bg_main', 'fg_main')

            text_label = tk.Label(frame, text=label, font=("Helvetica", 11, "bold"))
            text_label.pack()
            self.theme_manager.register_widget(text_label, 'bg_main', 'fg_main')

            # Interactions
            def on_enter(event, f=frame, e=emoji_label, t=text_label):
                for w in [f, e, t]:
                    w.config(bg=self.theme_manager.bg_hover)

            def on_leave(event, f=frame, e=emoji_label, t=text_label):
                for w in [f, e, t]:
                    w.config(bg=self.theme_manager.bg_main)

            def on_press(event, f=frame, e=emoji_label, t=text_label):
                for w in [f, e, t]:
                    w.config(bg=self.theme_manager.bg_hover)

            def on_release(event, cmd=command):
                cmd()

            for widget in [frame, emoji_label, text_label]:
                widget.bind("<Enter>", on_enter)
                widget.bind("<Leave>", on_leave)
                widget.bind("<ButtonPress-1>", on_press)
                widget.bind("<ButtonRelease-1>", on_release)


    def toggle_theme(self):
        """Bascule le thème et rafraîchit l'interface"""
        self.theme_manager.toggle_theme()
        self.setup_styles()
        self.update_all_widgets()
        self.update_idletasks()

    def update_all_widgets(self):
        """Force la mise à jour de tous les widgets"""
        for widget_info in self.theme_manager.widgets:
            if widget_info['widget'].winfo_exists():
                self.theme_manager._update_widget_appearance(widget_info)

    def run(self):
        self.mainloop()

    def init_scanner(self):
        self.clear_main_content()
        # Recharge les sous-réseaux depuis le fichier JSON
        self.update_networks_from_json()
        self.scanner = NetworkScanner(
            parent=self.main_content,
            networks=self.main_content.networks,  # maintenant à jour
            theme_manager=self.theme_manager
        )
        self.scanner.pack(expand=True, fill="both")  # Important pour l'affichage
        self.create_buttons()
        
        # Lancement du scan
        self.scanner.scan_network()


    # Actions fictives pour les autres menus
    
    def show_dashboard(self):
        self.clear_main_content()

        def task(update_progress):
            update_progress(10, "Tableau de bord...")

            # Création de l'instance (lourde)
            dashboard = Dashboard(
                parent=self.main_content,
                controller=self,
                theme_manager=self.theme_manager
            )

            update_progress(80, "Chargement des données...")
            dashboard.remplir_treeview()  # ⚠️ Appelle la méthode synchrone ici

            update_progress(95, "Finalisation...")
            time.sleep(0.3)

            return dashboard

        def after_task(dashboard):
            dashboard.pack(fill="both", expand=True)
            self.dashboard = dashboard  # pour accès futur si nécessaire

        run_with_loading(
            content_frame=self.main_content,
            task_function=task,
            callback=after_task,
            theme_manager=self.theme_manager
        )
    
    def show_schedule(self):
        self.clear_main_content()

        def task(update_progress):
            update_progress(30, "Préparation...")
            return BackupScheduler(
                parent=self.main_content,
                theme_manager=self.theme_manager
            )

        def after_task(backup_scheduler):
            backup_scheduler.pack(fill="both", expand=True)
            self.create_buttons()

        run_with_loading(
            content_frame=self.main_content,  # ou self.parent selon ton contexte
            task_function=task,
            callback=after_task,
            theme_manager=self.theme_manager
        )


    def show_settings(self):
        print('Parametre')


    # Dans votre classe principale
    def show_saverestauration(self):
        self.clear_main_content()
        self.sauvegarde_view = SaveRestauration(
            parent=self.main_content,
            theme_manager=self.theme_manager
        )
        self.sauvegarde_view.pack(expand=True, fill="both")
        self.create_buttons()
        


    def scann(self):
        self.clear_main_content()
        # Créer le cadre SousReseaux
        self.sous_reseaux_frame = SousReseaux(
            parent=self.main_content,
            theme_manager=self.theme_manager
        )
        self.sous_reseaux_frame.pack(fill="both", expand=True)
        self.create_buttons()
    


    def show_sous_reseaux_enregistres(self):
        self.clear_main_content()
        # Créer le cadre SousReseaux
        self.sous_reseaux_frame =SousReseauxEnregistres(
            parent=self.main_content,
            theme_manager=self.theme_manager
        )
        self.sous_reseaux_frame.pack(fill="both", expand=True)
        self.create_buttons()

    
    

    def open_scan_choice_window(self):
        ChoiceMenu(
            parent=self,
            theme_manager=self.theme_manager,
            choices=[
                ("Réseaux disponibles", self.scann),
                ("Réseaux enregistrés", self.show_sous_reseaux_enregistres),
            ]
        )

    def open_users_choice_window(self):
        ChoiceMenu(
            parent=self,
            theme_manager=self.theme_manager,
            choices=[
                ("Compte utilisateurs", self.show_users),
                ("Historiques des connexions", self.show_historique_user_frame),
            ]
        )
        
    def show_users(self):
        self.clear_main_content()
        # Créer le cadre SousReseaux
        self.user_frame =UsersManager(
            parent=self.main_content,
            theme_manager=self.theme_manager
        )
        self.user_frame.pack(fill="both", expand=True)
        self.create_buttons()


    def show_historique_user_frame(self):
        self.clear_main_content()
        # Créer le cadre SousReseaux
        self.historique_user_frame =HistoriqueUsers(
            parent=self.main_content,
            theme_manager=self.theme_manager
        )
        self.historique_user_frame.pack(fill="both", expand=True)
        self.create_buttons()

    def deconnect(self):
        """Gère la déconnexion de l'utilisateur"""
        # Chemin vers le fichier users.json
        users_file_path = os.path.join(os.path.dirname(__file__), "view", "files", "users.json")
        # Créer et utiliser la classe Deconnexion
        Deconnexion(
            parent=self,  # self fait référence à la fenêtre principale
            username=self.nom_utilisateur,  # Assurez-vous que cette variable est disponible
            users_file_path=users_file_path
        ).deconnecter()


    def fermer(self):
        """Gère la déconnexion de l'utilisateur et la fermeture de l'application"""
        # Chemin vers le fichier users.json
        users_file_path = os.path.join(os.path.dirname(__file__), "view", "files", "users.json")
        
        # Fermeture de l'application
        Fermer(
            parent=self,
            username=getattr(self, 'nom_utilisateur', None),
            users_file_path=users_file_path
        ).fermer_application()
        

                



                