"use client";

// Modullar markazi: kirgandan keyingi birinchi sahifa.

import Link from "next/link";
import { RequireAuth, useAuth } from "@/lib/auth";
import { usePerms } from "@/lib/hooks";
import { MODULES } from "@/lib/modules";
import { Badge, Header } from "./ui";

function HubInner() {
  const { me, zakovat } = useAuth();
  const perms = usePerms();
  const roleIn = (key: string) => {
    if (key === "zakovat") return perms.zakovatTg ? "Tashkiliy guruh" : perms.zakovatScorer ? "Hisob hay'ati" : zakovat?.team ? `Jamoa: ${zakovat.team.name}` : null;
    if (key === "kitobxonlik") return perms.kitobOrganizer ? "Tashkilotchi" : perms.kitobReviewer ? "Tekshiruvchi" : null;
    return null;
  };

  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-10">
        <div className="mb-10">
          <p className="text-sm uppercase tracking-[0.2em] text-accent">{me?.season?.name ?? "Mavsum"}</p>
          <h1 className="glow-text mt-2 text-4xl font-bold tracking-tight md:text-5xl">
            Salom, {me?.employee?.full_name?.split(" ")[1] ?? me?.name}!
          </h1>
          <p className="mt-3 max-w-2xl text-muted">Modulni tanlang. Har bir modulda o&apos;z bo&apos;limlari va vazifangizga mos imkoniyatlar bor.</p>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          {MODULES.map((m) => {
            const role = roleIn(m.key);
            return (
              <Link key={m.key} href={m.href} className="card card-hover group relative overflow-hidden p-6">
                <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-accent/10 blur-2xl transition group-hover:bg-accent/20" />
                <div className="flex items-start justify-between">
                  <span className="grid h-14 w-14 place-items-center rounded-2xl bg-accent-soft text-3xl">{m.icon}</span>
                  {m.ready ? <Badge tone="green">Faol</Badge> : <Badge tone="amber">Tez kunda</Badge>}
                </div>
                <h2 className="mt-5 text-2xl font-semibold">{m.title}</h2>
                <p className="mt-1.5 text-sm text-muted">{m.tagline}</p>
                <div className="mt-5 flex flex-wrap items-center gap-2">
                  {m.sections
                    .filter(() => m.ready)
                    .map((s) => (
                      <span key={s.href} className="rounded-md border border-line px-2 py-0.5 text-xs text-muted">
                        {s.title}
                      </span>
                    ))}
                </div>
                <div className="mt-5 flex items-center justify-between text-sm">
                  <span className="text-muted">{role ?? (m.ready ? "Ishtirokchi" : "Rejalashtirilmoqda")}</span>
                  <span className="text-accent transition group-hover:translate-x-1">Kirish →</span>
                </div>
              </Link>
            );
          })}
        </div>
      </main>
    </>
  );
}

export default function Hub() {
  return (
    <RequireAuth>
      <HubInner />
    </RequireAuth>
  );
}
