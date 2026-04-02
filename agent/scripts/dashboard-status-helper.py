"""Helper for dashboard-status.bat — prints network stats and recent activations."""
import json
import sys
import urllib.request

def fetch(path):
    try:
        resp = urllib.request.urlopen(f"http://localhost:8051{path}", timeout=3)
        return json.loads(resp.read())
    except Exception:
        return None

stats = fetch("/api/stats")
if stats:
    print(f"  Nodes: {stats['total_nodes']}")
    print(f"  Connections: {stats['total_connections']}")
    print(f"  Avg strength: {stats['avg_strength']:.3f}")
    print(f"  Active scouts: {stats['active_scouts']}")
    print(f"  Anastomosis events: {stats['anastomosis_events']}")
else:
    print("  (dashboard not reachable)")
    sys.exit(0)

print()
print("--- Recent Activations ---")
activations = fetch("/api/activations")
if not activations:
    print("  No activations yet")
else:
    for a in activations[-5:]:
        concepts = json.loads(a["concepts"]) if isinstance(a["concepts"], str) else a["concepts"]
        print(f"  [{a['timestamp']}] session={a['session']}, {len(concepts)} concepts: {', '.join(concepts[:5])}")
