"use client";

// Hali qurilmagan modullar: rejalashtirilgan bo'limlar ko'rinishi (TZ asosida).

import { moduleByKey } from "@/lib/modules";
import { Badge, Card, PageTitle } from "./ui";

const PLANS: Record<"munozara" | "sport", { title: string; items: string[] }[]> = {
  munozara: [
    { title: "Mavzular", items: ["Rezolyutsiya e'lon qilish", "Mavzu bo'yicha materiallar"] },
    { title: "Jamoalar", items: ["Tarafdor / qarshi jamoalarga bo'lish", "Spikerlar tartibi"] },
    { title: "Hakamlik", items: ["Baholash varaqasi: mantiq, dalil, nutq", "Hakamlar o'rtacha bahosi"] },
    { title: "Turnir", items: ["Turnir to'ri", "Natijalar va eng yaxshi spiker"] },
  ],
  sport: [
    { title: "Sport turlari", items: ["Futbol, voleybol, shaxmat va boshqalar", "Jamoaviy va individual"] },
    { title: "Jadval", items: ["O'yinlar taqvimi", "Guruh bosqichi yoki turnir to'ri"] },
    { title: "Natijalar", items: ["Hisob kiritish", "Statistika: gollar, ochkolar"] },
    { title: "Reyting", items: ["Jamoalar jadvali", "Eng yaxshi o'yinchilar"] },
  ],
};

export default function ComingSoon({ moduleKey }: { moduleKey: "munozara" | "sport" }) {
  const mod = moduleByKey(moduleKey);
  return (
    <>
      <PageTitle
        title={
          <span className="flex items-center gap-3">
            {mod.title} <Badge tone="amber">Tez kunda</Badge>
          </span>
        }
        subtitle={mod.tagline}
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {PLANS[moduleKey].map((s) => (
          <Card key={s.title} className="p-5 opacity-90">
            <h3 className="font-semibold">{s.title}</h3>
            <ul className="mt-3 space-y-1.5 text-sm text-muted">
              {s.items.map((i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-accent">•</span>
                  {i}
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
      <Card className="p-5 text-sm text-muted">
        Bu modul uchun texnik topshiriq tayyorlanadi. Qanday bo&apos;limlar kerakligini aytsangiz, reja shu yerda yangilanadi.
      </Card>
    </>
  );
}
