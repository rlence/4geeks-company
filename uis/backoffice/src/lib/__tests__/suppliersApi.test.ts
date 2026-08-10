import { ApiError, getApiErrorMessage } from "@/lib/suppliersApi";

// getApiErrorMessage y ApiError están duplicados byte a byte entre authApi.ts
// y suppliersApi.ts (hallazgo de IA, ver TESTING.md — candidato a extraer a
// un módulo compartido, no se toca en este ticket). Este archivo repite el
// mínimo necesario para confirmar que la copia de suppliersApi.ts se
// comporta igual, no para duplicar la cobertura de casos de authApi.test.ts.
describe("getApiErrorMessage (suppliersApi)", () => {
  it("returns the string detail of an ApiError", () => {
    const error = new ApiError("Error 404", 404, "Proveedor 999 no encontrado");

    expect(getApiErrorMessage(error)).toBe("Proveedor 999 no encontrado");
  });

  it("falls back to a generic message for a non-Error thrown value", () => {
    expect(getApiErrorMessage(undefined)).toBe("Ha ocurrido un error inesperado");
  });
});
