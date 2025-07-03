from tkinter import messagebox
import json
from datetime import datetime
import os
import time
from view.plannification import BackupSchedulerManager

class Fermer:
    def __init__(self, parent, dashboard_instance, username, users_file_path):
        self.parent = parent  # Référence à NetworkConfigApp
        self.username = username
        self.users_file_path = users_file_path
        self.dashboard_instance = dashboard_instance# L'instance du dashboard
        self.backup_manager = BackupSchedulerManager()
        
        # Chemins des fichiers gérés de manière centralisée
        dossier_fichiers = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')
        self.FICHIER_HISTORIQUE = os.path.join(dossier_fichiers, 'historique_users.json')

    def _arreter_sauvegarde(self):
        """Tente d'arrêter proprement la sauvegarde et retourne True si réussi."""
        try:
            print("[INFO] Tentative d'arrêt du service de sauvegarde...")
            self.backup_manager.stop()
            # On pourrait ajouter une vérification plus poussée ici si nécessaire
            time.sleep(0.5) # Petit délai pour laisser le temps à l'arrêt
            print("[INFO] Service de sauvegarde arrêté.")
            return True
        except Exception as e:
            print(f"[ERREUR] Échec de l'arrêt de la sauvegarde: {str(e)}")
            messagebox.showerror("Erreur Critique", f"Impossible d'arrêter le service de sauvegarde:\n{e}")
            return False

    def _maj_fichiers_utilisateur(self):
        """Met à jour les fichiers de statut et d'historique de l'utilisateur."""
        if not self.username:
            return # Rien à faire s'il n'y a pas d'utilisateur

        # 1. Mise à jour du statut (dernière déconnexion)
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
            print(f"[ERREUR] Mise à jour du statut utilisateur: {str(e)}")

        # 2. Ajout à l'historique de connexion/déconnexion
        try:
            historique = []
            if os.path.exists(self.FICHIER_HISTORIQUE):
                try:
                    with open(self.FICHIER_HISTORIQUE, 'r') as f:
                        historique = json.load(f)
                except json.JSONDecodeError:
                    pass  # Le fichier est corrompu ou vide, on le récrée
            
            nouvelle_entree = {
                "utilisateur": self.username,
                "date_deconnexion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "connect": False
            }
            historique.append(nouvelle_entree)
            
            with open(self.FICHIER_HISTORIQUE, 'w') as f:
                json.dump(historique, f, indent=4)
        except Exception as e:
            print(f"[ERREUR] Mise à jour de l'historique: {str(e)}")


    def demander_fermeture(self):
        """
        Gère le processus complet de fermeture de l'application de manière sécurisée.
        C'est la seule méthode publique à appeler.
        """
        # --- ÉTAPE 1: Gérer la sauvegarde en cours ---
        if self.backup_manager.running:
            arreter = messagebox.askyesno(
                "Sauvegarde en cours",
                "Une tâche de sauvegarde est actuellement en cours.\n"
                "Voulez-vous l'arrêter pour pouvoir quitter ?",
                icon="warning"
            )
            if arreter:
                if not self._arreter_sauvegarde():
                    # Si l'arrêt échoue, on ne ferme pas l'application
                    return
            else:
                # L'utilisateur a choisi de ne pas arrêter, on annule la fermeture
                messagebox.showinfo("Fermeture annulée", "L'application ne sera pas fermée. "
                                    "Veuillez attendre la fin de la sauvegarde.")
                return

        # --- ÉTAPE 2: Confirmer la fermeture ---
        confirmation = messagebox.askyesno(
            "Quitter l'application",
            "Voulez-vous vraiment fermer l'application ?",
            icon="question"
        )
        if not confirmation:
            return # L'utilisateur a annulé

        # --- ÉTAPE 3: Exécuter les actions de fermeture (point de non-retour) ---
        print("[INFO] Fermeture de l'application...")
        
        if self.dashboard_instance and self.dashboard_instance.winfo_exists():
            self.dashboard_instance.prepare_for_close()
        
        # 2. Mettre à jour les fichiers si un utilisateur est connecté
        self._maj_fichiers_utilisateur()
        
        # 3. Finalement, détruire la fenêtre principale
        self.parent.destroy()