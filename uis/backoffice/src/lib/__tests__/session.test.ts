import { clearToken, getToken, setToken } from "@/lib/session";

describe("session token storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("returns the token that was stored", () => {
    setToken("my-jwt-token");

    expect(getToken()).toBe("my-jwt-token");
  });

  it("returns null after the token is cleared", () => {
    setToken("my-jwt-token");

    clearToken();

    expect(getToken()).toBeNull();
  });

  it("clearing an already-empty session does not throw", () => {
    expect(() => clearToken()).not.toThrow();
    expect(getToken()).toBeNull();
  });
});

// Nota: la rama `typeof window === "undefined"` de getToken() (comportamiento
// en SSR) no es testeable en este entorno jsdom, donde `window` siempre
// existe. Ver TESTING.md.
