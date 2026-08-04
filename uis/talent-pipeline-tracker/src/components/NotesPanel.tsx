"use client";

import { useEffect, useState } from "react";
import { addNote, deleteNote, getNotes } from "@/lib/api";
import type { CandidateNote } from "@/types/tracker";

type FetchStatus = "loading" | "success" | "error";

export const NotesPanel = ({ candidateId }: { candidateId: string }) => {
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [notes, setNotes] = useState<CandidateNote[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newNote, setNewNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadNotes = async () => {
    setStatus("loading");
    try {
      const result = await getNotes(candidateId);
      setNotes(result.data);
      setStatus("success");
    } catch {
      setError("No se pudieron cargar las notas.");
      setStatus("error");
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loadNotes sets status synchronously before the async fetch resolves
    loadNotes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId]);

  const handleAdd = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!newNote.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await addNote(candidateId, newNote.trim());
      setNewNote("");
      await loadNotes();
    } catch {
      setError("No se pudo guardar la nota.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (noteId: string) => {
    setDeletingId(noteId);
    try {
      await deleteNote(candidateId, noteId);
      setNotes((prev) => prev.filter((note) => note.id !== noteId));
    } catch {
      setError("No se pudo eliminar la nota.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section>
      <h2 className="mb-2 text-lg font-semibold">Notas internas</h2>

      {status === "loading" && <p>Cargando notas…</p>}
      {status === "error" && <p className="text-red-600">{error}</p>}
      {status === "success" && notes.length === 0 && <p className="text-gray-500">Sin notas todavía.</p>}

      <ul className="mb-4 space-y-2">
        {notes.map((note) => (
          <li key={note.id} className="flex justify-between gap-3 rounded border p-3">
            <div>
              <p>{note.content}</p>
              <p className="text-xs text-gray-500">{new Date(note.created_at).toLocaleString("es-CO")}</p>
            </div>
            <button
              onClick={() => handleDelete(note.id)}
              disabled={deletingId === note.id}
              className="shrink-0 text-sm text-red-600"
            >
              {deletingId === note.id ? "Eliminando…" : "Eliminar"}
            </button>
          </li>
        ))}
      </ul>

      <form onSubmit={handleAdd} className="flex gap-2">
        <input
          value={newNote}
          onChange={(event) => setNewNote(event.target.value)}
          placeholder="Escribe una nota interna…"
          className="flex-1 rounded border px-3 py-2"
        />
        <button type="submit" disabled={submitting} className="rounded bg-orange-700 px-4 py-2 text-white">
          {submitting ? "Guardando…" : "Añadir nota"}
        </button>
      </form>
    </section>
  );
};
