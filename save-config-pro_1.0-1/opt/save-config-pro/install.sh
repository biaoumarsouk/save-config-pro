#!/bin/bash

echo "🔧 Installation globale des dépendances..."

# Aller dans le dossier du projet
cd "$(dirname "$0")"

# Vérifie si on est root
if [ "$EUID" -ne 0 ]; then
  echo "🔐 Ce programme nécessite les droits administrateur (sudo)."
  exec sudo "$0" "$@"
  exit
fi

# Liste des dépendances
DEPENDANCES=(
  paramiko
  psutil
  Pillow
  matplotlib
)

# Installer les paquets avec --break-system-packages
for package in "${DEPENDANCES[@]}"; do
  echo "📦 Installation de $package..."
  pip install "$package" --break-system-packages
done

# Lancer l'application
echo "🚀 Lancement de Save Config Pro..."
python3 main.py
