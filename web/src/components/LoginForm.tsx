"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError, tokens } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button, ErrorBar } from "./ui";

type LoginResponse =
  | { status: "active"; access: string; refresh: string }
  | { status: "pending" | "blocked"; detail: string };

export default function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { reload } = useAuth();
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function requestCode(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api<{ detail: string; dev_code?: string }>("auth/email/request-code", {
        method: "POST",
        body: { email },
      });
      setInfo(r.detail);
      setDevCode(r.dev_code ?? null);
      if (r.dev_code) setCode(r.dev_code);
      setStep("code");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Server bilan aloqa yo'q.");
    } finally {
      setBusy(false);
    }
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await api<LoginResponse>("auth/email/verify", { method: "POST", body: { email, code } });
      if (r.status === "active") {
        tokens.set(r.access, r.refresh);
        await reload();
        router.replace(params.get("next") || "/");
      } else {
        setError(r.detail);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Server bilan aloqa yo'q.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full max-w-sm rounded-2xl border border-gray-200 bg-white p-8 shadow-sm">
      <div className="mb-6 text-center">
        <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-xl bg-brand-600 text-xl font-bold text-white">
          C
        </div>
        <h1 className="text-xl font-semibold">Colba platformasi</h1>
        <p className="mt-1 text-sm text-gray-500">Xodimlar uchun intellektual tadbirlar</p>
      </div>

      <ErrorBar message={error} onClose={() => setError(null)} />

      {step === "email" ? (
        <form onSubmit={requestCode} className="mt-4 space-y-4">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">Ish emailingiz</span>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              placeholder="ism@colba.uz"
            />
          </label>
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Yuborilmoqda…" : "Kod olish"}
          </Button>
          <p className="text-center text-xs text-gray-400">Telegram va Google orqali kirish keyinroq qo&apos;shiladi</p>
        </form>
      ) : (
        <form onSubmit={verify} className="mt-4 space-y-4">
          <p className="text-sm text-gray-600">{info}</p>
          {devCode && (
            <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Mahalliy sinov rejimi: kod avtomatik qo&apos;yildi ({devCode}).
            </p>
          )}
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-gray-700">6 xonali kod</span>
            <input
              inputMode="numeric"
              pattern="\d{6}"
              maxLength={6}
              required
              autoFocus
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-center text-lg tracking-[0.5em] outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </label>
          <Button type="submit" disabled={busy || code.length !== 6} className="w-full">
            {busy ? "Tekshirilmoqda…" : "Kirish"}
          </Button>
          <button type="button" className="w-full text-sm text-gray-500 hover:text-gray-700" onClick={() => setStep("email")}>
            ← Boshqa email
          </button>
        </form>
      )}
    </div>
  );
}
