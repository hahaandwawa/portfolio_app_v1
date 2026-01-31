"""Main application window with navigation."""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from app.app_context import AppContext


class MainWindow:
    """
    Main application window with tabbed navigation.

    Contains tabs for Accounts, Transactions, and Analysis views.
    """

    def __init__(self, root: tk.Tk, context: AppContext):
        """
        Initialize main window.

        Args:
            root: Tkinter root window
            context: Application context
        """
        self.root = root
        self.context = context

        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create header
        self._create_header()

        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Create views
        from app.ui.views import AccountsView, TransactionsView, AnalysisView

        self.accounts_view = AccountsView(self.notebook, context)
        self.transactions_view = TransactionsView(self.notebook, context)
        self.analysis_view = AnalysisView(self.notebook, context)

        # Add tabs
        self.notebook.add(self.accounts_view.frame, text="  Accounts  ")
        self.notebook.add(self.transactions_view.frame, text="  Transactions  ")
        self.notebook.add(self.analysis_view.frame, text="  Analysis  ")

        # Bind tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Initial load
        self.refresh_all()

    def _create_header(self) -> None:
        """Create the header section with summary info."""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # App title
        title_label = ttk.Label(
            header_frame,
            text="Investment Portfolio",
            style='Title.TLabel'
        )
        title_label.pack(side=tk.LEFT)

        # Summary info (right side)
        self.summary_frame = ttk.Frame(header_frame)
        self.summary_frame.pack(side=tk.RIGHT)

        # Today's P/L label
        self.pnl_label = ttk.Label(
            self.summary_frame,
            text="Today's P/L: --",
            style='Heading.TLabel'
        )
        self.pnl_label.pack(side=tk.RIGHT, padx=(20, 0))

        # Total value label
        self.total_label = ttk.Label(
            self.summary_frame,
            text="Total: --",
            style='Heading.TLabel'
        )
        self.total_label.pack(side=tk.RIGHT)

    def _on_tab_changed(self, event) -> None:
        """Handle tab change event."""
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 0:
            self.accounts_view.refresh()
        elif selected_tab == 1:
            self.transactions_view.refresh()
        elif selected_tab == 2:
            self.analysis_view.refresh()

    def refresh_all(self) -> None:
        """Refresh all views and header."""
        self._update_header_summary()
        self.accounts_view.refresh()
        self.transactions_view.refresh()
        self.analysis_view.refresh()

    def _update_header_summary(self) -> None:
        """Update the header summary information."""
        try:
            # Get all accounts
            accounts = self.context.ledger.list_accounts()
            account_ids = [a.account_id for a in accounts]

            if account_ids:
                # Calculate total value
                positions = self.context.analysis.get_positions_with_prices(account_ids)
                cash = self.context.portfolio.aggregate_cash(account_ids)

                total_value = cash
                for p in positions:
                    if p.market_value:
                        total_value += p.market_value

                self.total_label.config(text=f"Total: ${total_value:,.2f}")

                # Calculate today's P/L
                pnl = self.context.analysis.today_pnl(account_ids)
                pnl_text = f"Today's P/L: ${pnl.pnl_dollars:+,.2f}"
                if pnl.pnl_percent is not None:
                    pnl_text += f" ({pnl.pnl_percent:+.2f}%)"

                # Set color based on P/L
                if pnl.pnl_dollars > 0:
                    self.pnl_label.config(text=pnl_text, style='Positive.TLabel')
                elif pnl.pnl_dollars < 0:
                    self.pnl_label.config(text=pnl_text, style='Negative.TLabel')
                else:
                    self.pnl_label.config(text=pnl_text, style='Heading.TLabel')
            else:
                self.total_label.config(text="Total: $0.00")
                self.pnl_label.config(text="Today's P/L: $0.00", style='Heading.TLabel')

        except Exception as e:
            self.total_label.config(text="Total: --")
            self.pnl_label.config(text=f"Error: {str(e)[:30]}", style='Error.TLabel')
