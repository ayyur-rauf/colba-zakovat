"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function Button({
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" | "success" }) {
  const styles = {
    primary: "bg-brand-600 text-white hover:bg-brand-700 disabled:bg-gray-300",
    ghost: "bg-white text-gray-800 border border-gray-300 hover:bg-gray-50 disabled:text-gray-400",
    danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-gray-300",
    success: "bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-gray-300",
  }[variant];
  return (
    <button
      className={`inline-flex items-center justify-center gap-1 rounded-lg px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed ${styles} ${className}`}
      {...props}
    />
  );
}

export function Badge({ children, tone = "gray" }: { children: React.ReactNode; tone?: "gray" | "blue" | "green" | "amber" | "red" }) {
  const t = {
    gray: "bg-gray-100 text-gray-700",
    blue: "bg-brand-100 text-brand-700",
    green: "bg-emerald-100 text-emerald-800",
    amber: "bg-amber-100 text-amber-800",
    red: "bg-red-100 text-red-700",
  }[tone];
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${t}`}>{children}</span>;
}

export function ErrorBar({ message, onClose }: { message: string | null; onClose: () => void }) {
  if (!message) return null;
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      <span>{message}</span>
      <button onClick={onClose} className="text-red-500 hover:text-red-700" aria-label="Yopish">
        ✕
      </button>
    </div>
  );
}

export function Header() {
  const { me, logout } = useAuth();
  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold text-gray-900">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-white">C</span>
          Colba platformasi
        </Link>
        {me && (
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-gray-600 sm:inline">
              {me.name}
              {me.employee && <span className="text-gray-400"> · {me.employee.branch}</span>}
            </span>
            <Button variant="ghost" onClick={logout}>
              Chiqish
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleString("uz-UZ", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
