import { Suspense } from "react";
import ScoreSheet from "@/components/zakovat/ScoreSheet";

// Sahifa tizimga kirgandan keyin brauzerda chiziladi — oldindan chizish tekshiruvi kerak emas.
export const instant = false;

export default function SheetPage() {
  return (
    <Suspense fallback={<div className="p-10 text-center text-muted">Yuklanmoqda…</div>}>
      <ScoreSheet />
    </Suspense>
  );
}
