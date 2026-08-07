"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import {
  CITY_LOCATIONS,
  COUNTRY_CITIES,
  DIETARY_PREFERENCES,
  HOW_HEARD_OPTIONS,
  REALTIME_FIELDS,
  type RealtimeField,
  validators,
} from "@/lib/formOptions";

interface FormState {
  fullName: string;
  email: string;
  phone: string;
  country: string;
  city: string;
  favoriteLocation: string;
  dietaryPreferences: string[];
  howHeard: string;
  birthdate: string;
  acceptTerms: boolean;
  wantsOffers: boolean;
}

const EMPTY_FORM: FormState = {
  fullName: "",
  email: "",
  phone: "",
  country: "",
  city: "",
  favoriteLocation: "",
  dietaryPreferences: [],
  howHeard: "",
  birthdate: "",
  acceptTerms: false,
  wantsOffers: false,
};

export const BrasaPointsForm = () => {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<Partial<Record<RealtimeField, string>>>({});
  const [submitted, setSubmitted] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const fieldRefs = useRef<Partial<Record<RealtimeField, HTMLElement | null>>>({});

  const validateField = (fieldId: RealtimeField, value: string | boolean): boolean => {
    const error = validators[fieldId](value);
    setErrors((prev) => ({ ...prev, [fieldId]: error ?? undefined }));
    return !error;
  };

  const handleCountryChange = (value: string) => {
    setForm((prev) => ({ ...prev, country: value, city: "", favoriteLocation: "" }));
    setErrors((prev) => ({ ...prev, city: undefined, favoriteLocation: undefined }));
    validateField("country", value);
  };

  const handleCityChange = (value: string) => {
    setForm((prev) => ({ ...prev, city: value, favoriteLocation: "" }));
    validateField("city", value);
  };

  const handleDietaryToggle = (value: string) => {
    setForm((prev) => ({
      ...prev,
      dietaryPreferences: prev.dietaryPreferences.includes(value)
        ? prev.dietaryPreferences.filter((v) => v !== value)
        : [...prev.dietaryPreferences, value],
    }));
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();

    const invalidFields: RealtimeField[] = [];

    for (const fieldId of REALTIME_FIELDS) {
      const value = fieldId === "acceptTerms" ? form.acceptTerms : form[fieldId];
      if (!validateField(fieldId, value)) invalidFields.push(fieldId);
    }

    if (invalidFields.length > 0) {
      fieldRefs.current[invalidFields[0]]?.focus();
      return;
    }

    setSubmitted(true);
  };

  const handleReset = () => {
    setForm(EMPTY_FORM);
    setErrors({});
  };

  const cities = COUNTRY_CITIES[form.country] ?? [];
  const locations = CITY_LOCATIONS[form.city] ?? [];

  if (submitted) {
    return (
      <div className="text-center" role="status" aria-live="polite">
        <h2 className="text-2xl font-bold text-orange-700">¡Bienvenido a Brasa Points!</h2>
        <p className="mt-4 text-gray-700">
          Tu registro ha sido exitoso. Recibirás un email de confirmación en los próximos minutos con los
          detalles de tu cuenta y cómo empezar a acumular puntos.
        </p>
        <p className="mt-4 text-gray-700">
          ¡Ya puedes disfrutar de tus beneficios en cualquiera de nuestras 14 ubicaciones!
        </p>
        <Link
          href="/"
          className="mt-8 inline-block rounded-full bg-orange-700 px-8 py-3 font-semibold text-white hover:bg-orange-800"
        >
          Volver al inicio
        </Link>
      </div>
    );
  }

  return (
    <form ref={formRef} noValidate onSubmit={handleSubmit} onReset={handleReset} className="mt-10 space-y-6">
      <div>
        <label htmlFor="fullName" className="block text-sm font-medium">
          Nombre completo *
        </label>
        <input
          type="text"
          id="fullName"
          required
          ref={(el) => {
            fieldRefs.current.fullName = el;
          }}
          value={form.fullName}
          onChange={(e) => setForm((prev) => ({ ...prev, fullName: e.target.value }))}
          onBlur={(e) => validateField("fullName", e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-orange-600 focus:outline-none focus:ring-1 focus:ring-orange-600"
          aria-describedby="fullName-error"
          aria-invalid={errors.fullName ? "true" : undefined}
        />
        {errors.fullName && (
          <p id="fullName-error" className="mt-1 text-sm text-red-600" aria-live="polite">
            {errors.fullName}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="email" className="block text-sm font-medium">
          Email *
        </label>
        <input
          type="email"
          id="email"
          required
          ref={(el) => {
            fieldRefs.current.email = el;
          }}
          value={form.email}
          onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
          onBlur={(e) => validateField("email", e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-orange-600 focus:outline-none focus:ring-1 focus:ring-orange-600"
          aria-describedby="email-error"
          aria-invalid={errors.email ? "true" : undefined}
        />
        {errors.email && (
          <p id="email-error" className="mt-1 text-sm text-red-600" aria-live="polite">
            {errors.email}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="phone" className="block text-sm font-medium">
          Teléfono *
        </label>
        <input
          type="tel"
          id="phone"
          required
          placeholder="+57 300 123 4567"
          ref={(el) => {
            fieldRefs.current.phone = el;
          }}
          value={form.phone}
          onChange={(e) => setForm((prev) => ({ ...prev, phone: e.target.value }))}
          onBlur={(e) => validateField("phone", e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-orange-600 focus:outline-none focus:ring-1 focus:ring-orange-600"
          aria-describedby="phone-error"
          aria-invalid={errors.phone ? "true" : undefined}
        />
        {errors.phone && (
          <p id="phone-error" className="mt-1 text-sm text-red-600" aria-live="polite">
            {errors.phone}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="country" className="block text-sm font-medium">
          País *
        </label>
        <select
          id="country"
          required
          ref={(el) => {
            fieldRefs.current.country = el;
          }}
          value={form.country}
          onChange={(e) => handleCountryChange(e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 focus:border-orange-600 focus:outline-none focus:ring-1 focus:ring-orange-600"
          aria-describedby="country-error"
          aria-invalid={errors.country ? "true" : undefined}
        >
          <option value="">Selecciona tu país</option>
          {Object.keys(COUNTRY_CITIES).map((country) => (
            <option key={country} value={country}>
              {country}
            </option>
          ))}
        </select>
        {errors.country && (
          <p id="country-error" className="mt-1 text-sm text-red-600" aria-live="polite">
            {errors.country}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="city" className="block text-sm font-medium">
          Ciudad *
        </label>
        <select
          id="city"
          required
          disabled={cities.length === 0}
          ref={(el) => {
            fieldRefs.current.city = el;
          }}
          value={form.city}
          onChange={(e) => handleCityChange(e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 focus:border-orange-600 focus:outline-none focus:ring-1 focus:ring-orange-600 disabled:bg-gray-100"
          aria-describedby="city-error"
          aria-invalid={errors.city ? "true" : undefined}
        >
          <option value="">{cities.length === 0 ? "Selecciona primero tu país" : "Selecciona tu ciudad"}</option>
          {cities.map((city) => (
            <option key={city} value={city}>
              {city}
            </option>
          ))}
        </select>
        {errors.city && (
          <p id="city-error" className="mt-1 text-sm text-red-600" aria-live="polite">
            {errors.city}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="favoriteLocation" className="block text-sm font-medium">
          Ubicación favorita de Brasaland
        </label>
        <select
          id="favoriteLocation"
          disabled={locations.length === 0}
          value={form.favoriteLocation}
          onChange={(e) => setForm((prev) => ({ ...prev, favoriteLocation: e.target.value }))}
          className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 focus:border-orange-600 focus:outline-none focus:ring-1 focus:ring-orange-600 disabled:bg-gray-100"
        >
          <option value="">
            {locations.length === 0 ? "Selecciona primero tu ciudad" : "Selecciona tu ubicación favorita (opcional)"}
          </option>
          {locations.map((location) => (
            <option key={location} value={location}>
              {location}
            </option>
          ))}
        </select>
      </div>

      <fieldset>
        <legend className="text-sm font-medium">Preferencias alimentarias</legend>
        <div className="mt-2 space-y-2">
          {DIETARY_PREFERENCES.map((preference) => (
            <label key={preference} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.dietaryPreferences.includes(preference)}
                onChange={() => handleDietaryToggle(preference)}
                className="rounded border-gray-300 text-orange-700 focus:ring-orange-600"
              />
              {preference}
            </label>
          ))}
        </div>
      </fieldset>

      <div>
        <label htmlFor="howHeard" className="block text-sm font-medium">
          ¿Cómo nos conociste? *
        </label>
        <select
          id="howHeard"
          required
          ref={(el) => {
            fieldRefs.current.howHeard = el;
          }}
          value={form.howHeard}
          onChange={(e) => {
            setForm((prev) => ({ ...prev, howHeard: e.target.value }));
            validateField("howHeard", e.target.value);
          }}
          className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 focus:border-orange-600 focus:outline-none focus:ring-1 focus:ring-orange-600"
          aria-describedby="howHeard-error"
          aria-invalid={errors.howHeard ? "true" : undefined}
        >
          <option value="">Selecciona una opción</option>
          {HOW_HEARD_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        {errors.howHeard && (
          <p id="howHeard-error" className="mt-1 text-sm text-red-600" aria-live="polite">
            {errors.howHeard}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="birthdate" className="block text-sm font-medium">
          Fecha de nacimiento *
        </label>
        <input
          type="date"
          id="birthdate"
          required
          ref={(el) => {
            fieldRefs.current.birthdate = el;
          }}
          value={form.birthdate}
          onChange={(e) => setForm((prev) => ({ ...prev, birthdate: e.target.value }))}
          onBlur={(e) => validateField("birthdate", e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 focus:border-orange-600 focus:outline-none focus:ring-1 focus:ring-orange-600"
          aria-describedby="birthdate-error"
          aria-invalid={errors.birthdate ? "true" : undefined}
        />
        {errors.birthdate && (
          <p id="birthdate-error" className="mt-1 text-sm text-red-600" aria-live="polite">
            {errors.birthdate}
          </p>
        )}
      </div>

      <div>
        <label className="flex items-start gap-2">
          <input
            type="checkbox"
            id="acceptTerms"
            required
            ref={(el) => {
              fieldRefs.current.acceptTerms = el;
            }}
            checked={form.acceptTerms}
            onChange={(e) => {
              setForm((prev) => ({ ...prev, acceptTerms: e.target.checked }));
              validateField("acceptTerms", e.target.checked);
            }}
            className="mt-1 rounded border-gray-300 text-orange-700 focus:ring-orange-600"
            aria-describedby="acceptTerms-error"
            aria-invalid={errors.acceptTerms ? "true" : undefined}
          />
          <span className="text-sm">Acepto los términos del programa Brasa Points *</span>
        </label>
        {errors.acceptTerms && (
          <p id="acceptTerms-error" className="mt-1 text-sm text-red-600" aria-live="polite">
            {errors.acceptTerms}
          </p>
        )}
      </div>

      <div>
        <label className="flex items-start gap-2">
          <input
            type="checkbox"
            checked={form.wantsOffers}
            onChange={(e) => setForm((prev) => ({ ...prev, wantsOffers: e.target.checked }))}
            className="mt-1 rounded border-gray-300 text-orange-700 focus:ring-orange-600"
          />
          <span className="text-sm">Quiero recibir ofertas por email</span>
        </label>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row-reverse">
        <button
          type="submit"
          className="w-full rounded-md bg-orange-700 py-3 text-base font-semibold text-white shadow-md transition hover:bg-orange-800"
        >
          Registrarme en Brasa Points
        </button>
        <button
          type="reset"
          className="w-full rounded-md border border-gray-300 py-3 text-base font-semibold text-gray-700 transition hover:bg-gray-50"
        >
          Limpiar formulario
        </button>
      </div>
    </form>
  );
};
