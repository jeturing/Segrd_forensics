import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

const moduleColors = {
  foren: "from-cyan-500 to-blue-600",
  axion: "from-blue-500 to-indigo-600",
  vigil: "from-indigo-500 to-purple-600",
  orbia: "from-purple-500 to-pink-600",
  cortexa: "from-pink-500 to-rose-600",
  clouda: "from-orange-500 to-amber-600",
  nodos: "from-emerald-500 to-teal-600",
};

const ModulesGrid = () => {
  const { t } = useTranslation("modules");
  const modules = t("modules", { returnObjects: true });
  const moduleKeys = Object.keys(modules);

  return (
    <section className="py-24 bg-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            {t("title")}
          </h2>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            {t("subtitle")}
          </p>
          <div className="w-20 h-1 bg-gradient-to-r from-cyan-500 to-blue-600 mx-auto rounded-full mt-6"></div>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {moduleKeys.map((key) => {
            const mod = modules[key];
            return (
              <Link
                key={key}
                to={`/${key}`}
                className="group relative p-6 bg-gray-900/50 rounded-2xl border border-gray-700/50 hover:border-transparent transition-all duration-300 overflow-hidden"
              >
                {/* Gradient border on hover */}
                <div className={`absolute inset-0 bg-gradient-to-br ${moduleColors[key]} opacity-0 group-hover:opacity-10 transition-opacity duration-300`}></div>
                
                <div className="relative">
                  {/* Module name with gradient */}
                  <h3 className={`text-2xl font-bold bg-gradient-to-r ${moduleColors[key]} bg-clip-text text-transparent mb-2`}>
                    {mod.name}
                  </h3>
                  
                  <p className="text-cyan-400 text-sm font-medium mb-3">
                    {mod.tagline}
                  </p>
                  
                  <p className="text-gray-400 text-sm leading-relaxed mb-4 line-clamp-3">
                    {mod.description}
                  </p>

                  {/* Tools preview */}
                  <div className="flex flex-wrap gap-1">
                    {mod.tools.slice(0, 3).map((tool, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-400"
                      >
                        {tool}
                      </span>
                    ))}
                    {mod.tools.length > 3 && (
                      <span className="px-2 py-1 text-xs text-gray-500">
                        +{mod.tools.length - 3}
                      </span>
                    )}
                  </div>

                  {/* Arrow */}
                  <div className="absolute top-0 right-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default ModulesGrid;
