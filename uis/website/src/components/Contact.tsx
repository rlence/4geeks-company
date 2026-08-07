export const Contact = () => {
  return (
    <section id="contacto" aria-labelledby="contacto-heading" className="bg-orange-900 py-16 text-white sm:py-24">
      <div className="mx-auto max-w-3xl px-4 text-center">
        <h2 id="contacto-heading" className="text-3xl font-bold sm:text-4xl">
          Contacto
        </h2>
        <dl className="mt-8 space-y-3 text-lg">
          <div>
            <dt className="sr-only">Email</dt>
            <dd>
              <a href="mailto:hola@brasaland.com" className="hover:underline">
                hola@brasaland.com
              </a>
            </dd>
          </div>
          <div>
            <dt className="sr-only">Teléfono Colombia</dt>
            <dd>
              Colombia:{" "}
              <a href="tel:+5741234567" className="hover:underline">
                +57 4 123 4567
              </a>
            </dd>
          </div>
          <div>
            <dt className="sr-only">Teléfono Florida</dt>
            <dd>
              Florida:{" "}
              <a href="tel:+13051234567" className="hover:underline">
                +1 305 123 4567
              </a>
            </dd>
          </div>
        </dl>
      </div>
    </section>
  );
};
