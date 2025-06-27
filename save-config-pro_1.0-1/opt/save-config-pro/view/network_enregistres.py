import tkinter as tk
from tkinter import ttk, messagebox,filedialog
import psutil
import ipaddress
import json
import os
from .composants.loading import run_with_loading

# Chemin du fichier JSON relatif au script
json_file_path = os.path.join(os.path.dirname(__file__), "files", "networks.json")
os.makedirs(os.path.dirname(json_file_path), exist_ok=True)

class SousReseauxEnregistres(tk.Frame):
    def __init__(self, parent, theme_manager):
        super().__init__(parent, bg=theme_manager.bg_main)
        self.theme_manager = theme_manager
        self.theme_manager.register_widget(self, 'bg_main')
        self.parent = parent
        self.saved_networks = []
        # Initialisation des variables
        self.device_count_var = tk.StringVar()
        self.device_count_var.set("Appareils détectés : 0")
        self.create_widgets()
        self.load_networks()
        self.insert_data()

    def create_widgets(self):
        """Crée les widgets principaux"""
        # Titre principal
        title = tk.Label(
            self,
            text="\U0001F4BB Système de Gestion des Configurations Réseaux Informatiques",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=20)
        self.theme_manager.register_widget(title, 'bg_main', 'fg_main')

        # Label du mode
        self.mode_label = tk.Label(
            self, 
            text="Tous les réseaux enregistrés", 
            font=("Arial", 14, "bold")
        )
        self.mode_label.pack(pady=10)
        self.theme_manager.register_widget(self.mode_label, 'bg_main', 'fg_main')

        # Frame du tableau
        self.table_frame = tk.Frame(self)
        self.table_frame.pack(pady=10)
        self.theme_manager.register_widget(self.table_frame, 'bg_main')

        # Treeview
        self.columns = ("Réseaux", "Interfaces", "Addresse IP", "Scan")
        self.tree = ttk.Treeview(self.table_frame, columns=self.columns, show="headings", height=14)
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=273)

        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.tree.pack()
        self.tree.bind("<Double-1>", self.on_select)

        # Frame de statut
        self.status_frame = tk.Frame(self)
        self.status_frame.pack(pady=20)
        self.theme_manager.register_widget(self.status_frame, 'bg_main')

        # Compteur d'appareils
        self.device_count_var = tk.StringVar()
        self.device_count_var.set("Appareils détectés : 0")
        
        count_label = tk.Label(
            self.status_frame,
            textvariable=self.device_count_var,
            font=("Arial", 14, "bold")
        )
        count_label.grid(row=0, column=0, padx=20)
        self.theme_manager.register_widget(count_label, 'bg_main', 'fg_main')

        # Statut système
        status_label = tk.Label(
            self.status_frame,
            text="État du système : OK",
            font=("Arial", 14, "bold")
        )
        status_label.grid(row=0, column=1, padx=20)
        self.theme_manager.register_widget(status_label, 'bg_main', 'fg_success')

        export_button = tk.Button(
            self,
            text="🖨️",
            background=self.theme_manager.bg_main,
            foreground=self.theme_manager.fg_main,
            activebackground=self.theme_manager.bg_hover,
            activeforeground=self.theme_manager.fg_main,
            relief="raised",
            cursor="hand2",
            command=self.export_to_json
        )
        export_button.place(relx=1.0, y=10, anchor="ne", x=-20)
        self.theme_manager.register_widget(export_button, 'bg_main', 'fg_main', 'bg_hover')
        

    def load_networks(self):
        if os.path.exists(json_file_path):
            with open(json_file_path, "r") as f:
                self.saved_networks = json.load(f)
        else:
            self.saved_networks = []

    def save_networks(self):
        with open(json_file_path, "w") as f:
            json.dump(self.saved_networks, f, indent=2)
        if hasattr(self.parent, "update_networks_from_json"):
            self.parent.update_networks_from_json()
    
    def insert_data(self):
        def task(update_progress):
            update_progress(10, "Scan des sous-réseaux...")

            interfaces = psutil.net_if_addrs()
            rows = []
            count = 0

            for interface_name, addrs in interfaces.items():
                for addr in addrs:
                    if addr.family.name == 'AF_INET' and addr.address != '127.0.0.1':
                        try:
                            ip_obj = ipaddress.IPv4Interface(f"{addr.address}/{addr.netmask}")
                            subnet = str(ip_obj.network)
                            if subnet in self.saved_networks:
                                icon = "✔️"
                                rows.append((subnet, interface_name, addr.address, icon))
                                count += 1
                            else:
                                continue  # Ne pas afficher si non enregistré
                        except Exception:
                            pass

            # Ajouter les réseaux enregistrés qui ne sont plus connectés
            all_current_subnets = [
                str(ipaddress.IPv4Interface(f"{a.address}/{a.netmask}").network)
                for addrs in interfaces.values()
                for a in addrs if a.family.name == 'AF_INET' and a.address != '127.0.0.1'
            ]

            for saved_subnet in self.saved_networks:
                if saved_subnet not in all_current_subnets:
                    rows.append((saved_subnet, "N/A", "N/A", "❌"))
                    count += 1

            update_progress(100, "Scan terminé.")
            return rows, count

        def callback(result):
            rows, count = result
            self.tree.delete(*self.tree.get_children())
            for row in rows:
                self.tree.insert("", "end", values=row)
            self.device_count_var.set(f"Appareils détectés : {count}")

        run_with_loading(
            content_frame=self.parent,
            task_function=task,
            callback=callback,
            theme_manager=self.theme_manager
        )

    def on_select(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        item_id = selected_item[0]
        values = self.tree.item(item_id)["values"]
        subnet = values[0]

        result = messagebox.askyesno("Supprimer", f"Voulez-vous supprimer le sous-réseau {subnet} ?")
        if result:
            if subnet in self.saved_networks:
                self.saved_networks.remove(subnet)
                self.save_networks()
                self.insert_data()
                messagebox.showinfo("Suppression", f"Sous-réseau {subnet} supprimé avec succès.")

    def export_to_json(self):
        # Confirmation avant export
        confirm = messagebox.askyesno("Export JSON", "Voulez-vous exporter les sous-réseaux enregistrés en JSON ?")
        if not confirm:
            return

        data = []
        for item_id in self.tree.get_children():
            values = self.tree.item(item_id)["values"]
            data.append({
                "network": values[0],
                "interface": values[1],
                "ip": values[2],
            })

        # Ouvrir une boîte de dialogue pour choisir où sauvegarder le fichier
        export_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Fichier JSON", "*.json")],
            title="Enregistrer sous",
            initialfile="networks_enregistrés.json"
        )

        if not export_path:
            return  # L'utilisateur a annulé

        try:
            with open(export_path, "w") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Export réussi", f"Export effectué avec succès dans :\n{export_path}")
        except Exception as e:
            messagebox.showerror("Erreur export", f"Une erreur est survenue lors de l'export :\n{e}")