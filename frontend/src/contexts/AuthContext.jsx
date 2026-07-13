import { createContext, useContext, useEffect, useMemo, useState, useCallback } from "react";

const AuthContext = createContext(null);

const STORAGE_KEY = "compose-yml.auth";
const GUEST_KEY = "compose-yml.guest";
const API_BASE = "/api";

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
    } finally {
      setHydrated(true);
    }
  }, []);

  const login = useCallback(async ({ username, password, remember }) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const err = new Error(body.detail || "用户名或密码错误");
      err.code = "INVALID_CREDENTIALS";
      throw err;
    }
    const data = await res.json();
    const next = {
      id: data.id,
      username: data.username,
      role: data.role || "user",
      loggedInAt: Date.now(),
    };
    setUser(next);
    setIsGuest(false);
    const storage = remember ? localStorage : sessionStorage;
    if (!remember) localStorage.removeItem(STORAGE_KEY);
    storage.setItem(STORAGE_KEY, JSON.stringify(next));
    localStorage.removeItem(GUEST_KEY);

    // 后台拉取一次最新的 role/id,确保 localStorage 与服务端一致
    try {
      const meRes = await fetch(`${API_BASE}/auth/getUserInfo?user_id=${next.id}`);
      if (meRes.ok) {
        const me = await meRes.json();
        const enriched = { ...next, role: me.role || next.role, username: me.username || next.username };
        setUser(enriched);
        storage.setItem(STORAGE_KEY, JSON.stringify(enriched));
        return enriched;
      }
    } catch {
      // 网络/服务异常不影响主登录流程
    }
    return next;
  }, []);

  const register = useCallback(async ({ username, password }) => {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "注册失败");
    }
    return res.json();
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
    () => ({
      user,
      isGuest,
      hydrated,
      isAuthenticated: !!user,
      isAdmin: !!user && user.role === "admin",
      login,
      register,
      logout,
      enterAsGuest,
    }),
    [user, isGuest, hydrated, login, register, logout, enterAsGuest],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
