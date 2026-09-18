"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { askKnowledgeBase, getApiErrorMessage } from "@/lib/knowledgeApi";

type QueryStatus = "idle" | "loading" | "success" | "error";

export const useKnowledgeQuery = () => {
  const [status, setStatus] = useState<QueryStatus>("idle");
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [askedQuestion, setAskedQuestion] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  // A diferencia de useWeeklyPerformance, esto no se dispara en un efecto al
  // montar: la consulta la inicia el gerente al enviar su pregunta.
  const ask = useCallback(async (question: string) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setStatus("loading");
    setError(null);
    setAnswer(null);
    setAskedQuestion(question);

    try {
      const data = await askKnowledgeBase(question, controller.signal);
      if (controller.signal.aborted) return;
      setAnswer(data.answer);
      setStatus("success");
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(getApiErrorMessage(err));
      setStatus("error");
    }
  }, []);

  useEffect(() => () => controllerRef.current?.abort(), []);

  return { status, answer, error, askedQuestion, ask };
};
