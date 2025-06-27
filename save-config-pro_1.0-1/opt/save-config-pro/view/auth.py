import tkinter as tk
from tkinter import messagebox, filedialog
import json
import os
import hashlib
from PIL import Image, ImageTk, ImageDraw, ImageOps
from datetime import datetime

# === Chemins et fichiers ===
DOSSIER_FICHIERS = os.path.join(os.path.dirname(__file__), 'files')
DOSSIER_PROFILS = os.path.join(DOSSIER_FICHIERS, 'profils')
os.makedirs(DOSSIER_FICHIERS, exist_ok=True)
os.makedirs(DOSSIER_PROFILS, exist_ok=True)
FICHIER_HISTORIQUE = os.path.join(DOSSIER_FICHIERS, 'historique_users.json')
FICHIER_UTILISATEURS = os.path.join(DOSSIER_FICHIERS, 'users.json')
if not os.path.exists(FICHIER_UTILISATEURS):
    with open(FICHIER_UTILISATEURS, 'w') as f:
        json.dump({}, f)

def hacher_motdepasse(mdp):
    return hashlib.sha256(mdp.encode()).hexdigest()

def charger_utilisateurs():
    with open(FICHIER_UTILISATEURS, "r") as f:
        return json.load(f)

def sauvegarder_utilisateurs(utilisateurs):
    with open(FICHIER_UTILISATEURS, "w") as f:
        json.dump(utilisateurs, f, indent=4)

def creer_image_cercle(image_pil, size=(100, 100)):
    # Créer un masque circulaire
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, *size), fill=255)
    
    # Redimensionner et rogner l'image pour remplir le cercle
    width, height = size
    # Créer une image carrée en rognant
    if image_pil.width > image_pil.height:
        # Image large - rogner les côtés
        left = (image_pil.width - image_pil.height) / 2
        right = left + image_pil.height
        top = 0
        bottom = image_pil.height
    else:
        # Image haute - rogner le haut et bas
        left = 0
        right = image_pil.width
        top = (image_pil.height - image_pil.width) / 2
        bottom = top + image_pil.width
    
    # Rogner et redimensionner
    image = image_pil.crop((left, top, right, bottom)).resize(size, Image.Resampling.LANCZOS)
    
    # Appliquer le masque
    result = Image.new("RGBA", size)
    result.paste(image, (0, 0), mask)
    
    return ImageTk.PhotoImage(result)

def creer_cercle_vide_avec_icone(size=(100, 100), couleur_bordure="#1c2333", epaisseur=1):
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Cercle extérieur
    draw.ellipse((0, 0, size[0]-1, size[1]-1), outline=couleur_bordure, width=epaisseur)

    # Tête (descendue encore un peu)
    draw.ellipse([30, 30, 70, 70], outline=couleur_bordure, width=2)

    # Corps (aussi descendu pour ne pas toucher la tête)
    draw.arc([25, 70, 75, 110], start=180, end=360, fill=couleur_bordure, width=2)

    return ImageTk.PhotoImage(img)


class LoginFrame(tk.Frame):
    def __init__(self, parent, on_login_success):
        super().__init__(parent)
        self.parent = parent
        self.on_login_success = on_login_success
        
        self.nom_utilisateur = None
        self.chemin_image_profil = None
        self.image_profil_tk = None
        
        self.configure(bg="white")
        self.pack(fill="both", expand=True)
        
        # Configuration des frames
        self.left_frame = tk.Frame(self, bg="white")
        self.right_frame = tk.Frame(self, bg="#1c2333")
        self.left_frame.pack(side="left", fill="both", expand=True)
        self.right_frame.pack(side="right", fill="both", expand=True)

        # Container principal
        self.container_left = tk.Frame(self.left_frame, bg="white", width=350, height=500)
        self.container_left.place(relx=0.5, rely=0.5, anchor="center")
        self.container_left.pack_propagate(False)

        self.create_login_ui()
        self.create_welcome_ui()

    def create_login_ui(self):
        for widget in self.container_left.winfo_children():
            widget.destroy()

        title = tk.Label(self.container_left, text="Se connecter", font=("Arial", 18, "bold"), bg="white")
        title.pack(pady=(30, 15))

        # Fonctions pour les champs de saisie
        def on_entry_click_user(event):
            if self.entry_user.get() == "username":
                self.entry_user.delete(0, "end")

        def on_entry_click_pwd(event):
            if self.entry_pwd.get() == "password":
                self.entry_pwd.delete(0, "end")
                self.entry_pwd.config(show="*")

        def on_focusout_user(event):
            if not self.entry_user.get():
                self.entry_user.insert(0, "username")
                self.entry_pwd.config(show="")
                self.entry_pwd.delete(0, "end")
                self.entry_pwd.insert(0, "password")

        # Champ utilisateur
        self.entry_user = tk.Entry(self.container_left, font=("Arial", 12), width=30,
                                 bd=0, highlightthickness=1, highlightbackground="#aaa", 
                                 highlightcolor="#1c2333", relief="solid")
        self.entry_user.insert(0, "username")
        self.entry_user.bind('<FocusIn>', on_entry_click_user)
        self.entry_user.bind('<FocusOut>', on_focusout_user)
        self.entry_user.pack(pady=10, ipady=8, ipadx=10, fill='x', padx=20)

        # Champ mot de passe
        self.entry_pwd = tk.Entry(self.container_left, font=("Arial", 12), width=30,
                                bd=0, highlightthickness=1, highlightbackground="#aaa", 
                                highlightcolor="#1c2333", relief="solid")
        self.entry_pwd.insert(0, "password")
        self.entry_pwd.bind('<FocusIn>', on_entry_click_pwd)
        self.entry_pwd.pack(pady=10, ipady=8, ipadx=10, fill='x', padx=20)

        # Frame pour le bouton pour contrôler la largeur
        button_frame = tk.Frame(self.container_left, bg="white")
        button_frame.pack(pady=20, fill='x', padx=20)

        # Bouton login - même largeur que les champs
        btn_login = tk.Button(button_frame, text="Se connecter", bg="#1c2333", fg="white", 
                            font=("Arial", 12), command=self.verifier_connexion, 
                            bd=0, relief="ridge", activebackground="#2c3e50",activeforeground="white")
        btn_login.pack(ipady=5, fill='x')

        # Lien signup
        link_signup = tk.Label(self.container_left, text="Vous n'avez pas de compte ? S'inscrire", 
                             fg="#1c2333", bg="white", cursor="hand2", font=("Arial", 10))
        link_signup.pack(pady=(10, 0))
        link_signup.bind("<Button-1>", lambda e: self.show_signup_ui())

    def choisir_image(self, event=None):
        chemin = filedialog.askopenfilename(
            title="Choisir une image",
            filetypes=[("Images", "*.png *.jpg *.jpeg")]
        )
        if chemin:
            try:
                self.chemin_image_profil = chemin
                img_pil = Image.open(chemin)
                
                # Créer l'image circulaire qui remplit tout l'espace
                photo = creer_image_cercle(img_pil)
                
                # Sauvegarder la référence
                self.image_profil_tk = photo
                
                # Mettre à jour le canvas
                self.canvas_profil.delete("all")
                self.canvas_profil.create_image(50, 50, image=self.image_profil_tk)
                
                # Redessiner la bordure fine par-dessus
                self.canvas_profil.create_oval(1, 1, 99, 99, outline="#1c2333", width=1)
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de charger l'image: {str(e)}")

    def create_welcome_ui(self):
        container = tk.Frame(self.right_frame, bg="#1c2333")
        container.place(relx=0.5, rely=0.4, anchor="center")

        label = tk.Label(container, text="BIENVENUE !", fg="white", bg="#1c2333", 
                        font=("Arial", 22, "bold"))
        label.pack(pady=(0, 10))

        labelst = tk.Label(container, 
                         text="Système de Gestion des Configurations Réseaux\nInformatiques",
                         fg="white", bg="#1c2333", font=("Arial", 16, "bold"))
        labelst.pack(pady=(0, 10))

        subtitle = tk.Label(container, text="Se connecter pour continuer", 
                           fg="white", bg="#1c2333", font=("Arial", 12))
        subtitle.pack()

    def show_signup_ui(self):
        for widget in self.container_left.winfo_children():
            widget.destroy()

        # Titre
        tk.Label(self.container_left, text="S'inscrire", font=("Arial", 18, "bold"), 
               bg="white").pack(pady=(0, 20))

        # Canvas pour la photo de profil
        self.canvas_profil = tk.Canvas(self.container_left, width=100, height=100, 
                                     bg="white", highlightthickness=0)
        self.canvas_profil.pack(pady=(0, 20))
        self.canvas_profil.bind("<Button-1>", self.choisir_image)

        # Icône utilisateur par défaut avec bordure fine
        self.img_cercle_vide_icone = creer_cercle_vide_avec_icone()
        self.image_profil_tk = self.img_cercle_vide_icone
        self.canvas_profil.create_image(50, 50, image=self.image_profil_tk)

        # Fonctions pour les champs de saisie
        def on_entry_click_nom(event):
            if self.entry_nom.get() == "Nom":
                self.entry_nom.delete(0, "end")

        def on_focusout_nom(event):
            if not self.entry_nom.get():
                self.entry_nom.insert(0, "Nom")

        def on_entry_click_prenom(event):
            if self.entry_prenom.get() == "Prénom":
                self.entry_prenom.delete(0, "end")

        def on_focusout_prenom(event):
            if not self.entry_prenom.get():
                self.entry_prenom.insert(0, "Prénom")

        def on_entry_click_new_user(event):
            if self.entry_new_user.get() == "username":
                self.entry_new_user.delete(0, "end")

        def on_entry_click_new_pwd(event):
            if self.entry_new_pwd.get() == "password":
                self.entry_new_pwd.delete(0, "end")
                self.entry_new_pwd.config(show="*")

        def on_focusout_new_user(event):
            if not self.entry_new_user.get():
                self.entry_new_user.insert(0, "username")
                self.entry_new_pwd.config(show="")
                self.entry_new_pwd.delete(0, "end")
                self.entry_new_pwd.insert(0, "password")

        # Champ Nom
        self.entry_nom = tk.Entry(self.container_left, font=("Arial", 12), width=30,
                                bd=0, highlightthickness=1, highlightbackground="#aaa", 
                                highlightcolor="#1c2333", relief="solid")
        self.entry_nom.insert(0, "Nom")
        self.entry_nom.bind('<FocusIn>', on_entry_click_nom)
        self.entry_nom.bind('<FocusOut>', on_focusout_nom)
        self.entry_nom.pack(pady=5, ipady=8, ipadx=10, fill='x', padx=20)

        # Champ Prénom
        self.entry_prenom = tk.Entry(self.container_left, font=("Arial", 12), width=30,
                                    bd=0, highlightthickness=1, highlightbackground="#aaa", 
                                    highlightcolor="#1c2333", relief="solid")
        self.entry_prenom.insert(0, "Prénom")
        self.entry_prenom.bind('<FocusIn>', on_entry_click_prenom)
        self.entry_prenom.bind('<FocusOut>', on_focusout_prenom)
        self.entry_prenom.pack(pady=5, ipady=8, ipadx=10, fill='x', padx=20)

        # Champ Username
        self.entry_new_user = tk.Entry(self.container_left, font=("Arial", 12), width=30,
                                     bd=0, highlightthickness=1, highlightbackground="#aaa", 
                                     highlightcolor="#1c2333", relief="solid")
        self.entry_new_user.insert(0, "username")
        self.entry_new_user.bind('<FocusIn>', on_entry_click_new_user)
        self.entry_new_user.bind('<FocusOut>', on_focusout_new_user)
        self.entry_new_user.pack(pady=5, ipady=8, ipadx=10, fill='x', padx=20)

        # Champ Mot de passe
        self.entry_new_pwd = tk.Entry(self.container_left, font=("Arial", 12), width=30,
                                    bd=0, highlightthickness=1, highlightbackground="#aaa", 
                                    highlightcolor="#1c2333", relief="solid")
        self.entry_new_pwd.insert(0, "password")
        self.entry_new_pwd.bind('<FocusIn>', on_entry_click_new_pwd)
        self.entry_new_pwd.pack(pady=5, ipady=8, ipadx=10, fill='x', padx=20)

        # Frame pour le bouton pour contrôler la largeur
        button_frame = tk.Frame(self.container_left, bg="white")
        button_frame.pack(pady=20, fill='x', padx=20)

        # Bouton créer compte - même largeur que les champs
        btn_create = tk.Button(button_frame, text="Créer un compte", bg="#1c2333", 
                            fg="white", font=("Arial", 12), command=self.creer_compte, 
                            bd=0, relief="ridge", activebackground="#2c3e50",activeforeground="white")
        btn_create.pack(ipady=5, fill='x')

        # Lien retour
        link_back = tk.Label(self.container_left, text="Vous avez déjà un compte ? Se connecter", 
                           fg="#1c2333", bg="white", cursor="hand2", font=("Arial", 10))
        link_back.pack()
        link_back.bind("<Button-1>", lambda e: self.reset_login_ui())

    def reset_login_ui(self):
        for widget in self.container_left.winfo_children():
            widget.destroy()
        self.create_login_ui()

    def enregistrer_connexion(self, nom_utilisateur, connect=True, tentative=False):
        historique = []

        if os.path.exists(FICHIER_HISTORIQUE):
            with open(FICHIER_HISTORIQUE, "r") as f:
                try:
                    historique = json.load(f)
                except json.JSONDecodeError:
                    historique = []

        nouvelle_entree = {
            "utilisateur": nom_utilisateur,
            "date_connexion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "connect": connect,
            "tentative": tentative,
            "date_deconnexion": None
        }

        historique.append(nouvelle_entree)

        with open(FICHIER_HISTORIQUE, "w") as f:
            json.dump(historique, f, indent=4)
            
    def verifier_connexion(self):
        utilisateurs = charger_utilisateurs()
        nom = self.entry_user.get()
        mdp = self.entry_pwd.get()

        if nom == "username" or mdp == "password":
            messagebox.showerror("Erreur", "Veuillez saisir vos identifiants")
            self.enregistrer_connexion(nom_utilisateur=nom, connect=False, tentative=True)
            return

        mdp_hache = hacher_motdepasse(mdp)

        if nom in utilisateurs:
            if utilisateurs[nom]["password"] == mdp_hache:
                if not utilisateurs[nom].get("status", False):
                    messagebox.showerror("Erreur", "La connexion à ce compte n'est pas autorisée")
                    self.enregistrer_connexion(nom_utilisateur=nom, connect=False, tentative=True)
                    return

                # Connexion réussie
                utilisateurs[nom]["connexion"] = True
                utilisateurs[nom]["derniere_connexion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                sauvegarder_utilisateurs(utilisateurs)

                self.enregistrer_connexion(nom_utilisateur=nom, connect=True, tentative=False)
                self.nom_utilisateur = nom
                self.on_login_success(nom)
            else:
                messagebox.showerror("Erreur", "Mot de passe incorrect")
                self.enregistrer_connexion(nom_utilisateur=nom, connect=False, tentative=True)
        else:
            messagebox.showerror("Erreur", "Nom d'utilisateur incorrect")
            self.enregistrer_connexion(nom_utilisateur=nom, connect=False, tentative=True)




    def creer_compte(self):
        utilisateurs = charger_utilisateurs()
        nom = self.entry_nom.get()
        prenom = self.entry_prenom.get()
        username = self.entry_new_user.get()
        mdp = self.entry_new_pwd.get()

        # Validation des champs
        if (nom == "Nom" or prenom == "Prénom" or 
            username == "username" or mdp == "password"):
            messagebox.showerror("Erreur", "Veuillez remplir tous les champs")
            return

        if username in utilisateurs:
            messagebox.showerror("Erreur", "Ce nom d'utilisateur existe déjà.")
        elif len(username.strip()) < 3 or len(mdp.strip()) < 4:
            messagebox.showerror("Erreur", "Nom d'utilisateur ou mot de passe trop court.")
        else:
            # Par défaut
            photo_fichier = "default.png"

            # Enregistrement de l'image de profil si sélectionnée
            if self.chemin_image_profil:
                ext = os.path.splitext(self.chemin_image_profil)[1]
                photo_fichier = f"{username}{ext}"
                chemin_destination = os.path.join(DOSSIER_PROFILS, photo_fichier)
                with open(self.chemin_image_profil, 'rb') as src, open(chemin_destination, 'wb') as dst:
                    dst.write(src.read())

            # Création du compte
            utilisateurs[username] = {
                "nom": nom,
                "prenom": prenom,
                "password": hacher_motdepasse(mdp),
                "status": False,
                "role": "user",
                "connexion": False,
                "derniere_connexion": None,
                "date_creation": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "photo_profil": photo_fichier
            }

            sauvegarder_utilisateurs(utilisateurs)
            messagebox.showinfo("Succès", "Compte créé avec succès !")
            self.reset_login_ui()
