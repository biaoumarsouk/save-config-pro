import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime
from .composants.loading import run_with_loading
from PIL import Image, ImageTk
from .plannification import BackupSchedulerManager
import sys
import time


USERS_JSON_PATH = os.path.join(os.path.dirname(__file__), "files", "users.json")
os.makedirs(os.path.dirname(USERS_JSON_PATH), exist_ok=True)
DOSSIER_FICHIERS = os.path.join(os.path.dirname(__file__), 'files')
DOSSIER_PROFILS = os.path.join(DOSSIER_FICHIERS, 'profils')
os.makedirs(DOSSIER_FICHIERS, exist_ok=True)
os.makedirs(DOSSIER_PROFILS, exist_ok=True)


class UsersManager(tk.Frame):
    def __init__(self, parent, theme_manager):
        super().__init__(parent, bg=theme_manager.bg_main)
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main') 
        self.parent = parent
        self.users = {}
        self.backup_manager = BackupSchedulerManager()
        self.create_widgets()
        self.load_users()
        self.insert_data()

    def _arreter_sauvegarde(self):
        """Arrête proprement la sauvegarde"""
        try:
            if self.backup_manager.running:
                print("[DEBUG] Arrêt du service de sauvegarde...")
                self.backup_manager.stop()
                time.sleep(1)
                return True
        except Exception as e:
            print(f"[ERREUR] Arrêt sauvegarde: {str(e)}")
        return False

    def delete_account(self, username, top):
        """Gère la suppression d'un compte utilisateur"""
        if not messagebox.askyesno("Confirmation", f"Supprimer définitivement {username} ?"):
            return

        # Vérifier si c'est l'utilisateur actuellement connecté
        current_user = getattr(self.parent, 'current_user', None)
        is_current_user = current_user and current_user.get('username') == username

        # Supprimer l'utilisateur et son image
        self._perform_user_deletion(username)

        # Cas nécessitant un redémarrage
        if is_current_user or len(self.users) == 0:
            self._graceful_restart()
        else:
            # Mise à jour normale de l'interface
            self.insert_data()
            top.destroy()
            messagebox.showinfo("Succès", f"Utilisateur {username} supprimé.")

    def _perform_user_deletion(self, username):
        """Exécute la suppression des données utilisateur"""
        # Suppression de l'entrée utilisateur
        if username in self.users:
            del self.users[username]
        
        # Suppression de l'image de profil
        for ext in ['.png', '.jpg', '.jpeg']:
            img_path = os.path.join(DOSSIER_PROFILS, f"{username}{ext}")
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
            except Exception as e:
                print(f"Erreur suppression image: {e}")
        
        # Sauvegarde des modifications
        self.save_users()

    def _graceful_restart(self):
        """Redémarrage propre de l'application"""
        # Arrêt des services en cours
        if hasattr(self, 'backup_manager') and self.backup_manager.running:
            self._arreter_sauvegarde()
        
        # Fermeture de l'interface
        self.parent.destroy()
        
        # Redémarrage
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def create_widgets(self):
        # Titre principal
        title = tk.Label(
            self,
            text="\U0001F4BB Système de Gestion des Configurations Réseaux Informatiques",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=20)
        self.theme_manager.register_widget(title, 'bg_main', 'fg_main')

        title_sub = tk.Label(self, text="Gestion des comptes", font=("Arial", 16, "bold"))
        title_sub.pack(pady=10)
        self.theme_manager.register_widget(title_sub, 'bg_main', 'fg_main')


        self.table_frame = tk.Frame(self)
        self.table_frame.pack(pady=10)
        self.theme_manager.register_widget(self.table_frame, 'bg_main')

        self.columns = ("Utilisateurs", "Compte", "Rôle", "Statut")
        self.tree = ttk.Treeview(self.table_frame, columns=self.columns, show="headings", height=14)
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=273)

        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_user_select)

        status_bar = tk.Frame(self)
        status_bar.pack(pady=10)
        self.theme_manager.register_widget(status_bar, 'bg_main')

        self.user_count_var = tk.StringVar()
        self.update_user_count()

        count_label = tk.Label(status_bar, textvariable=self.user_count_var, font=("Arial", 10))
        count_label.pack(side=tk.LEFT, padx=10)
        self.theme_manager.register_widget(count_label, 'bg_main', 'fg_main')

    def update_user_count(self):
        total = len(self.users)
        active = sum(1 for u in self.users.values() if u.get('status', False))
        connected = sum(1 for u in self.users.values() if u.get('connexion', False))
        self.user_count_var.set(f"Utilisateurs: {total} | Actifs: {active} | Connectés: {connected}")

    def load_users(self):
        try:
            if os.path.exists(USERS_JSON_PATH):
                with open(USERS_JSON_PATH, "r", encoding="utf-8") as f:
                    self.users = json.load(f)
            else:
                self.users = {}
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger les utilisateurs:\n{e}")
            self.users = {}

    def save_users(self):
        try:
            with open(USERS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de sauvegarder:\n{e}")
            return False

    def insert_data(self):
        def task(update_progress):
            update_progress(10, "Chargement des utilisateurs...")
            rows = []
            for username, user_data in self.users.items():
                role = user_data.get("role", "utilisateur")
                account_status = "Activé" if user_data.get("status", False) else "Désactivé"
                login_status = "🟢 Connecté" if user_data.get("connexion", False) else "🔴 Déconnecté"
                rows.append((username, account_status, role.capitalize(), login_status))
            update_progress(100, "Fini")
            return rows

        def callback(rows):
            self.tree.delete(*self.tree.get_children())
            for row in rows:
                self.tree.insert("", tk.END, values=row)
            self.update_user_count()

        run_with_loading(self.parent, task, callback, self.theme_manager)

    def on_user_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        username = self.tree.item(selected[0])["values"][0]
        self.show_user_details(username)

    def show_user_details(self, username):
        user = self.users.get(username)
        if not user:
            messagebox.showerror("Erreur", "Utilisateur introuvable.")
            return

        top = tk.Toplevel(self)
        top.title(f"Détails de {username}")
        top.geometry("420x450")
        top.transient(self)
        top.resizable(False, False)
        top.after(10, lambda: top.grab_set())  # fenêtre modale

        top.configure(bg=self.theme_manager.bg_main)
        self.theme_manager.register_widget(top, 'bg_main')

        container = tk.Frame(top, bg=self.theme_manager.bg_main)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        self.theme_manager.register_widget(container, 'bg_main')

        # === Image de profil ===
        image_extensions = ['.png', '.jpg', '.jpeg']
        image_path = next((os.path.join(DOSSIER_PROFILS, f"{username}{ext}")
                        for ext in image_extensions if os.path.exists(os.path.join(DOSSIER_PROFILS, f"{username}{ext}"))),
                        os.path.join(DOSSIER_PROFILS, "default.png"))

        try:
            image = Image.open(image_path).resize((100, 100))
            photo = ImageTk.PhotoImage(image)
            img_label = tk.Label(container, image=photo, bg=self.theme_manager.bg_main)
            img_label.image = photo
            img_label.pack(pady=10)
            self.theme_manager.register_widget(img_label, 'bg_main')
        except Exception:
            lbl = tk.Label(container, text="Sans profil", bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main)
            lbl.pack(pady=10)
            self.theme_manager.register_widget(lbl, 'bg_main', 'fg_main')

        # === Nom ===
        tk.Label(container, text="Nom", bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main).pack(anchor="w")
        nom_var = tk.StringVar(value=user.get("nom", ""))
        nom_entry = tk.Entry(container, textvariable=nom_var, bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main)
        nom_entry.pack(fill=tk.X, pady=(0, 10))
        self.theme_manager.register_widget(nom_entry, 'bg_main', 'fg_main')

        # === Prénom ===
        tk.Label(container, text="Prénom", bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main).pack(anchor="w")
        prenom_var = tk.StringVar(value=user.get("prenom", ""))
        prenom_entry = tk.Entry(container, textvariable=prenom_var, bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main)
        prenom_entry.pack(fill=tk.X, pady=(0, 10))
        self.theme_manager.register_widget(prenom_entry, 'bg_main', 'fg_main')

        # === Rôle ===
        tk.Label(container, text="Rôle", bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main).pack(anchor="w", pady=(10, 0))
        role_var = tk.StringVar(value=user.get("role", "user"))
        role_frame = tk.Frame(container, bg=self.theme_manager.bg_main)
        role_frame.pack(pady=5)

        radio_user = tk.Radiobutton(role_frame, text="Utilisateur", variable=role_var, value="user",
                                    bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main,
                                    selectcolor=self.theme_manager.bg_main,
                                    activebackground=self.theme_manager.bg_hover,
                                    activeforeground=self.theme_manager.fg_main)
        radio_user.pack(side=tk.LEFT, padx=10)

        radio_admin = tk.Radiobutton(role_frame, text="Administrateur", variable=role_var, value="admin",
                                    bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main,
                                    selectcolor=self.theme_manager.bg_main,
                                    activebackground=self.theme_manager.bg_hover,
                                    activeforeground=self.theme_manager.fg_main)
        radio_admin.pack(side=tk.LEFT, padx=10)

        self.theme_manager.register_widget(role_frame, 'bg_main')
        self.theme_manager.register_widget(radio_user, 'bg_main', 'fg_main')
        self.theme_manager.register_widget(radio_admin, 'bg_main', 'fg_main')

        # === Boutons ===
        button_frame = tk.Frame(container, bg=self.theme_manager.bg_main)
        button_frame.pack(pady=20)
        self.theme_manager.register_widget(button_frame, 'bg_main')

        # === Fonction de mise à jour du bouton status ===
        status_button_text = tk.StringVar()
        def update_status_button():
            status_actuel = user.get("status", False)
            status_button_text.set("❌ Désactiver" if status_actuel else "✅ Activer")

        def save_changes():
            user["nom"] = nom_var.get()
            user["prenom"] = prenom_var.get()
            user["role"] = role_var.get()
            self.save_users()
            self.insert_data()
            messagebox.showinfo("Succès", "Modifications enregistrées.")

        def delete_account():
            if messagebox.askyesno("Confirmation", f"Supprimer {username} ?"):
                top.destroy()
                # Utiliser la nouvelle méthode de suppression
                self.delete_account(username, top)
                
        def toggle_account_status():
            user["status"] = not user.get("status", False)
            self.save_users()
            self.insert_data()
            update_status_button()
            statut_txt = "activé" if user["status"] else "désactivé"
            messagebox.showinfo("Statut modifié", f"Le compte a été {statut_txt}.")

        # === Boutons avec mise à jour dynamique ===
        btn_status = tk.Button(button_frame, textvariable=status_button_text, command=toggle_account_status,
                            bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main,
                            activebackground=self.theme_manager.bg_hover,
                            activeforeground=self.theme_manager.fg_main)
        btn_status.pack(side=tk.LEFT, padx=5)
        self.theme_manager.register_widget(btn_status, 'bg_main')

        btn_edit = tk.Button(button_frame, text="🖊️ Modifier", command=save_changes,
                            bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main,
                            activebackground=self.theme_manager.bg_hover,
                            activeforeground=self.theme_manager.fg_main)
        btn_edit.pack(side=tk.LEFT, padx=5)
        self.theme_manager.register_widget(btn_edit, 'bg_main')

        btn_delete = tk.Button(button_frame, text="🗑️ Supprimer", command=delete_account,
                            bg=self.theme_manager.bg_main, fg=self.theme_manager.fg_main,
                            activebackground=self.theme_manager.bg_hover,
                            activeforeground=self.theme_manager.fg_main)
        btn_delete.pack(side=tk.LEFT, padx=5)
        self.theme_manager.register_widget(btn_delete, 'bg_main')

        update_status_button()  # initialisation du texte du bouton




    def export_to_json(self):
        if not self.users:
            messagebox.showwarning("Avertissement", "Aucun utilisateur à exporter")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Fichier JSON", "*.json")],
            title="Exporter les utilisateurs",
            initialfile="utilisateurs_export.json"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Succès", f"Exporté avec succès :\n{file_path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de l'export :\n{e}")
