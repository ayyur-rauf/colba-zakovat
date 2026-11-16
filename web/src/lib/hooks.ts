"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "./api";
import { useAuth } from "./auth";
import type { Me } from "./types";

export function errText(e: unknown) {
  return e instanceof ApiError ? e.message : "Server bilan aloqa yo'q.";
}

/** GET so'rov: ma'lumot, xato, qayta yuklash. path=null bo'lsa so'rov yuborilmaydi. */
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    if (!path) return;
    try {
      setData(await api<T>(path));
      setError(null);
    } catch (e) {
      setError(errText(e));
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    const t = setTimeout(reload, 0);
    return () => clearTimeout(t);
  }, [reload]);

  return { data, error, loading, reload, setError };
}

/** Tugma amallari: band holati, xato va muvaffaqiyat xabari. */
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const run = useCallback(async (fn: () => Promise<unknown>, ok?: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await fn();
      if (ok) setNotice(ok);
      return true;
    } catch (e) {
      setError(errText(e));
      return false;
    } finally {
      setBusy(false);
    }
  }, []);

  const clear = useCallback(() => {
    setError(null);
    setNotice(null);
  }, []);

  return { busy, error, notice, run, clear, setError };
}

export function hasRole(me: Me | null, role: string, module: string) {
  if (!me) return false;
  if (me.is_admin || me.roles.some((r) => r.role === "admin")) return true;
  return me.roles.some((r) => r.role === role && r.module === module);
}

/** Joriy foydalanuvchining modullardagi huquqlari. */
export function usePerms() {
  const { me, zakovat } = useAuth();
  const kitobOrganizer = hasRole(me, "organizer", "kitobxonlik");
  return {
    zakovatTg: !!zakovat?.is_tg,
    zakovatScorer: !!zakovat?.is_scorer,
    kitobOrganizer,
    kitobReviewer: kitobOrganizer || hasRole(me, "reviewer", "kitobxonlik"),
  };
}
