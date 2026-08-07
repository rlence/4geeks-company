const LOCATIONS = [
  {
    country: "Colombia",
    description: "10 restaurantes en Medellín, Bogotá y Cali",
    hours: "Horario: Lun-Dom 11:00 - 22:00",
  },
  {
    country: "Estados Unidos (Florida)",
    description: "4 restaurantes en Miami y Orlando",
    hours: "Horario: Mon-Sun 11:00 AM - 10:00 PM",
  },
];

export const Locations = () => {
  return (
    <section id="ubicaciones" aria-labelledby="ubicaciones-heading" className="mx-auto max-w-6xl px-4 py-16 sm:py-24">
      <h2 id="ubicaciones-heading" className="text-center text-3xl font-bold sm:text-4xl">
        Nuestras Ubicaciones
      </h2>
      <div className="mt-12 grid gap-8 sm:grid-cols-2">
        {LOCATIONS.map((location) => (
          <article key={location.country} className="rounded-2xl border border-gray-200 p-8">
            <h3 className="text-xl font-semibold">{location.country}</h3>
            <p className="mt-3 text-gray-600">{location.description}</p>
            <p className="mt-1 text-gray-600">{location.hours}</p>
          </article>
        ))}
      </div>
    </section>
  );
};
