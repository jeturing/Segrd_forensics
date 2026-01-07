import { useTranslation } from "react-i18next";

const marketIcons = {
  soc: (
    <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
  legal: (
    <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
    </svg>
  ),
  banking: (
    <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z" />
    </svg>
  ),
};

const TargetMarkets = () => {
  const { t } = useTranslation("landing");
  const segments = t("markets.segments", { returnObjects: true });

  return (
    <section className="py-24 bg-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            {t("markets.title")}
          </h2>
          <div className="w-20 h-1 bg-gradient-to-r from-cyan-500 to-blue-600 mx-auto rounded-full"></div>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {segments.map((segment, index) => (
            <div
              key={segment.id}
              className="relative p-8 bg-gray-900/50 rounded-2xl border border-gray-700/50 hover:border-cyan-500/30 transition-all duration-300"
            >
              {/* Icon */}
              <div className="w-20 h-20 bg-gradient-to-br from-cyan-500/20 to-blue-600/20 rounded-2xl flex items-center justify-center text-cyan-400 mb-6">
                {marketIcons[segment.id]}
              </div>

              {/* Content */}
              <h3 className="text-2xl font-bold text-white mb-3">
                {segment.title}
              </h3>
              <p className="text-gray-400 mb-6 leading-relaxed">
                {segment.description}
              </p>

              {/* Features */}
              <ul className="space-y-3">
                {segment.features.map((feature, fIndex) => (
                  <li key={fIndex} className="flex items-center gap-3 text-gray-300">
                    <svg className="w-5 h-5 text-cyan-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default TargetMarkets;
