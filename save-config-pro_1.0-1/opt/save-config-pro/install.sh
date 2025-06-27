#!/bin/bash

echo "🔧 Installation de l'environnement virtuel..."

# Aller dans le dossier du projet
cd "$(dirname "$0")"

# Vérifie si on est root
if [ "$EUID" -ne 0 ]; then
  echo "🔐 Ce programme nécessite les droits administrateur."
  exec sudo "$0" "$@"
  exit
fi

# Créer un venv s'il n'existe pas déjà
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activer le venv
source venv/bin/activate

# Mettre à jour pip
pip install --upgrade pip

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
echo "🚀 Lancement de Save Config Pro..."
python main.py
