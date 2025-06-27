import tkinter as tk
from tkinter import ttk

class ChoiceMenu(tk.Toplevel):
    def __init__(self, parent, theme_manager, choices):
        """
        choices: liste de tuples (label, callback)
        """
        super().__init__(parent)
        self.title("Sélectionnez une option")
        self.transient(parent)  # Fenêtre liée à la principale
        self.resizable(False, False)

        self.parent = parent
        self.theme_manager = theme_manager
        self.choices = choices

        win_width = 300
        win_height = 100 + 50 * len(choices)

        # Centrage
        self_center_x = parent.winfo_rootx() + parent.winfo_width() // 2
        self_center_y = parent.winfo_rooty() + parent.winfo_height() // 2
        pos_x = self_center_x - win_width // 2
        pos_y = self_center_y - win_height // 2
        self.geometry(f"{win_width}x{win_height}+{pos_x}+{pos_y}")

        self.build_ui()

        # Appliquer thème
        self.theme_manager.register_widget(self, 'bg_main', 'fg_main')

        # Bloquer fenêtre principale
        self.update()
        self.grab_set()
        self.focus()

        self.wait_window(self)

    def build_ui(self):
        label = tk.Label(self, text="Choisissez une action :", font=("Helvetica", 12, "bold"))
        label.pack(fill='x',pady=15)
        self.theme_manager.register_widget(label, 'bg_main', 'fg_main')
        self.separator = ttk.Separator(self, orient='horizontal')
        self.separator.pack(fill='x')

        for text, callback in self.choices:
            btn = tk.Button(
                self,
                text=text,
                command=lambda cb=callback: self.launch(cb),
                font=("Helvetica", 11),
                relief="flat",
                anchor="w",
                padx=30,
                pady=4,
                bd=0,
                highlightthickness=0,
                activeforeground=self.theme_manager.fg_main,
                activebackground=self.theme_manager.bg_main,
            )
            btn.pack(fill='x',pady=5)
            self.theme_manager.register_widget(btn, 'bg_main', 'fg_main', 'bg_hover')

    def launch(self, callback):
        self.grab_release()
        self.destroy()
        if callable(callback):
            callback()

    def on_parent_hidden(self, event=None):
        if self.winfo_exists():
            self.destroy()

    def on_parent_closed(self, event=None):
        if self.winfo_exists():
            self.destroy()
