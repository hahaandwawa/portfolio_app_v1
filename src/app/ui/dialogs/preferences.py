"""Preferences dialog."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, Dict, Any

from app.app_context import AppContext
from app.config.settings import get_settings


class PreferencesDialog:
    """
    Preferences dialog for application settings.

    Allows user to change data directory and other settings.
    """

    def __init__(self, parent, context: AppContext):
        """
        Initialize preferences dialog.

        Args:
            parent: Parent window
            context: Application context
        """
        self.parent = parent
        self.context = context
        self.result: Optional[Dict[str, Any]] = None

        # Get current settings
        self.settings = get_settings()

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Preferences")
        self.dialog.geometry("500x250")
        self.dialog.resizable(False, False)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.update_idletasks()
        parent_widget = parent if isinstance(parent, tk.Tk) else parent.winfo_toplevel()
        x = parent_widget.winfo_x() + (parent_widget.winfo_width() - 500) // 2
        y = parent_widget.winfo_y() + (parent_widget.winfo_height() - 250) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Create content
        self._create_content()

        # Handle close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Wait for dialog to close
        parent_widget.wait_window(self.dialog)

    def _create_content(self) -> None:
        """Create dialog content."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(
            main_frame,
            text="Preferences",
            font=('Helvetica', 16, 'bold')
        ).pack(anchor=tk.W, pady=(0, 20))

        # Data directory section
        data_frame = ttk.LabelFrame(main_frame, text="Data Storage", padding="10")
        data_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(data_frame, text="Data folder:").pack(anchor=tk.W)

        path_entry_frame = ttk.Frame(data_frame)
        path_entry_frame.pack(fill=tk.X, pady=(5, 0))

        self.path_var = tk.StringVar(value=str(self.settings.get_data_dir()))
        self.path_entry = ttk.Entry(
            path_entry_frame,
            textvariable=self.path_var,
            width=45
        )
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(
            path_entry_frame,
            text="Browse...",
            command=self._on_browse
        ).pack(side=tk.RIGHT)

        # Info label
        ttk.Label(
            data_frame,
            text="Changing this will require an app restart.",
            style='Info.TLabel'
        ).pack(anchor=tk.W, pady=(5, 0))

        # Options section
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 15))

        self.enforce_cash_var = tk.BooleanVar(value=self.settings.enforce_cash_balance)
        ttk.Checkbutton(
            options_frame,
            text="Enforce cash balance (prevent overdrafts)",
            variable=self.enforce_cash_var
        ).pack(anchor=tk.W)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel
        ).pack(side=tk.LEFT)

        ttk.Button(
            button_frame,
            text="Save",
            command=self._on_save
        ).pack(side=tk.RIGHT)

    def _on_browse(self) -> None:
        """Handle browse button click."""
        current_path = Path(self.path_var.get())
        path = filedialog.askdirectory(
            parent=self.dialog,
            title="Select Data Folder",
            initialdir=str(current_path.parent if current_path.exists() else Path.home()),
        )
        if path:
            self.path_var.set(path)

    def _on_save(self) -> None:
        """Handle save button click."""
        new_path = Path(self.path_var.get())
        current_path = self.settings.get_data_dir()

        # Check if path changed
        if new_path != current_path:
            # Confirm change
            if not messagebox.askyesno(
                "Confirm Change",
                "Changing the data directory requires an app restart.\n\n"
                "Your existing data will remain in the old location.\n"
                "Continue?",
                parent=self.dialog
            ):
                return

            # Validate new path
            try:
                new_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Cannot create directory:\n{str(e)}",
                    parent=self.dialog
                )
                return

        self.result = {
            'data_dir': new_path,
            'enforce_cash_balance': self.enforce_cash_var.get(),
        }
        self.dialog.destroy()

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self.result = None
        self.dialog.destroy()
