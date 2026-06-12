# Sunum Rehberi - Multi-Agent Stock Analysis and Paper Trading System

Bu dokuman sunumda ne anlatacagini, hangi ekrani hangi sirayla gosterecegini ve gelebilecek teknik sorulara nasil cevap verecegini toparlar.

---

## 1. Tek Cumlelik Proje Tanimi

Bu proje, hisse senetlerini coklu agent mimarisiyle analiz eden, analiz sonucunu ikinci bir LLM judge ile denetleyen, ardindan ayri bir trading agent ile backtest veya Alpaca paper trading kararina donusturebilen bir karar destek sistemidir.

Kisa versiyon:

> "Sistem once uzman agentlarla hisseyi analiz ediyor, supervisor agent bu analizleri tek bir BUY/HOLD/SELL onerisine ceviriyor, judge agent bu oneriyi denetliyor. Trading tarafinda ise ayri bir trade decision agent portfoy durumunu, risk limitlerini ve varsa supervisor raporunu kullanarak trade karari veriyor."

---

## 2. Sunumun Ana Mesaji

Sunum boyunca su fikri tekrar et:

> "Analysis recommendation ile trade execution ayni sey degil. Oneri ureten agent ve emir veren agent ayrildi. Bu sayede sistem daha aciklanabilir, test edilebilir ve daha guvenli."

Bu ayrim projeyi guclu gosterir:

- Specialist agentlar veri toplar ve sinyal uretir.
- Supervisor agent rapor ve nihai oneriyi sentezler.
- LLM judge onerinin tutarli olup olmadigini denetler.
- Trade decision agent portfoy ve risk limitlerine bakarak trade aksiyonu uretir.
- Deterministik gate'ler emrin gercekten gonderilip gonderilmeyecegine karar verir.
- Backtest Alpaca market data kullanir ama Alpaca hesabina emir yazmaz.

---

## 3. Mimariyi Anlatma Sirasi

### 3.1 Analysis Pipeline

Slaytta veya kodda su akisi goster:

```text
technical_agent
news_agent
risk_agent
fundamentals_agent
      |
      v
supervisor_agent
      |
      v
llm_judge
```

Konusma metni:

> "Burada dort specialist agent paralel calisiyor. Technical agent fiyat ve indikatorlere, news agent haber sentiment'ine, risk agent volatilite ve benchmark riskine, fundamentals agent ise sirket profiline ve finansallara bakiyor. Supervisor agent bu dort sonucu structured output ile tek bir FinalRecommendation modeline ceviriyor. Sonra llm_judge bu kararin kanita dayali olup olmadigini, riskle uyumlu olup olmadigini ve kendi icinde tutarli olup olmadigini puanliyor."

Vurgula:

- Specialist agentlar deterministic.
- Supervisor LLM kullaniyor.
- Judge baska bir LLM pass'i.
- Output Pydantic schema ile validate ediliyor.

### 3.2 Trading Pipeline

Su akisi goster:

```text
market_observer
  -> analysis_fetcher
  -> memory_retrieval
  -> trade_decision_agent
  -> execute / virtual_execute / skip
```

Konusma metni:

> "Trading pipeline farkli. Burada asil karar trade_decision_agent tarafindan veriliyor. Bu agent current market observation, portfolio state, memory ve varsa cache'teki supervisor analysis context'ini goruyor. Ama emir gondermek tamamen deterministik safety gate'lerden geciyor."

Vurgula:

- `TRADING_ENABLED=false`: sanal pozisyon.
- `TRADING_ENABLED=true`: Alpaca paper order.
- HOLD asla execute olmaz.
- Confidence threshold var.
- Max position ve position size limitleri var.

---

## 4. Supervisor Agent ve Trade Decision Agent Farki

Bu soru kesin gelebilir.

Kisa cevap:

> "Supervisor agent analiz katmaninin final onerisi. Trade decision agent ise trading katmaninin aksiyon karari. Trading agent supervisor raporunu context olarak kullanabilir ama birebir kopyalamaz."

Tabloyla anlat:

| Agent | Ne yapar | Output | Sonraki adim |
| --- | --- | --- | --- |
| `supervisor_agent` | Dort analizi sentezler | `FinalRecommendation` | UI raporu ve trading context |
| `trade_decision_agent` | Portfoy ve riskle trade aksiyonu verir | `TradeDecisionOutput` | Execute, virtual execute veya skip |

Ornek:

> "Supervisor BUY diyebilir ama trade agent HOLD diyebilir. Cunku trade agent portfoyde zaten pozisyon oldugunu, confidence'in dusuk oldugunu veya max position limitine gelindigini gorebilir."

---

## 5. Alpaca Entegrasyonunu Anlatma

Burada iki endpoint ayrimini net soyle:

```text
Market data:
https://data.alpaca.markets/v2/stocks/bars

Paper trading orders:
https://paper-api.alpaca.markets/v2/orders
```

Konusma metni:

> "Alpaca'yi iki farkli amacla kullaniyoruz. Backtestte historical market data cekiyoruz. Bu data endpoint'i. Paper tradingde ise paper account'a order gonderiyoruz. Bu trading endpoint'i. Backtestte cikan trade'ler Alpaca dashboard'a dusmez, cunku Alpaca gecmis tarihli fill yaratmaz."

Eger ekranda Alpaca Orders gorunuyorsa:

> "Bu order'lar historical backtestten gelmedi. Bunlar live/manual paper trading cycle tarafindan bugunun paper account'una gonderilen emirler."

Eger `status=new`, `filled_qty=0` gorunuyorsa:

> "Market order gonderilmis ama henuz fill olmamis. Regular market saatleri disinda DAY market order'lar acilis saatine kadar new status'te kalabilir."

---

## 6. Backtesti Anlatma

Kisa cevap:

> "Backtest, gecmisteki gunleri tek tek replay ediyor. Her gun agent'a sadece o gune kadar olan barlar veriliyor. Gelecek barlar karar aninda prompt'a girmiyor."

Akis:

```text
User range: 2024-09-02 -> 2024-10-31
Fetch range: 2023-09-03 -> 2024-10-31
Reason: 365-day warmup for indicators

For each trading day:
  build observation from bars up to that day
  call trade_decision_agent
  simulate BUY/SELL/HOLD locally
  update equity curve
```

Neden warmup var?

> "RSI, MACD, ATR, ADX gibi indikatorler sadece secilen ilk gunden baslatilirsa yanlis hesaplanir. Bu yuzden start date'ten onceki 365 gunu warmup olarak cekiyoruz."

Neden Alpaca dashboard'da gorunmez?

> "Backtest local simulation. Alpaca paper account gercek zamanli emir sistemi. Gecmis tarihli emir create edemeyiz."

Mevcut varsayimlari durustce soyle:

- Historical news neutral.
- Historical supervisor context kapali.
- Entry same-day close.
- Daha katı versiyonda next-day open entry yapilabilir.

Bu durustluk sunumda guven verir.

---

## 7. Demo Akisi

### Hazirlik

Demo oncesi:

1. Docker servisleri calisiyor olsun.
2. Frontend acik: `http://localhost:5173`
3. API docs acik: `http://localhost:8000/docs`
4. Alpaca dashboard acik.
5. `.env` icinde API keyler var.
6. `TRADING_ENABLED` degerini bil:
   - Guvenli demo icin once `false`.
   - Alpaca Orders gostermek istiyorsan sadece kisa bolumde `true`.

Komut:

```bash
docker compose up --build
```

### 7.1 Analysis Sayfasi

Goster:

1. Symbol search: `NVDA`
2. Analyze butonu
3. Loading steps: Fundamentals, Technical, News, Risk, Supervisor
4. Recommendation card
5. Technical panel
6. News panel
7. Risk panel
8. Financials panel
9. Judge verdict

Ne diyeceksin:

> "Burada dort uzman agent paralel calisiyor. Supervisor tek bir oneride birlestiriyor. Judge ise bu onerinin kanita dayali olup olmadigini kontrol ediyor."

### 7.2 Trading Sayfasi

Goster:

1. `/trading`
2. System status
3. Watchlist
4. Limits
5. Recent Decisions
6. Open Positions
7. Trade History

Ne diyeceksin:

> "Trading page analiz raporundan farkli. Burada portfoy durumu, risk limitleri ve trade karar gecmisi var."

### 7.3 Historical Backtest

Ornek:

```text
Symbol: NVDA
Start: 2024-09-02
End: 2024-10-31
Initial capital: 10000
Min confidence: 0.4
```

Goster:

- Initial capital
- Final equity
- Agent return
- Trades
- Max drawdown
- Decision counts
- Market data: alpaca
- Trade table

Ne diyeceksin:

> "Bu kisim Alpaca historical market data kullanarak gecmisi replay ediyor. Buradaki trade'ler local simulation. Alpaca dashboard'da gorunmemesi dogru davranis."

### 7.4 Alpaca Paper Order Demo

Bunu sadece gerekirse yap.

1. `TRADING_ENABLED=true`
2. Trader servisini restart et.
3. Trading page -> Run Cycle Now
4. Alpaca Dashboard -> Orders

Ne diyeceksin:

> "Bu historical backtest degil. Bu bugunun paper account'una giden gercek paper order."

Dikkat:

- Market kapaliysa order `new` kalabilir.
- Pozisyona donusmesi icin fill gerekir.
- Duplicate pending order riskini known limitation olarak anlat.

---

## 8. 8 Dakikalik Sunum Scripti

### 0:00 - 0:45 Problem

> "Tek bir LLM'e 'bu hisse alinir mi?' diye sormak kontrolsuz ve denetlenmesi zor. Biz bunu uzman agentlara ayirdik: teknik, haber, risk ve fundamentals."

### 0:45 - 2:00 Analysis Architecture

> "Dort agent paralel calisiyor. Her biri kendi veri kaynagini ve tool'unu kullaniyor. Supervisor structured output ile nihai recommendation uretiyor."

### 2:00 - 2:45 Evaluation

> "Ayrica ikinci bir LLM judge var. Bu judge coherence, evidence grounding ve risk alignment puanlariyla supervisor sonucunu denetliyor."

### 2:45 - 4:00 Trading Architecture

> "Trading icin ayri bir graph kurduk. Burada trade_decision_agent portfoy durumunu, memory'yi ve varsa supervisor context'ini goruyor. Ama emir gondermek safety gate'lerden geciyor."

### 4:00 - 5:30 Backtest

> "Backtest Alpaca historical data kullanarak gecmis gunleri replay ediyor. Agent karar aninda gelecegi gormuyor. Trade'ler local simulation oldugu icin Alpaca dashboard'a dusmuyor."

### 5:30 - 6:30 Alpaca Paper Trading

> "Canli paper trading modunda ise `TRADING_ENABLED=true` olursa Alpaca paper API'ye order gonderiyoruz. Bu order'lar Alpaca dashboard'da gorunuyor."

### 6:30 - 7:30 Demo Results

> "Burada NVDA backtestinde equity curve, trade listesi, drawdown ve decision count'lari goruyoruz. `Market data: alpaca` historical verinin Alpaca'dan geldigini gosteriyor."

### 7:30 - 8:00 Conclusion

> "Projenin ana katkisi, recommendation, evaluation, trading decision ve execution'i ayri katmanlarda tutmasi. Bu hem explainability hem safety hem de test edilebilirlik sagliyor."

---

## 9. Muhtemel Sorular ve Cevaplar

### Soru: Backtestte gelecek datayi goruyor mu?

Hayir. Engine tum datayi basta cekiyor ama karar gununde agent'a sadece o gune kadar olan slice veriliyor. Gelecek barlar sadece sonraki P&L ve exit hesaplari icin kullaniliyor.

### Soru: Backtest trade'leri neden Alpaca'da gorunmuyor?

Cunku backtest local simulation. Alpaca paper trading API gecmis tarihli emir/fill yaratmaz. Alpaca Orders'da gorunen emirler sadece live/manual paper trading cycle'dan gelir.

### Soru: Supervisor agent trade emri mi veriyor?

Hayir. Supervisor analiz onerisi uretir. Trade emrini trade_decision_agent ve deterministic execution gate'ler belirler.

### Soru: Sistemde kac LLM call var?

Analysis tarafinda news sentiment, supervisor ve judge LLM kullanir. Trading tarafinda trade_decision_agent LLM kullanir. Reflection ve advisor gibi ek moduller de LLM kullanir.

### Soru: Specialist agentlar LLM mi?

Hayir, technical/risk/fundamentals deterministic tool-based agentlardir. News agent haber sentiment'i icin LLM kullanir.

### Soru: Risk kontrolleri nerede?

Trading graph ve execution agent icinde. Minimum confidence, max open positions, max position size, circuit breaker ve no-pyramiding gate'leri var.

### Soru: Neden supervisor'i backtestte direkt kullanmadiniz?

Mevcut supervisor pipeline gunumuz haber/fundamental verisini cekebilir. 2024 backtestinde bunu kullanmak future leakage riski yaratir. Dogru cozum historical/as-of analysis context uretmektir.

### Soru: Alpaca endpoint olarak hangisini kullaniyorsunuz?

Market data icin `data.alpaca.markets`; paper order icin `paper-api.alpaca.markets`. Bunlar farkli amaclara hizmet eder.

### Soru: Bu gercek para ile calisir mi?

Proje paper trading sandbox icindir. Gercek para icin ek risk kontrolleri, monitoring, compliance ve daha kapsamli test gerekir.

---

## 10. Gosterirken Dikkat Et

Sunu deme:

- "Backtest Alpaca'da trade yapiyor."
- "Supervisor direkt al-sat yapiyor."
- "Sistem kesin kar eder."
- "Gelecegi tahmin ediyor."

Bunun yerine sunu de:

- "Backtest Alpaca market data ile local simulation yapiyor."
- "Supervisor analysis recommendation uretir; trade decision agent execution kararini verir."
- "Bu karar destek ve paper trading sistemidir."
- "Future leakage'i azaltmak icin karar gununde sadece o gune kadar olan data veriliyor."

---

## 11. Teknik Dosya Referanslari

Sunumda kod gosterilecekse bu dosyalar yeterli:

- Analysis graph: `packages/agent_core/orchestrator/graph.py`
- Supervisor agent: `packages/agent_core/agents/supervisor_agent.py`
- Trading graph: `packages/trading_agent/orchestrator/trading_graph.py`
- Trade decision agent: `packages/trading_agent/agents/trade_decision_agent.py`
- Alpaca tools: `packages/trading_agent/tools/alpaca_trading.py`
- Backtest engine: `packages/trading_agent/backtest/engine.py`
- API routes: `apps/api/app/api/routes.py`, `apps/api/app/api/trader_routes.py`
- Frontend trading page: `apps/frontend/src/views/TradingView.vue`

---

## 12. Final Kapanis

Kapanis cumlesi:

> "Bu projede en onemli nokta tek bir agent'a butun sorumlulugu vermemekti. Analysis, judge, trade decision, execution ve backtest katmanlarini ayirdik. Bu ayrim sistemi daha aciklanabilir, daha guvenli ve daha kolay test edilebilir hale getirdi."
