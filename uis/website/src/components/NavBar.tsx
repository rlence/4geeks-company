const NAV_LINKS = [
  { href: "#inicio", label: "Inicio" },
  { href: "#ubicaciones", label: "Ubicaciones" },
  { href: "#menu", label: "Menú" },
  { href: "#brasa-points", label: "Brasa Points" },
  { href: "#contacto", label: "Contacto" },
];

export const NavBar = () => {
  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur shadow-sm">
      <nav aria-label="Navegación principal" className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <a href="#inicio" className="text-xl font-extrabold tracking-tight text-orange-700">
          Brasaland
        </a>

        <details className="sm:hidden">
          <summary className="cursor-pointer list-none rounded-md border border-gray-300 px-3 py-2 text-sm font-medium">
            Menú
          </summary>
          <ul className="absolute left-0 right-0 mt-2 space-y-1 bg-white px-4 py-4 shadow-md">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <a href={link.href} className="block py-2 hover:text-orange-700">
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </details>

        <ul className="hidden gap-8 text-sm font-medium sm:flex">
          {NAV_LINKS.map((link) => (
            <li key={link.href}>
              <a href={link.href} className="hover:text-orange-700">
                {link.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
};
