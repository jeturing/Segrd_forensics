import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import enCommon from '../locales/en/common.json';
import enLanding from '../locales/en/landing.json';
import enModules from '../locales/en/modules.json';
import enFaq from '../locales/en/faq.json';

import esCommon from '../locales/es/common.json';
import esLanding from '../locales/es/landing.json';
import esModules from '../locales/es/modules.json';
import esFaq from '../locales/es/faq.json';

const resources = {
  en: {
    common: enCommon,
    landing: enLanding,
    modules: enModules,
    faq: enFaq,
  },
  es: {
    common: esCommon,
    landing: esLanding,
    modules: esModules,
    faq: esFaq,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    supportedLngs: ['en', 'es'],
    defaultNS: 'common',
    ns: ['common', 'landing', 'modules', 'faq'],
    
    detection: {
      order: ['querystring', 'localStorage', 'navigator', 'htmlTag'],
      lookupQuerystring: 'lang',
      lookupLocalStorage: 'segrd-language',
      caches: ['localStorage'],
    },

    interpolation: {
      escapeValue: false,
    },

    react: {
      useSuspense: false,
    },
  });

export default i18n;
