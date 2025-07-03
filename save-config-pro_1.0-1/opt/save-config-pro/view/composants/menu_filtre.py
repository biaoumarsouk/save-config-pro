# view/composants/toggle_menu.py
import tkinter as tk

class ToggleMenu(tk.Frame):
    def __init__(self, root, show_cisco, show_mikrotik, show_huawei, show_juniper, show_fortinet, export_data, theme_manager, menu_width=188):
        super().__init__(root, width=menu_width)
        self.root = root
        self.theme_manager = theme_manager
        self.show_cisco = show_cisco
        self.show_mikrotik = show_mikrotik
        self.show_huawei = show_huawei
        self.show_juniper = show_juniper
        self.show_fortinet = show_fortinet
        self.export_data = export_data
        self.menu_panel = None
        self.menu_visible = False
        self.toggle_button = None
        self.menu_width = menu_width

        # Enregistrer ce frame dans le theme_manager
        self.theme_manager.register_widget(self, 'bg_secondary')
        self.pack_propagate(False)

        self.create_toggle_button()

    def on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def toggle_menu(self):
        if self.menu_visible:
            self.close_menu()
            return

        if self.toggle_button and self.toggle_button.winfo_exists():
            self.toggle_button.destroy()

        self.menu_panel = tk.Frame(self.root, width=self.menu_width)
        self.theme_manager.register_widget(self.menu_panel, 'bg_secondary')
        self.menu_panel.place(x=self.root.winfo_width() - self.menu_width, y=0,
                            width=self.menu_width, height=self.root.winfo_height())

        self.canvas = tk.Canvas(self.menu_panel, highlightthickness=0)
        self.theme_manager.register_widget(self.canvas, 'bg_secondary')
        self.canvas.pack(side="left", fill="both", expand=True)

        content_frame = tk.Frame(self.canvas)
        self.theme_manager.register_widget(content_frame, 'bg_secondary')
        self.canvas.create_window((0, 0), window=content_frame, anchor="nw")

        def update_scroll_region(event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        content_frame.bind("<Configure>", update_scroll_region)
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        close_btn = tk.Button(
            self.menu_panel, text="➡", font=("Helvetica", 12, "bold"),
            relief="flat", cursor="hand2", command=self.close_menu
        )
        self.theme_manager.register_widget(close_btn, 'bg_secondary', 'fg_main','bg_hover')
        close_btn.config(
            activebackground=self.theme_manager.bg_hover,
            activeforeground=self.theme_manager.fg_main
        )
        close_btn.place(relx=0.0, rely=0.5, anchor="w", x=-10)

        button_style = {
            "font": ("Helvetica", 10, "bold"),
            "relief": "flat", "anchor": "w", "width": 20,
            "padx": 20, "pady": 5, "bd": 0, "highlightthickness": 0
        }

        button_export = {
            "font": ("Helvetica", 10, "bold"),
            "relief": "flat", "anchor": "center", "width": 20,
            "padx": 20, "pady": 5
        }

        # Espacement
        tk.Label(content_frame).pack(pady=2)
        self.theme_manager.register_widget(content_frame.winfo_children()[-1], 'bg_secondary')

        # Boutons du menu
        buttons = [
            ("Exporter les données 🖨️", self.export_data, button_export),
            ("Equipements", None, button_export),
            ("Cisco", lambda: [self.close_menu(), self.show_cisco()], button_style),
            ("MikroTik", lambda: [self.close_menu(), self.show_mikrotik()], button_style),
            ("Huawei", lambda: [self.close_menu(), self.show_huawei()], button_style),
            ("Juniper", lambda: [self.close_menu(), self.show_juniper()], button_style),
            ("Fortinet", lambda: [self.close_menu(), self.show_fortinet()], button_style)
        ]

        for text, cmd, style in buttons:
            if cmd:  # Bouton avec commande
                btn = tk.Button(content_frame, text=text, command=cmd, **style)
            else:    # Bouton sans commande (titre)
                btn = tk.Button(content_frame, text=text, **style)
            btn.pack(fill="x")
            self.theme_manager.register_widget(btn, 'bg_secondary', 'fg_main')
            btn.config(
                activebackground=self.theme_manager.bg_hover,
                activeforeground=self.theme_manager.fg_main
            )
            
            
            # Espacement après certains boutons
            if text in ["Equipements", "Exporter les données 🖨️"]:
                tk.Label(content_frame).pack()
                self.theme_manager.register_widget(content_frame.winfo_children()[-1], 'bg_secondary')

        self.menu_visible = True
        self.root.bind("<Button-1>", self.close_menu_if_clicked_outside)
        self.root.bind("<Configure>", self.on_window_resize)

    def on_window_resize(self, event=None):
        if self.menu_visible and self.menu_panel:
            self.menu_panel.place_configure(x=self.root.winfo_width() - self.menu_width,
                                          height=self.root.winfo_height())

    def close_menu(self, event=None):
        if self.menu_panel:
            self.menu_panel.destroy()
        self.menu_visible = False
        self.create_toggle_button()
        self.root.unbind("<Configure>")

    def close_menu_if_clicked_outside(self, event):
        if self.menu_panel and not self.menu_panel.winfo_containing(event.x_root, event.y_root):
            self.close_menu()

    def create_toggle_button(self):
        self.toggle_button = tk.Button(
            self.root, text="⬅", font=("Helvetica", 12, "bold"),
            relief="flat", cursor="hand2", command=self.toggle_menu
        )
        self.toggle_button.place(relx=1.0, rely=0.5, anchor="e", x=10)
        self.theme_manager.register_widget(self.toggle_button, 'bg_main', 'fg_main','bg_hover')
        self.toggle_button.config(
            activebackground=self.theme_manager.bg_hover,
            activeforeground=self.theme_manager.fg_main
        )
        