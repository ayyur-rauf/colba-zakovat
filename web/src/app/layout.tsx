import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { THEME_BOOT_SCRIPT } from "@/lib/theme";

export const metadata: Metadata = {
  title: "Colba platformasi",
  description: "Colba maktabi xodimlari uchun intellektual tadbirlar platformasi",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // data-theme brauzerda skript bilan qo'yiladi — shuning uchun server/brauzer farqi ogohlantirilmaydi
    <html lang="uz" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
