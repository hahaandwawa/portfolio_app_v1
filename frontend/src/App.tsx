import { useCallback, useEffect, useState, useMemo } from "react";
import { TopBar } from "./components/TopBar/TopBar";
import { GeneralOverviewBlock } from "./components/GeneralOverviewBlock/GeneralOverviewBlock";
import { AccountManagementBlock } from "./components/AccountManagementBlock/AccountManagementBlock";
import { PortfolioBlock } from "./components/PortfolioBlock/PortfolioBlock";
import { TransactionBlock } from "./components/TransactionBlock/TransactionBlock";
import { Footer } from "./components/Footer";
import { api } from "./api/client";
import type { Account, PortfolioSummary } from "./types";

function App() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountNames, setSelectedAccountNames] = useState<Set<string>>(
    () => new Set()
  );
  const [refreshKey, setRefreshKey] = useState(0);
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);

  const loadAccounts = useCallback(() => {
    api
      .getAccounts()
      .then((list) => {
        setAccounts(list);
        setSelectedAccountNames((prev) => {
          if (prev.size === 0 && list.length > 0) {
            return new Set(list.map((a) => a.name));
          }
          return prev;
        });
      })
      .catch(() => setAccounts([]));
  }, []);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  // Fetch portfolio when selected accounts or refresh key change.
  // Loading/error state is reset in event handlers (handleAccountSelectionChange,
  // onRefresh) to avoid synchronous setState in the effect body.
  // The initial render already starts with portfolioLoading=true.
  useEffect(() => {
    let cancelled = false;
    const accountParam =
      selectedAccountNames.size > 0 ? Array.from(selectedAccountNames) : undefined;
    api
      .getPortfolio({ account: accountParam })
      .then((data) => {
        if (!cancelled) setPortfolio(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setPortfolioError(err instanceof Error ? err.message : "加载失败");
          setPortfolio(null);
        }
      })
      .finally(() => {
        if (!cancelled) setPortfolioLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedAccountNames, refreshKey]);

  const accountCashList = portfolio?.account_cash;
  const accountCashMap = useMemo(() => {
    if (!accountCashList) return undefined;
    const map: Record<string, number> = {};
    for (const ac of accountCashList) {
      map[ac.account_name] = ac.cash_balance;
    }
    return map;
  }, [accountCashList]);

  const handleAccountSelectionChange = useCallback((selected: Set<string>) => {
    setSelectedAccountNames(selected);
    setPortfolioLoading(true);
    setPortfolioError(null);
  }, []);

  const onRefresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
    setPortfolioLoading(true);
    setPortfolioError(null);
    loadAccounts();
  }, [loadAccounts]);

  return (
    <div className="flex min-h-screen flex-col">
      <TopBar
        accounts={accounts}
        selectedAccountNames={selectedAccountNames}
        onAccountSelectionChange={handleAccountSelectionChange}
        onTransactionAdded={onRefresh}
      />
      <div className="mx-auto w-full max-w-5xl flex-1 px-8 md:px-12">
        <GeneralOverviewBlock
          portfolio={portfolio}
          loading={portfolioLoading}
          error={portfolioError}
        />
        <AccountManagementBlock
          accounts={accounts}
          accountCashMap={accountCashMap}
          onAccountAdded={onRefresh}
          onAccountRenamed={(oldName, newName) => {
            setSelectedAccountNames((prev) => {
              if (!prev.has(oldName)) return prev;
              const next = new Set(prev);
              next.delete(oldName);
              next.add(newName);
              return next;
            });
          }}
        />
        <main className="flex-1">
          <PortfolioBlock
            positions={portfolio?.positions ?? []}
            loading={portfolioLoading}
            error={portfolioError}
          />
          <TransactionBlock
            accounts={accounts}
            selectedAccountNames={selectedAccountNames}
            refreshKey={refreshKey}
            onRefresh={onRefresh}
          />
        </main>
        <Footer />
      </div>
    </div>
  );
}

export default App;
