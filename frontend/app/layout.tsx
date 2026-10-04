import type { Metadata } from "next";
import "./globals.css";
import { DisclaimerBanner } from "@/components/clinical/DisclaimerBanner";
import { Header } from "@/components/clinical/Header";
import { Sidebar } from "@/components/clinical/Sidebar";

export const metadata: Metadata = {
  title: "NIDAN AI — Intelligent Clinical Insights",
  description:
    "Production-oriented clinical decision-support platform assisting medical professionals with document extraction, laboratory normalization, and structured summaries.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col antialiased selection:bg-sky-500 selection:text-white">
        <DisclaimerBanner />
        <Header />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
