import { useTranslation } from "react-i18next";

const BYOLLMSection = () => {
  const { t } = useTranslation("landing");
  const providers = t("byollm.providers", { returnObjects: true });
  const steps = t("byollm.steps", { returnObjects: true });

  return (
    <section className="py-24 bg-gray-900 overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: Content */}
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 mb-6">
              <span className="text-purple-400 text-sm font-medium">BYO-LLM</span>
            </div>
            
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-6">
              {t("byollm.title")}
            </h2>
            
            <p className="text-lg text-gray-400 mb-8 leading-relaxed">
              {t("byollm.description")}
            </p>

            {/* Provider logos */}
            <div className="flex flex-wrap gap-3 mb-10">
              {providers.map((provider, index) => (
                <span
                  key={index}
                  className="px-4 py-2 bg-gray-800 rounded-lg text-gray-300 text-sm font-medium border border-gray-700"
                >
                  {provider}
                </span>
              ))}
            </div>
          </div>

          {/* Right: Steps */}
          <div className="relative">
            <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-cyan-500 via-purple-500 to-blue-600"></div>
            
            <div className="space-y-8">
              {steps.map((step, index) => (
                <div key={index} className="relative pl-20">
                  {/* Number circle */}
                  <div className="absolute left-0 w-16 h-16 bg-gradient-to-br from-cyan-500 to-purple-600 rounded-2xl flex items-center justify-center text-white text-2xl font-bold shadow-lg shadow-cyan-500/20">
                    {step.number}
                  </div>
                  
                  <div className="bg-gray-800/50 rounded-2xl p-6 border border-gray-700/50">
                    <h3 className="text-xl font-semibold text-white mb-2">
                      {step.title}
                    </h3>
                    <p className="text-gray-400">
                      {step.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default BYOLLMSection;
