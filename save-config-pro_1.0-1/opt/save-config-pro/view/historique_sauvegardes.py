import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from datetime import datetime

class HistoriqueSauvegarde(tk.Frame):
    def __init__(self, parent, theme_manager):
        super().__init__(parent, bg=theme_manager.bg_main)
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main')
        self.parent = parent
        self.log_path = os.path.join(os.path.dirname(__file__), "files", "operation_sauvegarde.json")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

        self.detail_window = None  # 🔒 Pour bloquer ouverture multiple
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
            text="Historique des Sauvegardes",
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

        self.columns = ("Utilisateur", "Date Début", "Date Fin", "Nb Équipements", "Statut", "Cycle")
        self.tree = ttk.Treeview(self.table_frame, columns=self.columns, show="headings")

        col_widths = {
            "Utilisateur": 100,
            "Date Début": 140,
            "Date Fin": 140,
            "Nb Équipements": 90,
            "Statut": 90,
            "Cycle": 80
        }

        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_widths[col], anchor="center")

        self.scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind('<Double-1>', self.on_row_click)

    def load_history(self):
        try:
            with open(self.log_path, 'r') as f:
                history_data = json.load(f)

            self.tree.delete(*self.tree.get_children())

            for entry in history_data:
                user = entry.get("utilisateur", "N/A")
                date_debut = entry.get("date_debut", "N/A")
                date_fin = entry.get("date_fin", "N/A")
                nb_equipements = len(entry.get("equipements", []))
                status = entry.get("status", "N/A")
                cycle = entry.get("intervalle", "N/A")

                try:
                    date_debut = datetime.strptime(date_debut, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                    if date_fin and date_fin.lower() != "null":
                        date_fin = datetime.strptime(date_fin, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
                    else:
                        date_fin = "En cours"
                except:
                    pass

                status_display = {
                    "en_cours": "En cours",
                    "succes": "Succès",
                    "echec": "Échec"
                }.get(status.lower(), status.capitalize())

                self.tree.insert("", "end", values=(
                    user, date_debut, date_fin, nb_equipements, status_display, cycle
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
        date_debut_str = values[1]

        try:
            date_debut = datetime.strptime(date_debut_str, "%d/%m/%Y %H:%M").strftime("%Y-%m-%d %H:%M:%S")
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
            entry_date = entry.get("date_debut", "")
            if (entry.get("utilisateur") == utilisateur and 
                entry_date.startswith(date_debut[:16])):
                self.open_detail_window(entry)
                break

    def open_detail_window(self, entry):
        if self.detail_window is not None and self.detail_window.winfo_exists():
            self.detail_window.lift()
            return

        self.detail_window = tk.Toplevel(self)
        top = self.detail_window
        top.title("Détails de la sauvegarde")
        top.geometry("700x400")
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

        infos = [
            ("Utilisateur", entry.get("utilisateur", "N/A")),
            ("Date Début", self.format_date(entry.get("date_debut"))),
            ("Date Fin", self.format_date(entry.get("date_fin"))),
            ("Cycle", entry.get("intervalle", "N/A")),
            ("Statut", self.format_status(entry.get("status")))
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

        columns = ("Nom", "Adresse MAC")
        tree = ttk.Treeview(eq_frame, columns=columns, show="headings")
        tree.heading("Nom", text="Nom")
        tree.heading("Adresse MAC", text="Adresse MAC")
        tree.column("Nom", width=200, anchor="center")
        tree.column("Adresse MAC", width=200, anchor="center")

        scrollbar = ttk.Scrollbar(eq_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        for eq in entry.get("equipements", []):
            tree.insert("", "end", values=(eq.get('name', 'N/A'), eq.get('mac', 'N/A')))

        # === Bouton supprimer cette sauvegarde ===
        btn_supprimer = tk.Button(
            top,
            text="🗑️ Supprimer cette sauvegarde",
            font=("Arial", 10, "bold"),
            bg="#ff4d4d",
            fg="white",
            command=lambda: self.supprimer_sauvegarde(entry, top)
        )
        btn_supprimer.grid(row=2, column=0, sticky="e", padx=10, pady=(0, 10))
        self.theme_manager.register_widget(btn_supprimer, 'bg_main')

    def supprimer_sauvegarde(self, entry, window):
        if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer cette sauvegarde ?"):
            return
        try:
            with open(self.log_path, 'r') as f:
                history = json.load(f)

            history = [
                e for e in history
                if not (e.get("date_debut") == entry.get("date_debut") and
                        e.get("utilisateur") == entry.get("utilisateur"))
            ]

            with open(self.log_path, 'w') as f:
                json.dump(history, f, indent=4)

            window.destroy()
            self.detail_window = None  # 🔄 Réinitialiser pour permettre réouverture
            self.load_history()

        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de supprimer : {e}")

    def supprimer_tout(self):
        if not messagebox.askyesno("Confirmation", "Supprimer tout l'historique des sauvegardes ?"):
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
            return "En cours"

    def format_status(self, status):
        return {
            "en_cours": "En cours",
            "succes": "Succès",
            "echec": "Échec"
        }.get(status.lower(), status.capitalize())
