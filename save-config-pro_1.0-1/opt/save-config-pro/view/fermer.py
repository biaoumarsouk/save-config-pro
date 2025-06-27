from tkinter import messagebox
import json
from datetime import datetime
import os
import time
from view.plannification import BackupSchedulerManager

class Fermer:
    def __init__(self, parent, username, users_file_path):
        self.parent = parent  # Référence à NetworkConfigApp
        self.username = username
        self.users_file_path = users_file_path
        self.backup_manager = BackupSchedulerManager()
        self.DOSSIER_FICHIERS = os.path.join(os.path.dirname(__file__), 'files')
        self.FICHIER_HISTORIQUE = os.path.join(self.DOSSIER_FICHIERS, 'historique_users.json')

    def _arreter_sauvegarde(self):
        """Arrête proprement la sauvegarde"""
        try:
            if self.backup_manager.running:
                print("[DEBUG] Arrêt du service de sauvegarde...")
                self.backup_manager.stop()
                time.sleep(1)  # Petit délai pour laisser le temps à l'arrêt
                return True
        except Exception as e:
            print(f"[ERREUR] Arrêt sauvegarde: {str(e)}")
        return False

    def _verifier_sauvegarde_en_cours(self):
        """Vérifie si une sauvegarde est en cours"""
        try:
            return self.backup_manager.running
        except Exception as e:
            print(f"[ERREUR] Verification sauvegarde: {str(e)}")
            return False

    def _fermer_sans_utilisateur(self):
        """Ferme l'application directement quand il n'y a pas d'utilisateur"""
        sauvegarde_en_cours = self._verifier_sauvegarde_en_cours()
        
        if sauvegarde_en_cours:
            if not self._arreter_sauvegarde():
                messagebox.showerror("Erreur", "Échec de l'arrêt de la sauvegarde.")
                return False
        
        self.parent.destroy()
        return True

    def _fermer_avec_utilisateur(self):
        """Processus complet de fermeture avec utilisateur"""
        # Mise à jour du statut utilisateur
        try:
            if os.path.exists(self.users_file_path) and os.path.getsize(self.users_file_path) > 0:
                with open(self.users_file_path, "r+") as f:
                    users = json.load(f)
                    if self.username in users:
                        users[self.username]["connexion"] = False
                        users[self.username]["derniere_connexion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        f.seek(0)
                        json.dump(users, f, indent=4)
                        f.truncate()
        except Exception as e:
            print(f"[ERREUR] Mise à jour statut utilisateur: {str(e)}")

        # Mise à jour historique
        try:
            if self.username:
                historique = []
                if os.path.exists(self.FICHIER_HISTORIQUE):
                    try:
                        with open(self.FICHIER_HISTORIQUE, 'r') as f:
                            historique = json.load(f)
                    except json.JSONDecodeError:
                        pass
                
                nouvelle_entree = {
                    "utilisateur": self.username,
                    "date_connexion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "date_deconnexion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "connect": False
                }
                historique.append(nouvelle_entree)
                
                with open(self.FICHIER_HISTORIQUE, 'w') as f:
                    json.dump(historique, f, indent=4)
        except Exception as e:
            print(f"[ERREUR] Mise à jour historique: {str(e)}")

        self.parent.destroy()
        return True

    def fermer_application(self):
        """Ferme l'application avec une logique différente selon la présence d'un utilisateur"""
        # Vérification sauvegarde en cours
        sauvegarde_en_cours = self._verifier_sauvegarde_en_cours()

        if sauvegarde_en_cours:
            arreter_sauvegarde = messagebox.askyesno(
                "Sauvegarde en cours",
                "Une sauvegarde est en cours.\nSouhaitez-vous l'arrêter avant de quitter ?",
                icon="warning"
            )
            if arreter_sauvegarde:
                if not self._arreter_sauvegarde():
                    messagebox.showerror("Erreur", "Échec de l'arrêt de la sauvegarde.")
                    return
            else:
                messagebox.showinfo("Fermeture annulée", "Veuillez attendre la fin de la sauvegarde.")
                return

        # Si pas d'utilisateur, fermeture simple
        if not self.username:
            return self._fermer_sans_utilisateur()

        # Si utilisateur, confirmation et fermeture avec mise à jour
        confirmation = messagebox.askyesno(
            "Quitter l'application",
            f"Voulez-vous vraiment fermer l'application ?",
            icon="question"
        )
        if confirmation:
            self._fermer_avec_utilisateur()