import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import os
import json
from tkinter import ttk

DOSSIER_FICHIERS = os.path.join(os.path.dirname(__file__), '..', 'files')
FICHIER_UTILISATEURS = os.path.join(DOSSIER_FICHIERS, 'users.json')

class BarreHaut(tk.Frame):
    def __init__(self, root, theme_manager, username, dossier_profils):
        super().__init__(root, height=65)
        self.root = root
        self.theme_manager = theme_manager

        # Enregistrer ce frame dans le theme_manager
        self.theme_manager.register_widget(self, 'bg_secondary')
        self.pack(fill="x", side="top")

        # Charger les données utilisateur
        nom, prenom, role = self.get_user_info(username)
        role_affiche = "Administrateur" if role == "admin" else "Utilisateur"

        # Conteneur principal
        main_frame = tk.Frame(self, bg=self.theme_manager.bg_secondary)
        main_frame.pack(fill="x", expand=True)
        self.theme_manager.register_widget(main_frame, 'bg_secondary')

        # === Gauche : Bienvenue NOM
        left_frame = tk.Frame(main_frame, bg=self.theme_manager.bg_secondary)
        left_frame.pack(side="left", padx=20)

        # le logo

        # === Droite : rôle + nom/prénom en petit + image cercle
        right_frame = tk.Frame(main_frame, bg=self.theme_manager.bg_secondary)
        right_frame.pack(side="right", padx=10)
        self.theme_manager.register_widget(right_frame, 'bg_secondary')

        # Sous-frame pour rôle + nom/prénom
        infos_frame = tk.Frame(right_frame, bg=self.theme_manager.bg_secondary)
        infos_frame.pack(side="right", padx=10, anchor="e")
        self.theme_manager.register_widget(infos_frame, 'bg_secondary')

        label_role = tk.Label(
            infos_frame,
            text=role_affiche,
            font=("Helvetica", 12),
            bg=self.theme_manager.bg_secondary
        )
        label_role.pack(side="top", anchor="e")
        self.theme_manager.register_widget(label_role, 'bg_secondary', 'fg_main')

        label_nom_prenom = tk.Label(
            infos_frame,
            text=f"{prenom} {nom.upper()}",
            font=("Helvetica", 8, "italic"),
            bg=self.theme_manager.bg_secondary
        )
        label_nom_prenom.pack(side="top", anchor="e")
        self.theme_manager.register_widget(label_nom_prenom, 'bg_secondary', 'fg_main')

        # Image circulaire
        self.canvas = tk.Canvas(
            right_frame,
            width=40,
            height=40,
            bg=self.theme_manager.bg_secondary,
            highlightthickness=0
        )
        self.canvas.pack(side="right")
        self.theme_manager.register_widget(self.canvas, 'bg_secondary')

        image_path = self.trouver_image_profil(username, dossier_profils)
        self.photo_cercle = self.creer_image_cercle(image_path)
        self.canvas.create_image(20, 20, image=self.photo_cercle)

        # Séparateur en bas
        self.separator = tk.Frame(self, height=0.1, bg=self.theme_manager.separator)
        self.separator.pack(fill='x', side='bottom')
        self.theme_manager.register_widget(self.separator, 'separator')

    def get_user_info(self, username):
        """Charge les infos de l'utilisateur depuis users.json"""
        if not os.path.exists(FICHIER_UTILISATEURS):
            return "", "", "user"

        try:
            with open(FICHIER_UTILISATEURS, "r") as f:
                users = json.load(f)
                user_data = users.get(username)
                if user_data:
                    nom = user_data.get("nom", "")
                    prenom = user_data.get("prenom", "")
                    role = user_data.get("role", "user")
                    return nom, prenom, role
        except Exception as e:
            print(f"Erreur lecture fichier utilisateur : {e}")

        return "", "", "user"

    def trouver_image_profil(self, username, dossier):
        for ext in ['.png', '.jpg', '.jpeg']:
            path = os.path.join(dossier, f"{username}{ext}")
            if os.path.exists(path):
                return path
        return os.path.join(dossier, "default.png")

    def creer_image_cercle(self, path_img):
        """Crée une image circulaire à partir d'un chemin"""
        try:
            img = Image.open(path_img).resize((40, 40)).convert("RGBA")
        except Exception:
            img = Image.new("RGBA", (40, 40), (150, 150, 150, 255))  # gris par défaut

        # Création du masque circulaire
        masque = Image.new('L', (40, 40), 0)
        draw = ImageDraw.Draw(masque)
        draw.ellipse((0, 0, 40, 40), fill=255)
        img.putalpha(masque)

        cercle = Image.new("RGBA", (40, 40))
        cercle.paste(img, (0, 0), img)
        return ImageTk.PhotoImage(cercle)
