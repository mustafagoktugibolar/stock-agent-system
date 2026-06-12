export type Language = 'en' | 'tr'

type Translations = {
  [key in Language]: Record<string, string>
}

export const messages: Translations = {
  en: {
    'nav.market.overview': 'Market Overview',
    'nav.select.ticker': 'Select a ticker below or search for any global instrument.',
    'nav.agent': 'AI-POWERED STOCK ANALYSIS',
    'nav.refresh': '↻ Refresh',
    'nav.ask.agent': 'Ask Agent',
    
    'header.employees': 'employees',
    'header.market.cap': 'Market Cap',
    'header.pe': 'P/E',
    'header.fwd.pe': 'Fwd P/E',
    'header.div.yield': 'Div. Yield',
    'header.read.more': 'Read more',
    'header.show.less': 'Show less',

    'rec.recommendation': 'Recommendation',
    'rec.target': 'Target',
    'rec.stop': 'Stop Loss',
    'rec.horizon': 'Horizon',
    'rec.confidence': 'Confidence',
    'rec.very.high': 'Very high conviction',
    'rec.high': 'High conviction',
    'rec.moderate': 'Moderate conviction',
    'rec.low': 'Low conviction',
    'rec.cached': 'Cached',

    'judge.title': 'LLM Judge',
    'judge.subtitle': 'Independent evaluation of this recommendation',
    'judge.pass': 'PASS',
    'judge.fail': 'FAIL',
    'judge.overall': 'Overall',
    'judge.coherence': 'Coherence',
    'judge.evidence': 'Evidence',
    'judge.risk.alignment': 'Risk Alignment',
    'judge.critique': 'Critique',
    'judge.suggestions': 'Suggestions',

    'tech.title': 'Technical Analysis',
    'tech.support': 'Support',
    'tech.resistance': 'Resistance',
    'tech.atr': 'ATR(14)',

    'news.title': 'News & Sentiment',
    'news.negative': 'Negative',
    'news.positive': 'Positive',

    'risk.title': 'Risk Assessment',
    'risk.drawdown': 'Max Drawdown',

    'fin.title': 'Financial Statements',
    'fin.balance': 'Balance Sheet',
    'fin.income': 'Income',
    'fin.cashflow': 'Cash Flow',
    'fin.ratios': 'Key Ratios',
    'fin.quarterly': 'Quarterly',
    'fin.annual': 'Annual',
    'fin.no.data': 'No data available.',

    'chat.placeholder': 'Ask a follow-up question...',
    'chat.context': 'Context: {symbol} Analysis',

    'advisor.title': 'Portfolio Advisor',
    'advisor.open': 'Portfolio Advisor',
    'advisor.welcome': 'Tell me your investment goals and I\'ll suggest specific stocks to analyze. Example: "What energy companies should I look at?" or "Give me a defensive dividend stock."',
    'advisor.placeholder': 'Ask for investment ideas...',
    'advisor.prefs.title': 'Your Preferences',
    'advisor.prefs.risk': 'Risk Tolerance',
    'advisor.prefs.sectors': 'Sectors of Interest',
    'advisor.prefs.horizon': 'Investment Horizon',
    'advisor.prefs.save': 'Save Preferences',
    'advisor.analyze': 'Analyze',

    'val.buy': 'BUY',
    'val.sell': 'SELL',
    'val.hold': 'HOLD',
    'val.bullish': 'BULLISH',
    'val.bearish': 'BEARISH',
    'val.neutral': 'NEUTRAL',
    'val.low': 'LOW',
    'val.medium': 'MEDIUM',
    'val.high': 'HIGH',
    'val.very_high': 'VERY HIGH'
  },
  tr: {
    'nav.market.overview': 'Piyasa Özeti',
    'nav.select.ticker': 'Aşağıdaki listeden hisse seçin veya arama yapın.',
    'nav.agent': 'YAPAY ZEKA BORSA ANALİZİ',
    'nav.refresh': '↻ Yenile',
    'nav.ask.agent': 'Ajana Sor',
    
    'header.employees': 'çalışan',
    'header.market.cap': 'Piyasa Değeri',
    'header.pe': 'F/K',
    'header.fwd.pe': 'İleri F/K',
    'header.div.yield': 'Temettü',
    'header.read.more': 'Devamını Oku',
    'header.show.less': 'Gizle',

    'rec.recommendation': 'Tavsiye',
    'rec.target': 'Hedef Fiyat',
    'rec.stop': 'Zarar Kes (Stop)',
    'rec.horizon': 'Vade',
    'rec.confidence': 'Güven',
    'rec.very.high': 'Çok yüksek güven seviyesi',
    'rec.high': 'Yüksek güven seviyesi',
    'rec.moderate': 'Orta güven seviyesi',
    'rec.low': 'Düşük güven seviyesi',
    'rec.cached': 'Önbellekten (Cached)',

    'judge.title': 'LLM Hakem',
    'judge.subtitle': 'Bu tavsiyenin bağımsız değerlendirmesi',
    'judge.pass': 'GEÇTİ',
    'judge.fail': 'KALDI',
    'judge.overall': 'Genel',
    'judge.coherence': 'Tutarlılık',
    'judge.evidence': 'Kanıt',
    'judge.risk.alignment': 'Risk Uyumu',
    'judge.critique': 'Değerlendirme',
    'judge.suggestions': 'Öneriler',

    'tech.title': 'Teknik Analiz',
    'tech.support': 'Destek',
    'tech.resistance': 'Direnç',
    'tech.atr': 'ATR(14)',

    'news.title': 'Haberler & Duygu',
    'news.negative': 'Negatif',
    'news.positive': 'Pozitif',

    'risk.title': 'Risk Değerlendirmesi',
    'risk.drawdown': 'Maksimum Düşüş',

    'fin.title': 'Finansal Tablolar (Bilançolar)',
    'fin.balance': 'Bilanço',
    'fin.income': 'Gelir Tablosu',
    'fin.cashflow': 'Nakit Akışı',
    'fin.ratios': 'Temel Rasyolar',
    'fin.quarterly': 'Çeyreklik',
    'fin.annual': 'Yıllık',
    'fin.no.data': 'Veri bulunamadı.',

    'chat.placeholder': 'Ek bir soru sorun...',
    'chat.context': 'Bağlam: {symbol} Analizi',

    'advisor.title': 'Portföy Danışmanı',
    'advisor.open': 'Portföy Danışmanı',
    'advisor.welcome': 'Yatırım hedeflerinizi anlatın, analiz edebileceğiniz hisseler önereceğim. Örnek: "Enerji sektöründe hangi şirkete bakmalıyım?" veya "Temettü veren savunmacı bir hisse öner."',
    'advisor.placeholder': 'Yatırım fikri sorun...',
    'advisor.prefs.title': 'Tercihleriniz',
    'advisor.prefs.risk': 'Risk Toleransı',
    'advisor.prefs.sectors': 'İlgi Alanı Sektörler',
    'advisor.prefs.horizon': 'Yatırım Vadesi',
    'advisor.prefs.save': 'Tercihleri Kaydet',
    'advisor.analyze': 'Analiz Et',

    'val.buy': 'AL',
    'val.sell': 'SAT',
    'val.hold': 'TUT',
    'val.bullish': 'YÜKSELİŞ',
    'val.bearish': 'DÜŞÜŞ',
    'val.neutral': 'NÖTR',
    'val.low': 'DÜŞÜK',
    'val.medium': 'ORTA',
    'val.high': 'YÜKSEK',
    'val.very_high': 'ÇOK YÜKSEK'
  }
}

let currentLanguage: Language = (localStorage.getItem('lang') as Language) || 'tr'

export function setLanguage(lang: Language) {
  currentLanguage = lang
  localStorage.setItem('lang', lang)
  // trigger a page reload or state update if implemented functionally globally
}

export function getLanguage(): Language {
  return currentLanguage
}

export function t(key: string, params?: Record<string, string>): string {
  let val = messages[currentLanguage][key] || key
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      val = val.replace(`{${k}}`, v)
    }
  }
  return val
}

export function tVal(val: string): string {
  const k = `val.${val.toLowerCase()}`
  return messages[currentLanguage][k] || val
}
