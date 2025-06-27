import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import json, os, hashlib, datetime, shutil
from PIL import Image, ImageTk

# Configuration des dossiers
DOSSIER_FICHIERS = os.path.join(os.path.dirname(__file__), 'files')
DOSSIER_PROFILS = os.path.join(DOSSIER_FICHIERS, 'profils')
os.makedirs(DOSSIER_FICHIERS, exist_ok=True)
os.makedirs(DOSSIER_PROFILS, exist_ok=True)
FICHIER_UTILISATEURS = os.path.join(DOSSIER_FICHIERS, 'users.json')

class AdminCreationFrame(tk.Frame):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.parent = parent
        self.on_success = on_success
        self.chemin_image_profil = None
        self.photo_img = None
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.create_widgets()
        self.show_welcome_screen()

    def create_widgets(self):
        self.bg_color = "#f5f5f5"
        self.frame_color = "#ffffff"
        self.text_color = "#333333"
        self.accent_color = "#1c2333"
        self.border_color = "#d5d5d5"
        
        self.configure(bg=self.bg_color)
        self.pack(expand=True, fill="both")
        
        # Conteneur principal
        self.main_frame = tk.Frame(self, bg=self.bg_color)
        self.main_frame.pack(expand=True, fill="both")
        
        # Frame de bienvenue
        self.welcome_frame = tk.Frame(self.main_frame, bg="#1c2333")
        
        # Frame du formulaire
        self.form_frame = tk.Frame(self.main_frame, bg=self.frame_color, 
                                 padx=60, pady=50, 
                                 highlightthickness=1, 
                                 highlightbackground=self.border_color)
        
        # Frame de succès
        self.success_frame = tk.Frame(self, bg=self.bg_color, padx=40, pady=40)

    def show_welcome_screen(self):
        self.welcome_frame.pack(expand=True, fill="both")
        
        tk.Label(self.welcome_frame, text="Bienvenue !", 
                font=("Helvetica", 36, "bold"), 
                fg="white", bg="#1c2333").pack(pady=(200, 20))
        
        tk.Label(self.welcome_frame, 
                text="Système de Gestion des Configurations Réseaux Informatiques", 
                font=("Helvetica", 24), 
                fg="white", bg="#1c2333").pack(pady=20)
        
        self.after(5000, self.init_admin_creation_ui)

    def init_admin_creation_ui(self):
        self.welcome_frame.pack_forget()
        
        tk.Label(self.main_frame, 
                text="Création du compte administrateur principal", 
                font=("Helvetica", 24, "bold"), 
                fg=self.text_color, bg=self.bg_color).pack(pady=(20, 50))
        
        self.form_frame.pack(ipadx=20, ipady=20)
        
        self.current_step = 0
        self.labels = ["Nom", "Prénom", "Identifiant", "Mot de passe", "Photo de profil"]
        self.values = {}
        
        self.setup_navigation()
        self.setup_current_step()

    def setup_navigation(self):
        self.step_label = tk.Label(self.form_frame, 
                                 text=f"Étape {self.current_step+1}/{len(self.labels)}", 
                                 font=("Helvetica", 14), 
                                 fg="#666666", bg=self.frame_color)
        self.step_label.pack(pady=(0, 20))
        
        self.content_frame = tk.Frame(self.form_frame, bg=self.frame_color)
        self.content_frame.pack(fill="x", pady=10)
        
        self.button_frame = tk.Frame(self.form_frame, bg=self.frame_color)
        self.button_frame.pack(pady=20)
        
        self.button_prev = tk.Button(self.button_frame, 
                                   text="← Précédent", 
                                   command=self.precedent,
                                   font=("Helvetica", 14, "bold"), 
                                   bg="#cccccc", fg="black", bd=0, 
                                   padx=30, pady=10)
        self.button_prev.grid(row=0, column=0, padx=10)
        
        self.button_next = tk.Button(self.button_frame, 
                                   text="Suivant  →", 
                                   command=self.suivant,
                                   font=("Helvetica", 14, "bold"), 
                                   bg=self.accent_color, fg="white", 
                                   bd=0, padx=30, pady=10)
        self.button_next.grid(row=0, column=1, padx=10)
        
        self.bind("<Return>", lambda e: self.suivant())

    def setup_current_step(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        frame_color = "#ffffff"

        if self.current_step < len(self.labels) - 1:
            self.field_label = tk.Label(self.content_frame, text=self.labels[self.current_step], font=("Helvetica", 16), fg="#333333", bg=frame_color)
            self.field_label.pack()

            self.entry_field = tk.Entry(self.content_frame, font=("Helvetica", 14), width=40, bg="#ffffff", fg="#333333", insertbackground="#333333", relief="solid", bd=1)
            self.entry_field.pack(pady=20, ipadx=15, ipady=12)
            self.entry_field.focus()

            if self.labels[self.current_step] == "Mot de passe":
                self.entry_field.config(show="•")
            else:
                self.entry_field.config(show="")
        else:
            self.avatar_frame = tk.Frame(self.content_frame, bg=frame_color)
            self.avatar_frame.pack(expand=True, pady=20)

            self.avatar_label = tk.Label(self.avatar_frame, text="👤", font=("Helvetica", 72), bg=frame_color)
            self.avatar_label.pack(pady=20)

            self.btn_select_photo = tk.Button(self.avatar_frame, text="Sélectionner une photo", command=self.select_profile_picture, font=("Helvetica", 12), bg="#1c2333", fg="white", bd=0, padx=20, pady=8)
            self.btn_select_photo.pack(pady=10)

            self.lbl_file = tk.Label(self.avatar_frame, text="", font=("Helvetica", 10), fg="#666666", bg=frame_color)
            self.lbl_file.pack(pady=5)

    def select_profile_picture(self):
        filetypes = (("Images", "*.jpg *.jpeg *.png"), ("Tous les fichiers", "*.*"))
        filename = filedialog.askopenfilename(title="Sélectionner une photo de profil", initialdir="/", filetypes=filetypes)
        if filename:
            try:
                img = Image.open(filename)
                img.thumbnail((200, 200))
                self.photo_img = ImageTk.PhotoImage(img)
                self.avatar_label.config(image=self.photo_img, text="")
                self.chemin_image_profil = filename
                self.lbl_file.config(text=os.path.basename(filename))
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de charger l'image: {str(e)}")

    def suivant(self):
        if self.current_step < len(self.labels) - 1:
            value = self.entry_field.get().strip()
            if not value:
                messagebox.showwarning("Champ vide", "Veuillez remplir ce champ.")
                return
        else:
            value = "profile_set"

        key = self.labels[self.current_step].lower().replace(" ", "_")
        self.values[key] = value

        self.current_step += 1
        if self.current_step < len(self.labels):
            self.step_label.config(text=f"Étape {self.current_step+1}/{len(self.labels)}")
            self.setup_current_step()
            if self.current_step == len(self.labels) - 1:
                self.button_next.config(text="Créer le compte  ✓")
            else:
                self.button_next.config(text="Suivant  →")
        else:
            self.creer_admin()

    def precedent(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.step_label.config(text=f"Étape {self.current_step+1}/{len(self.labels)}")
            self.setup_current_step()
            if self.current_step < len(self.labels) - 1:
                self.button_next.config(text="Suivant  →")

    def creer_admin(self):
        nom = self.values.get("nom")
        prenom = self.values.get("prénom")
        identifiant = self.values.get("identifiant")
        password = self.values.get("mot_de_passe")

        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        user_data = {
            "nom": nom,
            "prenom": prenom,
            "password": hashed_pw,
            "status": True,
            "role": "admin",
            "connexion": False,
            "date_creation": now,
            "derniere_connexion": None,
            "photo_profil":"default.png"
        }

        if self.chemin_image_profil:
            ext = os.path.splitext(self.chemin_image_profil)[1]
            nouveau_nom = f"{identifiant}{ext}"
            chemin_destination = os.path.join(DOSSIER_PROFILS, nouveau_nom)
            try:
                shutil.copy2(self.chemin_image_profil, chemin_destination)
                user_data["photo_profil"] = nouveau_nom
            except Exception as e:
                messagebox.showwarning("Avertissement", f"Erreur lors de la copie de l'image: {str(e)}")
        # Pas besoin d'ajouter "photo_profil": "default.png" si aucune image n'est sélectionnée

        data = {identifiant: user_data}

        try:
            with open(FICHIER_UTILISATEURS, 'w') as f:
                json.dump(data, f, indent=4)
            self.show_success_screen()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de créer le compte: {str(e)}")

    def show_success_screen(self):
        self.main_frame.pack_forget()
        bg_color = "#d5d5d5"
        frame_color = "#ffffff"
        accent_color = "#192134"

        success_frame = tk.Frame(self, bg=bg_color, padx=40, pady=40)
        success_frame.place(relx=0.5, rely=0.5, anchor="center")

        content_frame = tk.Frame(success_frame, bg=frame_color, padx=60, pady=50, highlightthickness=1, highlightbackground="#d5d5d5")
        content_frame.pack(ipadx=20, ipady=20)

        tk.Label(content_frame, text="✓", font=("Helvetica", 72), fg=accent_color, bg=frame_color).pack(pady=20)
        tk.Label(content_frame, text="Compte administrateur créé avec succès", font=("Helvetica", 18, "bold"), fg="#333333", bg=frame_color).pack(pady=10)

        nom = self.values.get("nom")
        prenom = self.values.get("prénom")

        tk.Label(content_frame, text=f"Bienvenue, {prenom} {nom} !", font=("Helvetica", 16), fg="#666666", bg=frame_color).pack(pady=10)
        tk.Label(content_frame, text="Vous êtes maintenant l'administrateur principal du système.", font=("Helvetica", 14), fg="#666666", bg=frame_color, wraplength=400).pack(pady=20)

        tk.Button(content_frame, text="Terminer", command=self.on_success, font=("Helvetica", 14, "bold"), bg=accent_color, fg="white", bd=0, padx=30, pady=10, activebackground="#1c2333", activeforeground="white").pack(pady=20)