import Link from "next/link";

export const Hero = () => {
  return (
    <section id="inicio" className="bg-gradient-to-b from-orange-50 to-white">
      <div className="mx-auto max-w-4xl px-4 py-20 text-center sm:py-28">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          El sabor de la brasa, en cada bocado
        </h1>
        <p className="mt-6 text-lg text-gray-600 sm:text-xl">
          Desde 2008 sirviendo las mejores carnes a la brasa en Colombia y Estados Unidos. 14 ubicaciones, una
          misma pasión por la calidad y el sabor.
        </p>
        <Link
          href="/brasa-points"
          className="mt-10 inline-block rounded-full bg-orange-700 px-8 py-3 text-base font-semibold text-white shadow-md transition hover:bg-orange-800"
        >
          Únete a Brasa Points
        </Link>
      </div>
    </section>
  );
};
