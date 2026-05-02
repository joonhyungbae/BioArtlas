import { createI18n } from 'vue-i18n'
import ko from '../locales/ko.json'
import en from '../locales/en.json'

const messages = {
  ko,
  en
}

// 저장된 언어 설정을 불러오거나 기본값 설정 (English 우선)
const savedLocale = localStorage.getItem('locale') || 'en'

const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: 'en',
  messages
})

export default i18n 