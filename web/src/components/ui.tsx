"use client";

// Umumiy UI komponentlari. Ranglar globals.css dagi o'zgaruvchilardan olinadi.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { MODULES } from "@/lib/modules";

type Variant = "primary" | "ghost" | "danger" | "success" | "soft";

const BTN: Record<Variant, string> = {
  primary: "bg-accent text-white hover:bg-accent-strong shadow-[0_8px_24px_-10px_var(--accent)]",
  ghost: "border border-line bg-transparent text-fg hover:bg-surface-2",
  soft: "bg-accent-soft text-accent hover:bg-accent/25",
  danger: "bg-danger/90 text-white hover:bg-danger",
  success: "bg-success/90 text-white hover:bg-success",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 rounded-[10px] px-3.5 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${BTN[variant]} ${className}`}
      {...props}
    />
  );
}

export function LinkButton({
  href,
  variant = "ghost",
  className = "",
  children,
  ...rest
}: { href: string; variant?: Variant; className?: string; children: React.ReactNode; target?: string }) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center gap-1.5 rounded-[10px] px-3.5 py-2 text-sm font-medium transition ${BTN[variant]} ${className}`}
      {...rest}
    >
      {children}
    </Link>
  );
}

type Tone = "gray" | "red" | "green" | "amber" | "gold";
const TONE: Record<Tone, string> = {
  gray: "bg-surface-2 text-muted",
  red: "bg-accent-soft text-accent",
  green: "bg-success/15 text-success",
  amber: "bg-warning/15 text-warning",
  gold: "bg-gold/15 text-gold",
};

export function Badge({ children, tone = "gray" }: { children: React.ReactNode; tone?: Tone }) {
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${TONE[tone]}`}>
      {children}
    </span>
  );
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function CardHeader({ title, subtitle, actions }: { title: React.ReactNode; subtitle?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
      <div>
        <h2 className="font-semibold">{title}</h2>
        {subtitle && <div className="mt-0.5 text-sm text-muted">{subtitle}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function PageTitle({ title, subtitle, actions }: { title: React.ReactNode; subtitle?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <div className="mt-1 text-muted">{subtitle}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Notice({ error, notice, onClose }: { error?: string | null; notice?: string | null; onClose: () => void }) {
  if (!error && !notice) return null;
  const isErr = !!error;
  return (
    <div
      className={`flex items-start justify-between gap-3 rounded-xl border px-4 py-3 text-sm ${
        isErr ? "border-danger/40 bg-danger/10 text-danger" : "border-success/40 bg-success/10 text-success"
      }`}
    >
      <span>{error ?? notice}</span>
      <button onClick={onClose} className="opacity-70 hover:opacity-100" aria-label="Yopish">
        ✕
      </button>
    </div>
  );
}

/** Eski nom bilan moslik uchun */
export function ErrorBar({ message, onClose }: { message: string | null; onClose: () => void }) {
  return <Notice error={message} onClose={onClose} />;
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="px-5 py-10 text-center text-sm text-muted">{children}</div>;
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block font-medium text-fg/90">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="card px-5 py-4">
      <div className="text-xs uppercase tracking-wider text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted">{hint}</div>}
    </div>
  );
}

export function Logo({ size = 36 }: { size?: number }) {
  return (
    <span
      className="grid place-items-center rounded-xl bg-gradient-to-br from-accent to-accent-strong font-bold text-white shadow-[0_6px_24px_-6px_var(--accent)]"
      style={{ width: size, height: size, fontSize: size * 0.5 }}
    >
      C
    </span>
  );
}

export function Header() {
  const { me, logout } = useAuth();
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg-elev/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
        <Link href="/" className="flex items-center gap-2.5 font-semibold">
          <Logo size={32} />
          <span className="hidden sm:inline">Colba</span>
        </Link>
        <nav className="flex flex-1 items-center gap-1 overflow-x-auto">
          {MODULES.map((m) => {
            const active = pathname.startsWith(m.href);
            return (
              <Link
                key={m.key}
                href={m.href}
                className={`flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm transition ${
                  active ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-2 hover:text-fg"
                }`}
              >
                <span>{m.icon}</span>
                {m.title}
              </Link>
            );
          })}
        </nav>
        {me && (
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-right leading-tight md:block">
              <span className="block">{me.employee?.full_name ?? me.name}</span>
              {me.employee && <span className="block text-xs text-muted">{me.employee.branch}</span>}
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

export function formatDate(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
