"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getCandidates } from "@/lib/api";
import type { Candidate } from "@/types/tracker";

type FetchStatus = "loading" | "success" | "error";

export const useCandidates = () => {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<FetchStatus>("loading");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const statusParam = searchParams.get("status") ?? undefined;
  const stageParam = searchParams.get("stage") ?? undefined;
  const searchParam = searchParams.get("search") ?? undefined;
  const page = Number(searchParams.get("page") ?? "1");

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset to loading before re-fetching on filter/page change
    setStatus("loading");
    setError(null);

    getCandidates({ status: statusParam, stage: stageParam, search: searchParam, page, limit: 20 }, controller.signal)
      .then((result) => {
        setCandidates(result.data);
        setTotal(result.total);
        setStatus("success");
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Error al cargar candidaturas");
        setStatus("error");
      });

    return () => controller.abort();
  }, [statusParam, stageParam, searchParam, page]);

  return { status, candidates, total, error, page };
};
