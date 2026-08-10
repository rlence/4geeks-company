"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/session";

// Redirige a /login si no hay sesión. Mientras decide (o redirige), `ready`
// es false y la página no debe montar contenido protegido.
export const useRequireAuth = () => {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage solo es legible client-side, tras montar
    setReady(true);
  }, [router]);

  return ready;
};
