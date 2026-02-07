# CSV Import/Export — Frontend Design

## 1. Entry point

- **TopBar:** Add one button (e.g. “CSV” or “导入/导出”) next to “新增记录” / ThemeToggle.
- **On click:** Open a **popup (modal)**. No navigation.

---

## 2. Main popup (first screen)

- **Purpose:** Let user choose **Import** or **Export**, and offer template download.
- **Content:**
  - Two primary actions (buttons or cards):
    - **Import** — “导入 CSV” — leads to import flow (§3).
    - **Export** — “导出 CSV” — leads to export flow (§4).
  - Below: one **secondary action**: **“下载模板”** (Download template) — triggers template download only; optional brief toast or no extra UI if browser handles download.
- **Close:** Modal close (X or backdrop) returns to app. After Import/Export, show result in a second modal (§3 / §4) rather than inside this one.

Reuse existing `Modal` (title + children). No form yet on this screen.

---

## 3. Import flow

1. User chose **Import** in main popup → close main popup and show **Import** modal (or same modal, content switch).
2. **Import modal content:**
   - **File input:** User selects a single CSV file (e.g. “选择文件” / “Choose file”). Accept `.csv` (and optionally `text/csv`).
   - **Submit:** “上传并导入” (or “Import”). On submit: call `POST /transactions/import` with the file (multipart), then show **result**.
3. **Result (success or error):**
   - Show in a **window/modal** (can be the same modal with content replaced, or a small result modal).
   - **Success:** e.g. “成功导入 N 条记录，新建 M 个账户。” (use `imported`, `accounts_created` from API). If `errors` is non-empty (best-effort mode), also show: “部分行有误：” + list of messages (e.g. row + message).
   - **Error:** Show API error message or list (e.g. “导入失败：” + `detail` or `errors`). No transactions/accounts created if backend is strict.
   - Provide a **关闭** (Close) button; on close, refresh transaction list (and account list if accounts were created) and close modal.

---

## 4. Export flow

1. User chose **Export** in main popup → close main popup and trigger export.
2. **Behavior:**
   - Call `GET /transactions/export` (optionally with current account filter: same `account` query as transaction list). Response is CSV file.
   - Trigger **download** to user’s download directory (e.g. `filename="transactions.csv"` from `Content-Disposition` or fixed name).
3. **Result:**
   - Show a **short feedback** in a small window/modal or toast:
     - **Success:** e.g. “导出成功，文件已保存到下载目录。”
     - **Error:** e.g. “导出失败：” + error message.

No file picker for export; path is the browser’s download directory.

---

## 5. Template download

- **Trigger:** “下载模板” in main popup (§2).
- **Action:** `GET /transactions/export?template=1` (or `GET /transactions/template` per backend). Receive CSV (header-only or with example rows), trigger download (e.g. `transactions_template.csv`).
- **Feedback:** Rely on browser download; optional short toast “模板已下载” if desired.

---

## 6. API (reference)

| Action           | Method | Endpoint                    | Request / Response |
|-----------------|--------|-----------------------------|---------------------|
| Import           | POST   | `/transactions/import`      | `multipart/form-data` with `file`. Response: `{ imported, accounts_created, errors[] }`. |
| Export           | GET    | `/transactions/export`      | Query: optional `account`. Response: CSV file (download). |
| Template         | GET    | `/transactions/export?template=1` or `/transactions/template` | Response: CSV file (download). |

Use existing `api` base and error handling; add `importTransactionsCsv(file)`, `exportTransactionsCsv(params?)`, `downloadTransactionsTemplate()` in `client.ts` that return blobs/trigger download and return parsed JSON for import.

---

## 7. Files to add or change

| File | Change |
|------|--------|
| `frontend/src/components/TopBar/TopBar.tsx` | Add CSV button; state for “CSV modal open”; render CSV modal. |
| **New** `frontend/src/components/TopBar/CsvModal.tsx` (or under a shared folder) | Main popup (Import / Export choice + “下载模板”). Can embed Import sub-flow (file input + result) and call export + result in same component. |
| `frontend/src/api/client.ts` | Add `importTransactionsCsv(file: File)`, `exportTransactionsCsv(params?)`, `downloadTransactionsTemplate()`. |
| `frontend/src/types/index.ts` | Optional: `TransactionImportResult { imported, accounts_created, errors }`. |
| `frontend/src/App.tsx` | Pass `onRefresh` (or equivalent) to TopBar so that after successful import/export the transaction (and account) list can refresh. TopBar already has `onTransactionAdded`; reuse or extend for “data changed” callback. |

Use existing `Modal` for main popup and for result windows; keep styling consistent with `AddTransactionModal` / theme.

---

## 8. Copy (for UX)

- TopBar button: e.g. **“CSV”** or **“导入/导出”**.
- Main popup title: e.g. **“CSV 导入 / 导出”**.
- Buttons: **“导入 CSV”**, **“导出 CSV”**, **“下载模板”**.
- Import result success: **“成功导入 {N} 条记录，新建 {M} 个账户。”**
- Import result error: **“导入失败：{message}”** (or list per row).
- Export result success: **“导出成功，文件已保存到下载目录。”**
- Export result error: **“导出失败：{message}”**.
