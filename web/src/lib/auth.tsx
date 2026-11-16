"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, tokens } from "./api";
import type { Me, ZakovatMe } from "./types";

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
      const m = await api<Me>("me");
      setMe(m);
      setZakovat(await api<ZakovatMe>("zakovat/me").catch(() => null));
    } catch {
      tokens.clear();
      setMe(null);
      setZakovat(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(reload, 0); // birinchi yuklash (localStorage faqat brauzerda)
    return () => clearTimeout(t);
  }, [reload]);

  const logout = useCallback(() => {
    tokens.clear();
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
    return <div className="p-10 text-center text-gray-500">Yuklanmoqda…</div>;
  }
  return <>{children}</>;
}
