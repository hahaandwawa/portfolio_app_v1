import { Modal } from "./Modal";

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void> | boolean | Promise<boolean>;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "default";
  loading?: boolean;
}

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "确认",
  cancelText = "取消",
  variant = "default",
  loading = false,
}: ConfirmModalProps) {
  const handleConfirm = async () => {
    const result = await onConfirm();
    if (result !== false) onClose();
  };

  const confirmClass =
    variant === "danger"
      ? "bg-red-600 text-white shadow-sm transition hover:bg-red-700"
      : "bg-[var(--accent)] text-white shadow-sm transition hover:bg-[var(--accent-hover)]";

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title}>
      <p className="mb-6 text-[var(--text-primary)]">{message}</p>
      <div className="flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          disabled={loading}
          className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-primary)] transition hover:bg-[var(--accent-soft)] disabled:opacity-50"
        >
          {cancelText}
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={loading}
          className={`rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 ${confirmClass}`}
        >
          {loading ? "处理中..." : confirmText}
        </button>
      </div>
    </Modal>
  );
}
