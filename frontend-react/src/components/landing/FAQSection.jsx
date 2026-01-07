import { useTranslation } from "react-i18next";
import { useState } from "react";

const FAQSection = () => {
  const { t } = useTranslation("faq");
  const items = t("items", { returnObjects: true }) || [];
  const [openItems, setOpenItems] = useState({});

  const toggleItem = (index) => {
    setOpenItems((prev) => ({ ...prev, [index]: !prev[index] }));
  };

  // Group by category
  const categories = Array.isArray(items) ? items.reduce((acc, item) => {
    if (!acc[item.category]) {
      acc[item.category] = [];
    }
    acc[item.category].push(item);
    return acc;
  }, {}) : {};

  return (
    <section className="py-24 bg-gray-900">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            {t("title")}
          </h2>
          <p className="text-gray-400">{t("subtitle")}</p>
          <div className="w-20 h-1 bg-gradient-to-r from-cyan-500 to-blue-600 mx-auto rounded-full mt-6"></div>
        </div>

        <div className="space-y-8">
          {Object.entries(categories).map(([category, questions]) => (
            <div key={category}>
              <h3 className="text-lg font-semibold text-cyan-400 mb-4 capitalize">
                {category.replace("_", " ")}
              </h3>
              <div className="space-y-3">
                {questions.map((item, index) => {
                  const itemKey = `${category}-${index}`;
                  const isOpen = openItems[itemKey];
                  
                  return (
                    <div
                      key={itemKey}
                      className="bg-gray-800/50 rounded-xl border border-gray-700/50 overflow-hidden"
                    >
                      <button
                        onClick={() => toggleItem(itemKey)}
                        className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-800/80 transition-colors"
                      >
                        <span className="text-white font-medium pr-8">
                          {item.question}
                        </span>
                        <svg
                          className={`w-5 h-5 text-cyan-400 transition-transform flex-shrink-0 ${
                            isOpen ? "rotate-180" : ""
                          }`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 9l-7 7-7-7"
                          />
                        </svg>
                      </button>
                      {isOpen && (
                        <div className="px-6 pb-4 text-gray-400 leading-relaxed">
                          {item.answer}
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
