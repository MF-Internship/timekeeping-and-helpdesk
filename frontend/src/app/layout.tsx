import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AuthProvider } from "@/features/identity/model/AuthProvider";
import { ApplicationFrame } from "@/shared/ui/shell/ApplicationFrame";
import { ThemeProvider } from "@/shared/ui/theme";

import "./globals.css";

export const metadata: Metadata = {
  title: "MobiFone Helpdesk",
  description: "Chấm công và quản lý công việc Helpdesk.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <AuthProvider>
            <ApplicationFrame>{children}</ApplicationFrame>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
