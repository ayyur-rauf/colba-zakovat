"use client";

import { useEffect } from "react";

/** fn ni darhol (keyingi tick'da) va keyin har `ms` da chaqiradi. Sahifa yopilganda to'xtaydi. */
export function usePolling(fn: () => void, ms: number) {
  useEffect(() => {
    const first = setTimeout(fn, 0);
    const timer = setInterval(fn, ms);
    return () => {
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [fn, ms]);
}
