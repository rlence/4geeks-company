export const COUNTRY_CITIES: Record<string, string[]> = {
  Colombia: ["Medellín", "Bogotá", "Cali"],
  "Estados Unidos": ["Miami", "Orlando"],
};

export const CITY_LOCATIONS: Record<string, string[]> = {
  Medellín: ["Brasaland El Poblado", "Brasaland Laureles", "Brasaland Envigado", "Brasaland Sabaneta"],
  Bogotá: ["Brasaland Usaquén", "Brasaland Chapinero", "Brasaland Zona Rosa"],
  Cali: ["Brasaland Granada", "Brasaland Ciudad Jardín", "Brasaland Unicentro"],
  Miami: ["Brasaland Brickell", "Brasaland Coral Gables"],
  Orlando: ["Brasaland Downtown", "Brasaland International Drive"],
};

export const DIETARY_PREFERENCES = ["Sin restricciones", "Vegetariano", "Sin gluten", "Otro"];

export const HOW_HEARD_OPTIONS = [
  "Redes sociales",
  "Recomendación",
  "Pasando por el local",
  "Búsqueda en internet",
  "Otro",
];

export const ERROR_MESSAGES = {
  fullName: "Ingresa tu nombre completo (nombre y apellido)",
  email: "Ingresa un email válido (ejemplo: nombre@correo.com)",
  phone: "El teléfono debe incluir código de país (ejemplo: +57 300 123 4567 o +1 305 123 4567)",
  country: "Selecciona tu país",
  city: "Selecciona tu ciudad",
  howHeard: "Cuéntanos cómo conociste Brasaland",
  birthdate: "Debes ser mayor de 18 años para registrarte en Brasa Points",
  acceptTerms: "Debes aceptar los términos del programa Brasa Points para continuar",
} as const;

export const calculateAge = (birthdateValue: string): number => {
  const birthDate = new Date(birthdateValue);
  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDiff = today.getMonth() - birthDate.getMonth();
  const dayDiff = today.getDate() - birthDate.getDate();
  if (monthDiff < 0 || (monthDiff === 0 && dayDiff < 0)) {
    age -= 1;
  }
  return age;
};

export type RealtimeField = keyof typeof ERROR_MESSAGES;

export const REALTIME_FIELDS: RealtimeField[] = [
  "fullName",
  "email",
  "phone",
  "country",
  "city",
  "howHeard",
  "birthdate",
  "acceptTerms",
];

export const validators: Record<RealtimeField, (value: string | boolean) => string | null> = {
  fullName: (value) =>
    (value as string).trim().split(/\s+/).filter(Boolean).length >= 2 ? null : ERROR_MESSAGES.fullName,
  email: (value) => (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((value as string).trim()) ? null : ERROR_MESSAGES.email),
  phone: (value) =>
    /^\+(57|1)\s?\d{3}\s?\d{3}\s?\d{4}$/.test((value as string).trim()) ? null : ERROR_MESSAGES.phone,
  country: (value) => ((value as string) ? null : ERROR_MESSAGES.country),
  city: (value) => ((value as string) ? null : ERROR_MESSAGES.city),
  howHeard: (value) => ((value as string) ? null : ERROR_MESSAGES.howHeard),
  birthdate: (value) => {
    if (!value) return ERROR_MESSAGES.birthdate;
    return calculateAge(value as string) >= 18 ? null : ERROR_MESSAGES.birthdate;
  },
  acceptTerms: (value) => ((value as boolean) ? null : ERROR_MESSAGES.acceptTerms),
};
