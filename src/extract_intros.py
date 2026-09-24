import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

FIELDS = {"nome": "nome", "linked": "linkedin", "linktree": "linkedin",
          "curios": "curiosidade", "área": "area", "area": "area", "atu": "area"}

MODEL = "sonnet"

PROMPT = """
    Você recebe apresentações de membros de uma comunidade tech, uma por linha: id|nome|area|curiosidade.
    Para cada pessoa devolva:
    - grupo: a área profissional principal. Use entre 6 e 10 grupos no total, sempre com os mesmos nomes (ex.: "Backend", "Dados & IA").
    - tags: de 2 a 6 tags curtas e específicas, em minúsculas, sobre stack, interesses e curiosidades (ex.: "java", "violão", "alemanha").
    Não repita o grupo como tag.
    - temas: de 1 a 3 temas amplos. Primeiro defina no máximo 12 temas para o grupo inteiro (ex.: "música & arte",
    "esportes", "viagem & morar fora", "mudança de carreira", "games & nerd", "empreendedorismo"), depois atribua
    a cada pessoa só temas dessa lista, com o nome idêntico. O objetivo é que muitas pessoas compartilhem temas.
    Inclua todas as pessoas.
"""

SCHEMA = {
    "type": "object", "required": ["people"], "properties": {
        "people": {"type": "array", "items": {
            "type": "object", "required": ["id", "grupo", "tags", "temas"], 
            "properties": {
                "id": {"type": "integer"}, "grupo": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "temas": {"type": "array", "items": {"type": "string"}}
                }
            }
        }
    }
}

PALETTE = [
    "#7aa2f7", 
    "#f7768e", 
    "#9ece6a", 
    "#e0af68", 
    "#bb9af7", 
    "#7dcfff", 
    "#ff9e64", 
    "#73daca", 
    "#c0caf5"
]

HTML = """
<!doctype html><meta charset="utf-8"><title>Intros</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  html, body, #g { margin: 0; height: 100%; background: #0f1117; font-family: Inter, system-ui, sans-serif }
  #hint { position: fixed; left: 16px; bottom: 12px; color: #565f89; font-size: 13px }
  div.vis-tooltip { background: #1f2335; color: #c0caf5; border: 1px solid #3b4261; border-radius: 8px;
    padding: 10px 12px; max-width: 320px; white-space: normal; font: 13px/1.45 Inter, system-ui, sans-serif }
</style>
<div id="g"></div>
<div id="hint">Clique numa pessoa para abrir o LinkedIn · Clique num grupo ou tema para destacar as conexões</div>
<script>
const data = __DATA__;
for (const n of data.nodes) if (n.title) { const d = document.createElement('div'); d.innerText = n.title; n.title = d; }
const nodes = new vis.DataSet(data.nodes), edges = new vis.DataSet(data.edges);
const net = new vis.Network(document.getElementById('g'), {nodes, edges}, {
  nodes: {shape: 'dot', borderWidth: 0, font: {color: '#a9b1d6', size: 12, face: 'Inter, system-ui, sans-serif'}},
  edges: {width: 1, smooth: false},
  physics: {solver: 'forceAtlas2Based', stabilization: {iterations: 500},
            forceAtlas2Based: {gravitationalConstant: -80, springLength: 110, avoidOverlap: 0.5}},
  interaction: {hover: true, tooltipDelay: 100},
});
net.once('stabilizationIterationsDone', () => net.setOptions({physics: false}));
net.on('click', ({nodes: [id]}) => {
  const url = id === undefined ? null : nodes.get(id).url;
  if (url) window.open(url, '_blank', 'noopener');
  const keep = id === undefined ? null : new Set([id, ...net.getConnectedNodes(id)]);
  nodes.update(nodes.getIds().map((n) => ({id: n, opacity: !keep || keep.has(n) ? 1 : 0.1})));
  edges.update(edges.get().map((e) => ({id: e.id, hidden: !!keep && !(keep.has(e.from) && keep.has(e.to))})));
});
</script>
"""


def parse(text):
    intro, pending = {}, None
    for line in text.splitlines():
        line = re.sub(r"^[\s⁠]*(\d+\.|-)?[\s⁠]*", "", line).strip()
        if not line:
            continue
        key, sep, value = line.partition(":")
        field = next((f for k, f in FIELDS.items() if k in key.lower()), None) if sep else None
        url = re.search(r"https?://\S*linkedin\S*", line)
        if field and not value.strip(" *_"):
            pending = field
            continue
        if field:
            intro.setdefault(field, value.strip(" *_"))
        elif url:
            intro.setdefault("linkedin", url.group())
        elif pending:
            intro.setdefault(pending, line)
        pending = None
    return intro if "nome" in intro and len(intro) > 1 else None


def group(people):
    lines = "\n".join(f"{i}|{p['nome']}|{p.get('area', '')}|{p.get('curiosidade', '')}"
                      for i, p in enumerate(people))
    out = subprocess.run(
        ["claude", "-p", "--model", MODEL, "--output-format", "json", "--tools", "",
         "--system-prompt", PROMPT, "--json-schema", json.dumps(SCHEMA)],
        input=lines, capture_output=True, text=True)
    result = json.loads(out.stdout or "{}")
    if out.returncode or result.get("is_error") or "structured_output" not in result:
        sys.exit(out.stderr or result.get("result") or out.stdout)
    grouped = [people[g["id"]] | {"grupo": g["grupo"], "tags": g["tags"], "temas": g["temas"]}
               for g in result["structured_output"]["people"] if 0 <= g["id"] < len(people)]
    if len(grouped) != len(people):
        print(f"warning: LLM returned {len(grouped)} of {len(people)} people", file=sys.stderr)
    return grouped


def graph(grouped):
    colors = dict(zip(sorted({p["grupo"] for p in grouped}), PALETTE * 3))
    nodes = [{"id": f"g:{g}", "label": g, "color": c, "size": 26,
              "font": {"size": 24, "color": "#ffffff", "strokeWidth": 5, "strokeColor": "#0f1117"}}
             for g, c in colors.items()]
    nodes += [{"id": f"t:{t}", "label": t, "shape": "box", "margin": 10, "shapeProperties": {"borderRadius": 14},
               "color": {"background": "#1f2335", "border": "#3b4261"}, "borderWidth": 1,
               "font": {"size": 17, "color": "#c0caf5"}}
              for t in sorted({t for p in grouped for t in p["temas"]})]
    edges = []
    for i, p in enumerate(grouped):
        name = re.findall(r"\w[\w'.]*", re.sub(r"\(.*?\)", "", p["nome"])) or [p["nome"]]
        link = p.get("linkedin", "")
        nodes.append({"id": i, "label": " ".join(dict.fromkeys([name[0], name[-1]])),
                      "url": link if re.match(r"https?://", link) else None, "color": colors[p["grupo"]], "size": 7,
                      "title": "\n".join([p["nome"], p["grupo"]] + [p.get(k, "") for k in ("area", "curiosidade")]
                                         + [" · ".join(p["tags"]), p.get("linkedin", "")])})
        edges.append({"from": i, "to": f"g:{p['grupo']}", "color": {"color": colors[p["grupo"]], "opacity": 0.45}})
        edges += [{"from": i, "to": f"t:{t}", "color": {"color": "#565f89", "opacity": 0.3}} for t in p["temas"]]
    return HTML.replace("__DATA__", json.dumps({"nodes": nodes, "edges": edges}))


src = Path(sys.argv[1])
index = Path(__file__).resolve().parent.parent / "index.html"
if src.name.endswith(".grupos.json"):
    index.write_text(graph(json.loads(src.read_text())))
    print(f"wrote {index}")
    sys.exit()
people = [p for line in src.open(encoding="utf-8") if (p := parse(json.loads(line)["text"] or ""))]

if "--graph" in sys.argv:
    grouped = group(people)
    src.with_suffix(".grupos.json").write_text(json.dumps(grouped, ensure_ascii=False, indent=2))
    index.write_text(graph(grouped))
    print(f"wrote {index}")
    print(Counter(p["grupo"] for p in grouped).most_common())
else:
    writer = csv.DictWriter(sys.stdout, ["nome", "area", "curiosidade", "linkedin"])
    writer.writeheader()
    writer.writerows(people)
