import json
from ..core.protocol import Result

def format_json(results: list[Result]) -> str:
    data = [
        {
            "endpoint": f"{r.endpoint.host}:{r.endpoint.port}",
            "protocol": r.endpoint.protocol.value,
            "status": r.status.value,
            "reason": r.reason.value if r.reason else None,
            "latency_ms": round(r.latency_ms, 2) if r.latency_ms else None,
            "schema_version": r.schema_version,
        }
        for r in results
    ]
    return json.dumps(data, indent=2, ensure_ascii=False)
