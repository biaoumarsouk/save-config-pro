import threading
import time
import tkinter as tk
from tkinter import ttk

def run_with_loading(content_frame, task_function, callback=None, theme_manager=None):
    progress_bar = None
    percent_label = None
    loader_bind_id = None  # pour désactiver le binding après chargement

    def build_loader_widgets():
        nonlocal progress_bar, percent_label, loader_bind_id

        style = ttk.Style()
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor="#1c2333",
                        background="#007bff",
                        thickness=20)

        progress_bar = ttk.Progressbar(
            content_frame,
            orient="horizontal",
            length=250,
            mode="determinate",
            style="Custom.Horizontal.TProgressbar"
        )
        percent_label = tk.Label(
            content_frame,
            text="",
            bg=theme_manager.bg_main if theme_manager else "#1c2333",
            fg=theme_manager.fg_main if theme_manager else "white",
            font=("Helvetica", 10)
        )

        if theme_manager:
            theme_manager.register_widget(percent_label, 'bg_main', 'fg_main')
            theme_manager.register_widget(progress_bar, None, None)

        progress_bar.place(x=0, y=0)  # position provisoire
        percent_label.place(x=0, y=0)  # position provisoire
        center_loader_widgets()

        # Recentrer dynamiquement quand le cadre change de taille
        loader_bind_id = content_frame.bind("<Configure>", lambda event: center_loader_widgets())

    def center_loader_widgets():
        if not progress_bar or not percent_label:
            return
        frame_width = content_frame.winfo_width()
        frame_height = content_frame.winfo_height()
        bar_width = 250
        bar_x = (frame_width - bar_width) // 2
        bar_y = frame_height // 2 - 20

        progress_bar.place(x=bar_x, y=bar_y)
        percent_label.place(x=bar_x + bar_width // 2 - 40, y=bar_y + 30)

    def update_progress(percent, text=""):
        def update_ui():
            if progress_bar and percent_label:
                progress_bar['value'] = percent
                if text:
                    percent_label.config(text=text)
                    if theme_manager:
                        theme_manager.apply_theme()
        content_frame.after(0, update_ui)

    def wrapper():
        widgets_to_restore = []
        for widget in content_frame.winfo_children():
            widgets_to_restore.append(widget)
            if widget.winfo_manager() == "place":
                widget._original_place_info = widget.place_info()
            elif widget.winfo_manager() == "pack":
                widget._original_pack_info = widget.pack_info()
            elif widget.winfo_manager() == "grid":
                widget._original_grid_info = widget.grid_info()
            widget.place_forget()
            widget.pack_forget()
            widget.grid_forget()

        content_frame.after(0, build_loader_widgets)
        update_progress(0, "Chargement...")

        result = task_function(update_progress)

        update_progress(100, "Terminé ✅")
        time.sleep(0.5)

        def clean_and_restore():
            if progress_bar:
                progress_bar.place_forget()
            if percent_label:
                percent_label.place_forget()
            # Supprimer le binding pour ne plus recentrer à chaque redimensionnement
            if loader_bind_id is not None:
                content_frame.unbind("<Configure>", loader_bind_id)

            for widget in widgets_to_restore:
                if hasattr(widget, "_original_place_info"):
                    widget.place(**widget._original_place_info)
                elif hasattr(widget, "_original_pack_info"):
                    widget.pack(**widget._original_pack_info)
                elif hasattr(widget, "_original_grid_info"):
                    widget.grid(**widget._original_grid_info)

            if callback:
                callback(result)

        content_frame.after(0, clean_and_restore)

    threading.Thread(target=wrapper).start()
