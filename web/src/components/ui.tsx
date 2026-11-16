"use client";

// Umumiy UI komponentlari. Ranglar globals.css dagi o'zgaruvchilardan olinadi
// (kunduzgi va tungi mavzu avtomatik almashadi).

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { usePerms } from "@/lib/hooks";
import { ADMIN_MODULE, MODULES } from "@/lib/modules";
import { useTheme } from "@/lib/theme";

type Variant = "primary" | "ghost" | "danger" | "success" | "soft";

const BTN: Record<Variant, string> = {
  primary: "rounded-[10px] bg-accent text-white hover:bg-accent-strong",
  ghost: "rounded-full border border-line bg-surface text-fg hover:bg-surface-2",
  soft: "rounded-[10px] bg-accent-soft text-accent hover:brightness-95",
  danger: "rounded-[10px] bg-danger/10 text-danger hover:bg-danger/20",
  success: "rounded-[10px] bg-success text-white hover:bg-accent-strong",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${BTN[variant]} ${className}`}
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
      className={`inline-flex items-center justify-center gap-1.5 px-4 py-2 text-sm font-semibold transition ${BTN[variant]} ${className}`}
      {...rest}
    >
      {children}
    </Link>
  );
}

type Tone = "gray" | "accent" | "red" | "green" | "amber" | "gold";
const TONE: Record<Tone, string> = {
  gray: "bg-surface-2 text-muted",
  accent: "bg-accent-soft text-accent",
  red: "bg-danger/10 text-danger",
  green: "bg-accent-soft text-success",
  amber: "bg-warning/12 text-warning",
  gold: "bg-gold/12 text-gold",
};

export function Badge({ children, tone = "gray" }: { children: React.ReactNode; tone?: Tone }) {
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${TONE[tone]}`}>
      {children}
    </span>
  );
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function CardHeader({ title, subtitle, actions }: { title: React.ReactNode; subtitle?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-6 pb-2 pt-5">
      <div>
        <h2 className="text-lg font-bold tracking-tight">{title}</h2>
        {subtitle && <div className="mt-0.5 text-xs text-muted">{subtitle}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function PageTitle({ title, subtitle, actions }: { title: React.ReactNode; subtitle?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {subtitle && <div className="mt-1 text-sm text-muted">{subtitle}</div>}
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
        isErr ? "border-danger/30 bg-danger/8 text-danger" : "border-accent/25 bg-accent-soft text-accent"
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
      <span className="mb-1.5 block text-xs font-semibold text-fg/80">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

export function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="card px-5 py-5">
      <div className="text-xs font-medium text-muted">{label}</div>
      <div className="mt-2 text-2xl font-bold tracking-tight">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted">{hint}</div>}
    </div>
  );
}

/** Qalqon shaklidagi logotip (rasmdagi kabi). Rangi mavzuga qarab o'zgaradi. */
export function Logo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true" className="shrink-0 text-accent">
      <path
        d="M20 3 6 8v10c0 9 6.2 16.3 14 19 7.8-2.7 14-10 14-19V8L20 3Z"
        fill="currentColor"
        fillOpacity="0.12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path d="M24.5 15.5a6 6 0 1 0 0 9" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}

export function Brand({ sub = "INTELLEKTUAL PLATFORMA" }: { sub?: string }) {
  return (
    <Link href="/" className="flex items-center gap-3">
      <Logo size={38} />
      <span className="leading-tight">
        <span className="block text-[17px] font-extrabold tracking-wide">
          COLBA <span className="text-accent">PLATFORMA</span>
        </span>
        <span className="block text-[10px] font-semibold tracking-[0.2em] text-muted">{sub}</span>
      </span>
    </Link>
  );
}

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
  return (
    <button
      onClick={toggle}
      title={dark ? "Kunduzgi ko'rinish" : "Tungi ko'rinish"}
      aria-label={dark ? "Kunduzgi ko'rinish" : "Tungi ko'rinish"}
      className="grid h-9 w-9 place-items-center rounded-full border border-line bg-surface text-muted transition hover:text-fg"
    >
      {dark ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
        </svg>
      )}
    </button>
  );
}

function roleLabel(perms: ReturnType<typeof usePerms>) {
  if (perms.admin) return "Administrator";
  if (perms.zakovatTg) return "Tashkiliy guruh";
  if (perms.kitobOrganizer) return "Tashkilotchi";
  if (perms.zakovatScorer) return "Hisob hay'ati";
  if (perms.kitobReviewer) return "Tekshiruvchi";
  return null;
}

export function Header() {
  const { me, logout } = useAuth();
  const pathname = usePathname();
  const perms = usePerms();
  const role = roleLabel(perms);
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg-elev/90 backdrop-blur">
      <div className="mx-auto flex h-[68px] max-w-7xl items-center gap-6 px-4">
        <Brand />
        <nav className="flex flex-1 items-center justify-center gap-1 overflow-x-auto">
          {MODULES.map((m) => {
            const active = pathname.startsWith(m.href);
            return (
              <Link
                key={m.key}
                href={m.href}
                className={`whitespace-nowrap rounded-xl px-3.5 py-2 text-sm font-semibold transition ${
                  active ? "bg-accent-soft text-accent" : "text-muted hover:text-fg"
                }`}
              >
                {m.title}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-2 text-sm">
          {role && (
            <span className="hidden rounded-lg border border-line px-2 py-1 text-[11px] font-semibold text-muted lg:inline">{role}</span>
          )}
          {perms.admin && (
            <Link
              href={ADMIN_MODULE.href}
              className={`hidden items-center gap-1.5 rounded-full border px-3.5 py-2 font-semibold transition sm:inline-flex ${
                pathname.startsWith(ADMIN_MODULE.href) ? "border-accent/40 bg-accent-soft text-accent" : "border-line bg-surface hover:bg-surface-2"
              }`}
            >
              ⚙ Boshqaruv
            </Link>
          )}
          <ThemeToggle />
          {me && (
            <Button variant="ghost" onClick={logout} title={me.employee?.full_name ?? me.name}>
              Chiqish
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}

export function Footer() {
  return <footer className="py-8 text-center text-xs text-muted">COLBA · Intellektual tadbirlar boshqaruv tizimi</footer>;
}

export function formatDate(iso: string | null | undefined) {
  if (!iso) return "—";
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
