"use client";

import { useState } from "react";
import { useKnowledgeQuery } from "@/hooks/useKnowledgeQuery";

const EJEMPLOS = [
  "¿Cuántos puntos necesito para el nivel Oro?",
  "¿La Costilla BBQ tiene alérgenos?",
  "¿Cuándo debo escalar un caso de merma a Felipe Guerrero?",
  "¿Hasta qué hora puedo enviar el pedido semanal a proveedores?",
];

export default function KnowledgePage() {
  const [question, setQuestion] = useState("");
  const { status, answer, error, askedQuestion, ask } = useKnowledgeQuery();

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || status === "loading") return;
    ask(trimmed);
  };

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-bold text-gray-900">Base de Conocimiento</h1>
      <p className="mt-2 text-sm text-gray-600">
        Pregunta en lenguaje natural sobre el programa de lealtad, el protocolo de desperdicio,
        los alérgenos del menú o el procedimiento de pedido a proveedores.
      </p>

      <form onSubmit={submit} className="mt-6">
        <label htmlFor="question" className="sr-only">
          Tu pregunta
        </label>
        <textarea
          id="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
          maxLength={1000}
          placeholder="¿Cuántos puntos necesito para el nivel Oro?"
          className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-orange-600 focus:outline-none"
        />
        <div className="mt-3 flex items-center gap-3">
          <button
            type="submit"
            disabled={!question.trim() || status === "loading"}
            className="rounded bg-orange-700 px-4 py-2 text-sm font-medium text-white hover:bg-orange-800 disabled:cursor-not-allowed disabled:bg-gray-300"
          >
            {status === "loading" ? "Consultando…" : "Preguntar"}
          </button>
          {status === "loading" && (
            <span className="text-sm text-gray-600">
              Consultando la base de conocimiento…
            </span>
          )}
        </div>
      </form>

      {status === "idle" && (
        <section className="mt-8">
          <h2 className="text-sm font-medium text-gray-700">Preguntas de ejemplo</h2>
          <ul className="mt-2 space-y-1">
            {EJEMPLOS.map((ejemplo) => (
              <li key={ejemplo}>
                <button
                  type="button"
                  onClick={() => setQuestion(ejemplo)}
                  className="text-left text-sm text-orange-700 hover:underline"
                >
                  {ejemplo}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Un fallo de API nunca debe parecer una respuesta vacía — se
          distingue visualmente del caso "sí respondió". */}
      {status === "error" && (
        <section
          role="alert"
          className="mt-8 rounded border border-red-200 bg-red-50 px-4 py-3"
        >
          <h2 className="text-sm font-medium text-red-800">No se pudo completar la consulta</h2>
          <p className="mt-1 text-sm text-red-700">{error}</p>
        </section>
      )}

      {status === "success" && answer && (
        <section className="mt-8 rounded border border-gray-200 bg-white px-4 py-4">
          {askedQuestion && (
            <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
              {askedQuestion}
            </p>
          )}
          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-gray-900">
            {answer}
          </p>
        </section>
      )}
    </main>
  );
}
