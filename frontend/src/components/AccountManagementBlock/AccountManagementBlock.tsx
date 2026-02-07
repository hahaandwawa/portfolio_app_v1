import { useState } from "react";
import { AddAccountModal } from "./AddAccountModal";
import { EditAccountModal } from "./EditAccountModal";
import { AccountListItem } from "./AccountListItem";
import { ConfirmModal } from "../ConfirmModal";
import { api } from "../../api/client";
import type { Account } from "../../types";

interface AccountManagementBlockProps {
  accounts: Account[];
  onAccountAdded: () => void;
  onAccountRenamed?: (oldName: string, newName: string) => void;
}

export function AccountManagementBlock({
  accounts,
  onAccountAdded,
  onAccountRenamed,
}: AccountManagementBlockProps) {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editAccount, setEditAccount] = useState<Account | null>(null);
  const [deleteAccount, setDeleteAccount] = useState<Account | null>(null);
  const [deleteStep, setDeleteStep] = useState<1 | 2>(1);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const onRefresh = () => {
    onAccountAdded();
  };

  return (
    <section className="py-6">
      <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-[var(--shadow-md)] md:p-8">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
              账户管理
            </h2>
            <p className="mt-1 text-sm text-[var(--text-muted)]">
              共 {accounts.length} 个账户
            </p>
          </div>
          <button
            type="button"
            onClick={() => setAddModalOpen(true)}
            className="shrink-0 rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-[var(--accent-hover)]"
          >
            + 添加账户
          </button>
        </div>

        <div className="flex flex-col gap-3">
          {accounts.length === 0 ? (
            <p className="py-8 text-center text-sm text-[var(--text-secondary)]">
              暂无账户，点击「添加账户」创建
            </p>
          ) : (
            accounts.map((acc) => (
              <AccountListItem
                key={acc.name}
                account={acc}
                onEdit={setEditAccount}
                onDelete={(a) => {
                  setDeleteAccount(a);
                  setDeleteStep(1);
                }}
              />
            ))
          )}
        </div>
      </div>

      <AddAccountModal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        onSubmit={async (name) => {
          await api.postAccount(name);
        }}
        onSuccess={onRefresh}
      />

      <EditAccountModal
        isOpen={editAccount !== null}
        onClose={() => setEditAccount(null)}
        account={editAccount}
        onSubmit={async (oldName, newName) => {
          await api.putAccount(oldName, newName);
        }}
        onSuccess={(oldName, newName) => {
          onAccountRenamed?.(oldName, newName);
          setTimeout(() => onRefresh(), 0);
        }}
      />

      <ConfirmModal
        isOpen={deleteAccount !== null}
        onClose={() => {
          setDeleteAccount(null);
          setDeleteStep(1);
        }}
        onConfirm={async () => {
          if (!deleteAccount) return true;
          if (deleteStep === 1) {
            setDeleteStep(2);
            return false;
          }
          setDeleteLoading(true);
          try {
            await api.deleteAccount(deleteAccount.name);
            setDeleteAccount(null);
            setDeleteStep(1);
            setTimeout(() => onRefresh(), 0);
            return true;
          } finally {
            setDeleteLoading(false);
          }
        }}
        title={deleteStep === 1 ? "确认删除" : "再次确认"}
        message={
          deleteStep === 1
            ? `确定要删除账户「${deleteAccount?.name}」吗？`
            : "此操作不可撤销。确定要删除此账户吗？"
        }
        confirmText={deleteStep === 1 ? "下一步" : "确认删除"}
        cancelText="取消"
        variant="danger"
        loading={deleteLoading}
      />
    </section>
  );
}
