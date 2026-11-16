import type { Role } from "@/lib/roles";

// shortcut: demo accounts live in localStorage in plain text. Replace with the
// backend user store when real auth lands.
export type AccountRole = Exclude<Role, "superadmin">;

export type Account = {
  id: string;
  name: string;
  email: string;
  password: string;
  role: AccountRole;
  createdAt: string;
};

const ACCOUNTS_KEY = "washroom_accounts";

const SEED: Account[] = [
  {
    id: "seed-admin",
    name: "S. Khan",
    email: "s.khan@fuelco.example",
    password: "admin",
    role: "admin",
    createdAt: "2026-11-10",
  },
  {
    id: "seed-branch",
    name: "M. Ali",
    email: "m.ali@fuelco.example",
    password: "branch",
    role: "branch",
    createdAt: "2026-11-10",
  },
];

function readRaw(): Account[] | null {
  if (typeof window === "undefined") return null;
  try {
    const value = window.localStorage.getItem(ACCOUNTS_KEY);
    if (!value) return null;
    const parsed = JSON.parse(value) as Account[];
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function readAccounts(): Account[] {
  const stored = readRaw();
  if (stored) return stored;
  // First run: seed two demo accounts so the list is never empty.
  writeAccounts(SEED);
  return SEED;
}

export function writeAccounts(accounts: Account[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(accounts));
  } catch {
    // Storage can be unavailable in private mode; the demo still works in-session.
  }
}

export function findAccountByEmail(email: string): Account | undefined {
  const value = email.trim().toLowerCase();
  return readAccounts().find(
    (account) => account.email.toLowerCase() === value
  );
}

export function createAccount(
  input: Omit<Account, "id" | "createdAt">
): Account {
  const account: Account = {
    ...input,
    name: input.name.trim(),
    email: input.email.trim(),
    id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
    createdAt: new Date().toISOString().slice(0, 10),
  };
  writeAccounts([...readAccounts(), account]);
  return account;
}

export function removeAccount(id: string) {
  writeAccounts(readAccounts().filter((account) => account.id !== id));
}
