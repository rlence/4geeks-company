import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Backoffice — Brasaland",
  description: "Panel interno de Brasaland Digital.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <header className="border-b border-gray-200 bg-white">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
            <span className="text-lg font-bold text-orange-700">Brasaland — Backoffice</span>
            <span className="text-sm text-gray-500">Panel interno</span>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
