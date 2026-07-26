"use strict";

const COUNTRY_CITIES = {
  "Colombia": ["Medellín", "Bogotá", "Cali"],
  "Estados Unidos": ["Miami", "Orlando"],
};

const CITY_LOCATIONS = {
  "Medellín": ["Brasaland El Poblado", "Brasaland Laureles", "Brasaland Envigado", "Brasaland Sabaneta"],
  "Bogotá": ["Brasaland Usaquén", "Brasaland Chapinero", "Brasaland Zona Rosa"],
  "Cali": ["Brasaland Granada", "Brasaland Ciudad Jardín", "Brasaland Unicentro"],
  "Miami": ["Brasaland Brickell", "Brasaland Coral Gables"],
  "Orlando": ["Brasaland Downtown", "Brasaland International Drive"],
};

const ERROR_MESSAGES = {
  fullName: "Ingresa tu nombre completo (nombre y apellido)",
  email: "Ingresa un email válido (ejemplo: nombre@correo.com)",
  phone: "El teléfono debe incluir código de país (ejemplo: +57 300 123 4567 o +1 305 123 4567)",
  country: "Selecciona tu país",
  city: "Selecciona tu ciudad",
  howHeard: "Cuéntanos cómo conociste Brasaland",
  birthdate: "Debes ser mayor de 18 años para registrarte en Brasa Points",
  acceptTerms: "Debes aceptar los términos del programa Brasa Points para continuar",
};

const validators = {
  fullName: (value) =>
    value.trim().split(/\s+/).filter(Boolean).length >= 2 ? null : ERROR_MESSAGES.fullName,

  email: (value) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim()) ? null : ERROR_MESSAGES.email,

  phone: (value) =>
    /^\+(57|1)\s?\d{3}\s?\d{3}\s?\d{4}$/.test(value.trim()) ? null : ERROR_MESSAGES.phone,

  country: (value) => (value ? null : ERROR_MESSAGES.country),

  city: (value) => (value ? null : ERROR_MESSAGES.city),

  howHeard: (value) => (value ? null : ERROR_MESSAGES.howHeard),

  birthdate: (value) => {
    if (!value) return ERROR_MESSAGES.birthdate;
    return calculateAge(value) >= 18 ? null : ERROR_MESSAGES.birthdate;
  },

  acceptTerms: (checked) => (checked ? null : ERROR_MESSAGES.acceptTerms),
};

function calculateAge(birthdateValue) {
  const birthDate = new Date(birthdateValue);
  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDiff = today.getMonth() - birthDate.getMonth();
  const dayDiff = today.getDate() - birthDate.getDate();
  if (monthDiff < 0 || (monthDiff === 0 && dayDiff < 0)) {
    age -= 1;
  }
  return age;
}

function populateSelect(select, options, placeholder, { enabled } = { enabled: true }) {
  select.innerHTML = "";
  const placeholderOption = document.createElement("option");
  placeholderOption.value = "";
  placeholderOption.textContent = placeholder;
  select.appendChild(placeholderOption);

  options.forEach((optionValue) => {
    const option = document.createElement("option");
    option.value = optionValue;
    option.textContent = optionValue;
    select.appendChild(option);
  });

  select.disabled = !enabled || options.length === 0;
}

function showError(fieldId, message) {
  const errorEl = document.getElementById(`${fieldId}-error`);
  const inputEl = document.getElementById(fieldId);
  if (!errorEl || !inputEl) return;

  if (message) {
    errorEl.textContent = message;
    errorEl.classList.remove("hidden");
    inputEl.setAttribute("aria-invalid", "true");
  } else {
    clearError(fieldId);
  }
}

function clearError(fieldId) {
  const errorEl = document.getElementById(`${fieldId}-error`);
  const inputEl = document.getElementById(fieldId);
  if (errorEl) {
    errorEl.textContent = "";
    errorEl.classList.add("hidden");
  }
  if (inputEl) {
    inputEl.removeAttribute("aria-invalid");
  }
}

function handleCountryChange() {
  const cities = COUNTRY_CITIES[countrySelect.value] || [];
  populateSelect(citySelect, cities, "Selecciona tu ciudad", { enabled: cities.length > 0 });
  populateSelect(locationSelect, [], "Selecciona primero tu ciudad", { enabled: false });
  clearError("city");
  clearError("favoriteLocation");
}

function handleCityChange() {
  const locations = CITY_LOCATIONS[citySelect.value] || [];
  populateSelect(
    locationSelect,
    locations,
    "Selecciona tu ubicación favorita (opcional)",
    { enabled: locations.length > 0 }
  );
}

const REALTIME_FIELDS = ["fullName", "email", "phone", "country", "city", "howHeard", "birthdate", "acceptTerms"];

function getFieldValue(fieldId) {
  const el = document.getElementById(fieldId);
  return fieldId === "acceptTerms" ? el.checked : el.value;
}

function validateField(fieldId) {
  const error = validators[fieldId](getFieldValue(fieldId));
  showError(fieldId, error);
  return !error;
}

function attachRealtimeValidation() {
  REALTIME_FIELDS.forEach((fieldId) => {
    const el = document.getElementById(fieldId);
    if (!el) return;

    const isSelectOrCheckbox = el.tagName === "SELECT" || el.type === "checkbox";
    el.addEventListener(isSelectOrCheckbox ? "change" : "blur", () => validateField(fieldId));

    if (!isSelectOrCheckbox) {
      el.addEventListener("input", () => {
        if (el.getAttribute("aria-invalid") === "true") validateField(fieldId);
      });
    }
  });
}

function handleSubmit(event) {
  event.preventDefault();

  let isValid = true;
  let firstInvalidField = null;

  REALTIME_FIELDS.forEach((fieldId) => {
    const fieldIsValid = validateField(fieldId);
    if (!fieldIsValid) {
      isValid = false;
      if (!firstInvalidField) firstInvalidField = fieldId;
    }
  });

  if (!isValid) {
    document.getElementById(firstInvalidField).focus();
    return;
  }

  document.getElementById("form-wrapper").classList.add("hidden");
  document.getElementById("success-message").classList.remove("hidden");
}

function handleReset() {
  Object.keys(validators).forEach(clearError);
  populateSelect(citySelect, [], "Selecciona primero tu país", { enabled: false });
  populateSelect(locationSelect, [], "Selecciona primero tu ciudad", { enabled: false });
}

const form = document.getElementById("brasa-points-form");
const countrySelect = document.getElementById("country");
const citySelect = document.getElementById("city");
const locationSelect = document.getElementById("favoriteLocation");

if (form) {
  countrySelect.addEventListener("change", handleCountryChange);
  citySelect.addEventListener("change", handleCityChange);
  form.addEventListener("submit", handleSubmit);
  form.addEventListener("reset", handleReset);
  attachRealtimeValidation();
}
