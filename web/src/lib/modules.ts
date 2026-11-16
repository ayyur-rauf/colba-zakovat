// Modullar ro'yxati — sarlavha menyusi, modullar markazi va har modulning bo'limlari shu yerdan.
// Yangi modul yoki bo'lim qo'shish uchun shu faylni tahrirlang.

export type ModuleSection = {
  href: string;
  title: string;
  staffOnly?: boolean;
  /** Qaysi manzillarda bu bo'lim faol ko'rinadi (bo'lmasa — href bilan boshlanganlar) */
  match?: RegExp;
};

export type ModuleDef = {
  key: "zakovat" | "kitobxonlik" | "munozara" | "sport" | "boshqaruv";
  title: string;
  icon: string;
  href: string;
  tagline: string;
  ready: boolean;
  /** Faqat bosh admin ko'radi (menyuda va markazda) */
  adminOnly?: boolean;
  sections: ModuleSection[];
};

export const MODULES: ModuleDef[] = [
  {
    key: "zakovat",
    title: "Zakovat",
    icon: "🧠",
    href: "/zakovat",
    tagline: "Colba ligasi: har oyning 3-shanbasi, jonli o'yin, jamoalar reytingi",
    ready: true,
    sections: [
      { href: "/zakovat", title: "Umumiy" },
      { href: "/zakovat/games", title: "O'yinlar", match: /^\/zakovat\/(games|\d+)/ },
      { href: "/zakovat/teams", title: "Jamoalar" },
      { href: "/zakovat/questions", title: "Savollar banki", staffOnly: true },
      { href: "/zakovat/standings", title: "Mavsum reytingi" },
    ],
  },
  {
    key: "kitobxonlik",
    title: "Kitobxonlik",
    icon: "📚",
    href: "/kitobxonlik",
    tagline: "Ovoz bilan tanlangan kitob, 10 kun o'qish, izoh va baholash",
    ready: true,
    sections: [
      { href: "/kitobxonlik", title: "Turlar" },
      { href: "/kitobxonlik/books", title: "Kitoblar", staffOnly: true },
      { href: "/kitobxonlik/grading", title: "Baholash", staffOnly: true },
      { href: "/kitobxonlik/leaderboard", title: "Reyting" },
    ],
  },
  {
    key: "munozara",
    title: "Munozara",
    icon: "🎤",
    href: "/munozara",
    tagline: "Rezolyutsiya, tarafdor va qarshi jamoalar, hakamlar baholashi",
    ready: false,
    sections: [{ href: "/munozara", title: "Reja" }],
  },
  {
    key: "sport",
    title: "Sport",
    icon: "⚽",
    href: "/sport",
    tagline: "Turnirlar, o'yin jadvali, natijalar va statistika",
    ready: false,
    sections: [{ href: "/sport", title: "Reja" }],
  },
];

export const ADMIN_MODULE: ModuleDef = {
  key: "boshqaruv",
  title: "Boshqaruv",
  icon: "⚙️",
  href: "/boshqaruv",
  tagline: "Xodimlar, akkauntlar, rollar, mavsumlar, e'lonlar va harakatlar jurnali",
  ready: true,
  adminOnly: true,
  sections: [
    { href: "/boshqaruv", title: "Xodimlar" },
    { href: "/boshqaruv/accounts", title: "Akkauntlar" },
    { href: "/boshqaruv/roles", title: "Rollar" },
    { href: "/boshqaruv/seasons", title: "Mavsumlar" },
    { href: "/boshqaruv/announcements", title: "E'lonlar" },
    { href: "/boshqaruv/audit", title: "Jurnal" },
  ],
};

export const moduleByKey = (key: ModuleDef["key"]) => [...MODULES, ADMIN_MODULE].find((m) => m.key === key)!;
