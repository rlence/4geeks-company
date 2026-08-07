const FEATURES = [
  {
    title: "Calidad Consistente",
    points: ["Mismas recetas y estándares en todos los locales", "Ingredientes frescos seleccionados diariamente"],
  },
  {
    title: "Experiencia Cálida",
    points: ["Servicio amable y atento", "Ambiente familiar en cada visita"],
  },
  {
    title: "Rapidez",
    points: ["Tu comida lista en minutos", "Sin sacrificar sabor ni calidad"],
  },
];

export const WhatMakesUsUnique = () => {
  return (
    <section aria-labelledby="unicos-heading" className="bg-orange-50 py-16 sm:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <h2 id="unicos-heading" className="text-center text-3xl font-bold sm:text-4xl">
          Lo que nos hace únicos
        </h2>
        <div className="mt-12 grid gap-8 sm:grid-cols-3">
          {FEATURES.map((feature) => (
            <article key={feature.title} className="rounded-2xl bg-white p-8 text-center shadow-sm">
              <h3 className="text-xl font-semibold text-orange-700">{feature.title}</h3>
              <ul className="mt-4 space-y-2 text-gray-600">
                {feature.points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
};
