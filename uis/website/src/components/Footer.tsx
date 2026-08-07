export const Footer = () => {
  return (
    <footer className="bg-gray-900 py-8 text-center text-sm text-gray-400">
      <p>© 2025 Brasaland. Todos los derechos reservados.</p>
      <p className="mt-2 space-x-4">
        <a
          href="https://instagram.com/brasaland"
          className="hover:text-white"
          aria-label="Instagram de Brasaland (enlace externo)"
        >
          Instagram
        </a>
        <span aria-hidden="true">|</span>
        <a
          href="https://facebook.com/brasaland"
          className="hover:text-white"
          aria-label="Facebook de Brasaland (enlace externo)"
        >
          Facebook
        </a>
      </p>
    </footer>
  );
};
