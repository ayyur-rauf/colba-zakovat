"use client";

// Modul sahifalari uchun umumiy qobiq: sarlavha, modul nomi va bo'limlar menyusi.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { RequireAuth } from "@/lib/auth";
import { usePerms } from "@/lib/hooks";
import { moduleByKey, type ModuleDef } from "@/lib/modules";
import { Header } from "./ui";

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

  return (
    <>
      <Header />
      <div className="border-b border-line bg-bg-elev/60">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 pt-4">
          <div className="flex items-center gap-3 pb-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent-soft text-xl">{mod.icon}</span>
            <div>
              <div className="text-lg font-semibold leading-tight">{mod.title}</div>
              <div className="text-xs text-muted">{!mod.ready ? "Rejalashtirilmoqda" : staff ? "Tashkilotchi rejimi" : "Ishtirokchi"}</div>
            </div>
          </div>
          <nav className="-mb-px flex flex-1 gap-1 overflow-x-auto">
            {sections.map((s) => (
              <Link
                key={s.href}
                href={s.href}
                className={`whitespace-nowrap border-b-2 px-3 pb-3 pt-2 text-sm transition ${
                  active?.href === s.href ? "border-accent text-fg" : "border-transparent text-muted hover:text-fg"
                }`}
              >
                {s.title}
              </Link>
            ))}
          </nav>
        </div>
      </div>
      <main className="mx-auto w-full max-w-7xl flex-1 space-y-5 px-4 py-6">
        {mod.adminOnly && !perms.admin ? (
          <div className="card px-5 py-10 text-center text-muted">Bu bo&apos;lim faqat bosh admin uchun.</div>
        ) : (
          children
        )}
      </main>
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
