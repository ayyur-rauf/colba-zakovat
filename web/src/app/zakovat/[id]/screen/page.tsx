import { Suspense } from "react";
import BigScreen from "@/components/zakovat/BigScreen";

export default function ScreenPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-slate-950" />}>
      <BigScreen />
    </Suspense>
  );
}
