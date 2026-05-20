from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pathlib import Path
import json
import statistics

app = FastAPI()


CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def with_cors_json(data, status_code=200):
    return JSONResponse(
        content=data,
        status_code=status_code,
        headers=CORS_HEADERS,
    )


def with_cors_empty(status_code=204):
    return Response(
        content="",
        status_code=status_code,
        headers=CORS_HEADERS,
    )


@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return with_cors_empty()

    response = await call_next(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    return response


def percentile_95(values):
    values = sorted(values)

    if not values:
        return None

    index = 0.95 * (len(values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    weight = index - lower

    return values[lower] * (1 - weight) + values[upper] * weight


def load_records():
    root = Path(__file__).resolve().parent.parent
    data_file = root / "q-vercel-latency.json"

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    for key in ["data", "records", "telemetry"]:
        if key in data and isinstance(data[key], list):
            return data[key]

    raise ValueError("Could not find telemetry records")


def compute_metrics(body):
    regions = body.get("regions", [])
    threshold_ms = body.get("threshold_ms", 180)

    records = load_records()
    result = {}

    for region in regions:
        rows = [
            r for r in records
            if str(r.get("region", "")).lower() == str(region).lower()
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
            "breaches": int(sum(1 for x in latencies if x > threshold_ms)),
        }

    return result


@app.get("/")
def home():
    return with_cors_json({"message": "Latency API running"})


@app.options("/")
def options_root():
    return with_cors_empty()


@app.post("/")
async def metrics_root(request: Request):
    body = await request.json()
    return with_cors_json(compute_metrics(body))


@app.get("/metrics")
def home_metrics():
    return with_cors_json({"message": "Latency metrics endpoint"})


@app.options("/metrics")
def options_metrics():
    return with_cors_empty()


@app.post("/metrics")
async def metrics_endpoint(request: Request):
    body = await request.json()
    return with_cors_json(compute_metrics(body))