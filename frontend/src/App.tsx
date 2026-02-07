import { useEffect, useState } from "react";
import { TopBar } from "./components/TopBar/TopBar";
import { AccountManagementBlock } from "./components/AccountManagementBlock/AccountManagementBlock";
import { TransactionBlock } from "./components/TransactionBlock/TransactionBlock";
import { Footer } from "./components/Footer";
import { api } from "./api/client";
import type { Account } from "./types";

function App() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountNames, setSelectedAccountNames] = useState<Set<string>>(
    () => new Set()
  );
  const [refreshKey, setRefreshKey] = useState(0);

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
