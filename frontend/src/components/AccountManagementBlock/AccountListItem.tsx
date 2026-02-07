import type { Account } from "../../types";

const BankIcon = () => (
  <svg
    className="h-5 w-5 text-[var(--text-muted)]"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.5}
      d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
    />
  </svg>
);

const PencilIcon = () => (
  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
  </svg>
);

const TrashIcon = () => (
  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>
);

function formatCash(value: number): string {
  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

interface AccountListItemProps {
  account: Account;
  cashBalance: number | undefined;
  onEdit: (account: Account) => void;
  onDelete: (account: Account) => void;
}

export function AccountListItem({
  account,
  cashBalance,
  onEdit,
  onDelete,
}: AccountListItemProps) {
  const canDelete = account.transaction_count === 0;
  const cashText =
    cashBalance === undefined ? "—" : `现金 ¥${formatCash(cashBalance)}`;

  return (
    <li className="flex items-center justify-between rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-4 py-3.5 transition hover:border-[var(--border-color)]">
      <div className="flex items-center gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[var(--border-subtle)]">
          <BankIcon />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-[var(--text-primary)]">
            {account.name}
          </span>
          <span className="rounded-lg bg-[var(--accent-soft)] px-2.5 py-1 text-xs font-medium text-[var(--accent)]">
            {account.transaction_count} 笔交易
          </span>
          <span className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] px-2.5 py-1 text-xs font-medium text-[var(--text-secondary)]">
            {cashText}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-0.5">
        <button
          type="button"
          onClick={() => onEdit(account)}
          className="rounded-lg p-2 text-[var(--text-muted)] transition hover:bg-[var(--accent-soft)] hover:text-[var(--accent)]"
          title="编辑"
        >
          <PencilIcon />
        </button>
        {canDelete && (
          <button
            type="button"
            onClick={() => onDelete(account)}
            className="rounded-lg p-2 text-[var(--text-muted)] transition hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/20 dark:hover:text-red-400"
            title="删除"
          >
            <TrashIcon />
          </button>
        )}
      </div>
    </li>
  );
}
