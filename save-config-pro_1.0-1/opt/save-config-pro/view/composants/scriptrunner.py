import os
import subprocess

class ScriptRunner:
    def __init__(self):
        # Répertoire de base = dossier de app.py
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def run(self, relative_script_path):
        """
        Exécute un script Python avec un chemin relatif à partir de la racine du projet.
        :param relative_script_path: Exemple : 'view/composants/scr_backup_cisco.py'
        :return: Tuple (code_retour, sortie, erreur)
        """
        script_path = os.path.join(self.base_dir, relative_script_path)

        if not os.path.isfile(script_path):
            return -1, "", f"❌ Fichier non trouvé : {script_path}"

        try:
            result = subprocess.run(
                ["python3", script_path],
                text=True,
                capture_output=True
            )
            return result.returncode, result.stdout, result.stderr

        except Exception as e:
            return -1, "", f"❌ Erreur lors de l'exécution : {e}"
