# 🌍 Carbon Footprint Tracker

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey)](https://flask.palletsprojects.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

A web app that calculates your daily CO₂ emissions across transport, energy, food, shopping, and waste — and gives you personalised reduction recommendations benchmarked against India's per-capita average.

---

## ✨ Features

- **5 emission categories** — Transport, Energy, Food, Goods, Waste
- **India-calibrated factors** — Uses India grid electricity factor (0.708 kg CO₂e/kWh), LPG, PNG, auto rickshaw, metro
- **Real-time analytics** — Doughnut chart, category breakdown bars, annual projection
- **Personalised recommendations** — Top 5 tips ranked by your highest-emission categories
- **REST API** — `/calculate` endpoint accepts JSON, returns full breakdown
- **Zero database required** — runs locally, no signup needed

---

## 🚀 Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/carbon-footprint-tracker.git
cd carbon-footprint-tracker
pip install -r requirements.txt
python app.py
# Open http://localhost:5001
```

---

## 🔌 API

**Calculate emissions:**
```bash
curl -X POST http://localhost:5001/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "car_petrol_km": 12,
    "electricity_kwh": 5,
    "rice_kg": 0.2,
    "dairy_litre": 0.3,
    "landfill_kg": 0.2
  }'
```

**Response:**
```json
{
  "total_kg_today": 5.42,
  "annual_projection_kg": 1978.3,
  "vs_india_average_pct": 104.1,
  "trees_to_offset": 94.2,
  "by_category": {
    "transport": 2.304,
    "energy": 3.54,
    "food": 1.5,
    "goods": 0.0,
    "waste": 0.1
  },
  "recommendations": [...]
}
```

---

## 📊 Emission Factors (Sources: IPCC AR6, EPA, CEA India)

| Category | Key Factors |
|---|---|
| Transport | Petrol car: 0.192 kg/km · Metro: 0.028 kg/km · Auto: 0.108 kg/km |
| Energy | India grid electricity: 0.708 kg/kWh · LPG: 2.983 kg/kg |
| Food | Beef: 27 kg/kg · Chicken: 6.9 kg/kg · Rice: 2.7 kg/kg |
| Goods | Electronics: 300 kg/item · Clothing: 10 kg/item |

---

## 🛠️ Tech Stack
**Backend:** Python · Flask &nbsp;|&nbsp; **Frontend:** HTML · CSS · JavaScript · Chart.js


