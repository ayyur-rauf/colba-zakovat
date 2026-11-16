"use client";

import { useCallback, useSyncExternalStore } from "react";

export type Theme = "light" | "dark";
export const THEME_KEY = "colba.theme";

/** Sahifa chizilishidan oldin ishlaydigan skript: saqlangan yoki tizim mavzusini qo'yadi (miltillamaslik uchun). */
export const THEME_BOOT_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_KEY}");if(t!=="light"&&t!=="dark"){t=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.dataset.theme=t}catch(e){}})();`;

const listeners = new Set<() => void>();

function current(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function useTheme() {
  const theme = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    current,
    () => "light" as Theme,
  );
  const toggle = useCallback(() => {
    const next: Theme = current() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem(THEME_KEY, next);
    listeners.forEach((l) => l());
  }, []);
  return { theme, toggle };
}
