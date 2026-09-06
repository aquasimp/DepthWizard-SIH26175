import json
import urllib.request
from pathlib import Path

headers = {'User-Agent': 'Mozilla/5.0 DepthWizard-Audit/1.1.0'}

targets = [
    ('earthflow', 'https://huggingface.co/api/datasets/earthflow/GAMUS', 'artifacts/v1.1.0/hf_source_earthflow.json'),
    ('xshadow', 'https://huggingface.co/api/datasets/XShadow/GAMUS', 'artifacts/v1.1.0/hf_source_xshadow.json')
]

for name, url, out_path in targets:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode('utf-8')
        data = json.loads(content)
    Path(out_path).write_text(json.dumps(data, indent=2))
    print(f"[{name}]")
    print(f"  requested: {url}")
    print(f"  canonical id: {data.get('id')}")
    print(f"  sha: {data.get('sha')}")
    print(f"  lastModified: {data.get('lastModified')}")
    print(f"  downloads: {data.get('downloads')}")
    print(f"  cardData: {data.get('cardData')}")
    print(f"  siblings count: {len(data.get('siblings', []))}")
