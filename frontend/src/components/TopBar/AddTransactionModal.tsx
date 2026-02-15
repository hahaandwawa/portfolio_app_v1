import { useEffect, useState, useCallback } from "react";
import { Modal } from "../Modal";
import type { Account, TransactionPayload, TransactionType } from "../../types";
import { api } from "../../api/client";
import { TXN_TYPES, toLocalDatetime } from "../../utils/transaction";

interface AddTransactionModalProps {
  isOpen: boolean;
  onClose: () => void;
  accounts: Account[];
  onSubmit: (data: TransactionPayload) => Promise<void>;
  onSuccess?: () => void;
}

export function AddTransactionModal({
  isOpen,
  onClose,
  accounts,
  onSubmit,
  onSuccess,
}: AddTransactionModalProps) {
  const [accountName, setAccountName] = useState("");
  const [cashDestinationAccount, setCashDestinationAccount] = useState("");
  useEffect(() => {
    if (isOpen && accounts.length > 0) {
      setAccountName((prev) =>
        accounts.some((a) => a.name === prev) ? prev : accounts[0].name
      );
      setCashDestinationAccount((prev) =>
        accounts.some((a) => a.name === prev) ? prev : accounts[0].name
      );
    }
  }, [isOpen, accounts]);
  const [txnType, setTxnType] = useState<TransactionType>("BUY");
  const [txnTime, setTxnTime] = useState(toLocalDatetime(new Date()));
  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [cashAmount, setCashAmount] = useState("");
  const [fees, setFees] = useState("0");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isStock = txnType === "BUY" || txnType === "SELL";
  const isCash = txnType === "CASH_DEPOSIT" || txnType === "CASH_WITHDRAW";

  // For SELL: default cash destination to source account when source changes
  useEffect(() => {
    if (txnType === "SELL" && accountName) setCashDestinationAccount(accountName);
  }, [txnType, accountName]);

  // For SELL: when symbol is entered, default source account to account with most shares
  const fetchPositionsForSymbol = useCallback(async (sym: string) => {
    const s = sym?.trim().toUpperCase();
    if (!s || accounts.length === 0) return;
    try {
      const res = await api.getPositionsBySymbol(s);
      if (res.positions.length > 0 && res.positions[0].account_name) {
        const top = res.positions[0].account_name;
        if (accounts.some((a) => a.name === top)) {
          setAccountName(top);
          setCashDestinationAccount(top);
        }
      }
    } catch {
      // ignore
    }
  }, [accounts]);

  useEffect(() => {
    if (txnType === "SELL" && symbol.trim()) {
      const t = setTimeout(() => fetchPositionsForSymbol(symbol), 300);
      return () => clearTimeout(t);
    }
  }, [txnType, symbol, fetchPositionsForSymbol]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!accountName) {
      setError("请选择账户");
      return;
    }

    const payload: TransactionPayload = {
      account_name: accountName,
      txn_type: txnType,
      txn_time_est: new Date(txnTime).toISOString(),
      fees: parseFloat(fees) || 0,
      note: note || undefined,
    };

    if (isStock) {
      if (!symbol.trim()) {
        setError("股票代码必填");
        return;
      }
      const q = parseFloat(quantity);
      const p = parseFloat(price);
      if (isNaN(q) || q <= 0) {
        setError("数量必须大于 0");
        return;
      }
      if (isNaN(p) || p < 0) {
        setError("单价必须大于等于 0");
        return;
      }
      payload.symbol = symbol.trim().toUpperCase();
      payload.quantity = q;
      payload.price = p;
      if (txnType === "SELL" && cashDestinationAccount && cashDestinationAccount !== accountName) {
        payload.cash_destination_account = cashDestinationAccount;
      }
    }

    if (isCash) {
      const c = parseFloat(cashAmount);
      if (isNaN(c) || c <= 0) {
        setError("现金金额必须大于 0");
        return;
      }
      payload.cash_amount = c;
    }

    setSubmitting(true);
    try {
      await onSubmit(payload);
      onClose();
      setSymbol("");
      setQuantity("");
      setPrice("");
      setCashAmount("");
      setFees("0");
      setNote("");
      setTimeout(() => onSuccess?.(), 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "提交失败");
      return;
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="新增记录">
      <form onSubmit={handleSubmit} className="space-y-4">
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
            {txnType === "SELL" && (
              <div>
                <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
                  卖出资金转入账户
                </label>
                <select
                  value={cashDestinationAccount}
                  onChange={(e) => setCashDestinationAccount(e.target.value)}
                  className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-[var(--text-primary)]"
                >
                  {accounts.map((a) => (
                    <option key={a.name} value={a.name}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
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
            {submitting ? "提交中..." : "提交"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
