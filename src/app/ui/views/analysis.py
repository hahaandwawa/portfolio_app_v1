"""Analysis view with charts and portfolio metrics."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List
from decimal import Decimal

from app.app_context import AppContext

# Import matplotlib with Tk backend
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class AnalysisView:
    """
    View for portfolio analysis with charts.

    Shows positions table, allocation pie chart, and P/L metrics.
    """

    def __init__(self, parent: ttk.Notebook, context: AppContext):
        """
        Initialize analysis view.

        Args:
            parent: Parent notebook widget
            context: Application context
        """
        self.parent = parent
        self.context = context

        # Create main frame
        self.frame = ttk.Frame(parent, padding="10")

        # Create paned window for layout
        self.paned = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Left panel: Positions and P/L
        self._create_left_panel()

        # Right panel: Charts
        self._create_right_panel()

    def _create_left_panel(self) -> None:
        """Create the left panel with positions table and metrics."""
        left_frame = ttk.Frame(self.paned, padding="5")
        self.paned.add(left_frame, weight=1)

        # Today's P/L section
        pnl_frame = ttk.LabelFrame(left_frame, text="Today's Performance", padding="10")
        pnl_frame.pack(fill=tk.X, pady=(0, 10))

        # P/L display
        self.pnl_amount_label = ttk.Label(
            pnl_frame,
            text="$0.00",
            font=('Helvetica', 24, 'bold')
        )
        self.pnl_amount_label.pack(anchor=tk.W)

        self.pnl_percent_label = ttk.Label(
            pnl_frame,
            text="0.00%",
            font=('Helvetica', 14)
        )
        self.pnl_percent_label.pack(anchor=tk.W)

        self.pnl_details_label = ttk.Label(
            pnl_frame,
            text="Prev Close: $0.00 → Current: $0.00",
            style='Info.TLabel'
        )
        self.pnl_details_label.pack(anchor=tk.W, pady=(5, 0))

        # Positions table
        positions_frame = ttk.LabelFrame(left_frame, text="Holdings", padding="5")
        positions_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview
        self.positions_tree = ttk.Treeview(
            positions_frame,
            columns=("symbol", "shares", "price", "value", "change"),
            show="headings",
            selectmode="browse",
        )

        self.positions_tree.heading("symbol", text="Symbol")
        self.positions_tree.heading("shares", text="Shares")
        self.positions_tree.heading("price", text="Last Price")
        self.positions_tree.heading("value", text="Market Value")
        self.positions_tree.heading("change", text="Day Change")

        self.positions_tree.column("symbol", width=80, anchor="center")
        self.positions_tree.column("shares", width=80, anchor="e")
        self.positions_tree.column("price", width=90, anchor="e")
        self.positions_tree.column("value", width=100, anchor="e")
        self.positions_tree.column("change", width=100, anchor="e")

        scrollbar = ttk.Scrollbar(
            positions_frame,
            orient=tk.VERTICAL,
            command=self.positions_tree.yview
        )
        self.positions_tree.configure(yscrollcommand=scrollbar.set)

        self.positions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Summary row
        summary_frame = ttk.Frame(left_frame)
        summary_frame.pack(fill=tk.X, pady=(5, 0))

        self.total_holdings_label = ttk.Label(
            summary_frame,
            text="Total Holdings: $0.00",
            style='Heading.TLabel'
        )
        self.total_holdings_label.pack(side=tk.LEFT)

        self.cash_label = ttk.Label(
            summary_frame,
            text="Cash: $0.00",
            style='Heading.TLabel'
        )
        self.cash_label.pack(side=tk.RIGHT)

    def _create_right_panel(self) -> None:
        """Create the right panel with charts."""
        right_frame = ttk.Frame(self.paned, padding="5")
        self.paned.add(right_frame, weight=1)

        # Allocation pie chart
        allocation_frame = ttk.LabelFrame(right_frame, text="Portfolio Allocation", padding="5")
        allocation_frame.pack(fill=tk.BOTH, expand=True)

        # Create matplotlib figure for pie chart
        self.pie_figure = Figure(figsize=(5, 4), dpi=100)
        self.pie_ax = self.pie_figure.add_subplot(111)

        self.pie_canvas = FigureCanvasTkAgg(self.pie_figure, allocation_frame)
        self.pie_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Allocation table below chart
        self.allocation_tree = ttk.Treeview(
            allocation_frame,
            columns=("symbol", "value", "percent"),
            show="headings",
            height=6,
        )

        self.allocation_tree.heading("symbol", text="Symbol")
        self.allocation_tree.heading("value", text="Value")
        self.allocation_tree.heading("percent", text="Allocation")

        self.allocation_tree.column("symbol", width=80, anchor="center")
        self.allocation_tree.column("value", width=100, anchor="e")
        self.allocation_tree.column("percent", width=80, anchor="e")

        self.allocation_tree.pack(fill=tk.X, pady=(10, 0))

    def refresh(self) -> None:
        """Refresh all analysis data and charts."""
        try:
            # Get all accounts
            accounts = self.context.ledger.list_accounts()
            account_ids = [a.account_id for a in accounts]

            if not account_ids:
                self._show_empty_state()
                return

            # Get positions with prices
            positions = self.context.analysis.get_positions_with_prices(account_ids)
            cash = self.context.portfolio.aggregate_cash(account_ids)

            # Update P/L
            self._update_pnl(account_ids)

            # Update positions table
            self._update_positions_table(positions, cash)

            # Update allocation chart
            self._update_allocation_chart(account_ids)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load analysis:\n{str(e)}")

    def _show_empty_state(self) -> None:
        """Show empty state when no accounts exist."""
        self.pnl_amount_label.config(text="$0.00")
        self.pnl_percent_label.config(text="No data")
        self.pnl_details_label.config(text="Create an account to get started")

        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)

        self.total_holdings_label.config(text="Total Holdings: $0.00")
        self.cash_label.config(text="Cash: $0.00")

        # Clear pie chart
        self.pie_ax.clear()
        self.pie_ax.text(0.5, 0.5, "No data", ha='center', va='center', fontsize=14)
        self.pie_ax.set_aspect('equal')
        self.pie_canvas.draw()

        for item in self.allocation_tree.get_children():
            self.allocation_tree.delete(item)

    def _update_pnl(self, account_ids: List[str]) -> None:
        """Update the P/L display."""
        pnl = self.context.analysis.today_pnl(account_ids)

        # Format P/L amount
        amount_text = f"${pnl.pnl_dollars:+,.2f}"
        self.pnl_amount_label.config(text=amount_text)

        # Set color
        if pnl.pnl_dollars > 0:
            self.pnl_amount_label.config(foreground='green')
        elif pnl.pnl_dollars < 0:
            self.pnl_amount_label.config(foreground='red')
        else:
            self.pnl_amount_label.config(foreground='black')

        # Format percentage
        if pnl.pnl_percent is not None:
            percent_text = f"{pnl.pnl_percent:+.2f}%"
            self.pnl_percent_label.config(text=percent_text)
            if pnl.pnl_percent > 0:
                self.pnl_percent_label.config(foreground='green')
            elif pnl.pnl_percent < 0:
                self.pnl_percent_label.config(foreground='red')
            else:
                self.pnl_percent_label.config(foreground='black')
        else:
            self.pnl_percent_label.config(text="N/A", foreground='gray')

        # Details
        details = f"Prev Close: ${pnl.prev_close_value:,.2f} → Current: ${pnl.current_value:,.2f}"
        if pnl.as_of:
            details += f" (as of {pnl.as_of.strftime('%H:%M')})"
        self.pnl_details_label.config(text=details)

    def _update_positions_table(self, positions, cash: Decimal) -> None:
        """Update the positions table."""
        # Clear existing items
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)

        total_holdings = Decimal("0")

        for p in positions:
            # Calculate day change
            if p.last_price and p.prev_close:
                day_change = p.shares * (p.last_price - p.prev_close)
                day_change_text = f"${day_change:+,.2f}"
            else:
                day_change_text = "--"

            market_value = p.market_value or Decimal("0")
            total_holdings += market_value

            self.positions_tree.insert(
                "",
                tk.END,
                values=(
                    p.symbol,
                    f"{p.shares:.4f}",
                    f"${p.last_price:.2f}" if p.last_price else "--",
                    f"${market_value:,.2f}",
                    day_change_text,
                )
            )

        # Update summary
        self.total_holdings_label.config(text=f"Total Holdings: ${total_holdings:,.2f}")
        self.cash_label.config(text=f"Cash: ${cash:,.2f}")

    def _update_allocation_chart(self, account_ids: List[str]) -> None:
        """Update the allocation pie chart."""
        allocation = self.context.analysis.allocation(account_ids)

        # Clear existing items in table
        for item in self.allocation_tree.get_children():
            self.allocation_tree.delete(item)

        # Clear pie chart
        self.pie_ax.clear()

        if not allocation.items:
            self.pie_ax.text(0.5, 0.5, "No holdings", ha='center', va='center', fontsize=14)
            self.pie_ax.set_aspect('equal')
            self.pie_canvas.draw()
            return

        # Prepare data for pie chart
        labels = []
        sizes = []
        colors = plt.cm.Set3.colors  # Color palette

        for i, item in enumerate(allocation.items):
            labels.append(item.symbol)
            sizes.append(float(item.percentage))

            # Add to table
            self.allocation_tree.insert(
                "",
                tk.END,
                values=(
                    item.symbol,
                    f"${item.market_value:,.2f}",
                    f"{item.percentage:.1f}%",
                )
            )

        # Create pie chart
        wedges, texts, autotexts = self.pie_ax.pie(
            sizes,
            labels=labels,
            autopct='%1.1f%%',
            colors=colors[:len(labels)],
            startangle=90,
        )

        # Style the chart
        for autotext in autotexts:
            autotext.set_fontsize(9)

        self.pie_ax.set_title(f"Total: ${allocation.total_value:,.2f}", fontsize=10, pad=10)

        # Ensure equal aspect ratio
        self.pie_ax.set_aspect('equal')

        # Redraw canvas
        self.pie_figure.tight_layout()
        self.pie_canvas.draw()
