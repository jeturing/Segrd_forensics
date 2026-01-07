import { HelmetProvider } from "react-helmet-async";
import {
  Navbar,
  Footer,
  HeroSection,
  ValueProps,
  TargetMarkets,
  BYOLLMSection,
  ModulesGrid,
  FAQSection,
  CTASection,
} from "../../components/landing";
import JsonLdSchema from "../../components/seo/JsonLdSchema";

const LandingPage = () => {
  return (
    <HelmetProvider>
      <div className="min-h-screen bg-gray-900">
        <JsonLdSchema />
        <Navbar />
        <main>
          <HeroSection />
          <ValueProps />
          <ModulesGrid />
          <TargetMarkets />
          <BYOLLMSection />
          <FAQSection />
          <CTASection />
        </main>
        <Footer />
      </div>
    </HelmetProvider>
  );
};

export default LandingPage;
