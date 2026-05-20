@app.get("/{path:path}")
def home(path: str = ""):
    return {"message": "Latency API running"}

@app.options("/{path:path}")
def options_handler(path: str = ""):
    return {}

@app.post("/{path:path}")
async def metrics(request: Request, path: str = ""):
    body = await request.json()

    regions = body.get("regions", [])
    threshold_ms = body.get("threshold_ms", 180)

    records = load_records()
    result = {}

    for region in regions:
        rows = [
            r for r in records
            if str(r.get("region", "")).lower() == region.lower()
        ]

        latencies = [
            float(r.get("latency_ms", r.get("latency", 0)))
            for r in rows
        ]

        uptimes = [
            float(r.get("uptime", r.get("uptime_pct", 0)))
            for r in rows
        ]

        result[region] = {
            "avg_latency": round(statistics.mean(latencies), 2) if latencies else None,
            "p95_latency": round(percentile_95(latencies), 2) if latencies else None,
            "avg_uptime": round(statistics.mean(uptimes), 4) if uptimes else None,
            "breaches": sum(1 for x in latencies if x > threshold_ms),
        }

    return result