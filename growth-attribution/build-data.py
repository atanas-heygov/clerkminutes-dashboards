#!/usr/bin/env python3
"""
Growth Attribution data builder for ClerkMinutes.

Reads the miniCRM "ClerkMinutes Customers" CSV export and classifies every WON
(paid) customer into a Foundational Channel and, where detectable, a Growth Lever
(campaign). Emits compact JSON that the dashboard (index.html) consumes.

Monthly refresh:
    python3 build-data.py "/path/to/HeyGov miniCRM (ARR) - ClerkMinutes Customers (NN).csv"
Then copy the printed JSON between the DATA markers in index.html, OR run with
--inject to rewrite index.html in place.

Attribution lives in the free-text "Notes / Lead Source" column, which encodes a
[CHANNEL][MMYY][campaign] code (e.g. PT0525SwitchGO = Postcard, May 2025, SwitchGO).
"""
import csv, re, json, sys, collections

DEFAULT_CSV = "/Users/User/Downloads/HeyGov miniCRM (ARR) - ClerkMinutes Customers (23).csv"

# ---- Channel taxonomy -------------------------------------------------------
# type: "foundational" (channel-level, ongoing) or "lever" rolls up under a channel.
# Each customer gets a foundational `channel` and an optional `lever` (campaign).
def money(s):
    s = re.sub(r'[^0-9.]', '', s or '')
    return float(s) if s else 0.0

def parse_month(s):
    m = re.match(r'\s*(\d{1,2})/(\d{1,2})/(\d{2,4})', s or '')
    if not m:
        return None
    mo, _, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    if not (1 <= mo <= 12):
        return None
    return f"{y}-{mo:02d}"

def code_month(mmyy):
    # codes are MMYY -> YYYY-MM
    mo, yy = int(mmyy[:2]), int(mmyy[2:])
    if not (1 <= mo <= 12):
        return None
    return f"20{yy:02d}-{mo:02d}"

# Campaign-Postcard lever detection from suffix / free text
LEVER_PATTERNS = [
    (r'coast[\s-]*to[\s-]*coast', 'Coast-to-Coast'),
    (r'land\s*grab',             'Land Grab'),
    (r'evolution',               'Evolution'),
    (r'pc\s*exclusive|30[\s-]*day\s*(postcard\s*)?trial|postcard\s*experiment', '30-day Postcard Experiment'),
    (r'win[\s-]*back',           'Win-Back'),
    (r'switchgo',                'SwitchGO'),
    (r'taxproperty',             'TaxProperty'),
    (r'advantage',               'Advantage'),
    (r'statewide|state[\s_-]*(mn|ny|fl|mi|specific)|cmstate', 'State-Specific'),
]

def detect_lever(text):
    t = text.lower()
    for pat, name in LEVER_PATTERNS:
        if re.search(pat, t):
            return name
    return None

# Channel constants: (full name, short code used by the dashboard color map)
REFERRAL_PC = ('Referral Postcard', 'RefPostcard')
CAMPAIGN_PC = ('Campaign Postcard', 'CampPostcard')
GOOGLE      = ('Google Ads', 'GoogleAds')
YOUTUBE     = ('YouTube Commercial', 'YouTube')
EVENTS      = ('Conferences & Events', 'Events')
NMMD        = ('Multi-channel (NMMD)', 'NMMD')
OUTBOUND    = ('Sales Outbound', 'Outbound')
TOWNWEB     = ('Partner — Town Web', 'TownWeb')
HEYGOV      = ('Partner — HeyGov', 'HeyGov')
REFERRAL    = ('Referral', 'Referral')
UNATTR      = ('Unattributed', 'Unattributed')

def is_referral_pc(text):
    """The HeyGov referral-postcard program: (HG_CM) coded rows + 'ClerkMinutes Trial Started'."""
    t = text.lower()
    return 'hg_cm' in t or '(hg' in t or 'trial started' in t

def classify(note):
    """Return (channel, channel_short, lever, campaign_month) for a Notes string."""
    n = (note or '').strip()
    low = n.lower()

    # 0) Unattributed placeholders (incl. bare municipality names with no source signal) handled at the end.
    if not n or low in ('??', '?', 'none', 'n/a', 'na', 'duplicate'):
        return (*UNATTR, None, None)

    # 1) Multi-channel NMMD (NMMD + Lightning Strike are the same campaign) — wins over everything.
    if re.search(r'\bnmmd\b|lightning\s*strike|meeting\s*minutes\s*day', low):
        return (*NMMD, 'NMMD', None)

    # 2) Referral Postcard program (foundational channel AND lever).
    if is_referral_pc(low):
        m = re.match(r'\s*[A-Za-z]{2}(\d{4})', n)
        return (*REFERRAL_PC, 'Referral Postcard', code_month(m.group(1)) if m else None)

    # 3) Coded entries: [AA][MMYY][rest]
    m = re.match(r'\s*([A-Za-z]{2})(\d{4})(.*)', n, re.S)
    if m:
        pre = m.group(1).upper()
        cmonth = code_month(m.group(2))
        rest = m.group(3).strip()
        lever = detect_lever(rest)
        if pre in ('PT', 'LT'):                       # postcard / letter direct mail campaign
            if '(tw)' in rest.lower():
                lever = lever or 'Town Web bundle'
            return (*CAMPAIGN_PC, lever, cmonth)
        if pre == 'TW':
            return (*TOWNWEB, lever, cmonth)
        if pre == 'HG':
            return (*HEYGOV, lever, cmonth)
        # unknown prefix code — don't mis-credit a real channel
        return (*UNATTR, lever, cmonth)

    # 4) Free-text entries
    if 'google ads' in low or 'adwords' in low or re.search(r'\bgas\b', low):
        return (*GOOGLE, None, None)
    if 'youtube' in low:
        return (*YOUTUBE, None, None)
    if 'exclusivecall' in low or 'call experiment' in low:
        return (*OUTBOUND, '30-day Call Experiment', None)
    if 'cold call' in low or 'outbound' in low or 'cold calling' in low:
        return (*OUTBOUND, None, None)
    # conference codes (NCAMC2025, OAMR2025, NEACTC…) and event keywords
    if re.search(r'ncamc|oamr|neactc|utconf|conference|\bconf\b|webinar|expo|summit|invitation', low) \
       or re.match(r'^[a-z]{3,7}\s*\d{4}$', low):
        return (*EVENTS, None, None)
    lev = detect_lever(low)
    if lev:                                           # named postcard campaign only
        return (*CAMPAIGN_PC, lev, None)
    # generic "postcard" with no identifiable campaign -> Unattributed (no 'Other postcard' bucket)
    if 'tw proposal' in low or '(tw)' in low or 'town web' in low:
        return (*TOWNWEB, None, None)
    if 'hg proposal' in low or 'heygov' in low:
        return (*HEYGOV, None, None)
    if 'referr' in low:
        return (*REFERRAL, None, None)
    return (*UNATTR, None, None)


def build(csv_path):
    rows = list(csv.reader(open(csv_path, newline='')))
    hdr = rows[0]
    idx = {h.strip(): i for i, h in enumerate(hdr)}
    def col(r, name):
        i = idx.get(name, -1)
        return r[i].strip() if 0 <= i < len(r) else ''
    data = [r for r in rows[1:] if len(r) > 15 and r[1].strip()]

    recs = []
    for r in data:
        note = col(r, 'Notes / Lead Source')
        channel, short, lever, cmonth = classify(note)
        won_month = parse_month(col(r, 'Created date'))
        bc = col(r, 'Billing cycle').strip().lower()
        bc = 'M' if bc.startswith('month') else 'A'   # Monthly -> M ; Annual/blank -> A (annual is the dominant default)
        recs.append({
            'm':  won_month,                 # month became paid customer (revenue recognition)
            'cm': cmonth,                    # campaign month from code (when the lever ran)
            'ch': channel,
            'cs': short,
            'lv': lever,
            'rev': round(money(col(r, 'Annual $'))),   # annualized revenue (ARR) for both billing types
            'bc': bc,                        # billing cycle: A=annual (paid upfront) / M=monthly (paid over 12)
            'plan': col(r, 'Plan'),
            'st': col(r, 'State'),
            'mun': col(r, 'Municipality'),
        })
    return recs


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    csv_path = args[0] if args else DEFAULT_CSV
    recs = build(csv_path)
    payload = {
        'source': csv_path.split('/')[-1],
        'count': len(recs),
        'records': recs,
    }
    out = json.dumps(payload, separators=(',', ':'))

    if '--inject' in sys.argv:
        import os
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
        html = open(html_path).read()
        new = re.sub(
            r'(/\*DATA_START\*/)(.*?)(/\*DATA_END\*/)',
            lambda mo: mo.group(1) + out + mo.group(3),
            html, flags=re.S)
        open(html_path, 'w').write(new)
        print(f"Injected {len(recs)} records into {html_path}")
    else:
        # summary to stderr, JSON to stdout
        chs = collections.Counter(r['cs'] for r in recs)
        sys.stderr.write("Channel split:\n")
        for k, v in chs.most_common():
            sys.stderr.write(f"  {v:4} {k}\n")
        print(out)


if __name__ == '__main__':
    main()
