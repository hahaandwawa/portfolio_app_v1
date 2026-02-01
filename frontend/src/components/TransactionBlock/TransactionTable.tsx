import type { Transaction } from "../../types";

interface TransactionTableProps {
  transactions: Transaction[];
  onEdit: (txn: Transaction) => void;
  onDelete: (txn: Transaction) => void;
}

const TXN_TYPE_LABELS: Record<string, string> = {
  BUY: "买入",
  SELL: "卖出",
  CASH_DEPOSIT: "现金存入",
  CASH_WITHDRAW: "现金取出",
};

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function TransactionTable({ transactions, onEdit, onDelete }: TransactionTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[800px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-[var(--border-color)] bg-[var(--bg-elevated)]">
            <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">日期</th>
            <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">账户</th>
            <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">类型</th>
            <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">代码</th>
            <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">数量</th>
            <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">单价</th>
            <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">金额</th>
            <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">手续费</th>
            <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">备注</th>
            <th className="w-24 px-2 py-3 text-center text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">操作</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((txn) => (
            <tr
              key={txn.txn_id}
              className="border-b border-[var(--border-subtle)] transition hover:bg-[var(--accent-soft)]/50"
            >
              <td className="px-4 py-2 text-center text-[var(--text-primary)]">{formatDate(txn.txn_time_est)}</td>
              <td className="px-4 py-2 text-center text-[var(--text-primary)]">{txn.account_name}</td>
              <td className="px-4 py-2 text-center text-[var(--text-primary)]">{TXN_TYPE_LABELS[txn.txn_type] ?? txn.txn_type}</td>
              <td className="px-4 py-2 text-center text-[var(--text-primary)]">{txn.symbol ?? "—"}</td>
              <td className="px-4 py-2 text-center text-[var(--text-primary)]">{txn.quantity != null ? txn.quantity : "—"}</td>
              <td className="px-4 py-2 text-center text-[var(--text-primary)]">{txn.price != null ? txn.price : "—"}</td>
              <td className="px-4 py-2 text-center text-[var(--text-primary)]">{txn.amount != null ? txn.amount : "—"}</td>
              <td className="px-4 py-2 text-center text-[var(--text-primary)]">{txn.fees ?? 0}</td>
              <td className="max-w-[120px] truncate px-4 py-2 text-center text-[var(--text-secondary)]">{txn.note ?? "—"}</td>
              <td className="px-2 py-2">
                <div className="flex items-center justify-center gap-1">
                  <button
                    type="button"
                    onClick={() => onEdit(txn)}
                    className="rounded-lg px-2 py-1 text-xs font-medium text-[var(--accent)] transition hover:bg-[var(--accent-soft)]"
                    title="编辑"
                  >
                    编辑
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(txn)}
                    className="rounded-lg px-2 py-1 text-xs font-medium text-red-500 transition hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                    title="删除"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {transactions.length === 0 && (
        <p className="py-8 text-center text-sm text-[var(--text-secondary)]">
          暂无交易记录
        </p>
      )}
    </div>
  );
}
