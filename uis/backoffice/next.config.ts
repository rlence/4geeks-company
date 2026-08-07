import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // packages/data-utils (Hito 2) vive fuera de este directorio de proyecto y no hay
  // workspace configurado en la raíz del monorepo — externalDir permite importar su
  // .ts fuente directamente en vez de copiarlo (ver .agents/rules/monorepo-imports.md).
  experimental: {
    externalDir: true,
  },
  webpack: (config) => {
    // packages/data-utils usa resolución NodeNext: sus imports internos apuntan a
    // ".js" pero los archivos reales son ".ts" — sin este alias webpack no los resuelve.
    config.resolve.extensionAlias = {
      ".js": [".ts", ".tsx", ".js"],
    };
    return config;
  },
};

export default nextConfig;
