import { Suspense } from "react";
import LoginForm from "@/components/LoginForm";
import { Footer, ThemeToggle } from "@/components/ui";

// Sahifa tizimga kirgandan keyin brauzerda chiziladi — oldindan chizish tekshiruvi kerak emas.
export const instant = false;

export default function LoginPage() {
  return (
    <>
      <div className="flex justify-end p-4">
        <ThemeToggle />
      </div>
      <main className="flex flex-1 items-start justify-center px-6 pt-10">
        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>
      </main>
      <Footer />
    </>
  );
}
