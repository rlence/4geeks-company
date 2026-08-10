const TOKEN_KEY = "brasaland_access_token";

export const getToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
};

export const setToken = (token: string): void => {
  window.localStorage.setItem(TOKEN_KEY, token);
};

export const clearToken = (): void => {
  window.localStorage.removeItem(TOKEN_KEY);
};

// Decodifica el claim "sub" del JWT (base64url del payload, sin librería nueva).
// Este repo identifica usuarios con un id numérico, no un UUID real — ver
// context/plans/hito5.md, decisión 5, para el porqué de este atajo.
export const getCurrentUserId = (): string | null => {
  const token = getToken();
  if (!token) return null;

  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(window.atob(normalized));
    return typeof decoded.sub === "string" ? decoded.sub : null;
  } catch {
    return null;
  }
};
