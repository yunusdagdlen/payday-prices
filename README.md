# payday-prices

Payday uygulaması için günlük fiyat beslemesi. GitHub Actions hafta içi her gün 16:00'da (TSİ):

- **Döviz:** TCMB günlük kurları (`today.xml`) — USD, EUR, GBP, CHF alış/satış
- **Gram altın:** TCMB EVDS `TP.ALTINPIYASA.KAP02` (BİST altın kapanışı, TL/kg → TL/gram)

çekip `prices.json` dosyasını günceller. Uygulama bu dosyayı okur; EVDS anahtarı yalnızca bu reponun secret'ında durur.

Besleme adresi: `https://raw.githubusercontent.com/yunusdagdlen/payday-prices/main/prices.json`

## Kurulum

1. GitHub'da **public** bir repo aç: `payday-prices` (raw dosyanın herkese açık okunabilmesi için public olmalı; içinde gizli bilgi yok).
2. Bu klasörü o repoya gönder:
   ```bash
   cd prices-feed
   git init -b main
   git add .
   git commit -m "Fiyat beslemesi"
   git remote add origin https://github.com/<KULLANICI_ADI>/payday-prices.git
   git push -u origin main
   ```
3. Repo → **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `EVDS_API_KEY`
   - Secret: EVDS API anahtarın
4. Repo → **Settings → Actions → General → Workflow permissions** → **Read and write permissions** → Save
5. Repo → **Actions → Fiyatları güncelle → Run workflow** ile ilk çalıştırmayı elle yap; yeşil olunca `prices.json` güncellenmiş olmalı.

## Yerelde test

```bash
EVDS_API_KEY=... python3 scripts/update_prices.py
```

## Notlar

- Bir kaynak hata verirse önceki değer korunur ve hata `errors` alanına yazılır; ikisi birden başarısız olursa iş akışı kırmızı olur.
- EVDS altın verisi yaklaşık 1 hafta gecikmeli yayımlanır; `gold.gram.date` fiyatın ait olduğu günü gösterir.
- GitHub, 60 gün boyunca hiç commit olmayan repolarda zamanlanmış iş akışlarını durdurur. Bu iş akışı her gün commit attığı için normalde sorun olmaz.
