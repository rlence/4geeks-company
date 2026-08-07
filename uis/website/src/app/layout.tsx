import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Brasaland — El sabor de la brasa, en cada bocado",
  description:
    "Brasaland es una cadena de restaurantes de comida a la brasa con 14 ubicaciones en Colombia y Estados Unidos. Conoce nuestra historia, ubicaciones y únete a Brasa Points.",
  icons: {
    icon: "https://placehold.co/640x420/c2410c/fff7ed?text=Brasaland",
  },
};

const restaurantJsonLd = {
  "@context": "https://schema.org",
  "@type": "Restaurant",
  name: "Brasaland",
  description: "Cadena de restaurantes de comida a la brasa en Colombia y Estados Unidos",
  url: "https://brasaland.com",
  foundingDate: "2008",
  servesCuisine: "Grilled food, Colombian cuisine",
  priceRange: "$$",
  address: [
    {
      "@type": "PostalAddress",
      addressCountry: "CO",
      addressLocality: "Medellín",
      addressRegion: "Antioquia",
    },
    {
      "@type": "PostalAddress",
      addressCountry: "US",
      addressLocality: "Miami",
      addressRegion: "FL",
    },
  ],
  contactPoint: {
    "@type": "ContactPoint",
    telephone: "+57-4-123-4567",
    contactType: "customer service",
    availableLanguage: ["Spanish"],
  },
  sameAs: ["https://instagram.com/brasaland", "https://facebook.com/brasaland"],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" className="scroll-smooth">
      <body className="bg-white text-gray-900 antialiased">
        {children}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(restaurantJsonLd) }}
        />
      </body>
    </html>
  );
}
