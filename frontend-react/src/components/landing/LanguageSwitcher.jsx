import { useTranslation } from "react-i18next";

const LanguageSwitcher = () => {
  const { i18n } = useTranslation();

  const languages = [
    { code: "en", label: "EN", flag: "🇺🇸" },
    { code: "es", label: "ES", flag: "🇪🇸" },
  ];

  return (
    <div className="flex items-center gap-1 bg-gray-800/50 rounded-lg p-1">
      {languages.map((lang) => (
        <button
          key={lang.code}
          onClick={() => i18n.changeLanguage(lang.code)}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center gap-1.5 ${
            i18n.language === lang.code
              ? "bg-cyan-600 text-white shadow-lg shadow-cyan-500/25"
              : "text-gray-400 hover:text-white hover:bg-gray-700/50"
          }`}
          aria-label={`Switch to ${lang.label}`}
        >
          <span>{lang.flag}</span>
          <span>{lang.label}</span>
        </button>
      ))}
    </div>
  );
};

export default LanguageSwitcher;
