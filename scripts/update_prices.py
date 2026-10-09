#!/usr/bin/env python3
"""Payday fiyat beslemesi: TCMB günlük kurları + EVDS gram altın → prices.json

Günde bir kez GitHub Actions tarafından çalıştırılır. Bir kaynak hata verirse
o kaynağın önceki değeri korunur, böylece uygulama her zaman en son bilinen fiyatı görür.

Ortam değişkenleri:
  EVDS_API_KEY  EVDS API anahtarı (repo secret)
"""
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "prices.json")
CURRENCIES = ["USD", "EUR", "GBP", "CHF"]
GOLD_SERIES = "TP.ALTINPIYASA.KAP02"  # BİST altın kapanış, TL/kg, iş günü
EVDS_BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
USER_AGENT = "PaydayPriceFeed/1.0"


def fetch(url, headers=None):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def fetch_tcmb():
    root = ET.fromstring(fetch("https://www.tcmb.gov.tr/kurlar/today.xml"))
    bulletin_date = datetime.strptime(root.attrib["Tarih"], "%d.%m.%Y").date().isoformat()
    rates = {}
    for currency in root.findall("Currency"):
        code = currency.attrib.get("Kod")
        if code not in CURRENCIES:
            continue
        unit = float(currency.findtext("Unit") or 1)
        buying = float(currency.findtext("ForexBuying")) / unit
        selling = float(currency.findtext("ForexSelling")) / unit
        rates[code] = {"buying": round(buying, 4), "selling": round(selling, 4), "date": bulletin_date}
    missing = set(CURRENCIES) - rates.keys()
    if missing:
        raise RuntimeError(f"TCMB bülteninde eksik kur: {sorted(missing)}")
    return rates


def fetch_gold():
    key = os.environ.get("EVDS_API_KEY")
    if not key:
        raise RuntimeError("EVDS_API_KEY tanımlı değil")
    end = date.today()
    start = end - timedelta(days=30)  # EVDS altın verisi ~1 hafta gecikmeli
    path = f"series={GOLD_SERIES}&startDate={start:%d-%m-%Y}&endDate={end:%d-%m-%Y}&type=json"
    data = json.loads(fetch(f"{EVDS_BASE}/{path}", headers={"key": key}))
    field = GOLD_SERIES.replace(".", "_")
    for item in reversed(data.get("items", [])):
        value = item.get(field)
        if value:
            per_kg = float(value)
            day = datetime.strptime(item["Tarih"], "%d-%m-%Y").date().isoformat()
            return {"price": round(per_kg / 1000, 2), "date": day, "series": GOLD_SERIES, "unit": "TRY/gram"}
    raise RuntimeError(f"EVDS {GOLD_SERIES} için son 30 günde veri yok")


def main():
    try:
        with open(OUTPUT, encoding="utf-8") as f:
            previous = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        previous = {}

    result = {
        "currencies": previous.get("currencies", {}),
        "gold": previous.get("gold", {}),
        "errors": {},
    }
    failed = 0

    try:
        result["currencies"] = fetch_tcmb()
    except Exception as error:  # noqa: BLE001 - kaynak hatası beslemeyi durdurmamalı
        result["errors"]["currencies"] = str(error)
        failed += 1

    try:
        result["gold"] = {"gram": fetch_gold()}
    except Exception as error:  # noqa: BLE001
        result["errors"]["gold"] = str(error)
        failed += 1

    if not result["errors"]:
        del result["errors"]
    result["updatedAt"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    result["source"] = "TCMB günlük kurlar (döviz alış/satış) · TCMB EVDS BİST altın kapanış"

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    # İki kaynak da başarısızsa iş akışı kırmızı görünsün.
    return 1 if failed == 2 else 0


if __name__ == "__main__":
    sys.exit(main())
