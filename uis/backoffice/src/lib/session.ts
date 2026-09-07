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

// Decodifica el payload del JWT (base64url, sin librería nueva). Este repo
// identifica usuarios con un id numérico, no un UUID real — ver
// context/plans/hito5.md, decisión 5, para el porqué de este atajo.
const decodeTokenPayload = (token: string): Record<string, unknown> | null => {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(window.atob(normalized));
  } catch {
    return null;
  }
};

export const getCurrentUserId = (): string | null => {
  const token = getToken();
  if (!token) return null;
  const decoded = decodeTokenPayload(token);
  return typeof decoded?.sub === "string" ? decoded.sub : null;
};

// token_age_seconds para el evento de telemetría session_expired — requiere
// el claim "iat" (segundos desde epoch, formato estándar de PyJWT) agregado
// en services/api/auth.py::create_access_token.
export const getTokenAgeSeconds = (): number | null => {
  const token = getToken();
  if (!token) return null;
  const decoded = decodeTokenPayload(token);
  if (typeof decoded?.iat !== "number") return null;
  return Math.max(0, Math.floor(Date.now() / 1000) - decoded.iat);
};

// SHA-256 en hex vía Web Crypto — usado para email_hash en eventos de
// telemetría de autenticación (login_attempt_failed, password_reset_requested):
// nunca se envía el email en texto plano.
export const sha256Hex = async (value: string): Promise<string> => {
  const bytes = new TextEncoder().encode(value.trim().toLowerCase());
  const digest = await window.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
};
