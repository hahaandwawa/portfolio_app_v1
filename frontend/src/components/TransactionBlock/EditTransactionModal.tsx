import { useEffect, useState } from "react";
import { Modal } from "../Modal";
import { ConfirmModal } from "../ConfirmModal";
import type { Account, Transaction, TransactionEditPayload, TransactionType } from "../../types";

const TXN_TYPES: { value: TransactionType; label: string }[] = [
  { value: "BUY", label: "买入" },
  { value: "SELL", label: "卖出" },
  { value: "CASH_DEPOSIT", label: "现金存入" },
  { value: "CASH_WITHDRAW", label: "现金取出" },
];

function toLocalDatetime(iso: string): string {
  try {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return "";
  }
}

interface EditTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  transaction: Transaction | null;
  accounts: Account[];
  onSubmit: (txnId: string, data: TransactionEditPayload) => Promise<void>;
  onSuccess?: () => void;
}

export function EditTransactionModal({
  isOpen,
  onClose,
  transaction,
  accounts,
  onSubmit,
  onSuccess,
}: EditTransactionModalProps) {
  const [accountName, setAccountName] = useState("");
  const [txnType, setTxnType] = useState<TransactionType>("BUY");
  const [txnTime, setTxnTime] = useState("");
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [cashAmount, setCashAmount] = useState("");
  const [fees, setFees] = useState("0");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showConfirmSave, setShowConfirmSave] = useState(false);

  useEffect(() => {
    if (isOpen && transaction) {
      setAccountName(transaction.account_name);
      setTxnType(transaction.txn_type as TransactionType);
      setTxnTime(toLocalDatetime(transaction.txn_time_est));
      setSymbol(transaction.symbol ?? "");
      setQuantity(transaction.quantity?.toString() ?? "");
      setPrice(transaction.price?.toString() ?? "");
      setCashAmount(transaction.cash_amount?.toString() ?? "");
      setFees(transaction.fees?.toString() ?? "0");
      setNote(transaction.note ?? "");
    }
  }, [isOpen, transaction]);

  const isStock = txnType === "BUY" || txnType === "SELL";
  const isCash = txnType === "CASH_DEPOSIT" || txnType === "CASH_WITHDRAW";

  const buildPayload = (): TransactionEditPayload | null => {
    if (!accountName || !transaction) return null;

    const payload: TransactionEditPayload = {
      account_name: accountName,
      txn_type: txnType,
      txn_time_est: new Date(txnTime).toISOString(),
      fees: parseFloat(fees) || 0,
      note: note || undefined,
    };

    if (isStock) {
      if (!symbol.trim()) return null;
      const q = parseFloat(quantity);
      const p = parseFloat(price);
      if (isNaN(q) || q <= 0 || isNaN(p) || p < 0) return null;
      payload.symbol = symbol.trim().toUpperCase();
      payload.quantity = q;
      payload.price = p;
    } else if (isCash) {
      const c = parseFloat(cashAmount);
      if (isNaN(c) || c <= 0) return null;
      payload.cash_amount = c;
    }

    return payload;
  };

  const handleSubmitClick = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!accountName) {
      setError("请选择账户");
      return;
    }

    const payload = buildPayload();
    if (!payload) {
      if (isStock) {
        if (!symbol.trim()) setError("股票代码必填");
        else if (parseFloat(quantity) <= 0 || isNaN(parseFloat(quantity))) setError("数量必须大于 0");
        else if (parseFloat(price) < 0 || isNaN(parseFloat(price))) setError("单价必须大于等于 0");
      } else if (isCash) {
        const c = parseFloat(cashAmount);
        if (isNaN(c) || c <= 0) setError("现金金额必须大于 0");
      }
      return;
    }

    setShowConfirmSave(true);
  };

  const handleConfirmSave = async () => {
    const payload = buildPayload();
    if (!payload || !transaction) return;

    setSubmitting(true);
    try {
      await onSubmit(transaction.txn_id, payload);
      setShowConfirmSave(false);
      onClose();
      setTimeout(() => onSuccess?.(), 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
      setShowConfirmSave(false);
    } finally {
      setSubmitting(false);
    }
  };

  if (!transaction) return null;

  return (
    <>
      <Modal isOpen={isOpen} onClose={onClose} title="编辑记录">
        <form onSubmit={handleSubmitClick} className="space-y-4">
          {error && (
            <p className="rounded bg-red-100 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
              {error}
            </p>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
              账户 <span className="text-red-500">*</span>
            </label>
            <select
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
              className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-[var(--text-primary)]"
              required
            >
              <option value="">请选择</option>
              {accounts.map((a) => (
                <option key={a.name} value={a.name}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
              类型 <span className="text-red-500">*</span>
            </label>
            <select
              value={txnType}
              onChange={(e) => setTxnType(e.target.value as TransactionType)}
              className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-[var(--text-primary)]"
            >
              {TXN_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
              时间 <span className="text-red-500">*</span>
            </label>
            <input
              type="datetime-local"
              value={txnTime}
              onChange={(e) => setTxnTime(e.target.value)}
              className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-[var(--text-primary)]"
              required
            />
          </div>

          {isStock && (
            <>
              <div>
                <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
                  股票代码 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  onBlur={() => setSymbol((s) => s.trim().toUpperCase())}
                  placeholder="AAPL"
                  className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-[var(--text-primary)]"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
                    数量 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-[var(--text-primary)]"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
                    单价 <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-[var(--text-primary)]"
                  />
                </div>
              </div>
            </>
          )}

          {isCash && (
            <div>
              <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
                现金金额 <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                step="any"
                min="0"
                value={cashAmount}
                onChange={(e) => setCashAmount(e.target.value)}
                className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-[var(--text-primary)]"
              />
            </div>
          )}

          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
              手续费
            </label>
            <input
              type="number"
              step="any"
              min="0"
              value={fees}
              onChange={(e) => setFees(e.target.value)}
              className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-[var(--text-primary)]"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
              备注
            </label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
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

      <ConfirmModal
        isOpen={showConfirmSave}
        onClose={() => setShowConfirmSave(false)}
        onConfirm={handleConfirmSave}
        title="确认保存"
        message="确定要保存对此次交易的修改吗？"
        confirmText="确认保存"
        cancelText="取消"
        loading={submitting}
      />
    </>
  );
}
