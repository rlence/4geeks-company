import { ApiError, getApiErrorMessage } from "@/lib/authApi";

describe("getApiErrorMessage (authApi)", () => {
  it("returns the string detail of an ApiError", () => {
    const error = new ApiError("Error 401", 401, "Email o contraseña incorrectos");

    expect(getApiErrorMessage(error)).toBe("Email o contraseña incorrectos");
  });

  it("joins validation details from a FastAPI 422 into one message", () => {
    const error = new ApiError("Error 422", 422, [
      { loc: ["body", "new_password"], msg: "String should have at least 8 characters", type: "string_too_short" },
      { loc: ["body", "email"], msg: "Field required", type: "missing" },
    ]);

    expect(getApiErrorMessage(error)).toBe(
      "String should have at least 8 characters — Field required",
    );
  });

  it("falls back to error.message for a generic Error that is not an ApiError", () => {
    const error = new Error("Network request failed");

    expect(getApiErrorMessage(error)).toBe("Network request failed");
  });

  it("falls back to a generic message for a non-Error thrown value", () => {
    expect(getApiErrorMessage("just a string, not an Error")).toBe(
      "Ha ocurrido un error inesperado",
    );
  });
});
