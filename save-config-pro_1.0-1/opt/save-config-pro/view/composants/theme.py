import tkinter as tk

class ThemeManager:
    def __init__(self, root=None):
        self.root = root
        self.widgets = []
        self._callbacks = []

        self._themes = {
            'dark': {
                'bg_main': "#1c2333",
                'bg_secondary': "#2e3b55",
                'bg_hover': "#556b8b",
                'fg_main': "white",
                'fg_success': "lightgreen",
                'separator': "#bbbbbb",
                'highlight': "#ffffff"
            },
            'light': {
                'bg_main': "#ffffff",
                'bg_secondary': "#f5f5f5",
                'bg_hover': "#f1f1f1",
                'fg_main': "#000000",
                'fg_success': "green",
                'separator': "#888888",
                'highlight': "#000000"
            }
        }
        self.current_theme = 'dark'
        self._update_attributes()

    def register_callback(self, callback):
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def _notify_callbacks(self):
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                print(f"[ThemeManager] Erreur dans callback: {e}")

    def _update_attributes(self):
        for key, value in self._themes[self.current_theme].items():
            setattr(self, key, value)

    def toggle_theme(self):
        self.current_theme = 'light' if self.current_theme == 'dark' else 'dark'
        self._update_attributes()
        self.apply_theme()
        self._notify_callbacks()
        return self

    def register_widget(self, widget, bg_prop=None, fg_prop=None, active_bg=None, active_fg=None, highlight_prop=None):
        widget_info = {
            'widget': widget,
            'bg': bg_prop,
            'fg': fg_prop,
            'active_bg': active_bg,
            'active_fg': active_fg,
            'highlight': highlight_prop
        }
        self.widgets.append(widget_info)
        self._update_widget_appearance(widget_info)

    def _update_widget_appearance(self, widget_info):
        widget = widget_info['widget']
        if not widget.winfo_exists():
            return

        config_options = widget.config()
        try:
            if widget_info['bg'] and 'bg' in config_options:
                widget.configure(bg=getattr(self, widget_info['bg']))
            if widget_info['fg'] and 'fg' in config_options:
                widget.configure(fg=getattr(self, widget_info['fg']))
            if widget_info['active_bg'] and 'activebackground' in config_options:
                widget.configure(activebackground=getattr(self, widget_info['active_bg']))
            if widget_info['active_fg'] and 'activeforeground' in config_options:
                widget.configure(activeforeground=getattr(self, widget_info['active_fg']))
            if widget_info['highlight'] and 'highlightbackground' in config_options:
                widget.configure(highlightbackground=getattr(self, widget_info['highlight']))

            # Ajout spécial pour Entry et Spinbox
            if isinstance(widget, (tk.Entry, tk.Spinbox)):
                widget.configure(
                    insertbackground=self.fg_main,
                    selectbackground=self.bg_hover,
                    selectforeground=self.fg_main
                )

            widget.update_idletasks()
        except Exception as e:
            print(f"[ThemeManager] Erreur de mise à jour du widget {widget}: {e}")

    def apply_theme(self):
        if self.root:
            if 'bg' in self.root.config():
                self.root.configure(bg=self.bg_main)
            self.root.update_idletasks()

        for widget_info in self.widgets:
            self._update_widget_appearance(widget_info)
