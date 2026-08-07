import Link from "next/link";

const BENEFITS = [
  "Acumula 1 punto por cada $10.000 COP o $5 USD",
  "Canjea tus puntos por descuentos y platos gratis",
  "Ofertas exclusivas para miembros",
  "Registro 100% digital - ¡ya no más tarjetas de papel!",
];

export const BrasaPointsTeaser = () => {
  return (
    <section
      id="brasa-points"
      aria-labelledby="brasa-points-heading"
      className="mx-auto max-w-4xl px-4 py-16 text-center sm:py-24"
    >
      <h2 id="brasa-points-heading" className="text-3xl font-bold sm:text-4xl">
        Brasa Points
      </h2>
      <p className="mt-4 text-xl font-semibold text-orange-700">Gana puntos con cada visita</p>
      <ul className="mx-auto mt-8 max-w-xl space-y-3 text-left text-gray-600">
        {BENEFITS.map((benefit) => (
          <li key={benefit} className="flex gap-3">
            <span aria-hidden="true">🔥</span> {benefit}
          </li>
        ))}
      </ul>
      <Link
        href="/brasa-points"
        className="mt-10 inline-block rounded-full bg-orange-700 px-8 py-3 text-base font-semibold text-white shadow-md transition hover:bg-orange-800"
      >
        Únete a Brasa Points
      </Link>
    </section>
  );
};
