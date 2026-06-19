#!/usr/bin/env python3
"""
Bake your entered settings (costs, graduates, decisions, layout) into index.html so they
ship with the site when you push to GitHub / deploy on Netlify.

Workflow:
  1. In the dashboard, enter your costs etc., then click "Export"  -> downloads
     growth-attribution-settings.json (to your Downloads folder).
  2. Run:   python3 save-settings.py --inject
     (auto-finds the newest growth-attribution-settings.json in ~/Downloads,
      or pass an explicit path:  python3 save-settings.py /path/to/settings.json --inject)
  3. git add index.html && git commit && git push   -> Netlify rebuilds with your data.

Without --inject it just prints what it would bake (dry run).
"""
import json, os, re, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, 'index.html')

def find_settings():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if args:
        return args[0]
    downloads = os.path.expanduser('~/Downloads')
    hits = glob.glob(os.path.join(downloads, 'growth-attribution-settings*.json'))
    if not hits:
        sys.exit("No settings file given and none found in ~/Downloads.\n"
                 "Click 'Export' in the dashboard first, or pass the path explicitly.")
    return max(hits, key=os.path.getmtime)   # newest

def main():
    path = find_settings()
    with open(path) as f:
        settings = json.load(f)                     # validate it's real JSON
    compact = json.dumps(settings, separators=(',', ':'))

    html = open(HTML).read()
    if '/*SETTINGS_START*/' not in html:
        sys.exit("Could not find the SETTINGS markers in index.html.")

    summary = (f"costs for {len(settings.get('costs',{}))} period bucket(s), "
               f"{len(settings.get('graduates',{}))} graduate tag(s), "
               f"{len(settings.get('decisions',{}))} manual decision(s)")
    if '--inject' not in sys.argv:
        print(f"DRY RUN — would bake settings from:\n  {path}\n  ({summary})\n"
              f"Re-run with --inject to write index.html.")
        return

    new = re.sub(r'(/\*SETTINGS_START\*/)(.*?)(/\*SETTINGS_END\*/)',
                 lambda m: m.group(1) + compact + m.group(3), html, flags=re.S)
    open(HTML, 'w').write(new)
    print(f"Baked settings into {HTML}\n  source: {path}\n  ({summary})\n"
          f"Now: git add index.html && git commit -m 'Update growth dashboard data' && git push")

if __name__ == '__main__':
    main()
