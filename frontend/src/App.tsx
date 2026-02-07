import { useEffect, useState, useMemo } from "react";
import { TopBar } from "./components/TopBar/TopBar";
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

  const loadAccounts = () => {
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
  };

  useEffect(() => {
    loadAccounts();
  }, []);

  useEffect(() => {
    let cancelled = false;
    setPortfolioLoading(true);
    setPortfolioError(null);
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

  const accountCashMap = useMemo(() => {
    if (!portfolio?.account_cash) return undefined;
    const map: Record<string, number> = {};
    for (const ac of portfolio.account_cash) {
      map[ac.account_name] = ac.cash_balance;
    }
    return map;
  }, [portfolio?.account_cash]);

  const onAccountSelectionChange = (selected: Set<string>) => {
    setSelectedAccountNames(selected);
  };

  const onRefresh = () => {
    setRefreshKey((k) => k + 1);
    loadAccounts();
  };

  return (
    <div className="flex min-h-screen flex-col">
      <div className="mx-auto w-full max-w-5xl flex-1 px-8 md:px-12">
        <TopBar
          accounts={accounts}
          selectedAccountNames={selectedAccountNames}
          onAccountSelectionChange={onAccountSelectionChange}
          onTransactionAdded={onRefresh}
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
