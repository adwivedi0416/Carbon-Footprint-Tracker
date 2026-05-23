"""
Carbon Footprint Tracker
========================
Flask web app that calculates daily CO2 emissions from user activities,
provides real-time analytics, and generates personalized reduction recommendations.
"""

from flask import Flask, request, jsonify, render_template_string, session
from datetime import datetime, timedelta
import json, os, uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ─────────────────────────────────────────────
# CO2 Emission Factors (kg CO2e per unit)
# Sources: IPCC AR6, Our World in Data, EPA
# ─────────────────────────────────────────────
EMISSION_FACTORS = {
    "transport": {
        "car_petrol_km":     0.192,
        "car_diesel_km":     0.171,
        "car_electric_km":   0.053,
        "bus_km":            0.089,
        "train_km":          0.041,
        "metro_km":          0.028,
        "flight_domestic_km":0.255,
        "flight_intl_km":    0.195,
        "motorcycle_km":     0.114,
        "cycling_km":        0.000,
        "walking_km":        0.000,
        "auto_rickshaw_km":  0.108,
    },
    "energy": {
        "electricity_kwh":   0.708,   # India grid average
        "lpg_kg":            2.983,
        "png_scm":           2.204,
        "coal_kg":           2.420,
    },
    "food": {
        "beef_kg":           27.0,
        "lamb_kg":           24.5,
        "chicken_kg":        6.9,
        "fish_kg":           6.1,
        "dairy_litre":       3.2,
        "eggs_dozen":        4.5,
        "rice_kg":           2.7,
        "vegetables_kg":     0.4,
        "fruits_kg":         0.5,
        "pulses_kg":         0.9,
    },
    "goods": {
        "clothing_item":     10.0,
        "electronics_item":  300.0,
        "plastic_kg":        6.0,
        "paper_kg":          1.8,
    },
    "waste": {
        "landfill_kg":       0.5,
        "recycled_kg":       0.02,
        "composted_kg":      0.01,
    }
}

CATEGORY_LABELS = {
    "transport": "🚗 Transport",
    "energy":    "⚡ Energy",
    "food":      "🍽️ Food",
    "goods":     "🛍️ Goods & Shopping",
    "waste":     "♻️ Waste"
}

RECOMMENDATIONS = {
    "transport": [
        {"tip": "Switch one car trip per week to public transport or metro.",
         "saving": "~15 kg CO₂/month"},
        {"tip": "Work from home 2 days a week if possible.",
         "saving": "~20 kg CO₂/month"},
        {"tip": "Consider an electric vehicle for your next purchase.",
         "saving": "Up to 60% reduction in transport emissions"},
        {"tip": "Carpool with colleagues for regular commutes.",
         "saving": "~10 kg CO₂/month"},
    ],
    "energy": [
        {"tip": "Set your AC to 24°C instead of 20°C.",
         "saving": "~8% electricity savings"},
        {"tip": "Switch to LED bulbs throughout your home.",
         "saving": "~5 kg CO₂/month"},
        {"tip": "Unplug devices when not in use to eliminate phantom loads.",
         "saving": "~3 kg CO₂/month"},
        {"tip": "Use a pressure cooker — it uses 70% less energy than boiling.",
         "saving": "~4 kg CO₂/month"},
    ],
    "food": [
        {"tip": "Try one plant-based meal per day.",
         "saving": "~30 kg CO₂/month"},
        {"tip": "Buy locally grown seasonal produce.",
         "saving": "~5 kg CO₂/month"},
        {"tip": "Reduce food waste — plan meals and use leftovers.",
         "saving": "~8 kg CO₂/month"},
    ],
    "goods": [
        {"tip": "Buy second-hand clothing and electronics.",
         "saving": "~50% per item"},
        {"tip": "Repair before replacing — extend product lifetimes.",
         "saving": "Variable"},
    ],
    "waste": [
        {"tip": "Start composting kitchen waste.",
         "saving": "~3 kg CO₂/month"},
        {"tip": "Segregate waste for recycling.",
         "saving": "~2 kg CO₂/month"},
    ]
}

INDIA_AVERAGE_ANNUAL_KG = 1900  # kg CO2e per capita per year


# ─────────────────────────────────────────────
# Calculation engine
# ─────────────────────────────────────────────

def calculate_emissions(activities: dict) -> dict:
    """
    Calculate CO2 emissions from a dict of {activity_key: quantity}.
    Returns totals by category and grand total.
    """
    results = {cat: 0.0 for cat in EMISSION_FACTORS}
    breakdown = {}

    for activity_key, quantity in activities.items():
        if quantity <= 0:
            continue
        for category, items in EMISSION_FACTORS.items():
            if activity_key in items:
                kg_co2 = items[activity_key] * quantity
                results[category] += kg_co2
                breakdown[activity_key] = {
                    "quantity": quantity,
                    "factor": items[activity_key],
                    "kg_co2": round(kg_co2, 3),
                    "category": category
                }
                break

    total = sum(results.values())
    annual_projection = total * 365

    # Percentile vs India average
    pct_vs_india = (annual_projection / INDIA_AVERAGE_ANNUAL_KG) * 100

    return {
        "by_category":         {k: round(v, 3) for k, v in results.items()},
        "breakdown":           breakdown,
        "total_kg_today":      round(total, 3),
        "annual_projection_kg": round(annual_projection, 1),
        "vs_india_average_pct": round(pct_vs_india, 1),
        "trees_to_offset":     round(annual_projection / 21, 1),
        "calculated_at":       datetime.now().isoformat()
    }


def get_recommendations(by_category: dict) -> list:
    """Return top recommendations based on highest emission categories."""
    sorted_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    recs = []
    for cat, val in sorted_cats:
        if val > 0 and cat in RECOMMENDATIONS:
            recs.extend(RECOMMENDATIONS[cat][:2])
        if len(recs) >= 5:
            break
    return recs[:5]


# ─────────────────────────────────────────────
# HTML Frontend
# ─────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Carbon Footprint Tracker</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
:root{--green:#16a34a;--green-light:#dcfce7;--amber:#d97706;--red:#dc2626;--bg:#f9fafb;--card:#fff;--border:#e5e7eb;--text:#111827;--muted:#6b7280}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.hero{background:linear-gradient(135deg,#052e16,#14532d);color:#fff;padding:2.5rem 1.5rem;text-align:center}
.hero h1{font-size:2rem;font-weight:700;margin-bottom:0.5rem}
.hero p{color:#86efac;font-size:1rem}
.container{max-width:960px;margin:0 auto;padding:1.5rem}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.25rem}
.card h2{font-size:0.85rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);margin-bottom:1rem}
.section-title{font-size:1.1rem;font-weight:700;color:var(--text);margin:1.5rem 0 0.75rem}
.form-group{margin-bottom:0.75rem}
label{font-size:12px;color:var(--muted);display:block;margin-bottom:3px;font-weight:500}
input[type=number]{width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:6px;font-size:13px;color:var(--text);background:#fff}
input[type=number]:focus{outline:2px solid var(--green);border-color:transparent}
.btn{display:inline-flex;align-items:center;gap:6px;background:var(--green);color:#fff;border:none;padding:12px 28px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;width:100%;justify-content:center;margin-top:0.5rem}
.btn:hover{background:#15803d}
.stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;margin-bottom:1rem}
.stat{text-align:center;padding:1rem;background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0}
.stat-val{font-size:1.6rem;font-weight:700;color:var(--green)}
.stat-label{font-size:11px;color:var(--muted);margin-top:2px}
.bar-row{display:flex;align-items:center;gap:8px;margin-bottom:0.6rem;font-size:13px}
.bar-label{width:90px;color:var(--muted);flex-shrink:0}
.bar-track{flex:1;height:8px;background:#f3f4f6;border-radius:100px;overflow:hidden}
.bar-fill{height:100%;border-radius:100px;background:var(--green);transition:width 0.4s}
.bar-val{width:60px;text-align:right;font-weight:600;font-size:12px;color:var(--text)}
.rec-item{display:flex;gap:10px;align-items:flex-start;padding:0.75rem;background:#f0fdf4;border-radius:8px;margin-bottom:0.5rem;border:1px solid #bbf7d0}
.rec-icon{font-size:1.2rem;flex-shrink:0}
.rec-text{font-size:13px;color:var(--text);line-height:1.5}
.rec-saving{font-size:11px;color:var(--green);font-weight:600;margin-top:2px}
.badge{font-size:11px;padding:2px 8px;border-radius:100px;font-weight:600}
.badge-good{background:#dcfce7;color:#15803d}
.badge-avg{background:#fef9c3;color:#a16207}
.badge-high{background:#fee2e2;color:#b91c1c}
#results{display:none}
.hidden{display:none}
@media(max-width:600px){.grid-2,.stat-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="hero">
  <h1>🌍 Carbon Footprint Tracker</h1>
  <p>Calculate your daily CO₂ emissions and get personalised reduction tips</p>
</div>

<div class="container">
  <form id="carbonForm">
    <div class="grid-2">
      <!-- Transport -->
      <div class="card">
        <h2>🚗 Transport</h2>
        <div class="form-group"><label>Petrol car (km)</label><input type="number" name="car_petrol_km" value="0" min="0" step="0.1"></div>
        <div class="form-group"><label>Diesel car (km)</label><input type="number" name="car_diesel_km" value="0" min="0" step="0.1"></div>
        <div class="form-group"><label>Electric car (km)</label><input type="number" name="car_electric_km" value="0" min="0" step="0.1"></div>
        <div class="form-group"><label>Bus (km)</label><input type="number" name="bus_km" value="0" min="0" step="0.1"></div>
        <div class="form-group"><label>Metro / Suburban train (km)</label><input type="number" name="metro_km" value="0" min="0" step="0.1"></div>
        <div class="form-group"><label>Auto rickshaw (km)</label><input type="number" name="auto_rickshaw_km" value="0" min="0" step="0.1"></div>
        <div class="form-group"><label>Motorcycle (km)</label><input type="number" name="motorcycle_km" value="0" min="0" step="0.1"></div>
        <div class="form-group"><label>Domestic flight (km)</label><input type="number" name="flight_domestic_km" value="0" min="0"></div>
      </div>

      <!-- Energy + Food -->
      <div>
        <div class="card" style="margin-bottom:1rem">
          <h2>⚡ Home Energy</h2>
          <div class="form-group"><label>Electricity (kWh)</label><input type="number" name="electricity_kwh" value="3" min="0" step="0.1"></div>
          <div class="form-group"><label>LPG (kg)</label><input type="number" name="lpg_kg" value="0" min="0" step="0.1"></div>
          <div class="form-group"><label>PNG / Natural gas (SCM)</label><input type="number" name="png_scm" value="0" min="0" step="0.1"></div>
        </div>
        <div class="card">
          <h2>🍽️ Food Consumed Today</h2>
          <div class="form-group"><label>Chicken (kg)</label><input type="number" name="chicken_kg" value="0" min="0" step="0.01"></div>
          <div class="form-group"><label>Beef / Mutton (kg)</label><input type="number" name="beef_kg" value="0" min="0" step="0.01"></div>
          <div class="form-group"><label>Fish / Seafood (kg)</label><input type="number" name="fish_kg" value="0" min="0" step="0.01"></div>
          <div class="form-group"><label>Dairy (litres)</label><input type="number" name="dairy_litre" value="0.3" min="0" step="0.1"></div>
          <div class="form-group"><label>Rice (kg)</label><input type="number" name="rice_kg" value="0.2" min="0" step="0.01"></div>
          <div class="form-group"><label>Vegetables (kg)</label><input type="number" name="vegetables_kg" value="0.3" min="0" step="0.01"></div>
        </div>
      </div>
    </div>

    <!-- Goods & Waste -->
    <div class="grid-2" style="margin-top:1rem">
      <div class="card">
        <h2>🛍️ Goods Purchased</h2>
        <div class="form-group"><label>Clothing items</label><input type="number" name="clothing_item" value="0" min="0"></div>
        <div class="form-group"><label>Electronics items</label><input type="number" name="electronics_item" value="0" min="0"></div>
        <div class="form-group"><label>Plastic waste (kg)</label><input type="number" name="plastic_kg" value="0" min="0" step="0.1"></div>
      </div>
      <div class="card">
        <h2>♻️ Waste Generated</h2>
        <div class="form-group"><label>Landfill waste (kg)</label><input type="number" name="landfill_kg" value="0.2" min="0" step="0.1"></div>
        <div class="form-group"><label>Recycled waste (kg)</label><input type="number" name="recycled_kg" value="0.1" min="0" step="0.1"></div>
        <div class="form-group"><label>Composted waste (kg)</label><input type="number" name="composted_kg" value="0" min="0" step="0.1"></div>
      </div>
    </div>

    <button class="btn" type="submit">🌍 Calculate My Footprint →</button>
  </form>

  <!-- Results -->
  <div id="results">
    <div class="section-title">📊 Your Results</div>
    <div class="stat-grid">
      <div class="stat">
        <div class="stat-val" id="total-today">—</div>
        <div class="stat-label">kg CO₂e today</div>
      </div>
      <div class="stat">
        <div class="stat-val" id="annual-proj">—</div>
        <div class="stat-label">kg CO₂e / year (projected)</div>
      </div>
      <div class="stat">
        <div class="stat-val" id="trees">—</div>
        <div class="stat-label">trees to offset annually</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <h2>Breakdown by Category</h2>
        <div id="bars"></div>
      </div>
      <div class="card">
        <h2>Distribution</h2>
        <canvas id="pieChart" height="200"></canvas>
      </div>
    </div>

    <div class="card" style="margin-top:1rem">
      <h2>vs. India Average</h2>
      <div id="compare-text" style="font-size:14px; line-height:1.7; color:var(--muted)"></div>
    </div>

    <div class="section-title">💡 Personalised Recommendations</div>
    <div id="recs"></div>
  </div>
</div>

<script>
let pieChart = null;

document.getElementById('carbonForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {};
  fd.forEach((v, k) => { if (parseFloat(v) > 0) body[k] = parseFloat(v); });

  const res = await fetch('/calculate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  const data = await res.json();
  renderResults(data);
});

function renderResults(data) {
  document.getElementById('results').style.display = 'block';
  document.getElementById('total-today').textContent = data.total_kg_today.toFixed(2);
  document.getElementById('annual-proj').textContent = data.annual_projection_kg.toLocaleString();
  document.getElementById('trees').textContent = data.trees_to_offset;

  // Compare text
  const pct = data.vs_india_average_pct;
  const badge = pct < 80 ? 'badge-good' : pct < 120 ? 'badge-avg' : 'badge-high';
  const label = pct < 80 ? 'Below average 🎉' : pct < 120 ? 'Near average' : 'Above average ⚠️';
  document.getElementById('compare-text').innerHTML =
    `Your projected annual footprint is <strong>${data.annual_projection_kg.toLocaleString()} kg CO₂e</strong>, 
     which is <strong>${pct}%</strong> of India's per-capita average (1,900 kg).
     <span class="badge ${badge}" style="margin-left:6px">${label}</span>
     <br><br>Global 1.5°C target: <strong>~2,300 kg per person per year</strong> by 2030.`;

  // Bars
  const cats = data.by_category;
  const maxVal = Math.max(...Object.values(cats), 0.01);
  const catIcons = {transport:'🚗',energy:'⚡',food:'🍽️',goods:'🛍️',waste:'♻️'};
  document.getElementById('bars').innerHTML = Object.entries(cats)
    .sort(([,a],[,b]) => b - a)
    .map(([cat, val]) => `
      <div class="bar-row">
        <span class="bar-label">${catIcons[cat]||''} ${cat}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${(val/maxVal*100).toFixed(1)}%"></div></div>
        <span class="bar-val">${val.toFixed(2)}</span>
      </div>`).join('');

  // Pie chart
  const nonZero = Object.entries(cats).filter(([,v]) => v > 0);
  const colors = ['#16a34a','#3b82f6','#f59e0b','#ef4444','#8b5cf6'];
  if (pieChart) pieChart.destroy();
  pieChart = new Chart(document.getElementById('pieChart'), {
    type: 'doughnut',
    data: {
      labels: nonZero.map(([k]) => k),
      datasets: [{
        data: nonZero.map(([,v]) => v),
        backgroundColor: colors.slice(0, nonZero.length),
        borderWidth: 2, borderColor: '#fff'
      }]
    },
    options: {
      plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } },
      cutout: '60%'
    }
  });

  // Recommendations
  document.getElementById('recs').innerHTML = (data.recommendations || [])
    .map(r => `
      <div class="rec-item">
        <div class="rec-icon">💡</div>
        <div>
          <div class="rec-text">${r.tip}</div>
          <div class="rec-saving">Potential saving: ${r.saving}</div>
        </div>
      </div>`).join('');

  document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}
</script>
</body>
</html>"""


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return HTML


@app.route("/calculate", methods=["POST"])
def calculate():
    activities = request.get_json()
    if not activities:
        return jsonify({"error": "No data provided"}), 400
    result = calculate_emissions(activities)
    result["recommendations"] = get_recommendations(result["by_category"])
    return jsonify(result)


@app.route("/factors")
def factors():
    """Return all emission factors — useful for frontend population."""
    return jsonify(EMISSION_FACTORS)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "1.0.0"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
