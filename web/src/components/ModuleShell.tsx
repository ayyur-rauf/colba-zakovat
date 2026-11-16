"use client";

// Modul sahifalari qobig'i: sarlavha, modul nomi, chapda bo'limlar menyusi, o'ngda mazmun.
// Tor ekranda menyu tepada gorizontal ko'rinishga o'tadi.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { RequireAuth } from "@/lib/auth";
import { usePerms } from "@/lib/hooks";
import { moduleByKey, type ModuleDef } from "@/lib/modules";
import { Footer, Header } from "./ui";

function Shell({ moduleKey, children }: { moduleKey: ModuleDef["key"]; children: React.ReactNode }) {
  const mod = moduleByKey(moduleKey);
  const pathname = usePathname();
  const perms = usePerms();
  const staff =
    moduleKey === "zakovat"
      ? perms.zakovatTg || perms.zakovatScorer
      : moduleKey === "kitobxonlik"
        ? perms.kitobReviewer
        : moduleKey === "boshqaruv"
          ? perms.admin
          : false;
  const sections = mod.sections.filter((s) => !s.staffOnly || staff);
  // Faol bo'lim: maxsus andoza → modul bosh sahifasi (aniq moslik) → eng uzun mos prefiks
  const active =
    sections.find((s) => s.match?.test(pathname)) ??
    [...sections]
      .sort((a, b) => b.href.length - a.href.length)
      .find((s) => (s.href === mod.href ? pathname === s.href : pathname.startsWith(s.href)));
  const blocked = mod.adminOnly && !perms.admin;
  const roleText = !mod.ready ? "Rejalashtirilmoqda" : mod.adminOnly ? "Administrator" : staff ? "Tashkilotchi rejimi" : "Ishtirokchi";

  return (
    <>
      <Header />
      <div className="mx-auto w-full max-w-7xl flex-1 px-4 pb-6 pt-8">
        <div className="mb-6">
          <h1 className="flex items-center gap-2.5 text-[28px] font-bold tracking-tight">
            <span className="text-2xl">{mod.icon}</span>
            {mod.title}
          </h1>
          <p className="mt-1 text-sm text-muted">
            {roleText} · {mod.tagline}
          </p>
        </div>

        <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
          {sections.length > 1 && (
            <aside className="card shrink-0 p-2.5 lg:sticky lg:top-[88px] lg:w-56">
              <nav className="flex gap-1 overflow-x-auto lg:flex-col">
                {sections.map((s) => (
                  <Link
                    key={s.href}
                    href={s.href}
                    className={`whitespace-nowrap rounded-xl px-3.5 py-2.5 text-sm font-semibold transition ${
                      active?.href === s.href ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-2 hover:text-fg"
                    }`}
                  >
                    {s.title}
                  </Link>
                ))}
              </nav>
            </aside>
          )}
          <main className="min-w-0 flex-1 space-y-5">
            {blocked ? <div className="card px-5 py-10 text-center text-muted">Bu bo&apos;lim faqat bosh admin uchun.</div> : children}
          </main>
        </div>
      </div>
      <Footer />
    </>
  );
}

export default function ModuleShell(props: { moduleKey: ModuleDef["key"]; children: React.ReactNode }) {
  return (
    <RequireAuth>
      <Shell {...props} />
    </RequireAuth>
  );
}
