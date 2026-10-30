import json, os, sys, urllib.request, datetime as dt
user = os.environ.get("GH_USER", "md-khadimul-islam")
token = os.environ["GH_TOKEN"]
q = '{user(login:"%s"){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}' % user
req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": q}).encode(),
    headers={"Authorization": "bearer " + token, "Content-Type": "application/json"})
data = json.load(urllib.request.urlopen(req))
days = [d for w in data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
days = sorted(days, key=lambda d: d["date"])[-30:]
active = sum(1 for d in days if d["contributionCount"] > 0)
total = sum(d["contributionCount"] for d in days)
def svg(bg, fg, sub, empty, fill, accent):
    W, cell, gap = 495, 11, 3
    x0 = (W - (30 * (cell + gap) - gap)) / 2
    mx = max([d["contributionCount"] for d in days] + [1])
    rects = ""
    for i, d in enumerate(days):
        c = d["contributionCount"]
        op = 0 if c == 0 else 0.35 + 0.65 * (c / mx)
        col = empty if c == 0 else fill
        rects += f'<rect x="{x0 + i*(cell+gap):.1f}" y="118" width="{cell}" height="{cell}" rx="2" fill="{col}" fill-opacity="{1 if c==0 else op:.2f}"><title>{d["date"]}: {c}</title></rect>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="170" viewBox="0 0 {W} 170">
<rect width="{W}" height="170" rx="6" fill="{bg}"/>
<g font-family="Segoe UI,Ubuntu,Helvetica,Arial,sans-serif" text-anchor="middle">
<text x="{W/2}" y="58" font-size="34" font-weight="700" fill="{accent}">{active}<tspan font-size="18" fill="{sub}" font-weight="400"> / 30 days</tspan></text>
<text x="{W/2}" y="86" font-size="14" fill="{fg}">Days I coded in the last 30 days</text>
<text x="{W/2}" y="106" font-size="11" fill="{sub}">{total} contributions · {days[0]["date"]} to {days[-1]["date"]}</text>
</g>{rects}</svg>'''
os.makedirs(sys.argv[1] if len(sys.argv) > 1 else "dist", exist_ok=True)
out = sys.argv[1] if len(sys.argv) > 1 else "dist"
open(f"{out}/active30-dark.svg", "w").write(svg("#0D1117", "#e6edf3", "#7d8590", "#21262d", "#39d353", "#58a6ff"))
open(f"{out}/active30-light.svg", "w").write(svg("#ffffff", "#1f2328", "#59636e", "#ebedf0", "#2da44e", "#0969da"))
print(active, total)
