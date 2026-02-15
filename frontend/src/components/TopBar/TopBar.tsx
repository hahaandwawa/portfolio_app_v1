import { useState } from "react";
import { AccountFilterDropdown } from "./AccountFilterDropdown";
import { AddTransactionModal } from "./AddTransactionModal";
import { CsvModal } from "./CsvModal";
import { ThemeToggle } from "./ThemeToggle";
import { api } from "../../api/client";
import type { Account } from "../../types";

interface TopBarProps {
  accounts: Account[];
  selectedAccountNames: Set<string>;
  onAccountSelectionChange: (selected: Set<string>) => void;
  onTransactionAdded: () => void;
}

export function TopBar({
  accounts,
  selectedAccountNames,
  onAccountSelectionChange,
  onTransactionAdded,
}: TopBarProps) {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [csvModalOpen, setCsvModalOpen] = useState(false);
  return (
    <>
      <header className="w-full border-b border-[var(--border-color)] bg-[var(--bg-card)] shadow-sm">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-8 py-4 md:px-12">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-md">
              <span className="text-lg font-bold">投</span>
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-[var(--text-primary)]">
                投资记录
              </h1>
              <p className="text-xs text-[var(--text-muted)]">
                投资小助手
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <AccountFilterDropdown
              accounts={accounts}
              selectedNames={selectedAccountNames}
              onSelectionChange={onAccountSelectionChange}
            />
            <button
              type="button"
              onClick={() => setCsvModalOpen(true)}
              className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-4 py-2 text-sm font-medium text-[var(--text-primary)] shadow-sm transition hover:bg-[var(--border-color)]"
            >
              导入/导出
            </button>
            <button
              type="button"
              onClick={() => setAddModalOpen(true)}
              className="flex items-center gap-1.5 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--accent-hover)]"
            >
              <span className="text-base leading-none">+</span>
              新增记录
            </button>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <AddTransactionModal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        accounts={accounts}
        onSubmit={async (data) => {
          await api.postTransaction(data);
        }}
        onSuccess={onTransactionAdded}
      />
      <CsvModal
        isOpen={csvModalOpen}
        onClose={() => setCsvModalOpen(false)}
        onRefresh={onTransactionAdded}
        exportAccountFilter={
          selectedAccountNames.size > 0
            ? Array.from(selectedAccountNames)
            : undefined
        }
      />
    </>
  );
}
