import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime

DOSSIER_FICHIERS = os.path.join(os.path.dirname(__file__), 'files')
FICHIER_HISTORIQUE = os.path.join(DOSSIER_FICHIERS, 'historique_users.json')


class HistoriqueUsers(tk.Frame):
    def __init__(self, parent, theme_manager):
        super().__init__(parent, bg=theme_manager.bg_main)
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main')
        self.parent = parent
        self.historique = []

        self.create_widgets()
        self.load_historique()
        self.insert_data()

    def create_widgets(self):
        """Widgets de l'historique de connexion avec layout grid responsive"""

        # Configuration de la fenêtre principale
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=0)  # Sous-titre
        self.grid_rowconfigure(2, weight=1)  # Tableau
        self.grid_columnconfigure(0, weight=1)

        # === En-tête avec titre et boutons
        header_frame = tk.Frame(self, bg=self.theme_manager.bg_main)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        header_frame.grid_columnconfigure(0, weight=1)  # Titre extensible
        header_frame.grid_columnconfigure(1, weight=0)  # Boutons
        self.theme_manager.register_widget(header_frame, 'bg_main', 'fg_main')

        # Titre principal à gauche
        title = tk.Label(
            header_frame,
            text="\U0001F4BB Système de Gestion des Configurations Réseaux Informatiques",
            font=("Arial", 16, "bold"),
            bg=self.theme_manager.bg_main
        )
        title.grid(row=0, column=0, sticky="ew", pady=10)
        self.theme_manager.register_widget(title, 'bg_main', 'fg_main')

        # Boutons d'action à droite
        btn_frame = tk.Frame(header_frame, bg=self.theme_manager.bg_main)
        btn_frame.grid(row=0, column=1, sticky="e")
        self.theme_manager.register_widget(btn_frame, 'bg_main', 'fg_main')

        btn_export = tk.Button(btn_frame, text="📤", command=self.exporter_historique, font=("Arial", 14), bd=0)
        btn_export.pack(side="right", padx=5)
        self.theme_manager.register_widget(btn_export, 'bg_main', 'fg_main')

        btn_supprimer = tk.Button(btn_frame, text="🗑️", command=self.supprimer_tout, font=("Arial", 14), bd=0)
        btn_supprimer.pack(side="right", padx=5)
        self.theme_manager.register_widget(btn_supprimer, 'bg_main', 'fg_main')

        # === Sous-titre centré
        title_sub = tk.Label(self, text="Historique des Connexions", font=("Arial", 16, "bold"))
        title_sub.grid(row=1, column=0, pady=(5, 10))
        self.theme_manager.register_widget(title_sub, 'bg_main', 'fg_main')

        # === Tableau
        self.table_frame = tk.Frame(self)
        self.table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.theme_manager.register_widget(self.table_frame, 'bg_main')

        # Nouvelle colonne "Action" ajoutée
        self.columns = ("Utilisateur", "Date de Connexion", "Date de Déconnexion", "Action", "Autorisation")
        self.tree = ttk.Treeview(self.table_frame, columns=self.columns, show="headings")
        
        # Configuration des colonnes
        col_widths = [150, 180, 180, 80, 100]  # Largeurs ajustées pour la nouvelle colonne
        for col, width in zip(self.columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center", stretch=False)

        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.tag_configure('refuse', foreground="red")
        self.tree.bind("<Configure>", self.adjust_column_widths)
        self.tree.bind("<Double-1>", self.supprimer_ligne_selectionnee)

    def adjust_column_widths(self, event):
        total_width = event.width - 20  # Marge pour la barre de défilement
        col_count = len(self.columns)
        if col_count > 0:
            for col in self.columns:
                self.tree.column(col, width=int(total_width / col_count))

    def load_historique(self):
        if os.path.exists(FICHIER_HISTORIQUE):
            with open(FICHIER_HISTORIQUE, "r") as f:
                try:
                    self.historique = json.load(f)
                except json.JSONDecodeError:
                    self.historique = []

    def insert_data(self):
        self.tree.delete(*self.tree.get_children())  # vide le tableau avant insertion
        for item in self.historique:
            utilisateur = item.get("utilisateur", "")
            date_conn = item.get("date_connexion", "") or "—"
            date_deconn = item.get("date_deconnexion", "") or "—"
            
            # Détermine le type d'action
            if date_conn != "—" and date_deconn == "—":
                action = "Entrée"
            elif date_deconn != "—":
                action = "Sortie"
            else:
                action = "—"  # Cas par défaut

            autorisation = "Refusée" if item.get("tentative", False) else "Autorisée"
            tag = ('refuse',) if item.get("tentative", False) else ()

            self.tree.insert("", tk.END, 
                            values=(utilisateur, date_conn, date_deconn, action, autorisation), 
                            tags=tag)

    def supprimer_tout(self):
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer tout l'historique ?"):
            self.historique = []
            with open(FICHIER_HISTORIQUE, "w") as f:
                json.dump(self.historique, f, indent=4)
            self.insert_data()

    def supprimer_ligne_selectionnee(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        
        valeurs = self.tree.item(item_id, "values")
        if not valeurs or len(valeurs) < 5:  # Vérifie qu'on a bien une ligne valide
            return
        
        utilisateur, date_entree, date_sortie, action, statut = valeurs
        
        # Message personnalisé selon le type d'action
        if messagebox.askyesno(
            "Confirmer la suppression",
            f"Voulez-vous vraiment supprimer l'enregistrement de {action.lower()} de {utilisateur} du {date_entree if action == 'Entrée' else date_sortie} ?",
            icon='question'
        ):
            # Filtre l'historique pour supprimer l'entrée correspondante
            self.historique = [
                h for h in self.historique
                if not (
                    h.get("utilisateur") == utilisateur and 
                    (
                        (action == "Entrée" and h.get("date_connexion") == date_entree) or
                        (action == "Sortie" and h.get("date_deconnexion") == date_sortie)
                    )
                )
            ]
            
            # Sauvegarde les modifications
            try:
                with open(FICHIER_HISTORIQUE, "w", encoding='utf-8') as f:
                    json.dump(self.historique, f, indent=4, ensure_ascii=False)
                self.insert_data()
            except IOError as e:
                messagebox.showerror("Erreur", f"Impossible de sauvegarder les modifications: {str(e)}")

    def exporter_historique(self):
        if not self.historique:
            messagebox.showinfo("Aucun historique", "Aucune donnée à exporter.")
            return

        fichier = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")],
            title="Exporter l'historique"
        )
        if fichier:
            try:
                with open(fichier, "w", encoding='utf-8') as f:
                    json.dump(self.historique, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("Exportation réussie", f"Historique exporté avec succès vers:\n{fichier}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Échec de l'exportation:\n{str(e)}")