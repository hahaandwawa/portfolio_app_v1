import { useState, useRef } from "react";
import { Modal } from "../Modal";
import { api } from "../../api/client";
import type { TransactionImportResult } from "../../types";

type View = "main" | "import" | "importResult" | "exportResult";

interface CsvModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRefresh: () => void;
  /** When set, export uses these account names as filter (same as transaction list). */
  exportAccountFilter?: string[];
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function CsvModal({
  isOpen,
  onClose,
  onRefresh,
  exportAccountFilter,
}: CsvModalProps) {
  const [view, setView] = useState<View>("main");
  const [templateToast, setTemplateToast] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Import: file selection and result
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importSubmitting, setImportSubmitting] = useState(false);
  const [importResult, setImportResult] = useState<{
    success: boolean;
    data?: TransactionImportResult;
    error?: string;
  } | null>(null);

  // Export: loading and result
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState<{
    success: boolean;
    error?: string;
  } | null>(null);

  const resetToMain = () => {
    setView("main");
    setSelectedFile(null);
    setImportResult(null);
    setExportResult(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleClose = () => {
    resetToMain();
    onClose();
  };

  const handleCloseAfterResult = () => {
    onRefresh();
    resetToMain();
    onClose();
  };

  // ----- Main: Import / Export / 下载模板 -----
  const handleImportClick = () => setView("import");
  const handleExportClick = async () => {
    setView("exportResult");
    setExportResult(null);
    setExporting(true);
    try {
      const accountParam =
        exportAccountFilter && exportAccountFilter.length > 0
          ? { account: exportAccountFilter }
          : undefined;
      const blob = await api.exportTransactionsCsv(accountParam);
      triggerDownload(blob, "transactions.csv");
      setExportResult({ success: true });
    } catch (err) {
      setExportResult({
        success: false,
        error: err instanceof Error ? err.message : "导出失败",
      });
    } finally {
      setExporting(false);
    }
  };
  const handleTemplateClick = async () => {
    try {
      const blob = await api.downloadTransactionsTemplate();
      triggerDownload(blob, "transactions_template.csv");
      setTemplateToast(true);
      setTimeout(() => setTemplateToast(false), 2000);
    } catch (err) {
      setTemplateToast(false);
      const msg = err instanceof Error ? err.message : "下载失败";
      setExportResult({ success: false, error: `模板：${msg}` });
      setView("exportResult");
    }
  };

  // ----- Import: submit -----
  const handleImportSubmit = async () => {
    if (!selectedFile) return;
    setImportSubmitting(true);
    setImportResult(null);
    try {
      const data = await api.importTransactionsCsv(selectedFile);
      setImportResult({ success: true, data });
      setView("importResult");
    } catch (err) {
      setImportResult({
        success: false,
        error: err instanceof Error ? err.message : "导入失败",
      });
      setView("importResult");
    } finally {
      setImportSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const title =
    view === "main"
      ? "CSV 导入 / 导出"
      : view === "import"
        ? "导入 CSV"
        : view === "importResult"
          ? "导入结果"
          : "导出结果";

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={title}>
      {view === "main" && (
        <div className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={handleImportClick}
              className="flex-1 rounded-lg bg-[var(--accent)] px-4 py-3 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
            >
              导入 CSV
            </button>
            <button
              type="button"
              onClick={handleExportClick}
              className="flex-1 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-4 py-3 text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--border-color)]"
            >
              导出 CSV
            </button>
          </div>
          <div className="border-t border-[var(--border-color)] pt-4">
            <button
              type="button"
              onClick={handleTemplateClick}
              className="text-sm text-[var(--accent)] hover:underline"
            >
              下载模板
            </button>
            {templateToast && (
              <p className="mt-2 text-xs text-[var(--text-muted)]">模板已下载</p>
            )}
          </div>
        </div>
      )}

      {view === "import" && (
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--text-primary)]">
              选择文件
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-primary)]"
            />
            {selectedFile && (
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                {selectedFile.name}
              </p>
            )}
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setView("main")}
              className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm font-medium text-[var(--text-primary)] hover:bg-[var(--border-color)]"
            >
              返回
            </button>
            <button
              type="button"
              onClick={handleImportSubmit}
              disabled={!selectedFile || importSubmitting}
              className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)] disabled:opacity-50"
            >
              {importSubmitting ? "上传中..." : "上传并导入"}
            </button>
          </div>
        </div>
      )}

      {view === "importResult" && importResult && (
        <div className="space-y-4">
          {importResult.success && importResult.data ? (
            <>
              <p className="text-[var(--text-primary)]">
                成功导入 {importResult.data.imported} 条记录，新建{" "}
                {importResult.data.accounts_created.length} 个账户。
              </p>
              {importResult.data.errors.length > 0 && (
                <div className="rounded bg-amber-100 p-3 text-sm text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
                  <p className="font-medium">部分行有误：</p>
                  <ul className="mt-1 list-inside list-disc space-y-0.5">
                    {importResult.data.errors.slice(0, 10).map((msg, i) => (
                      <li key={i}>{msg}</li>
                    ))}
                    {importResult.data.errors.length > 10 && (
                      <li>… 共 {importResult.data.errors.length} 条</li>
                    )}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <p className="rounded bg-red-100 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
              导入失败：{importResult.error}
            </p>
          )}
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleCloseAfterResult}
              className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
            >
              关闭
            </button>
          </div>
        </div>
      )}

      {view === "exportResult" && (
        <div className="space-y-4">
          {exporting ? (
            <p className="text-[var(--text-muted)]">导出中...</p>
          ) : exportResult ? (
            <>
              {exportResult.success ? (
                <p className="text-[var(--text-primary)]">
                  导出成功，文件已保存到下载目录。
                </p>
              ) : (
                <p className="rounded bg-red-100 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
                  导出失败：{exportResult.error}
                </p>
              )}
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={handleCloseAfterResult}
                  className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)]"
                >
                  关闭
                </button>
              </div>
            </>
          ) : null}
        </div>
      )}
    </Modal>
  );
}
