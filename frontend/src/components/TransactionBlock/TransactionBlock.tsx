import { useEffect, useState } from "react";
import { TransactionTable } from "./TransactionTable";
import { Pagination } from "./Pagination";
import { EditTransactionModal } from "./EditTransactionModal";
import { ConfirmModal } from "../ConfirmModal";
import { api } from "../../api/client";
import type { Account, Transaction } from "../../types";

interface TransactionBlockProps {
  accounts: Account[];
  selectedAccountNames: Set<string>;
  refreshKey: number;
  onRefresh: () => void;
}

export function TransactionBlock({
  accounts,
  selectedAccountNames,
  refreshKey,
  onRefresh,
}: TransactionBlockProps) {
  const [page, setPage] = useState(1);
  const [editTransaction, setEditTransaction] = useState<Transaction | null>(null);
  const [deleteTransaction, setDeleteTransaction] = useState<Transaction | null>(null);
  const [deleteConfirmStep, setDeleteConfirmStep] = useState<1 | 2>(1);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [data, setData] = useState<{
    items: Transaction[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPage(1);
  }, [selectedAccountNames]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const accounts =
      selectedAccountNames.size > 0 ? Array.from(selectedAccountNames) : undefined;

    api
      .getTransactions({
        account: accounts,
        page,
        page_size: 10,
      })
      .then((res) => {
        if (!cancelled) {
          setData(res);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "加载失败");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedAccountNames, page, refreshKey]);

  if (error) {
    return (
      <section className="py-8 text-center">
        <p className="text-center text-red-600 dark:text-red-400">{error}</p>
        <p className="mt-2 text-center text-sm text-[var(--text-secondary)]">
          请确保后端 API 已启动 (uvicorn src.app.main:app)
        </p>
      </section>
    );
  }

  return (
    <section className="py-6">
      <div className="rounded-2xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-[var(--shadow-md)] md:p-8">
        <div className="mb-4">
          <h2 className="text-xl font-bold tracking-tight text-[var(--text-primary)]">
            交易记录
          </h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            {data ? `共 ${data.total} 笔交易` : "加载中..."}
          </p>
        </div>
        <div className="h-[360px] overflow-y-auto -mx-2 px-2">
          {loading ? (
            <div className="flex h-full items-center justify-center text-[var(--text-secondary)]">
              加载中...
            </div>
          ) : data ? (
            <TransactionTable
              transactions={data.items}
              onEdit={(txn) => setEditTransaction(txn)}
              onDelete={(txn) => {
                setDeleteTransaction(txn);
                setDeleteConfirmStep(1);
              }}
            />
          ) : null}
        </div>
        {data && data.total_pages > 0 && (
          <div className="mt-4">
          <Pagination
            page={data.page}
            totalPages={data.total_pages}
            onPageChange={setPage}
          />
          </div>
        )}
      </div>

      <EditTransactionModal
        isOpen={editTransaction !== null}
        onClose={() => setEditTransaction(null)}
        transaction={editTransaction}
        accounts={accounts}
        onSubmit={async (txnId, payload) => {
          await api.putTransaction(txnId, payload);
        }}
        onSuccess={onRefresh}
      />

      <ConfirmModal
        isOpen={deleteTransaction !== null}
        onClose={() => {
          setDeleteTransaction(null);
          setDeleteConfirmStep(1);
        }}
        onConfirm={async () => {
          if (!deleteTransaction) return true;
          if (deleteConfirmStep === 1) {
            setDeleteConfirmStep(2);
            return false;
          }
          setDeleteLoading(true);
          try {
            await api.deleteTransaction(deleteTransaction.txn_id);
            setDeleteTransaction(null);
            setDeleteConfirmStep(1);
            setTimeout(() => onRefresh(), 0);
            return true;
          } finally {
            setDeleteLoading(false);
          }
        }}
        title={deleteConfirmStep === 1 ? "确认删除" : "再次确认"}
        message={
          deleteConfirmStep === 1
            ? "确定要删除此交易吗？"
            : "此操作不可撤销。确定要删除此交易吗？"
        }
        confirmText={deleteConfirmStep === 1 ? "下一步" : "确认删除"}
        cancelText="取消"
        variant="danger"
        loading={deleteLoading}
      />
    </section>
  );
}
