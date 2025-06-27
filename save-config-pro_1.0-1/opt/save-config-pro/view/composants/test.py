import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# Fenêtre principale
root = tk.Tk()
root.title("Diagrammes Réseau")
root.configure(bg="#1b2233")

# Données pour le Pie Chart
labels = ['Cisco', 'MikroTik', 'Fortinet']
counts = [4, 1, 2]

# Données pour le Bar Chart (en Ko)
space_used = [3.1, 0, 941.6]  # Cisco, Mikrotik, Fortinet

# Figure matplotlib
fig, axs = plt.subplots(1, 2, figsize=(8, 4), dpi=100)
fig.patch.set_facecolor('#1b2233')  # Fond du graphe global

# Pie chart – Répartition des équipements
axs[0].pie(counts, labels=labels, autopct='%1.1f%%', startangle=90, textprops={'color': "white"})
axs[0].set_title("Répartition des équipements", color='white')
axs[0].set_facecolor('#1b2233')

# Bar chart – Espace consommé
axs[1].bar(labels, space_used, color=['#FF6384', '#36A2EB', '#FFCE56'])
axs[1].set_title("Espace consommé (KB)", color='white')
axs[1].tick_params(colors='white')
axs[1].set_facecolor('#1b2233')

# Ajout dans Tkinter
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.draw()
canvas.get_tk_widget().pack(pady=20)

root.mainloop()
