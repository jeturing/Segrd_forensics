import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

const HeroSection = () => {
  const { t } = useTranslation("landing");

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-cyan-900/20 via-transparent to-transparent"></div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-cyan-500/10 border border-cyan-500/20 mb-8">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
          </span>
          <span className="text-cyan-400 text-sm font-medium">MCP-First Architecture</span>
        </div>

        {/* Title */}
        <h1 className="text-5xl md:text-7xl font-bold text-white mb-4 tracking-tight">
          {t("hero.title")}
        </h1>
        
        <p className="text-xl md:text-2xl text-cyan-400 font-medium mb-6">
          {t("hero.subtitle")}
        </p>

        <p className="text-lg md:text-xl text-gray-400 max-w-3xl mx-auto mb-10 leading-relaxed">
          {t("hero.description")}
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            to="/contact"
            className="inline-flex items-center justify-center px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold text-lg shadow-lg shadow-cyan-500/25 hover:shadow-xl hover:shadow-cyan-500/30 transform hover:-translate-y-0.5 transition-all duration-200"
          >
            {t("hero.cta_primary")}
            <svg className="ml-2 w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </Link>
          <Link
            to="/modules"
            className="inline-flex items-center justify-center px-8 py-4 rounded-xl border-2 border-gray-600 text-white font-semibold text-lg hover:border-cyan-500 hover:bg-cyan-500/10 transition-all duration-200"
          >
            {t("hero.cta_secondary")}
          </Link>
        </div>

        {/* Trust badges */}
        <div className="mt-16 pt-8 border-t border-gray-700/50">
          <p className="text-gray-500 text-sm mb-4">Trusted by security teams worldwide</p>
          <div className="flex flex-wrap justify-center gap-8 opacity-50">
            <span className="text-gray-400 font-semibold">SOC 2 Type II</span>
            <span className="text-gray-400 font-semibold">GDPR</span>
            <span className="text-gray-400 font-semibold">HIPAA Ready</span>
            <span className="text-gray-400 font-semibold">PCI-DSS</span>
          </div>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-bounce">
        <svg className="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </section>
  );
};

export default HeroSection;
