"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, tokens } from "./api";
import { clearApiCache } from "./cache";
import type { Me, ZakovatMe } from "./types";

const SESSION_KEY = "colba.session";

type AuthState = {
  me: Me | null;
  zakovat: ZakovatMe | null;
  loading: boolean;
  reload: () => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [zakovat, setZakovat] = useState<ZakovatMe | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!tokens.access) {
      setMe(null);
      setZakovat(null);
      setLoading(false);
      return;
    }
    try {
      // ikkala so'rov parallel
      const [m, z] = await Promise.all([api<Me>("me"), api<ZakovatMe>("zakovat/me").catch(() => null)]);
      setMe(m);
      setZakovat(z);
      sessionStorage.setItem(SESSION_KEY, JSON.stringify({ me: m, zakovat: z }));
    } catch {
      tokens.clear();
      sessionStorage.removeItem(SESSION_KEY);
      setMe(null);
      setZakovat(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Sahifa yangilanganda oxirgi profil darhol ko'rsatiladi, keyin serverdan tekshiriladi
    const t = setTimeout(() => {
      const saved = tokens.access ? sessionStorage.getItem(SESSION_KEY) : null;
      if (saved) {
        const { me: m, zakovat: z } = JSON.parse(saved);
        setMe(m);
        setZakovat(z);
        setLoading(false);
      }
      reload();
    }, 0);
    return () => clearTimeout(t);
  }, [reload]);

  const logout = useCallback(() => {
    tokens.clear();
    sessionStorage.removeItem(SESSION_KEY);
    clearApiCache();
    setMe(null);
    setZakovat(null);
  }, []);

  return (
    <AuthContext.Provider value={{ me, zakovat, loading, reload, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("AuthProvider yo'q");
  return ctx;
}

/** Kirmagan foydalanuvchini /login ga yuboradi. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { me, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => {
    if (!loading && !me) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [loading, me, router, pathname]);
  if (loading || !me) {
    return <div className="p-10 text-center text-muted">Yuklanmoqda…</div>;
  }
  return <>{children}</>;
}
