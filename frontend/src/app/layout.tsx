import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/features/identity/model/AuthProvider";

import "./globals.css";

export const metadata: Metadata = {
  title: "Nền tảng API",
  description: "Nền tảng kỹ thuật dùng chung cho các tính năng sau.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="vi">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
