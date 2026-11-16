import { tokens } from "./api";

/** Himoyalangan faylni (Excel va h.k.) token bilan yuklab, kompyuterga saqlaydi. */
export async function downloadFile(path: string, fallbackName = "fayl.xlsx") {
  const res = await fetch(`/api/${path}`, { headers: { Authorization: `Bearer ${tokens.access ?? ""}` } });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail ?? "Faylni yuklab bo'lmadi");
  }
  const cd = res.headers.get("Content-Disposition") ?? "";
  const m = cd.match(/filename\*=UTF-8''([^;]+)/);
  const name = m ? decodeURIComponent(m[1]) : fallbackName;
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}
