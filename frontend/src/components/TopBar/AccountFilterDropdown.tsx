import { useEffect, useRef, useState } from "react";
import type { Account } from "../../types";

interface AccountFilterDropdownProps {
  accounts: Account[];
  selectedNames: Set<string>;
  onSelectionChange: (selected: Set<string>) => void;
}

const ChevronIcon = () => (
  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

export function AccountFilterDropdown({
  accounts,
  selectedNames,
  onSelectionChange,
}: AccountFilterDropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const allSelected = accounts.length === 0 || selectedNames.size === accounts.length;
  const noneSelected = selectedNames.size === 0;

  const handleSelectAll = () => {
    onSelectionChange(new Set(accounts.map((a) => a.name)));
  };

  const handleSelectNone = () => {
    onSelectionChange(new Set());
  };

  const handleToggle = (name: string) => {
    const next = new Set(selectedNames);
    if (next.has(name)) {
      next.delete(name);
    } else {
      next.add(name);
    }
    onSelectionChange(next);
  };

  const displayText =
    noneSelected
      ? "所有账户"
      : allSelected && accounts.length > 0
        ? "所有账户"
        : `${selectedNames.size}/${accounts.length} 个账户`;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] transition hover:border-[var(--accent-muted)] hover:bg-[var(--accent-soft)]"
      >
        <ChevronIcon />
        {displayText}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 min-w-[220px] rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] py-2 shadow-lg">
          <p className="mb-2 px-4 text-xs font-medium text-[var(--text-muted)]">
            选择要显示的账户
          </p>
          <div className="border-t border-[var(--border-subtle)] px-2 pt-2">
            <button
              type="button"
              className="w-full rounded-lg px-3 py-2 text-left text-sm text-[var(--text-primary)] transition hover:bg-[var(--accent-soft)]"
              onClick={handleSelectAll}
            >
              全选
            </button>
            <button
              type="button"
              className="w-full rounded-lg px-3 py-2 text-left text-sm text-[var(--text-primary)] transition hover:bg-[var(--accent-soft)]"
              onClick={handleSelectNone}
            >
              全不选
            </button>
          </div>
          <div className="max-h-48 overflow-y-auto border-t border-[var(--border-subtle)]">
            {accounts.map((acc) => (
              <label
                key={acc.name}
                className="flex cursor-pointer items-center gap-2 px-4 py-2.5 transition hover:bg-[var(--accent-soft)]"
              >
                <input
                  type="checkbox"
                  checked={selectedNames.has(acc.name)}
                  onChange={() => handleToggle(acc.name)}
                  className="h-4 w-4 rounded border-[var(--border-color)] text-[var(--accent)]"
                />
                <span className="text-sm text-[var(--text-primary)]">{acc.name}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
