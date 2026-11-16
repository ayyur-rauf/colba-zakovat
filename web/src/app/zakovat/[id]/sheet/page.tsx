import { Suspense } from "react";
import ScoreSheet from "@/components/zakovat/ScoreSheet";

export default function SheetPage() {
  return (
    <Suspense fallback={<div className="p-10 text-center text-gray-500">Yuklanmoqda…</div>}>
      <ScoreSheet />
    </Suspense>
  );
}
