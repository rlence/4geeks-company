export const Menu = () => {
  return (
    <section id="menu" aria-labelledby="menu-heading" className="bg-orange-50 py-16 sm:py-24">
      <div className="mx-auto max-w-3xl px-4 text-center">
        <h2 id="menu-heading" className="text-3xl font-bold sm:text-4xl">
          Menú
        </h2>
        <p className="mt-6 text-lg text-gray-600">
          Carnes a la brasa, acompañamientos frescos y postres tradicionales, preparados con los mismos
          estándares en nuestras 14 ubicaciones.
        </p>
        <p role="note" className="mt-8 rounded-xl bg-white px-6 py-5 text-base font-medium text-orange-800 shadow-sm">
          ¿Quieres hacer un pedido? Llama a tu ubicación favorita o visítanos directamente. ¡Pronto tendremos
          pedidos en línea!
        </p>
      </div>
    </section>
  );
};
