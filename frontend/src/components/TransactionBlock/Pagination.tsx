interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({
  page,
  totalPages,
  onPageChange,
}: PaginationProps) {
  const showPages = getVisiblePages(page, totalPages);

  return (
    <div className="flex items-center justify-center gap-2 py-4">
      <button
        type="button"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="rounded-lg px-3 py-2 text-sm font-medium text-[var(--text-primary)] transition disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[var(--accent-soft)]"
      >
        ‹ 上一页
      </button>
      <div className="flex items-center gap-1">
        {showPages.map((p, i) =>
          p === "ellipsis" ? (
            <span key={`e-${i}`} className="px-2 text-[var(--text-secondary)]">
              …
            </span>
          ) : (
            <button
              key={p}
              type="button"
              onClick={() => onPageChange(p)}
              className={`min-w-[32px] rounded-lg px-2 py-2 text-sm font-medium transition ${
                p === page
                  ? "bg-[var(--accent)] text-white shadow-sm"
                  : "text-[var(--text-primary)] hover:bg-[var(--accent-soft)]"
              }`}
            >
              {p}
            </button>
          )
        )}
      </div>
      <button
        type="button"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="rounded-lg px-3 py-2 text-sm font-medium text-[var(--text-primary)] transition disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[var(--accent-soft)]"
      >
        下一页 ›
      </button>
    </div>
  );
}

function getVisiblePages(current: number, total: number): (number | "ellipsis")[] {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  const result: (number | "ellipsis")[] = [1];
  if (current > 3) result.push("ellipsis");
  const midStart = Math.max(2, current - 1);
  const midEnd = Math.min(total - 1, current + 1);
  for (let i = midStart; i <= midEnd; i++) {
    if (!result.includes(i)) result.push(i);
  }
  if (current < total - 2) result.push("ellipsis");
  if (total > 1) result.push(total);
  return result;
}
