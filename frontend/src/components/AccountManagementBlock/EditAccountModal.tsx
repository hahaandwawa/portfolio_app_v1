import { useEffect, useState } from "react";
import { Modal } from "../Modal";
import type { Account } from "../../types";

interface EditAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  account: Account | null;
  onSubmit: (oldName: string, newName: string) => Promise<void>;
  onSuccess?: (oldName: string, newName: string) => void;
}

export function EditAccountModal({
  isOpen,
  onClose,
  account,
  onSubmit,
  onSuccess,
}: EditAccountModalProps) {
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen && account) {
      setName(account.name);
    }
  }, [isOpen, account]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const trimmed = name.trim();
    if (!trimmed || !account) return;
    if (trimmed === account.name) {
      onClose();
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit(account.name, trimmed);
      onClose();
      onSuccess?.(account.name, trimmed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  };

  if (!account) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="编辑账户">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <p className="rounded bg-red-100 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
            {error}
          </p>
        )}
        <div>
          <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
            账户名称 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例如：主券商"
            className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-[var(--text-primary)]"
          />
        </div>
        <div className="flex justify-end gap-2 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--border-color)]"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
          >
            {submitting ? "保存中..." : "保存"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
