import { createContext, useContext, useEffect, useMemo, useState, useCallback } from "react";

const AuthContext = createContext(null);

const STORAGE_KEY = "compose-yml.auth";
const GUEST_KEY = "compose-yml.guest";

// Mock auth — replace with real /api/auth/login when backend is ready.
// Accepted credentials (mock): any email matching a basic shape + password >= 6 chars.
const MOCK_ACCOUNTS = [
  { email: "admin@local.dev", password: "admin123" },
  { email: "demo@local.dev", password: "demo1234" },
];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isGuest, setIsGuest] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setUser(JSON.parse(raw));
      setIsGuest(localStorage.getItem(GUEST_KEY) === "1");
    } catch {
      // ignore corrupted storage
    } finally {
      setHydrated(true);
    }
  }, []);

  const login = useCallback(async ({ email, password, remember }) => {
    // Simulate latency so the loading state is visible.
    await new Promise((r) => setTimeout(r, 600));
    const match = MOCK_ACCOUNTS.find(
      (a) => a.email.toLowerCase() === email.trim().toLowerCase() && a.password === password
    );
    if (!match) {
      const err = new Error("邮箱或密码错误");
      err.code = "INVALID_CREDENTIALS";
      throw err;
    }
    const next = { email: match.email, loggedInAt: Date.now() };
    setUser(next);
    setIsGuest(false);
    if (remember) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      localStorage.removeItem(GUEST_KEY);
    } else {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    }
    return next;
  }, []);

  const enterAsGuest = useCallback(() => {
    setIsGuest(true);
    setUser(null);
    localStorage.setItem(GUEST_KEY, "1");
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setIsGuest(false);
    localStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(GUEST_KEY);
  }, []);

  const value = useMemo(
    () => ({ user, isGuest, hydrated, isAuthenticated: !!user, login, logout, enterAsGuest }),
    [user, isGuest, hydrated, login, logout, enterAsGuest]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
