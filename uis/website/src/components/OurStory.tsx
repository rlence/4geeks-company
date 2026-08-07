import Image from "next/image";

export const OurStory = () => {
  return (
    <section aria-labelledby="historia-heading" className="mx-auto max-w-6xl px-4 py-16 sm:py-24">
      <div className="grid items-center gap-10 md:grid-cols-2">
        <div>
          <h2 id="historia-heading" className="text-3xl font-bold sm:text-4xl">
            Nuestra Historia
          </h2>
          <p className="mt-6 text-lg leading-relaxed text-gray-600">
            Fundada en Medellín en 2008, Brasaland comenzó como un sueño familiar: compartir el auténtico sabor
            de la carne a la brasa con calidad constante y servicio cálido. Hoy somos 14 restaurantes en dos
            países, pero mantenemos la misma receta de éxito: productos frescos, técnicas tradicionales, y
            pasión por cada plato que servimos.
          </p>
        </div>
        <Image
          src="https://placehold.co/640x420/c2410c/fff7ed?text=Brasaland"
          alt="Interior de un restaurante Brasaland con parrilla a la brasa"
          className="w-full rounded-2xl object-cover shadow-lg"
          width={640}
          height={420}
          unoptimized
        />
      </div>
    </section>
  );
};
