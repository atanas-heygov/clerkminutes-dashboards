import csv
import json
from datetime import datetime, date
from collections import defaultdict

CSV_PATH = '/Users/User/Downloads/HeyGov miniCRM (ARR) - ClerkMinutes Customers (2).csv'
OUTPUT_PATH = '/Users/User/Desktop/Claude Code Projects/heygov-dashboard/dashboard.html'
GOAL = 1_000_000
TODAY = date(2026, 4, 27)
HEYGOV_ARR = 248_505  # from spreadsheet row 470, separate product line


def parse_dollar(s):
    if not s:
        return 0
    s = s.strip().replace('$', '').replace(',', '')
    try:
        return float(s)
    except Exception:
        return 0


def parse_date(s):
    if not s or not s.strip():
        return None
    s = s.strip()
    try:
        return datetime.strptime(s, '%m/%d/%Y').date()
    except Exception:
        pass
    try:
        return datetime.strptime(s, '%-m/%-d/%Y').date()
    except Exception:
        return None


customers = []
with open(CSV_PATH, newline='', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    next(reader)  # header
    for row in reader:
        if len(row) < 6:
            continue
        name = row[1].strip() if len(row) > 1 else ''
        if not name or name.startswith('#') or 'are with CivicPlus' in name:
            continue
        annual_str = row[5].strip() if len(row) > 5 else ''
        if annual_str.startswith('#'):
            continue
        annual = parse_dollar(annual_str)
        if annual <= 0:
            continue
        date_val = parse_date(row[2]) if len(row) > 2 else None
        if not date_val:
            continue
        plan = row[3].strip() if len(row) > 3 else 'Unknown'
        state = row[6].strip() if len(row) > 6 else ''
        billing = row[13].strip() if len(row) > 13 else ''
        customers.append({
            'name': name,
            'date': date_val,
            'plan': plan,
            'annual': annual,
            'state': state,
            'billing': billing,
        })

customers.sort(key=lambda c: c['date'])

# ── Key metrics ─────────────────────────────────────────────────────────────
cm_arr = sum(c['annual'] for c in customers)
total_arr = cm_arr + HEYGOV_ARR
total_customers = len(customers)
avg_arr = cm_arr / total_customers if total_customers else 0
gap_to_goal = max(0, GOAL - total_arr)
progress_pct = min(100, total_arr / GOAL * 100)

# ── Monthly new ARR ──────────────────────────────────────────────────────────
monthly_new_arr = defaultdict(float)
monthly_new_customers = defaultdict(int)
cumulative_by_month = {}

running = 0
months_seen = set()
for c in customers:
    ym = c['date'].strftime('%Y-%m')
    monthly_new_arr[ym] += c['annual']
    monthly_new_customers[ym] += 1

# Build sorted month list from first customer to today
from_date = customers[0]['date'].replace(day=1)
to_date = TODAY.replace(day=1)

all_months = []
cur = from_date
while cur <= to_date:
    all_months.append(cur.strftime('%Y-%m'))
    if cur.month == 12:
        cur = cur.replace(year=cur.year + 1, month=1)
    else:
        cur = cur.replace(month=cur.month + 1)

cumulative = 0
cumulative_arr_series = []
new_arr_series = []
month_labels = []
for ym in all_months:
    new = monthly_new_arr.get(ym, 0)
    cumulative += new
    label = datetime.strptime(ym, '%Y-%m').strftime('%b %y')
    month_labels.append(label)
    cumulative_arr_series.append(round(cumulative, 2))
    new_arr_series.append(round(new, 2))

# ── Projection (last 90 days rolling avg new ARR / month) ───────────────────
recent_months = [ym for ym in all_months if ym >= '2025-10']
recent_new = sum(monthly_new_arr.get(ym, 0) for ym in recent_months)
months_count = len(recent_months) if recent_months else 1
avg_monthly_new = recent_new / months_count

if avg_monthly_new > 0 and gap_to_goal > 0:
    months_to_goal = gap_to_goal / avg_monthly_new
    # rough projection date
    from calendar import monthrange
    proj_month = TODAY.month + round(months_to_goal)
    proj_year = TODAY.year + (proj_month - 1) // 12
    proj_month = ((proj_month - 1) % 12) + 1
    proj_date = f"{datetime(proj_year, proj_month, 1).strftime('%B %Y')}"
else:
    proj_date = "Already achieved!" if gap_to_goal == 0 else "N/A"
    months_to_goal = 0

# ── By plan ──────────────────────────────────────────────────────────────────
plan_arr = defaultdict(float)
plan_count = defaultdict(int)
for c in customers:
    p = c['plan'] if c['plan'] else 'Unknown'
    plan_arr[p] += c['annual']
    plan_count[p] += 1

plan_order = sorted(plan_arr.keys(), key=lambda p: -plan_arr[p])

# ── By state (top 12) ────────────────────────────────────────────────────────
state_arr = defaultdict(float)
state_count = defaultdict(int)
for c in customers:
    if c['state'] and c['state'] not in ('N/A', 'n/a', '??', ''):
        state_arr[c['state']] += c['annual']
        state_count[c['state']] += 1

top_states = sorted(state_arr.keys(), key=lambda s: -state_arr[s])[:12]

# ── Recent customers (last 10) ───────────────────────────────────────────────
recent_customers = customers[-10:][::-1]

# ── Build JSON blobs for JS ──────────────────────────────────────────────────
chart_data = {
    'monthLabels': month_labels,
    'cumulativeArr': cumulative_arr_series,
    'newArr': new_arr_series,
    'planLabels': plan_order,
    'planArr': [round(plan_arr[p], 2) for p in plan_order],
    'planCounts': [plan_count[p] for p in plan_order],
    'stateLabels': top_states,
    'stateArr': [round(state_arr[s], 2) for s in top_states],
    'stateCounts': [state_count[s] for s in top_states],
    # Product split
    'productLabels': ['ClerkMinutes', 'HeyGov'],
    'productArr': [round(cm_arr, 2), round(HEYGOV_ARR, 2)],
}

summary = {
    'totalArr': round(total_arr, 2),
    'cmArr': round(cm_arr, 2),
    'hgArr': round(HEYGOV_ARR, 2),
    'totalCustomers': total_customers,
    'avgArr': round(avg_arr, 2),
    'gapToGoal': round(gap_to_goal, 2),
    'progressPct': round(progress_pct, 1),
    'avgMonthlyNew': round(avg_monthly_new, 2),
    'monthsToGoal': round(months_to_goal, 1),
    'projDate': proj_date,
    'recentCustomers': [
        {'name': c['name'], 'date': c['date'].strftime('%b %d, %Y'),
         'plan': c['plan'], 'annual': round(c['annual'], 2), 'state': c['state']}
        for c in recent_customers
    ],
}

# ── HTML ─────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>HeyGov ARR Dashboard — Road to $1M</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3a;
    --accent: #6366f1;
    --accent2: #22d3ee;
    --green: #10b981;
    --amber: #f59e0b;
    --red: #ef4444;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --goal: 1000000;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height: 100vh; }}

  header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 18px 32px; display: flex; align-items: center; justify-content: space-between; }}
  header h1 {{ font-size: 1.15rem; font-weight: 700; letter-spacing: -.3px; }}
  header h1 span {{ color: var(--accent); }}
  .pill {{ display: inline-flex; align-items: center; gap: 6px; font-size: .72rem; font-weight: 700; padding: 3px 10px; border-radius: 999px; }}
  .pill-cm {{ background: rgba(99,102,241,.15); color: #818cf8; }}
  .pill-hg {{ background: rgba(34,211,238,.15); color: #22d3ee; }}
  .split-row {{ display: flex; gap: 10px; margin-top: 10px; }}
  .badge {{ background: var(--accent); color: #fff; font-size: .7rem; font-weight: 700; padding: 3px 10px; border-radius: 999px; letter-spacing: .5px; }}
  .updated {{ font-size: .75rem; color: var(--muted); }}

  main {{ max-width: 1280px; margin: 0 auto; padding: 28px 24px 60px; display: flex; flex-direction: column; gap: 28px; }}

  /* ── Hero cards ── */
  .hero-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px; }}
  .card.wide {{ grid-column: span 2; }}
  .card label {{ font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); display: block; margin-bottom: 6px; }}
  .card .val {{ font-size: 2.1rem; font-weight: 800; letter-spacing: -1px; line-height: 1; }}
  .card .sub {{ font-size: .78rem; color: var(--muted); margin-top: 6px; }}
  .green {{ color: var(--green); }}
  .amber {{ color: var(--amber); }}
  .accent {{ color: var(--accent); }}
  .accent2 {{ color: var(--accent2); }}

  /* ── Progress bar ── */
  .progress-wrap {{ margin-top: 16px; }}
  .progress-bar-bg {{ background: var(--border); border-radius: 999px; height: 10px; overflow: hidden; }}
  .progress-bar-fill {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--accent) 0%, var(--accent2) 100%); transition: width .6s ease; }}
  .progress-labels {{ display: flex; justify-content: space-between; font-size: .72rem; color: var(--muted); margin-top: 6px; }}

  /* ── Two-col chart layout ── */
  .chart-grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }}
  .chart-grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }}
  .chart-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px; }}
  .chart-card h2 {{ font-size: .85rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .8px; margin-bottom: 18px; }}
  .chart-wrap {{ position: relative; height: 220px; }}

  /* ── Projection panel ── */
  .projection {{ display: flex; flex-direction: column; gap: 14px; height: 100%; justify-content: center; }}
  .proj-row {{ display: flex; flex-direction: column; gap: 3px; background: var(--bg); border-radius: 10px; padding: 14px 16px; }}
  .proj-row .proj-label {{ font-size: .68rem; text-transform: uppercase; letter-spacing: .8px; color: var(--muted); font-weight: 700; }}
  .proj-row .proj-val {{ font-size: 1.4rem; font-weight: 800; letter-spacing: -.5px; }}

  /* ── Recent customers table ── */
  .table-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px; }}
  .table-card h2 {{ font-size: .85rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .8px; margin-bottom: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .83rem; }}
  thead th {{ text-align: left; color: var(--muted); font-size: .7rem; text-transform: uppercase; letter-spacing: .8px; padding: 0 12px 10px 0; border-bottom: 1px solid var(--border); }}
  tbody tr {{ border-bottom: 1px solid var(--border); }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody td {{ padding: 10px 12px 10px 0; color: var(--text); }}
  .plan-badge {{ display: inline-block; font-size: .65rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; letter-spacing: .5px; text-transform: uppercase; }}
  .plan-starter {{ background: #1e3a5f; color: #60a5fa; }}
  .plan-growth {{ background: #14532d; color: #4ade80; }}
  .plan-custom {{ background: #3b1764; color: #c084fc; }}
  .plan-unknown {{ background: #292524; color: #a8a29e; }}
  .arr-cell {{ font-weight: 700; color: var(--green); }}
</style>
</head>
<body>
<header>
  <h1>HeyGov &mdash; <span>Road to $1M ARR</span></h1>
  <div style="display:flex;align-items:center;gap:12px;">
    <span class="badge">LIVE DATA</span>
    <span class="updated">Updated {TODAY.strftime('%B %d, %Y')}</span>
  </div>
</header>

<main>

  <!-- Hero row -->
  <div class="hero-grid">
    <div class="card">
      <label>Total ARR (Combined)</label>
      <div class="val green" id="totalArr"></div>
      <div class="split-row">
        <span class="pill pill-cm" id="cmPill"></span>
        <span class="pill pill-hg" id="hgPill"></span>
      </div>
    </div>
    <div class="card">
      <label>Gap to $1M</label>
      <div class="val amber" id="gapArr"></div>
      <div class="sub" id="gapSub"></div>
    </div>
    <div class="card">
      <label>ClerkMinutes Customers</label>
      <div class="val accent" id="custCount"></div>
      <div class="sub" id="custSub"></div>
    </div>
    <div class="card">
      <label>Avg ARR / CM Customer</label>
      <div class="val accent2" id="avgArr"></div>
      <div class="sub" id="avgSub"></div>
    </div>

    <!-- Progress bar spans full width -->
    <div class="card" style="grid-column: span 4;">
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px;">
        <label style="margin:0;">Combined Progress to $1M ARR Goal</label>
        <span id="pctLabel" style="font-size:1.1rem;font-weight:800;color:var(--accent);"></span>
      </div>
      <div class="progress-bar-bg" style="height:14px;">
        <div style="height:100%;display:flex;border-radius:999px;overflow:hidden;">
          <div id="barCM" style="background:#6366f1;transition:width .6s ease;"></div>
          <div id="barHG" style="background:#22d3ee;transition:width .6s ease;"></div>
        </div>
      </div>
      <div style="display:flex;gap:16px;margin-top:8px;font-size:.72rem;color:var(--muted);">
        <span style="display:flex;align-items:center;gap:5px;"><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#6366f1;"></span>ClerkMinutes</span>
        <span style="display:flex;align-items:center;gap:5px;"><span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:#22d3ee;"></span>HeyGov</span>
        <span style="margin-left:auto;">$1M 🎯</span>
      </div>
    </div>
  </div>

  <!-- Cumulative ARR + Projection -->
  <div class="chart-grid">
    <div class="chart-card">
      <h2>Cumulative ARR Growth</h2>
      <div class="chart-wrap">
        <canvas id="cumulativeChart"></canvas>
      </div>
    </div>
    <div class="chart-card">
      <h2>Projections</h2>
      <div class="projection" id="projPanel"></div>
    </div>
  </div>

  <!-- Monthly new ARR + Plans + States -->
  <div class="chart-grid-3">
    <div class="chart-card">
      <h2>Monthly New ARR (ClerkMinutes)</h2>
      <div class="chart-wrap">
        <canvas id="monthlyChart"></canvas>
      </div>
    </div>
    <div class="chart-card">
      <h2>ARR by Plan (ClerkMinutes)</h2>
      <div class="chart-wrap">
        <canvas id="planChart"></canvas>
      </div>
    </div>
    <div class="chart-card">
      <h2>ARR by State — Top 12 (ClerkMinutes)</h2>
      <div class="chart-wrap">
        <canvas id="stateChart"></canvas>
      </div>
    </div>
  </div>

  <!-- Product split + cumulative with both streams -->
  <div class="chart-grid">
    <div class="chart-card">
      <h2>ARR by Product</h2>
      <div class="chart-wrap" style="height:200px;">
        <canvas id="productChart"></canvas>
      </div>
    </div>
    <div class="chart-card" style="display:flex;flex-direction:column;gap:12px;justify-content:center;">
      <h2>Revenue Breakdown</h2>
      <div id="productBreakdown" style="display:flex;flex-direction:column;gap:10px;"></div>
    </div>
  </div>

  <!-- Recent customers -->
  <div class="table-card">
    <h2>Most Recent Customers</h2>
    <table>
      <thead>
        <tr>
          <th>Municipality</th>
          <th>State</th>
          <th>Plan</th>
          <th>Signed</th>
          <th>Annual ARR</th>
        </tr>
      </thead>
      <tbody id="recentTable"></tbody>
    </table>
  </div>

</main>

<script>
const S = {json.dumps(chart_data)}; // chart data
const M = {json.dumps(summary)};   // summary metrics

// ── Helpers ────────────────────────────────────────────────────────────────
const fmt = n => '$' + n.toLocaleString('en-US', {{minimumFractionDigits: 0, maximumFractionDigits: 0}});
const fmtK = n => n >= 1000 ? '$' + (n/1000).toFixed(1).replace(/\.0$/,'') + 'K' : fmt(n);

// ── Hero cards ────────────────────────────────────────────────────────────
document.getElementById('totalArr').textContent = fmt(M.totalArr);
document.getElementById('cmPill').textContent = 'CM ' + fmt(M.cmArr);
document.getElementById('hgPill').textContent = 'HG ' + fmt(M.hgArr);
document.getElementById('gapArr').textContent = fmt(M.gapToGoal);
document.getElementById('gapSub').textContent = M.progressPct + '% of $1M reached';
document.getElementById('custCount').textContent = M.totalCustomers.toLocaleString();
document.getElementById('custSub').textContent = 'paying ClerkMinutes customers';
document.getElementById('avgArr').textContent = fmt(M.avgArr);
document.getElementById('avgSub').textContent = 'avg annual contract value';
document.getElementById('pctLabel').textContent = M.progressPct + '%';
// Stacked progress bar — CM then HG proportions of goal
const cmPct = Math.min(100, M.cmArr / 1000000 * 100);
const hgPct = Math.min(100 - cmPct, M.hgArr / 1000000 * 100);
document.getElementById('barCM').style.width = cmPct + '%';
document.getElementById('barHG').style.width = hgPct + '%';

// ── Projection panel ──────────────────────────────────────────────────────
const proj = document.getElementById('projPanel');
const projRows = [
  ['Avg Monthly New ARR', fmt(M.avgMonthlyNew), 'var(--green)', '(6-month trailing avg)'],
  ['Months to $1M', M.monthsToGoal.toFixed(1) + ' months', 'var(--amber)', 'at current growth rate'],
  ['Projected Hit Date', M.projDate, 'var(--accent)', 'estimated $1M milestone'],
  ['Customers Needed', Math.ceil(M.gapToGoal / M.avgArr) + ' more', 'var(--accent2)', 'at avg contract value'],
];
projRows.forEach(([label, val, color, note]) => {{
  proj.innerHTML += `<div class="proj-row">
    <span class="proj-label">${{label}}</span>
    <span class="proj-val" style="color:${{color}}">${{val}}</span>
    <span style="font-size:.7rem;color:var(--muted)">${{note}}</span>
  </div>`;
}});

// ── Chart defaults ────────────────────────────────────────────────────────
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#2a2d3a';
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

const tooltipPlugin = {{
  callbacks: {{
    label: ctx => ' ' + fmt(ctx.parsed.y ?? ctx.parsed)
  }}
}};

// ── Cumulative ARR chart ──────────────────────────────────────────────────
new Chart(document.getElementById('cumulativeChart'), {{
  type: 'line',
  data: {{
    labels: S.monthLabels,
    datasets: [{{
      label: 'Cumulative ARR',
      data: S.cumulativeArr,
      borderColor: '#6366f1',
      backgroundColor: 'rgba(99,102,241,.12)',
      fill: true,
      tension: .35,
      pointRadius: 0,
      borderWidth: 2.5,
    }}, {{
      label: '$1M Goal',
      data: Array(S.monthLabels.length).fill(1000000),
      borderColor: '#ef4444',
      borderDash: [6, 4],
      borderWidth: 1.5,
      pointRadius: 0,
      fill: false,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{
      legend: {{ position: 'top', labels: {{ boxWidth: 12, padding: 16 }} }},
      tooltip: tooltipPlugin
    }},
    scales: {{
      y: {{
        ticks: {{ callback: v => fmtK(v) }},
        grid: {{ color: '#1e2130' }},
      }},
      x: {{
        ticks: {{ maxTicksLimit: 12 }},
        grid: {{ display: false }},
      }}
    }}
  }}
}});

// ── Monthly new ARR chart ─────────────────────────────────────────────────
new Chart(document.getElementById('monthlyChart'), {{
  type: 'bar',
  data: {{
    labels: S.monthLabels,
    datasets: [{{
      label: 'New ARR',
      data: S.newArr,
      backgroundColor: 'rgba(34,211,238,.7)',
      borderRadius: 4,
      borderSkipped: false,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: tooltipPlugin
    }},
    scales: {{
      y: {{
        ticks: {{ callback: v => fmtK(v) }},
        grid: {{ color: '#1e2130' }},
      }},
      x: {{
        ticks: {{ maxTicksLimit: 10 }},
        grid: {{ display: false }},
      }}
    }}
  }}
}});

// ── Plan chart ────────────────────────────────────────────────────────────
new Chart(document.getElementById('planChart'), {{
  type: 'doughnut',
  data: {{
    labels: S.planLabels,
    datasets: [{{
      data: S.planArr,
      backgroundColor: ['#6366f1','#10b981','#f59e0b','#ef4444','#94a3b8'],
      borderWidth: 0,
      hoverOffset: 6,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    cutout: '62%',
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 12 }} }},
      tooltip: {{
        callbacks: {{
          label: ctx => ` ${{ctx.label}}: ${{fmt(ctx.parsed)}} (${{S.planCounts[ctx.dataIndex]}} customers)`
        }}
      }}
    }}
  }}
}});

// ── State chart ───────────────────────────────────────────────────────────
new Chart(document.getElementById('stateChart'), {{
  type: 'bar',
  data: {{
    labels: S.stateLabels,
    datasets: [{{
      label: 'ARR',
      data: S.stateArr,
      backgroundColor: 'rgba(99,102,241,.7)',
      borderRadius: 4,
      borderSkipped: false,
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: ctx => ` ${{fmt(ctx.parsed.x)}} (${{S.stateCounts[ctx.dataIndex]}} customers)`
        }}
      }}
    }},
    scales: {{
      x: {{
        ticks: {{ callback: v => fmtK(v) }},
        grid: {{ color: '#1e2130' }},
      }},
      y: {{ grid: {{ display: false }} }}
    }}
  }}
}});

// ── Product split doughnut ────────────────────────────────────────────────
new Chart(document.getElementById('productChart'), {{
  type: 'doughnut',
  data: {{
    labels: S.productLabels,
    datasets: [{{
      data: S.productArr,
      backgroundColor: ['#6366f1', '#22d3ee'],
      borderWidth: 0,
      hoverOffset: 6,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    cutout: '65%',
    plugins: {{
      legend: {{ position: 'right', labels: {{ boxWidth: 14, padding: 16 }} }},
      tooltip: {{ callbacks: {{ label: ctx => ` ${{ctx.label}}: ${{fmt(ctx.parsed)}}` }} }}
    }}
  }}
}});

// ── Product breakdown panel ───────────────────────────────────────────────
const breakdown = document.getElementById('productBreakdown');
const products = [
  {{ label: 'ClerkMinutes', arr: M.cmArr, color: '#6366f1', note: M.totalCustomers + ' customers' }},
  {{ label: 'HeyGov', arr: M.hgArr, color: '#22d3ee', note: 'Platform ARR' }},
  {{ label: 'Combined Total', arr: M.totalArr, color: '#10b981', note: M.progressPct + '% of $1M goal', bold: true }},
];
products.forEach(p => {{
  breakdown.innerHTML += `<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px;background:var(--bg);border-radius:10px;${{p.bold ? 'border:1px solid #10b981;' : ''}}">
    <div>
      <div style="font-size:.72rem;font-weight:700;color:${{p.color}};text-transform:uppercase;letter-spacing:.5px">${{p.label}}</div>
      <div style="font-size:.7rem;color:var(--muted);margin-top:2px">${{p.note}}</div>
    </div>
    <div style="font-size:1.3rem;font-weight:800;color:${{p.color}}">${{fmt(p.arr)}}</div>
  </div>`;
}});

// ── Recent customers table ────────────────────────────────────────────────
const tbody = document.getElementById('recentTable');
M.recentCustomers.forEach(c => {{
  const planClass = {{
    'Starter': 'plan-starter',
    'Growth': 'plan-growth',
    'Custom': 'plan-custom',
  }}[c.plan] ?? 'plan-unknown';
  tbody.innerHTML += `<tr>
    <td>${{c.name}}</td>
    <td>${{c.state || '—'}}</td>
    <td><span class="plan-badge ${{planClass}}">${{c.plan}}</span></td>
    <td>${{c.date}}</td>
    <td class="arr-cell">${{fmt(c.annual)}}</td>
  </tr>`;
}});
</script>
</body>
</html>
"""

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Dashboard generated: {OUTPUT_PATH}")
print(f"\nKey metrics:")
print(f"  Total ARR:        ${total_arr:,.0f}")
print(f"  Total customers:  {total_customers}")
print(f"  Gap to $1M:       ${gap_to_goal:,.0f}")
print(f"  Progress:         {progress_pct:.1f}%")
print(f"  Avg monthly new:  ${avg_monthly_new:,.0f}")
print(f"  Projected date:   {proj_date}")
