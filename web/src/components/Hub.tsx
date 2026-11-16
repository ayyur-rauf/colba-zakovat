"use client";

// Bosh sahifa: yashil banner, qisqa ko'rsatkichlar, e'lonlar va modullarga tezkor o'tish.

import Link from "next/link";
import { RequireAuth, useAuth } from "@/lib/auth";
import { useApi, usePerms } from "@/lib/hooks";
import { ADMIN_MODULE, MODULES } from "@/lib/modules";
import type { Game, SeasonStandings } from "@/lib/types";
import AnnouncementsFeed from "./Announcements";
import { Badge, Footer, Header, Stat } from "./ui";

function HubInner() {
  const { me, zakovat } = useAuth();
  const perms = usePerms();
  const games = useApi<Game[]>("zakovat/games");
  const standings = useApi<SeasonStandings>("zakovat/standings");
  const league = (games.data ?? []).filter((g) => g.kind === "league");
  const played = league.filter((g) => g.status === "final").length;
  const leader = standings.data?.rows.find((r) => r.place === 1);
  const next = (games.data ?? []).find((g) => g.status === "registration" || g.status === "in_progress");

  const roleIn = (key: string) => {
    if (key === "zakovat") return perms.zakovatTg ? "Tashkiliy guruh" : perms.zakovatScorer ? "Hisob hay'ati" : zakovat?.team ? `Jamoa: ${zakovat.team.name}` : null;
    if (key === "kitobxonlik") return perms.kitobOrganizer ? "Tashkilotchi" : perms.kitobReviewer ? "Tekshiruvchi" : null;
    return null;
  };
  const firstName = me?.employee?.full_name?.split(" ")[1] ?? me?.name;

  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-7xl flex-1 space-y-8 px-4 py-8">
        {/* Banner */}
        <section className="hero px-8 py-10 md:px-10 md:py-12">
          <div className="relative z-10">
            <div className="text-xs font-semibold tracking-[0.25em] text-white/80">INTELLEKTUAL TADBIRLAR · {me?.season?.name}</div>
            <h1 className="mt-3 text-4xl font-extrabold tracking-tight md:text-5xl">COLBA PLATFORMASI</h1>
            <p className="mt-3 text-white/85">
              Salom, {firstName}! {next ? `Navbatdagi o'yin: ${next.title}${next.venue ? " · 📍 " + next.venue : ""}` : "Modulni tanlang va boshlang."}
            </p>
          </div>
          <span className="absolute right-10 top-1/2 z-10 hidden -translate-y-1/2 text-5xl text-white/70 md:block">✦</span>
        </section>

        {/* Ko'rsatkichlar */}
        <div className="grid gap-4 sm:grid-cols-3">
          <Stat label="Yakunlangan turlar (Zakovat)" value={`${played} / ${league.length || "—"}`} />
          <Stat label="Umumiy reyting yetakchisi" value={leader?.team.name ?? "—"} hint={leader ? `${leader.points} ball` : undefined} />
          <Stat label="Mening jamoam" value={zakovat?.team?.name ?? "—"} hint={zakovat?.is_captain ? "Siz sardorsiz" : undefined} />
        </div>

        <AnnouncementsFeed title="Yangiliklar" />

        {/* Modullar */}
        <section>
          <h2 className="mb-4 text-xl font-bold tracking-tight">Tezkor o&apos;tish</h2>
          <div className="grid gap-5 sm:grid-cols-2">
            {[...MODULES, ...(perms.admin ? [ADMIN_MODULE] : [])].map((m) => {
              const role = roleIn(m.key) ?? (m.adminOnly ? "Administrator" : m.ready ? "Ishtirokchi" : "Rejalashtirilmoqda");
              return (
                <div key={m.key} className="card flex flex-col p-6">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className="grid h-11 w-11 place-items-center rounded-xl bg-accent-soft text-2xl">{m.icon}</span>
                      <div>
                        <h3 className="font-bold">{m.title}</h3>
                        <div className="text-xs text-muted">{role}</div>
                      </div>
                    </div>
                    {m.ready ? <Badge tone="green">Faol</Badge> : <Badge tone="amber">Tez kunda</Badge>}
                  </div>
                  <p className="mt-3 flex-1 text-sm text-muted">{m.tagline}</p>
                  <div className="mt-5">
                    <Link
                      href={m.href}
                      className="inline-flex items-center gap-1.5 rounded-[10px] bg-accent px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent-strong"
                    >
                      {m.ready ? `${m.title}ga o'tish` : "Rejani ko'rish"} →
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </main>
      <Footer />
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
