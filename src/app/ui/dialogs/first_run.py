"""First run dialog for data directory selection."""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from typing import Optional

from app.config.settings import Settings, set_settings


class FirstRunDialog:
    """
    Dialog shown on first run to select data directory.

    Allows user to choose where to store application data.
    """

    def __init__(self, parent: tk.Tk, default_dir: Path):
        """
        Initialize first run dialog.

        Args:
            parent: Parent window
            default_dir: Default data directory path
        """
        self.parent = parent
        self.default_dir = default_dir
        self.result: Optional[Path] = None

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Welcome to Investment Management App")
        self.dialog.geometry("500x300")
        self.dialog.resizable(False, False)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 500) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 300) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Create content
        self._create_content()

        # Handle close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Wait for dialog to close
        parent.wait_window(self.dialog)

    def _create_content(self) -> None:
        """Create dialog content."""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Welcome message
        ttk.Label(
            main_frame,
            text="Welcome!",
            font=('Helvetica', 18, 'bold')
        ).pack(anchor=tk.W)

        ttk.Label(
            main_frame,
            text="Choose where to store your investment data.",
            font=('Helvetica', 12)
        ).pack(anchor=tk.W, pady=(5, 20))

        # Description
        desc_text = (
            "All your data (database, exports, logs) will be stored in this folder.\n"
            "You can back up or move this folder to transfer your data."
        )
        ttk.Label(
            main_frame,
            text=desc_text,
            wraplength=450,
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 20))

        # Path selection frame
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(path_frame, text="Data folder:").pack(anchor=tk.W)

        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.pack(fill=tk.X, pady=(5, 0))

        self.path_var = tk.StringVar(value=str(self.default_dir))
        self.path_entry = ttk.Entry(
            path_entry_frame,
            textvariable=self.path_var,
            width=50
        )
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ttk.Button(
            path_entry_frame,
            text="Browse...",
            command=self._on_browse
        ).pack(side=tk.RIGHT)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel
        ).pack(side=tk.LEFT)

        ttk.Button(
            button_frame,
            text="Continue",
            command=self._on_continue
        ).pack(side=tk.RIGHT)

    def _on_browse(self) -> None:
        """Handle browse button click."""
        path = filedialog.askdirectory(
            parent=self.dialog,
            title="Select Data Folder",
            initialdir=str(self.default_dir.parent),
        )
        if path:
            self.path_var.set(path)

    def _on_continue(self) -> None:
        """Handle continue button click."""
        path = Path(self.path_var.get())

        # Create directory if it doesn't exist
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            tk.messagebox.showerror(
                "Error",
                f"Cannot create directory:\n{str(e)}",
                parent=self.dialog
            )
            return

        # Update settings
        settings = Settings(data_dir=path)
        set_settings(settings)

        self.result = path
        self.dialog.destroy()

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self.result = None
        self.dialog.destroy()
