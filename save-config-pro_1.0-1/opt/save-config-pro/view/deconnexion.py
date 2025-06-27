from tkinter import messagebox
import json
from datetime import datetime
import os
import sys
import weakref
import threading
import time
import subprocess
from view.plannification import BackupSchedulerManager

class Deconnexion:
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

    def _demander_arret_sauvegarde(self):
        """Demande confirmation pour arrêter la sauvegarde"""
        return messagebox.askyesno(
            "Sauvegarde en cours",
            "Une sauvegarde est actuellement en cours.\n"
            "Souhaitez-vous l'arrêter avant de retourner à l'écran de connexion ?",
            icon="question"
        )

    def _mettre_a_jour_statut_utilisateur(self):
        """Met à jour le statut de l'utilisateur dans users.json"""
        try:
            with open(self.users_file_path, "r+") as f:
                users = json.load(f)
                if self.username in users:
                    users[self.username]["connexion"] = False
                    users[self.username]["derniere_connexion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.seek(0)
                    json.dump(users, f, indent=4)
                    f.truncate()
                    return True
        except Exception as e:
            print(f"[ERREUR] Mise à jour statut: {str(e)}")
        return False

    def _mettre_a_jour_historique(self):
        """Met à jour l'historique des connexions"""
        try:
            historique = []
            if os.path.exists(self.FICHIER_HISTORIQUE):
                with open(self.FICHIER_HISTORIQUE, 'r') as f:
                    historique = json.load(f)
            
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

    def deconnecter(self):
        """Processus complet de déconnexion avec confirmation"""

        sauvegarde_en_cours = self._verifier_sauvegarde_en_cours()

        if sauvegarde_en_cours:
            # 1. Demander s’il faut arrêter la sauvegarde
            arreter_sauvegarde = self._demander_arret_sauvegarde()
            if arreter_sauvegarde:
                if not self._arreter_sauvegarde():
                    messagebox.showerror("Erreur", "Échec de l'arrêt de la sauvegarde.")
                    return  # On ne continue pas si l'arrêt échoue

        # 2. Dans tous les cas, demander si on veut se déconnecter maintenant
        confirmation = messagebox.askyesno(
            "Déconnexion",
            "Voulez-vous maintenant vous déconnecter ?",
            icon="question"
        )
        if not confirmation:
            return  # ❌ L’utilisateur annule

        # 3. Mettre à jour les statuts
        self._mettre_a_jour_statut_utilisateur()
        self._mettre_a_jour_historique()

        # 4. Revenir à l'écran de login
        if hasattr(self.parent, 'show_login_screen'):
            self.parent.show_login_screen()
        else:
            messagebox.showerror("Erreur", "Impossible de retourner à l'écran de login.")
            self.parent.destroy()
