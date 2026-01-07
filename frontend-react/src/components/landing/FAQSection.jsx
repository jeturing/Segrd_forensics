import { useTranslation } from "react-i18next";
import { useState } from "react";

const FAQSection = () => {
  const { t } = useTranslation("faq");
  const categories = t("categories", { returnObjects: true });
  const [openItems, setOpenItems] = useState({});

  const toggleItem = (key) => {
    setOpenItems((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <section className="py-24 bg-gray-900">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            {t("title")}
          </h2>
          <div className="w-20 h-1 bg-gradient-to-r from-cyan-500 to-blue-600 mx-auto rounded-full"></div>
        </div>

        <div className="space-y-8">
          {Object.entries(categories).map(([catKey, category]) => (
            <div key={catKey}>
              <h3 className="text-lg font-semibold text-cyan-400 mb-4">
                {category.title}
              </h3>
              <div className="space-y-3">
                {category.questions.map((item, index) => {
                  const itemKey = `${catKey}-${index}`;
                  const isOpen = openItems[itemKey];
                  
                  return (
                    <div
                      key={itemKey}
                      className="bg-gray-800/50 rounded-xl border border-gray-700/50 overflow-hidden"
                    >
                      <button
                        onClick={() => toggleItem(itemKey)}
                        className="w-full px-6 py-4 text-left flex items-center justify-between gap-4 hover:bg-gray-800/80 transition-colors"
                      >
                        <span className="text-white font-medium">{item.q}</span>
                        <svg
                          className={`w-5 h-5 text-gray-400 flex-shrink-0 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                      {isOpen && (
                        <div className="px-6 pb-4">
                          <p className="text-gray-400 leading-relaxed">{item.a}</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default FAQSection;
