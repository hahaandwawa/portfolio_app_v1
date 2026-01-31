"""Accounts management view."""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional
from decimal import Decimal

from app.app_context import AppContext
from app.domain.models import CostBasisMethod


class AccountsView:
    """
    View for managing investment accounts.

    Shows list of accounts with their holdings and cash balances.
    """

    def __init__(self, parent: ttk.Notebook, context: AppContext):
        """
        Initialize accounts view.

        Args:
            parent: Parent notebook widget
            context: Application context
        """
        self.parent = parent
        self.context = context

        # Create main frame
        self.frame = ttk.Frame(parent, padding="10")

        # Create toolbar
        self._create_toolbar()

        # Create accounts list
        self._create_accounts_list()

        # Create account details panel
        self._create_details_panel()

    def _create_toolbar(self) -> None:
        """Create the toolbar with action buttons."""
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        # Add Account button
        add_btn = ttk.Button(
            toolbar,
            text="+ New Account",
            command=self._on_add_account
        )
        add_btn.pack(side=tk.LEFT)

        # Refresh button
        refresh_btn = ttk.Button(
            toolbar,
            text="Refresh",
            command=self.refresh
        )
        refresh_btn.pack(side=tk.RIGHT)

    def _create_accounts_list(self) -> None:
        """Create the accounts list treeview."""
        # Container frame
        list_frame = ttk.LabelFrame(self.frame, text="Accounts", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Treeview with scrollbar
        tree_container = ttk.Frame(list_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.accounts_tree = ttk.Treeview(
            tree_container,
            columns=("name", "holdings", "cash", "total", "method"),
            show="headings",
            selectmode="browse",
        )

        # Configure columns
        self.accounts_tree.heading("name", text="Account Name")
        self.accounts_tree.heading("holdings", text="Holdings Value")
        self.accounts_tree.heading("cash", text="Cash")
        self.accounts_tree.heading("total", text="Total Value")
        self.accounts_tree.heading("method", text="Cost Basis")

        self.accounts_tree.column("name", width=200, minwidth=150)
        self.accounts_tree.column("holdings", width=120, anchor="e")
        self.accounts_tree.column("cash", width=120, anchor="e")
        self.accounts_tree.column("total", width=120, anchor="e")
        self.accounts_tree.column("method", width=100, anchor="center")

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            tree_container,
            orient=tk.VERTICAL,
            command=self.accounts_tree.yview
        )
        self.accounts_tree.configure(yscrollcommand=scrollbar.set)

        self.accounts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind selection event
        self.accounts_tree.bind("<<TreeviewSelect>>", self._on_account_selected)

    def _create_details_panel(self) -> None:
        """Create the account details panel."""
        details_frame = ttk.LabelFrame(self.frame, text="Account Details", padding="10")
        details_frame.pack(fill=tk.X)

        # Account name
        name_frame = ttk.Frame(details_frame)
        name_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(name_frame, text="Name:", width=15).pack(side=tk.LEFT)
        self.detail_name = ttk.Label(name_frame, text="--")
        self.detail_name.pack(side=tk.LEFT)

        # Holdings
        holdings_frame = ttk.Frame(details_frame)
        holdings_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(holdings_frame, text="Holdings:", width=15).pack(side=tk.LEFT)
        self.detail_holdings = ttk.Label(holdings_frame, text="--")
        self.detail_holdings.pack(side=tk.LEFT)

        # Cash
        cash_frame = ttk.Frame(details_frame)
        cash_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(cash_frame, text="Cash Balance:", width=15).pack(side=tk.LEFT)
        self.detail_cash = ttk.Label(cash_frame, text="--")
        self.detail_cash.pack(side=tk.LEFT)

        # Positions list
        positions_frame = ttk.Frame(details_frame)
        positions_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(positions_frame, text="Positions:", style='Heading.TLabel').pack(anchor=tk.W)

        self.positions_text = tk.Text(positions_frame, height=6, width=60, state=tk.DISABLED)
        self.positions_text.pack(fill=tk.X, pady=(5, 0))

    def _on_add_account(self) -> None:
        """Handle add account action."""
        name = simpledialog.askstring(
            "New Account",
            "Enter account name:",
            parent=self.frame
        )
        if name:
            try:
                account = self.context.ledger.create_account(name.strip())
                self.refresh()
                messagebox.showinfo("Success", f"Account '{account.name}' created.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create account:\n{str(e)}")

    def _on_account_selected(self, event) -> None:
        """Handle account selection."""
        selection = self.accounts_tree.selection()
        if not selection:
            return

        item = self.accounts_tree.item(selection[0])
        account_id = selection[0]  # We use account_id as item ID

        # Update details panel
        try:
            account = self.context.ledger.get_account(account_id)
            self.detail_name.config(text=account.name)

            # Get positions
            positions = self.context.portfolio.get_positions(account_id)
            cash = self.context.portfolio.get_cash_balance(account_id)

            # Get prices for positions
            if positions:
                symbols = [p.symbol for p in positions]
                quotes = self.context.market_data.get_quotes(symbols)

                holdings_value = Decimal("0")
                positions_text = ""
                for p in positions:
                    quote = quotes.get(p.symbol)
                    if quote:
                        value = p.shares * quote.last_price
                        holdings_value += value
                        positions_text += f"{p.symbol}: {p.shares} shares @ ${quote.last_price:.2f} = ${value:,.2f}\n"
                    else:
                        positions_text += f"{p.symbol}: {p.shares} shares (no price)\n"

                self.detail_holdings.config(text=f"${holdings_value:,.2f}")

                self.positions_text.config(state=tk.NORMAL)
                self.positions_text.delete(1.0, tk.END)
                self.positions_text.insert(tk.END, positions_text.strip() or "No positions")
                self.positions_text.config(state=tk.DISABLED)
            else:
                self.detail_holdings.config(text="$0.00")
                self.positions_text.config(state=tk.NORMAL)
                self.positions_text.delete(1.0, tk.END)
                self.positions_text.insert(tk.END, "No positions")
                self.positions_text.config(state=tk.DISABLED)

            self.detail_cash.config(text=f"${cash:,.2f}")

        except Exception as e:
            self.detail_name.config(text="Error loading details")
            self.detail_holdings.config(text="--")
            self.detail_cash.config(text="--")

    def refresh(self) -> None:
        """Refresh the accounts list."""
        # Clear existing items
        for item in self.accounts_tree.get_children():
            self.accounts_tree.delete(item)

        try:
            accounts = self.context.ledger.list_accounts()

            for account in accounts:
                # Get positions and cash for each account
                positions = self.context.portfolio.get_positions(account.account_id)
                cash = self.context.portfolio.get_cash_balance(account.account_id)

                # Calculate holdings value
                holdings_value = Decimal("0")
                if positions:
                    symbols = [p.symbol for p in positions]
                    quotes = self.context.market_data.get_quotes(symbols)
                    for p in positions:
                        quote = quotes.get(p.symbol)
                        if quote:
                            holdings_value += p.shares * quote.last_price

                total = holdings_value + cash

                self.accounts_tree.insert(
                    "",
                    tk.END,
                    iid=account.account_id,
                    values=(
                        account.name,
                        f"${holdings_value:,.2f}",
                        f"${cash:,.2f}",
                        f"${total:,.2f}",
                        account.cost_basis_method.value,
                    )
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load accounts:\n{str(e)}")
