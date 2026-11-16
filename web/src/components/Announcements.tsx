"use client";

// E'lonlar: lenta (bosh sahifa va modullarda) va yozish formasi.
// Yozish huquqi: bosh admin — hamma modul, Tashkiliy guruh — Zakovat, tashkilotchi — Kitobxonlik.

import { useState } from "react";
import { api } from "@/lib/api";
import { useAction, useApi } from "@/lib/hooks";
import { MODULE_LABEL, type Announcement, type AnnouncementList } from "@/lib/types";
import { Badge, Button, Card, CardHeader, Field, formatDate, Notice } from "./ui";

export function AnnouncementForm({
  modules,
  initial,
  onDone,
  onCancel,
}: {
  modules: Announcement["module"][];
  initial?: Announcement;
  onDone: () => void;
  onCancel: () => void;
}) {
  const act = useAction();
  const [v, setV] = useState({
    title: initial?.title ?? "",
    body: initial?.body ?? "",
    module: initial?.module ?? modules[0] ?? "core",
    pinned: initial?.pinned ?? false,
    expires_at: initial?.expires_at ? initial.expires_at.slice(0, 16) : "",
  });
  return (
    <form
      className="space-y-3 rounded-xl border border-line bg-bg-elev/60 p-4"
      onSubmit={async (e) => {
        e.preventDefault();
        const body = { ...v, expires_at: v.expires_at ? new Date(v.expires_at).toISOString() : null };
        const ok = await act.run(() =>
          api(initial ? `announcements/${initial.id}` : "announcements", { method: initial ? "PATCH" : "POST", body }),
        );
        if (ok) onDone();
      }}
    >
      <Notice error={act.error} onClose={act.clear} />
      <input className="field text-base font-medium" required placeholder="Sarlavha" value={v.title} onChange={(e) => setV({ ...v, title: e.target.value })} />
      <textarea className="field min-h-20" placeholder="Matn (ixtiyoriy)" value={v.body} onChange={(e) => setV({ ...v, body: e.target.value })} />
      <div className="flex flex-wrap items-end gap-3">
        {modules.length > 1 && (
          <Field label="Modul">
            <select className="field w-auto" value={v.module} onChange={(e) => setV({ ...v, module: e.target.value as Announcement["module"] })}>
              {modules.map((m) => (
                <option key={m} value={m}>
                  {MODULE_LABEL[m]}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Ko'rinish muddati" hint="Bo'sh — o'chirilguncha">
          <input className="field w-auto" type="datetime-local" value={v.expires_at} onChange={(e) => setV({ ...v, expires_at: e.target.value })} />
        </Field>
        <label className="flex items-center gap-2 pb-2 text-sm">
          <input type="checkbox" checked={v.pinned} onChange={(e) => setV({ ...v, pinned: e.target.checked })} className="accent-[var(--accent)]" />
          📌 Yuqorida mahkamlash
        </label>
      </div>
      <div className="flex gap-2">
        <Button type="submit" disabled={act.busy}>
          {initial ? "Saqlash" : "E'lon qilish"}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Bekor qilish
        </Button>
      </div>
    </form>
  );
}

export function AnnouncementItem({ a, compact }: { a: Announcement; compact?: boolean }) {
  return (
    <div className={`rounded-xl border px-4 py-3 ${a.pinned ? "border-accent/50 bg-accent-soft" : "border-line bg-bg-elev/50"} ${a.is_active ? "" : "opacity-50"}`}>
      <div className="flex flex-wrap items-center gap-2">
        {a.pinned && <span title="Mahkamlangan">📌</span>}
        <span className="font-medium">{a.title}</span>
        {!compact && <Badge>{MODULE_LABEL[a.module]}</Badge>}
        {!a.is_active && <Badge tone="gray">yashirin</Badge>}
      </div>
      {a.body && <p className="mt-1 whitespace-pre-line text-sm text-muted">{a.body}</p>}
      <div className="mt-1.5 text-xs text-muted">
        {a.author} · {formatDate(a.created_at)}
        {a.expires_at && ` · ${formatDate(a.expires_at)} gacha`}
      </div>
    </div>
  );
}

/** Lenta: bosh sahifa (module yo'q) yoki modul sahifasi uchun. */
export default function AnnouncementsFeed({ module, title = "E'lonlar" }: { module?: Announcement["module"]; title?: string }) {
  const feed = useApi<AnnouncementList>(module ? `announcements?module=${module}` : "announcements");
  const [writing, setWriting] = useState(false);
  const items = feed.data?.items ?? [];
  const canPost = (feed.data?.can_post ?? []).filter((m) => !module || m === module || m === "core");
  if (!feed.data || (items.length === 0 && canPost.length === 0)) return null;

  return (
    <Card>
      <CardHeader
        title={`📢 ${title}`}
        actions={
          canPost.length > 0 && !writing && (
            <Button variant="soft" onClick={() => setWriting(true)}>
              + E&apos;lon
            </Button>
          )
        }
      />
      <div className="space-y-2.5 p-4">
        {writing && (
          <AnnouncementForm
            modules={module ? canPost.filter((m) => m === module).concat(canPost.filter((m) => m !== module)) : canPost}
            onDone={() => {
              setWriting(false);
              feed.reload();
            }}
            onCancel={() => setWriting(false)}
          />
        )}
        {items.slice(0, 5).map((a) => (
          <AnnouncementItem key={a.id} a={a} compact={!!module} />
        ))}
        {items.length === 0 && !writing && <p className="text-sm text-muted">Hozircha e&apos;lon yo&apos;q</p>}
      </div>
    </Card>
  );
}
