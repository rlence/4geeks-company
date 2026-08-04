import { CandidateForm } from "@/components/CandidateForm";

export default function NewCandidatePage() {
  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="mb-4 text-2xl font-bold">Registrar nueva candidatura</h1>
      <CandidateForm mode="create" />
    </main>
  );
}
