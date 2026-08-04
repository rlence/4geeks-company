import type {
  Candidate,
  CandidateFilters,
  CandidateInput,
  CandidateNote,
  CandidatePatch,
  CandidatesPage,
  NotesResponse,
} from "@/types/tracker";

const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

export class ApiError extends Error {}

const request = async <T>(path: string, init?: RequestInit, signal?: AbortSignal): Promise<T> => {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    signal,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    throw new ApiError(`Error ${response.status} al comunicarse con la API`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
};

export const getCandidates = (filters: CandidateFilters, signal?: AbortSignal): Promise<CandidatesPage> => {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.search) params.set("search", filters.search);
  params.set("page", String(filters.page ?? 1));
  params.set("limit", String(filters.limit ?? 20));
  return request<CandidatesPage>(`/records?${params.toString()}`, undefined, signal);
};

export const getCandidate = (id: string, signal?: AbortSignal): Promise<Candidate> =>
  request<Candidate>(`/records/${id}`, undefined, signal);

export const createCandidate = (input: CandidateInput): Promise<Candidate> =>
  request<Candidate>("/records", { method: "POST", body: JSON.stringify(input) });

export const replaceCandidate = (id: string, input: CandidateInput): Promise<Candidate> =>
  request<Candidate>(`/records/${id}`, { method: "PUT", body: JSON.stringify(input) });

export const patchCandidate = (id: string, patch: CandidatePatch): Promise<Candidate> =>
  request<Candidate>(`/records/${id}`, { method: "PATCH", body: JSON.stringify(patch) });

export const getNotes = (id: string, signal?: AbortSignal): Promise<NotesResponse> =>
  request<NotesResponse>(`/records/${id}/notes`, undefined, signal);

export const addNote = (id: string, content: string): Promise<CandidateNote> =>
  request<CandidateNote>(`/records/${id}/notes`, { method: "POST", body: JSON.stringify({ content }) });

export const deleteNote = (id: string, noteId: string): Promise<void> =>
  request<void>(`/records/${id}/notes/${noteId}`, { method: "DELETE" });
