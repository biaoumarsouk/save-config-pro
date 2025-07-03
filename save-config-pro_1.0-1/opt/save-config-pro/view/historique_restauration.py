import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from datetime import datetime
import re

class HistoriqueRestauration(tk.Frame):
    def __init__(self, parent, theme_manager):
        super().__init__(parent, bg=theme_manager.bg_main)
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main')
        self.parent = parent
        self.log_path = os.path.join(os.path.dirname(__file__), "files", "restauration.json")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

        self.detail_window = None  # Pour bloquer ouverture multiple
        self.create_widgets()
        self.load_history()

    def create_widgets(self):
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # === Haut ===
        top_frame = tk.Frame(self)
        top_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 0))
        top_frame.grid_columnconfigure(0, weight=1)
        self.theme_manager.register_widget(top_frame, 'bg_main')

        center_frame = tk.Frame(top_frame)
        center_frame.grid(row=0, column=0, sticky="n")
        self.theme_manager.register_widget(center_frame, 'bg_main')

        title = tk.Label(
            center_frame,
            text="\U0001F4BB Système de Gestion des Configurations Réseaux Informatiques",
            font=("Arial", 16, "bold")
        )
        title.pack()
        self.theme_manager.register_widget(title, 'bg_main', 'fg_main')

        self.mode_label = tk.Label(
            center_frame,
            text="Historique des Restaurations",
            font=("Arial", 14, "bold")
        )
        self.mode_label.pack(pady=5)
        self.theme_manager.register_widget(self.mode_label, 'bg_main', 'fg_main')

        # === Bouton emoji supprimer tout ===
        btn_clear_all = tk.Button(
            top_frame,
            text="🗑️",
            font=("Arial", 12, "bold"),
            fg="white",
            width=2,
            command=self.supprimer_tout
        )
        btn_clear_all.grid(row=0, column=1, sticky="e", padx=10)
        self.theme_manager.register_widget(btn_clear_all, 'bg_main')

        # === Centre : Treeview ===
        self.table_frame = tk.Frame(self)
        self.table_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.theme_manager.register_widget(self.table_frame, 'bg_main')

        self.columns = ("Utilisateur", "Date d'exécution", "Date du fichier", "MAC", "Fichier utilisé")
        self.tree = ttk.Treeview(self.table_frame, columns=self.columns, show="headings")

        col_widths = {
            "Utilisateur": 100,
            "Date d'exécution": 140,
            "Date du fichier": 140,
            "MAC": 140,
            "Fichier utilisé": 200
        }

        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths[col], anchor="center")

        self.scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind('<Double-1>', self.on_row_click)

    def extract_date_from_filename(self, filename):
        """Extrait la date du nom de fichier"""
        try:
            # Recherche le motif de date dans le nom de fichier
            match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', filename)
            if match:
                date_str = f"{match.group(1)} {match.group(2).replace('-', ':')}"
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
            return "N/A"
        except:
            return "N/A"

    def load_history(self):
        try:
            with open(self.log_path, 'r') as f:
                history_data = json.load(f)

            self.tree.delete(*self.tree.get_children())

            for entry in history_data:
                user = entry.get("username", "N/A")
                date_execution = entry.get("date_execution", "N/A")
                fichier_utilise = entry.get("fichiers_utilises", "N/A")
                mac = entry.get("equipement", {}).get("mac", "N/A")  # Note: il y avait une faute de frappe dans votre JSON ("equipement" au lieu de "equipement")
                
                try:
                    date_execution = datetime.strptime(date_execution, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                except:
                    date_execution = "N/A"
                
                date_fichier = self.extract_date_from_filename(fichier_utilise)

                self.tree.insert("", "end", values=(
                    user, 
                    date_execution, 
                    date_fichier, 
                    mac, 
                    fichier_utilise
                ), tags=('entry',))

        except FileNotFoundError:
            print("Fichier d'historique non trouvé.")
        except json.JSONDecodeError:
            print("Erreur de lecture JSON.")

    def on_row_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return

        self.tree.selection_set(item)
        values = self.tree.item(item, 'values')
        if not values or len(values) < 2:
            return

        utilisateur = values[0]
        date_execution_str = values[1]

        try:
            date_execution = datetime.strptime(date_execution_str, "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print("Erreur format date:", e)
            return

        try:
            with open(self.log_path, 'r') as f:
                history = json.load(f)
        except Exception as e:
            print("Erreur lecture fichier:", e)
            history = []

        for entry in history:
            entry_date = entry.get("date_execution", "")
            if (entry.get("username") == utilisateur and 
                entry_date.startswith(date_execution[:16])):
                self.open_detail_window(entry)
                break

    def open_detail_window(self, entry):
        if self.detail_window is not None and self.detail_window.winfo_exists():
            self.detail_window.lift()
            return

        self.detail_window = tk.Toplevel(self)
        top = self.detail_window
        top.title("Détails de la restauration")
        top.geometry("600x300")
        top.transient(self.winfo_toplevel())
        top.after(100, lambda: top.grab_set())
        self.theme_manager.register_widget(top, 'bg_main')

        top.grid_rowconfigure(0, weight=0)
        top.grid_rowconfigure(1, weight=1)
        top.grid_columnconfigure(0, weight=1)

        frame_infos = tk.Frame(top)
        frame_infos.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.theme_manager.register_widget(frame_infos, 'bg_main')

        for i in range(5):
            frame_infos.grid_columnconfigure(i, weight=1)

        equipement = entry.get("equipement", {})
        date_fichier = self.extract_date_from_filename(entry.get("fichiers_utilises", ""))

        infos = [
            ("Utilisateur", entry.get("username", "N/A")),
            ("Date Exécution", self.format_date(entry.get("date_execution"))),
            ("Date Fichier", date_fichier),
            ("Type Opération", entry.get("type_operation", "N/A")),
        ]

        for idx, (label, value) in enumerate(infos):
            f = tk.Frame(frame_infos)
            f.grid(row=0, column=idx, sticky="nsew", padx=5)
            self.theme_manager.register_widget(f, 'bg_main')

            lbl1 = tk.Label(f, text=label, font=("Arial", 9, "bold"))
            lbl2 = tk.Label(f, text=value, font=("Arial", 9))
            lbl1.pack()
            lbl2.pack()
            self.theme_manager.register_widget(lbl1, 'bg_main', 'fg_main')
            self.theme_manager.register_widget(lbl2, 'bg_main', 'fg_main')

        eq_frame = tk.Frame(top)
        eq_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.theme_manager.register_widget(eq_frame, 'bg_main')

        eq_frame.grid_rowconfigure(0, weight=1)
        eq_frame.grid_columnconfigure(0, weight=1)

        columns = ("Nom", "Adresse MAC", "IP", "Type")
        tree = ttk.Treeview(eq_frame, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="center")

        scrollbar = ttk.Scrollbar(eq_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        equipement = entry.get("equipement", {})
        tree.insert("", "end", values=(
            equipement.get('name', 'N/A'), 
            equipement.get('mac', 'N/A'),
            equipement.get('ip', 'N/A'),
            equipement.get('type', 'N/A')
        ))

        # === Bouton supprimer cette sauvegarde ===
        btn_supprimer = tk.Button(
            top,
            text="🗑️ Supprimer cette entrée",
            font=("Arial", 10, "bold"),
            command=lambda: self.supprimer_sauvegarde(entry, top)
        )
        btn_supprimer.grid(row=2, column=0, sticky="e", padx=10, pady=(0, 10))
        self.theme_manager.register_widget(btn_supprimer, 'bg_main','fg_main','bg_hover')

    def supprimer_sauvegarde(self, entry, window):
        if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer cette entrée ?"):
            return
        try:
            with open(self.log_path, 'r') as f:
                history = json.load(f)

            history = [
                e for e in history
                if not (e.get("date_execution") == entry.get("date_execution") and
                        e.get("username") == entry.get("username"))
            ]

            with open(self.log_path, 'w') as f:
                json.dump(history, f, indent=4)

            window.destroy()
            self.detail_window = None  # Réinitialiser pour permettre réouverture
            self.load_history()

        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de supprimer : {e}")

    def supprimer_tout(self):
        if not messagebox.askyesno("Confirmation", "Supprimer tout l'historique des restaurations ?"):
            return
        try:
            with open(self.log_path, 'w') as f:
                json.dump([], f)
            self.load_history()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de supprimer l'historique : {e}")

    def format_date(self, date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        except:
            return "N/A"