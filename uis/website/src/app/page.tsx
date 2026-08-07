import { NavBar } from "@/components/NavBar";
import { Hero } from "@/components/Hero";
import { OurStory } from "@/components/OurStory";
import { WhatMakesUsUnique } from "@/components/WhatMakesUsUnique";
import { Locations } from "@/components/Locations";
import { Menu } from "@/components/Menu";
import { BrasaPointsTeaser } from "@/components/BrasaPointsTeaser";
import { Contact } from "@/components/Contact";
import { Footer } from "@/components/Footer";

export default function Home() {
  return (
    <>
      <NavBar />
      <main>
        <Hero />
        <OurStory />
        <WhatMakesUsUnique />
        <Locations />
        <Menu />
        <BrasaPointsTeaser />
        <Contact />
      </main>
      <Footer />
    </>
  );
}
