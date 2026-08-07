import type { Metadata } from "next";
import Link from "next/link";
import { BrasaPointsForm } from "@/components/BrasaPointsForm";

export const metadata: Metadata = {
  title: "Regístrate en Brasa Points — Brasaland",
  description:
    "Regístrate en Brasa Points, el programa de fidelización digital de Brasaland, y empieza a acumular puntos en cada visita.",
};

export default function BrasaPointsPage() {
  return (
    <>
      <header className="border-b border-gray-200">
        <nav aria-label="Navegación principal" className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
          <Link href="/" className="text-xl font-extrabold tracking-tight text-orange-700">
            Brasaland
          </Link>
          <Link href="/" className="text-sm font-medium text-gray-600 hover:text-orange-700">
            ← Volver al inicio
          </Link>
        </nav>
      </header>

      <main className="mx-auto max-w-xl px-4 py-12 sm:py-16">
        <h1 className="text-3xl font-extrabold sm:text-4xl">Únete a Brasa Points</h1>
        <p className="mt-4 text-gray-600">
          Brasa Points está diseñado para clientes mayores de 18 años que quieren acumular puntos con sus
          visitas. Este no es un formulario de reservas ni de pedidos en línea.
        </p>

        <BrasaPointsForm />
      </main>

      <footer className="border-t border-gray-200 py-8 text-center text-sm text-gray-500">
        © 2025 Brasaland. Todos los derechos reservados.
      </footer>
    </>
  );
}
