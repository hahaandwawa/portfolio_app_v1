"""Transactions management view."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from app.app_context import AppContext
from app.domain.models import TransactionType


class TransactionsView:
    """
    View for managing transactions (ledger entries).

    Shows transaction list with filtering and CRUD operations.
    """

    def __init__(self, parent: ttk.Notebook, context: AppContext):
        """
        Initialize transactions view.

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

        # Create filter bar
        self._create_filter_bar()

        # Create transactions list
        self._create_transactions_list()

    def _create_toolbar(self) -> None:
        """Create the toolbar with action buttons."""
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        # Add Transaction button
        add_btn = ttk.Button(
            toolbar,
            text="+ Add Transaction",
            command=self._on_add_transaction
        )
        add_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Quick action buttons
        ttk.Button(
            toolbar,
            text="Cash Deposit",
            command=lambda: self._on_quick_transaction(TransactionType.CASH_DEPOSIT)
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            toolbar,
            text="Buy",
            command=lambda: self._on_quick_transaction(TransactionType.BUY)
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            toolbar,
            text="Sell",
            command=lambda: self._on_quick_transaction(TransactionType.SELL)
        ).pack(side=tk.LEFT, padx=(0, 5))

        # Right side buttons
        ttk.Button(
            toolbar,
            text="Delete Selected",
            command=self._on_delete_transaction
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(
            toolbar,
            text="Edit Selected",
            command=self._on_edit_transaction
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(
            toolbar,
            text="Refresh",
            command=self.refresh
        ).pack(side=tk.RIGHT)

    def _create_filter_bar(self) -> None:
        """Create the filter bar."""
        filter_frame = ttk.LabelFrame(self.frame, text="Filters", padding="5")
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        # Account filter
        ttk.Label(filter_frame, text="Account:").pack(side=tk.LEFT, padx=(0, 5))
        self.account_var = tk.StringVar(value="All")
        self.account_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.account_var,
            state="readonly",
            width=20
        )
        self.account_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.account_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Type filter
        ttk.Label(filter_frame, text="Type:").pack(side=tk.LEFT, padx=(0, 5))
        self.type_var = tk.StringVar(value="All")
        self.type_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.type_var,
            values=["All", "BUY", "SELL", "CASH_DEPOSIT", "CASH_WITHDRAW"],
            state="readonly",
            width=15
        )
        self.type_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        # Symbol filter
        ttk.Label(filter_frame, text="Symbol:").pack(side=tk.LEFT, padx=(0, 5))
        self.symbol_var = tk.StringVar()
        self.symbol_entry = ttk.Entry(filter_frame, textvariable=self.symbol_var, width=10)
        self.symbol_entry.pack(side=tk.LEFT, padx=(0, 15))
        self.symbol_entry.bind("<Return>", lambda e: self.refresh())

        # Clear filters button
        ttk.Button(
            filter_frame,
            text="Clear Filters",
            command=self._clear_filters
        ).pack(side=tk.RIGHT)

    def _create_transactions_list(self) -> None:
        """Create the transactions list treeview."""
        list_frame = ttk.Frame(self.frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview with scrollbar
        self.txn_tree = ttk.Treeview(
            list_frame,
            columns=("date", "account", "type", "symbol", "quantity", "price", "amount", "fees", "note"),
            show="headings",
            selectmode="browse",
        )

        # Configure columns
        self.txn_tree.heading("date", text="Date/Time")
        self.txn_tree.heading("account", text="Account")
        self.txn_tree.heading("type", text="Type")
        self.txn_tree.heading("symbol", text="Symbol")
        self.txn_tree.heading("quantity", text="Quantity")
        self.txn_tree.heading("price", text="Price")
        self.txn_tree.heading("amount", text="Amount")
        self.txn_tree.heading("fees", text="Fees")
        self.txn_tree.heading("note", text="Note")

        self.txn_tree.column("date", width=140, minwidth=120)
        self.txn_tree.column("account", width=120, minwidth=100)
        self.txn_tree.column("type", width=100, anchor="center")
        self.txn_tree.column("symbol", width=80, anchor="center")
        self.txn_tree.column("quantity", width=80, anchor="e")
        self.txn_tree.column("price", width=80, anchor="e")
        self.txn_tree.column("amount", width=100, anchor="e")
        self.txn_tree.column("fees", width=60, anchor="e")
        self.txn_tree.column("note", width=150)

        # Scrollbars
        y_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.txn_tree.yview)
        x_scroll = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.txn_tree.xview)
        self.txn_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        # Grid layout
        self.txn_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # Double-click to edit
        self.txn_tree.bind("<Double-1>", lambda e: self._on_edit_transaction())

    def _clear_filters(self) -> None:
        """Clear all filters."""
        self.account_var.set("All")
        self.type_var.set("All")
        self.symbol_var.set("")
        self.refresh()

    def _on_add_transaction(self) -> None:
        """Handle add transaction action."""
        from app.ui.dialogs.transaction_dialog import TransactionDialog
        dialog = TransactionDialog(self.frame, self.context)
        if dialog.result:
            self.context.refresh_session()
            self.refresh()

    def _on_quick_transaction(self, txn_type: TransactionType) -> None:
        """Handle quick transaction buttons."""
        from app.ui.dialogs.transaction_dialog import TransactionDialog
        dialog = TransactionDialog(self.frame, self.context, default_type=txn_type)
        if dialog.result:
            self.context.refresh_session()
            self.refresh()

    def _on_edit_transaction(self) -> None:
        """Handle edit transaction action."""
        selection = self.txn_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a transaction to edit.")
            return

        txn_id = selection[0]
        from app.ui.dialogs.transaction_dialog import TransactionDialog
        dialog = TransactionDialog(self.frame, self.context, edit_txn_id=txn_id)
        if dialog.result:
            self.context.refresh_session()
            self.refresh()

    def _on_delete_transaction(self) -> None:
        """Handle delete transaction action."""
        selection = self.txn_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a transaction to delete.")
            return

        txn_id = selection[0]
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this transaction?"):
            try:
                self.context.ledger.soft_delete_transaction(txn_id)

                # Rebuild portfolio for affected account
                transactions = self.context.ledger.query_transactions(include_deleted=True)
                txn = next((t for t in transactions if t.txn_id == txn_id), None)
                if txn:
                    self.context.portfolio.rebuild_account(txn.account_id)

                self.context.refresh_session()
                self.refresh()
                messagebox.showinfo("Success", "Transaction deleted.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete transaction:\n{str(e)}")

    def refresh(self) -> None:
        """Refresh the transactions list."""
        # Clear existing items
        for item in self.txn_tree.get_children():
            self.txn_tree.delete(item)

        try:
            # Update account combo
            accounts = self.context.ledger.list_accounts()
            account_names = ["All"] + [a.name for a in accounts]
            self.account_combo["values"] = account_names

            # Build account lookup
            account_lookup = {a.account_id: a.name for a in accounts}
            name_to_id = {a.name: a.account_id for a in accounts}

            # Build filters
            account_ids = None
            if self.account_var.get() != "All":
                account_name = self.account_var.get()
                if account_name in name_to_id:
                    account_ids = [name_to_id[account_name]]

            txn_types = None
            if self.type_var.get() != "All":
                txn_types = [TransactionType(self.type_var.get())]

            symbols = None
            if self.symbol_var.get().strip():
                symbols = [self.symbol_var.get().strip().upper()]

            # Query transactions
            transactions = self.context.ledger.query_transactions(
                account_ids=account_ids,
                txn_types=txn_types,
                symbols=symbols,
            )

            # Sort by date descending
            transactions.sort(key=lambda t: t.txn_time_est, reverse=True)

            for txn in transactions:
                # Calculate amount
                if txn.txn_type in (TransactionType.BUY, TransactionType.SELL):
                    amount = (txn.quantity or 0) * (txn.price or 0)
                    amount_str = f"${amount:,.2f}"
                else:
                    amount_str = f"${txn.cash_amount:,.2f}" if txn.cash_amount else "--"

                self.txn_tree.insert(
                    "",
                    tk.END,
                    iid=txn.txn_id,
                    values=(
                        txn.txn_time_est.strftime("%Y-%m-%d %H:%M") if txn.txn_time_est else "--",
                        account_lookup.get(txn.account_id, txn.account_id),
                        txn.txn_type.value,
                        txn.symbol or "--",
                        f"{txn.quantity:.4f}" if txn.quantity else "--",
                        f"${txn.price:.2f}" if txn.price else "--",
                        amount_str,
                        f"${txn.fees:.2f}" if txn.fees else "$0.00",
                        txn.note or "",
                    )
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load transactions:\n{str(e)}")
