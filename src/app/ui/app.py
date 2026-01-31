"""Desktop application main class."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional

from app.app_context import AppContext, get_app_context, set_app_context
from app.config.settings import get_settings, get_default_data_dir


class DesktopApp:
    """
    Main desktop application class.

    Manages the Tkinter root window, application context, and lifecycle.
    """

    def __init__(self):
        """Initialize the desktop application."""
        self.root: Optional[tk.Tk] = None
        self.context: Optional[AppContext] = None
        self.main_window = None

    def run(self) -> None:
        """Start the desktop application."""
        # Create root window
        self.root = tk.Tk()
        self.root.title("Investment Management App")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        # Set up app icon (if available)
        try:
            # macOS app icon
            self.root.createcommand('tk::mac::ReopenApplication', self._on_reopen)
        except tk.TclError:
            pass

        # Configure ttk style
        self._configure_style()

        # Check for first run / data directory
        if not self._check_data_directory():
            self.root.destroy()
            return

        # Initialize application context
        self.context = get_app_context()
        self.context.initialize()

        # Create main window
        from app.ui.main_window import MainWindow
        self.main_window = MainWindow(self.root, self.context)

        # Set up menu bar
        self._create_menu_bar()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start event loop
        self.root.mainloop()

    def _configure_style(self) -> None:
        """Configure ttk styles for consistent appearance."""
        style = ttk.Style()

        # Try to use a native-looking theme
        available_themes = style.theme_names()
        if 'aqua' in available_themes:  # macOS
            style.theme_use('aqua')
        elif 'clam' in available_themes:
            style.theme_use('clam')

        # Configure common styles
        style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'))
        style.configure('Heading.TLabel', font=('Helvetica', 12, 'bold'))
        style.configure('Info.TLabel', font=('Helvetica', 10))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Positive.TLabel', foreground='green', font=('Helvetica', 12, 'bold'))
        style.configure('Negative.TLabel', foreground='red', font=('Helvetica', 12, 'bold'))

    def _check_data_directory(self) -> bool:
        """
        Check if data directory exists or prompt user to select one.

        Returns True if a valid directory is configured, False to abort.
        """
        settings = get_settings()
        default_dir = get_default_data_dir()

        # Check if default directory exists and has data
        if default_dir.exists() and (default_dir / "investment.db").exists():
            return True

        # First run - show dialog
        from app.ui.dialogs.first_run import FirstRunDialog
        dialog = FirstRunDialog(self.root, default_dir)
        result = dialog.result

        if result is None:
            return False  # User cancelled

        return True

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Import CSV...", command=self._on_import_csv)
        file_menu.add_command(label="Export CSV...", command=self._on_export_csv)
        file_menu.add_command(label="Download Template...", command=self._on_download_template)
        file_menu.add_separator()
        file_menu.add_command(label="Preferences...", command=self._on_preferences)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._on_close, accelerator="Cmd+Q")

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Refresh", command=self._on_refresh, accelerator="Cmd+R")

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._on_about)

        # macOS-specific menu handling
        try:
            self.root.createcommand('tk::mac::ShowPreferences', self._on_preferences)
            self.root.createcommand('tk::mac::Quit', self._on_close)
        except tk.TclError:
            pass

    def _on_import_csv(self) -> None:
        """Handle CSV import."""
        filepath = filedialog.askopenfilename(
            title="Import Transactions",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if filepath:
            try:
                summary = self.context.csv_importer.import_csv(filepath)
                self.context.refresh_session()
                self.main_window.refresh_all()

                message = (
                    f"Import complete!\n\n"
                    f"Imported: {summary.imported_count}\n"
                    f"Errors: {summary.error_count}"
                )
                if summary.errors:
                    message += f"\n\nFirst errors:\n" + "\n".join(summary.errors[:5])

                messagebox.showinfo("Import Complete", message)
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import CSV:\n{str(e)}")

    def _on_export_csv(self) -> None:
        """Handle CSV export."""
        export_dir = get_settings().get_export_dir()
        filepath = filedialog.asksaveasfilename(
            title="Export Transactions",
            initialdir=export_dir,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if filepath:
            try:
                self.context.csv_exporter.export_csv(filepath)
                messagebox.showinfo("Export Complete", f"Transactions exported to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export CSV:\n{str(e)}")

    def _on_download_template(self) -> None:
        """Handle template download."""
        export_dir = get_settings().get_export_dir()
        filepath = filedialog.asksaveasfilename(
            title="Save Import Template",
            initialdir=export_dir,
            initialfile="import_template.csv",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if filepath:
            try:
                self.context.csv_template.generate_template(filepath)
                messagebox.showinfo("Template Saved", f"Import template saved to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save template:\n{str(e)}")

    def _on_preferences(self) -> None:
        """Show preferences dialog."""
        from app.ui.dialogs.preferences import PreferencesDialog
        dialog = PreferencesDialog(self.root, self.context)
        if dialog.result:
            # Preferences changed, reinitialize
            self.context.initialize(dialog.result.get('data_dir'))
            self.main_window.refresh_all()

    def _on_refresh(self) -> None:
        """Refresh all views."""
        self.context.refresh_session()
        self.main_window.refresh_all()

    def _on_about(self) -> None:
        """Show about dialog."""
        settings = get_settings()
        messagebox.showinfo(
            "About",
            f"{settings.app_name}\n"
            f"Version {settings.app_version}\n\n"
            f"A local-first investment tracking application.\n\n"
            f"Data directory:\n{self.context.data_dir}"
        )

    def _on_reopen(self) -> None:
        """Handle macOS dock click to reopen."""
        if self.root:
            self.root.deiconify()

    def _on_close(self) -> None:
        """Handle application close."""
        if self.context:
            self.context.close()
        if self.root:
            self.root.destroy()
