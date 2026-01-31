"""Transaction add/edit dialog."""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.app_context import AppContext
from app.domain.models import TransactionType
from app.services import TransactionCreate, TransactionUpdate
from app.core.timezone import now_eastern


class TransactionDialog:
    """
    Dialog for adding or editing transactions.

    Supports all transaction types: BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAW.
    """

    def __init__(
        self,
        parent,
        context: AppContext,
        edit_txn_id: Optional[str] = None,
        default_type: Optional[TransactionType] = None,
    ):
        """
        Initialize transaction dialog.

        Args:
            parent: Parent window
            context: Application context
            edit_txn_id: Transaction ID to edit (None for new)
            default_type: Default transaction type for new transactions
        """
        self.parent = parent
        self.context = context
        self.edit_txn_id = edit_txn_id
        self.default_type = default_type
        self.result: Optional[bool] = None
        self.editing_txn = None

        # Load transaction if editing
        if edit_txn_id:
            transactions = context.ledger.query_transactions(include_deleted=True)
            self.editing_txn = next(
                (t for t in transactions if t.txn_id == edit_txn_id),
                None
            )

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Transaction" if edit_txn_id else "Add Transaction")
        self.dialog.geometry("450x400")
        self.dialog.resizable(False, False)

        # Make modal
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.update_idletasks()
        parent_widget = parent if isinstance(parent, tk.Tk) else parent.winfo_toplevel()
        x = parent_widget.winfo_x() + (parent_widget.winfo_width() - 450) // 2
        y = parent_widget.winfo_y() + (parent_widget.winfo_height() - 400) // 2
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

        # Account selection
        account_frame = ttk.Frame(main_frame)
        account_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(account_frame, text="Account:", width=12).pack(side=tk.LEFT)

        accounts = self.context.ledger.list_accounts()
        self.account_lookup = {a.name: a.account_id for a in accounts}
        account_names = [a.name for a in accounts]

        self.account_var = tk.StringVar()
        self.account_combo = ttk.Combobox(
            account_frame,
            textvariable=self.account_var,
            values=account_names,
            state="readonly" if not self.edit_txn_id else "disabled",
            width=30
        )
        self.account_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        if self.editing_txn:
            # Find account name
            for name, aid in self.account_lookup.items():
                if aid == self.editing_txn.account_id:
                    self.account_var.set(name)
                    break
        elif account_names:
            self.account_var.set(account_names[0])

        # Transaction type
        type_frame = ttk.Frame(main_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(type_frame, text="Type:", width=12).pack(side=tk.LEFT)

        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(
            type_frame,
            textvariable=self.type_var,
            values=["BUY", "SELL", "CASH_DEPOSIT", "CASH_WITHDRAW"],
            state="readonly" if not self.edit_txn_id else "disabled",
            width=30
        )
        self.type_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)

        if self.editing_txn:
            self.type_var.set(self.editing_txn.txn_type.value)
        elif self.default_type:
            self.type_var.set(self.default_type.value)
        else:
            self.type_var.set("BUY")

        # Date/Time
        datetime_frame = ttk.Frame(main_frame)
        datetime_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(datetime_frame, text="Date/Time:", width=12).pack(side=tk.LEFT)

        now = now_eastern()
        if self.editing_txn and self.editing_txn.txn_time_est:
            default_dt = self.editing_txn.txn_time_est.strftime("%Y-%m-%d %H:%M")
        else:
            default_dt = now.strftime("%Y-%m-%d %H:%M")

        self.datetime_var = tk.StringVar(value=default_dt)
        self.datetime_entry = ttk.Entry(
            datetime_frame,
            textvariable=self.datetime_var,
            width=32
        )
        self.datetime_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Symbol (for BUY/SELL)
        self.symbol_frame = ttk.Frame(main_frame)
        self.symbol_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.symbol_frame, text="Symbol:", width=12).pack(side=tk.LEFT)

        self.symbol_var = tk.StringVar(
            value=self.editing_txn.symbol if self.editing_txn and self.editing_txn.symbol else ""
        )
        self.symbol_entry = ttk.Entry(
            self.symbol_frame,
            textvariable=self.symbol_var,
            width=32
        )
        self.symbol_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Quantity (for BUY/SELL)
        self.quantity_frame = ttk.Frame(main_frame)
        self.quantity_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.quantity_frame, text="Quantity:", width=12).pack(side=tk.LEFT)

        qty_val = str(self.editing_txn.quantity) if self.editing_txn and self.editing_txn.quantity else ""
        self.quantity_var = tk.StringVar(value=qty_val)
        self.quantity_entry = ttk.Entry(
            self.quantity_frame,
            textvariable=self.quantity_var,
            width=32
        )
        self.quantity_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Price (for BUY/SELL)
        self.price_frame = ttk.Frame(main_frame)
        self.price_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.price_frame, text="Price:", width=12).pack(side=tk.LEFT)

        price_val = str(self.editing_txn.price) if self.editing_txn and self.editing_txn.price else ""
        self.price_var = tk.StringVar(value=price_val)
        self.price_entry = ttk.Entry(
            self.price_frame,
            textvariable=self.price_var,
            width=32
        )
        self.price_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Cash Amount (for CASH_DEPOSIT/CASH_WITHDRAW)
        self.cash_frame = ttk.Frame(main_frame)
        self.cash_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.cash_frame, text="Amount:", width=12).pack(side=tk.LEFT)

        cash_val = str(self.editing_txn.cash_amount) if self.editing_txn and self.editing_txn.cash_amount else ""
        self.cash_var = tk.StringVar(value=cash_val)
        self.cash_entry = ttk.Entry(
            self.cash_frame,
            textvariable=self.cash_var,
            width=32
        )
        self.cash_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Fees
        fees_frame = ttk.Frame(main_frame)
        fees_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(fees_frame, text="Fees:", width=12).pack(side=tk.LEFT)

        fees_val = str(self.editing_txn.fees) if self.editing_txn else "0"
        self.fees_var = tk.StringVar(value=fees_val)
        self.fees_entry = ttk.Entry(
            fees_frame,
            textvariable=self.fees_var,
            width=32
        )
        self.fees_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Note
        note_frame = ttk.Frame(main_frame)
        note_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(note_frame, text="Note:", width=12).pack(side=tk.LEFT)

        self.note_var = tk.StringVar(
            value=self.editing_txn.note if self.editing_txn and self.editing_txn.note else ""
        )
        self.note_entry = ttk.Entry(
            note_frame,
            textvariable=self.note_var,
            width=32
        )
        self.note_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

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
            text="Save",
            command=self._on_save
        ).pack(side=tk.RIGHT)

        # Update field visibility
        self._on_type_changed(None)

    def _on_type_changed(self, event) -> None:
        """Update field visibility based on transaction type."""
        txn_type = self.type_var.get()
        is_stock = txn_type in ("BUY", "SELL")
        is_cash = txn_type in ("CASH_DEPOSIT", "CASH_WITHDRAW")

        # Show/hide stock fields
        if is_stock:
            self.symbol_frame.pack(fill=tk.X, pady=(0, 10), after=self.dialog.nametowidget(self.type_combo.winfo_parent()))
            self.quantity_frame.pack(fill=tk.X, pady=(0, 10), after=self.symbol_frame)
            self.price_frame.pack(fill=tk.X, pady=(0, 10), after=self.quantity_frame)
            self.cash_frame.pack_forget()
        else:
            self.symbol_frame.pack_forget()
            self.quantity_frame.pack_forget()
            self.price_frame.pack_forget()

        # Show/hide cash fields
        if is_cash:
            self.cash_frame.pack(fill=tk.X, pady=(0, 10))
        else:
            if not is_stock:
                self.cash_frame.pack_forget()

    def _on_save(self) -> None:
        """Handle save button click."""
        try:
            # Validate and parse inputs
            account_name = self.account_var.get()
            if not account_name or account_name not in self.account_lookup:
                messagebox.showerror("Error", "Please select an account.", parent=self.dialog)
                return

            account_id = self.account_lookup[account_name]
            txn_type = TransactionType(self.type_var.get())

            # Parse datetime
            try:
                txn_time = datetime.strptime(self.datetime_var.get(), "%Y-%m-%d %H:%M")
            except ValueError:
                messagebox.showerror(
                    "Error",
                    "Invalid date format. Use: YYYY-MM-DD HH:MM",
                    parent=self.dialog
                )
                return

            # Parse fees
            try:
                fees = Decimal(self.fees_var.get() or "0")
            except InvalidOperation:
                messagebox.showerror("Error", "Invalid fees amount.", parent=self.dialog)
                return

            note = self.note_var.get().strip() or None

            if txn_type in (TransactionType.BUY, TransactionType.SELL):
                # Validate stock transaction
                symbol = self.symbol_var.get().strip().upper()
                if not symbol:
                    messagebox.showerror("Error", "Symbol is required.", parent=self.dialog)
                    return

                try:
                    quantity = Decimal(self.quantity_var.get())
                    if quantity <= 0:
                        raise ValueError()
                except (InvalidOperation, ValueError):
                    messagebox.showerror("Error", "Quantity must be a positive number.", parent=self.dialog)
                    return

                try:
                    price = Decimal(self.price_var.get())
                    if price < 0:
                        raise ValueError()
                except (InvalidOperation, ValueError):
                    messagebox.showerror("Error", "Price must be a non-negative number.", parent=self.dialog)
                    return

                if self.editing_txn:
                    patch = TransactionUpdate(
                        txn_time_est=txn_time,
                        symbol=symbol,
                        quantity=quantity,
                        price=price,
                        fees=fees,
                        note=note,
                    )
                    self.context.ledger.edit_transaction(self.edit_txn_id, patch)
                else:
                    data = TransactionCreate(
                        account_id=account_id,
                        txn_type=txn_type,
                        txn_time_est=txn_time,
                        symbol=symbol,
                        quantity=quantity,
                        price=price,
                        fees=fees,
                        note=note,
                    )
                    self.context.ledger.add_transaction(data)

            else:
                # Validate cash transaction
                try:
                    cash_amount = Decimal(self.cash_var.get())
                    if cash_amount <= 0:
                        raise ValueError()
                except (InvalidOperation, ValueError):
                    messagebox.showerror("Error", "Amount must be a positive number.", parent=self.dialog)
                    return

                if self.editing_txn:
                    patch = TransactionUpdate(
                        txn_time_est=txn_time,
                        cash_amount=cash_amount,
                        fees=fees,
                        note=note,
                    )
                    self.context.ledger.edit_transaction(self.edit_txn_id, patch)
                else:
                    data = TransactionCreate(
                        account_id=account_id,
                        txn_type=txn_type,
                        txn_time_est=txn_time,
                        cash_amount=cash_amount,
                        fees=fees,
                        note=note,
                    )
                    self.context.ledger.add_transaction(data)

            # Rebuild portfolio
            self.context.portfolio.rebuild_account(account_id)

            self.result = True
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save transaction:\n{str(e)}", parent=self.dialog)

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        self.result = None
        self.dialog.destroy()
