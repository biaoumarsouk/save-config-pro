import tkinter as tk
from tkinter import ttk

class AideLogiciel(tk.Frame):
    def __init__(self, parent, theme_manager):
        super().__init__(parent, bg=theme_manager.bg_main)
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main')

        self.pack(fill="both", expand=True)

        # Canvas + Scrollbar
        canvas = tk.Canvas(self, bg=self.theme_manager.bg_main, highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Frame interne scrollable
        self.inner_frame = tk.Frame(canvas, bg=self.theme_manager.bg_main)
        self.inner_frame_id = canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # Scroll dynamique
        self.inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self.inner_frame_id, width=e.width))

        self.theme_manager.register_widget(canvas, 'bg_main')
        self.theme_manager.register_widget(self.inner_frame, 'bg_main')


        # Création des groupes
        self.create_group("Etapes de sauvegarde", [
            "1. Choisir le(s) réseau(x) à scanner parmi les réseaux disponibles.",
            "2. Effectuer le scan des réseaux sélectionnés.",
            "3. Sélectionner le(s) équipement(s) à sauvegarder.",
            "4. Entrer leurs identifiants d’accès.",
            "5. Accéder au module de planification.",
            "6. Créer une sauvegarde.",
            "7. Les équipements avec identifiants d'accès corrects seront validés.",
            "8. Définir l'intervalle de temps pour le cycle de sauvegarde.",
            "9. Cliquer sur le bouton démarrerou central pour démarrer.",
            "10. Vérifier les résultats dans le module sauvegarde.",
            "11. Vous pouvez visualiser les fichiers sauvegardés.",
            "12. Cliquer sur le bouton arreter ou central pour arreter.",
        ])


        self.create_group("Etapes de restauration", [
            "1. Accéder au module sauvegarde.",
            "2. Choisir un equipement.",
            "3. Cliquer sur un fichier de configuration.",
            "2. Vérifier l’équipement cible.",
            "3. Cliquer sur restaurer.",
            "4. Attendre le message de confirmation de restauration."
        ])
        
        self.create_group("Tableau de bord", [
            "1. Répartition des équipements enregistrés par constructeur.",
            "2. Liste des équipements en cours de sauvegarde avec leur état.",
            "3. Compte à rebours avant la prochaine sauvegarde automatique.",
            "4. État des outils du système (FTP, Ansible, etc.).",
            "5. Espace de stockage utilisé pour les fichiers sauvegardés.",
            "6. Liste détaillée des fichiers de configuration sauvegardés.",
            "7. Statistiques globales : réseaux détectés, équipements, fichiers, pannes."
        ])


    def create_group(self, title, steps, is_etape=True):
        group_frame = tk.LabelFrame(
            self.inner_frame,
            text=title,
            font=("Arial", 14, "bold"),
            bg=self.theme_manager.bg_main,
            fg=self.theme_manager.fg_main,
            bd=2,
            relief="groove",
            padx=10,
            pady=10
        )
        # Prend toute la largeur disponible du parent (inner_frame)
        group_frame.pack(fill="x", pady=10, padx=20)
        self.theme_manager.register_widget(group_frame, 'bg_main', 'fg_main')

        if is_etape:
            max_per_row = 3
            # Frame interne pour la grille
            row_frame = tk.Frame(group_frame, bg=self.theme_manager.bg_main)
            row_frame.pack(fill="x")
            self.theme_manager.register_widget(row_frame, 'bg_main', 'fg_main')

            for index, step in enumerate(steps):
                step_frame = tk.Frame(row_frame, bg=self.theme_manager.bg_main)
                step_frame.grid(row=index // max_per_row, column=index % max_per_row, padx=5, pady=5, sticky="nsew")

                # Séparer le numéro et le texte
                # Extrait numéro en début, par ex "1." ou "2."
                import re
                match = re.match(r"(\d+\.?)\s*(.*)", step)
                if match:
                    numero, texte = match.group(1), match.group(2)
                else:
                    numero, texte = "", step

                label_numero = tk.Label(
                    step_frame,
                    text=numero,
                    bg=self.theme_manager.bg_main,
                    fg=self.theme_manager.fg_main,
                    font=("Arial", 14, "bold"),
                    width=3,  # largeur fixe pour aligner les numéros
                    anchor="w"
                )
                label_numero.grid(row=0, column=0, sticky="nw", padx=(30, 0), pady=10)

                label_texte = tk.Label(
                    step_frame,
                    text=texte,
                    wraplength=220,
                    justify="left",
                    bg=self.theme_manager.bg_main,
                    fg=self.theme_manager.fg_main,
                    font=("Arial", 12)
                )
                label_texte.grid(row=0, column=1, sticky="nw", padx=(5, 10), pady=10)

                self.theme_manager.register_widget(step_frame, 'bg_main')
                self.theme_manager.register_widget(label_numero, 'bg_main', 'fg_main')
                self.theme_manager.register_widget(label_texte, 'bg_main', 'fg_main')

            # Configurer le poids des colonnes pour que la grille occupe toute la largeur
            for i in range(max_per_row):
                row_frame.grid_columnconfigure(i, weight=1)




class FonctionnaliteSysteme(tk.Frame):
    def __init__(self, parent, theme_manager):
        super().__init__(parent, bg=theme_manager.bg_main)
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main')

        self.pack(fill="both", expand=True)

        # Canvas + Scrollbar
        canvas = tk.Canvas(self, bg=self.theme_manager.bg_main, highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Frame interne scrollable
        self.inner_frame = tk.Frame(canvas, bg=self.theme_manager.bg_main)
        self.inner_frame_id = canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # Scroll dynamique
        self.inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self.inner_frame_id, width=e.width))

        self.theme_manager.register_widget(canvas, 'bg_main')
        self.theme_manager.register_widget(self.inner_frame, 'bg_main')

        # Ajout des sections
        self.create_section("Présentation générale", [
            "Les fonctionnalités sont regroupées en modules logiques et indépendants : détection, sauvegarde/restauration, supervision et gestion des utilisateurs.",
            "Le système repose sur des outils robustes : Nmap, Ansible, Paramiko, psutil, ipaddress, threading.",
            "Objectifs : automatisation, sécurité, clarté, et simplicité d’utilisation."
        ])

        self.create_section("Détection des sous-réseaux", [
            "• Identification automatique des plages d'adresses IPv4 locales.",
            "• Utilisation de `psutil` pour détecter les interfaces actives.",
            "• Génération de sous-réseaux via le module `ipaddress`.",
            "• Exportation possible des résultats au format JSON."
        ])

        self.create_section("Scan et découverte des équipements", [
            "• Analyse avec `Nmap` des sous-réseaux sélectionnés.",
            "• Identification des IP, hôtes et types de périphériques.",
            "• Mode rapide (ping) ou approfondi (scan ports).",
            "• Résultats affichés dans une table interactive."
        ])

        self.create_section("Identification des constructeurs", [
            "• Classement des équipements par fabricant (Cisco, MikroTik, Huawei...).",
            "• Exploitation des bannières de services et adresses MAC.",
            "• Exécution ciblée de commandes/playbooks par type."
        ])

        self.create_section("Sauvegarde des configurations", [
            "• Visualisation complète des équipements (IP, nom, constructeur, MAC...).",
            "• Indicateurs de disponibilité via `ping` et `ARP`.",
            "• Lecture des fichiers de configuration.",
            "• Mot de passe masqué, affichage contrôlé."
        ])

        self.create_section("Restauration des configurations", [
            "• Rétablissement rapide après panne.",
            "• Sélection intuitive des fichiers à restaurer.",
            "• Transmission sécurisée via `SSH/SCP` ou `Ansible`.",
            "• Vérification stricte : correspondance MAC-fichier."
        ])

        self.create_section("Automatisation des sauvegardes", [
            "• Planification flexible : jours, heures, minutes, secondes.",
            "• Exécution non bloquante via `threading.Timer`.",
            "• Compte à rebours dynamique et actualisé.",
            "• Empêche les sauvegardes simultanées."
        ])

        self.create_section("Supervision du système", [
            "• Tableau de bord en temps réel.",
            "• Suivi de l’état réseau, des sauvegardes/restaurations.",
            "• Vérification des services essentiels (FTP, SSH, etc.)."
        ])

        self.create_section("Paramètres d’interface", [
            "• Choix du thème (clair/sombre), langue, police.",
            "• Options graphiques et d’accessibilité personnalisables."
        ])

        self.create_section("Gestion des utilisateurs", [
            "• Création de comptes utilisateurs depuis l’interface.",
            "• Validation manuelle par l’administrateur principal.",
            "• Attribution de rôles :",
            "     - Utilisateur : accès restreint.",
            "     - Administrateur : accès total au système."
        ])

    def create_section(self, title, lignes):
        section = tk.LabelFrame(
            self.inner_frame,
            text=title,
            font=("Arial", 14, "bold"),
            bg=self.theme_manager.bg_main,
            fg=self.theme_manager.fg_main,
            bd=2,
            relief="groove",
            padx=10,
            pady=10
        )
        section.pack(fill="x", padx=20, pady=10)
        self.theme_manager.register_widget(section, 'bg_main', 'fg_main')

        for ligne in lignes:
            label = tk.Label(
                section,
                text=ligne,
                anchor="w",
                justify="left",
                wraplength=1000,
                font=("Arial", 12),
                bg=self.theme_manager.bg_main,
                fg=self.theme_manager.fg_main
            )
            label.pack(anchor="w", pady=3)
            self.theme_manager.register_widget(label, 'bg_main', 'fg_main')
