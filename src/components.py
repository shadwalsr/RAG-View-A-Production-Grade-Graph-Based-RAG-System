"""Minimal HTML components for the RAG-VIEW dashboard."""


def top_nav_html():
    return """
<div style="display:flex; justify-content:space-between; align-items:center;
    padding:14px 48px; border-bottom:1px solid #1a1d25;">
    <div style="display:flex; align-items:center; gap:10px;">
        <span class="material-symbols-outlined" style="color:#00E5B5; font-size:20px;">description</span>
        <span style="font-family:'Bebas Neue',sans-serif; font-size:28px; color:#00E5B5;
            letter-spacing:0.05em; line-height:1;">RAG-VIEW</span>
    </div>
    <div style="display:flex; align-items:center; gap:20px;">
        <span style="font-family:'Inter',sans-serif; font-size:11px; font-weight:600;
            letter-spacing:0.1em; color:#6B7280;">SHADWAL SINGH</span>
        <span style="font-family:'Inter',sans-serif; font-size:11px; font-weight:600;
            letter-spacing:0.1em; color:#6B7280;">V2.0</span>
        <button style="background:#00E5B5; color:#0A0D14; border:none; border-radius:8px;
            padding:8px 20px; font-family:'Inter',sans-serif; font-size:11px; font-weight:700;
            letter-spacing:0.08em; cursor:pointer; display:flex; align-items:center; gap:6px;">
            DEPLOY API <span class="material-symbols-outlined" style="font-size:14px;">rocket_launch</span>
        </button>
        <span class="material-symbols-outlined" style="color:#6B7280; font-size:20px; cursor:pointer;">settings</span>
        <span class="material-symbols-outlined" style="color:#6B7280; font-size:20px; cursor:pointer;">account_circle</span>
    </div>
</div>"""



def hero_section_html():
    svg = """
<svg viewBox="0 0 480 400" xmlns="http://www.w3.org/2000/svg" style="width:100%; max-width:460px; height:auto;">
  <defs>
    <filter id="glow">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="softGlow">
      <feGaussianBlur stdDeviation="12" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <radialGradient id="coreFill" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#00E5B5" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="#0A0D14" stop-opacity="1"/>
    </radialGradient>
  </defs>
  <style>
    @keyframes drawLine { from { stroke-dashoffset: 400; } to { stroke-dashoffset: 0; } }
    @keyframes fadeIn { from { opacity:0; transform:scale(0.3); } to { opacity:1; transform:scale(1); } }
    @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.7; } }
    @keyframes glowPulse { 0%,100% { opacity:0.2; r:50; } 50% { opacity:0.5; r:56; } }
    @keyframes ringPulse { 0%,100% { opacity:0.08; } 50% { opacity:0.2; } }
    @keyframes dashFlow { to { stroke-dashoffset:-20; } }
    @keyframes orbitSpin { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
    .edge { stroke-dasharray:400; stroke-dashoffset:400; animation:drawLine 2s ease-out forwards; }
    .ed1{animation-delay:.1s} .ed2{animation-delay:.25s} .ed3{animation-delay:.4s}
    .ed4{animation-delay:.55s} .ed5{animation-delay:.7s} .ed6{animation-delay:.85s}
    .ed7{animation-delay:1s} .ed8{animation-delay:1.1s}
    .dashed { stroke-dasharray:6,5; animation:dashFlow 1.4s linear infinite; }
    .nd { opacity:0; transform-origin:center; animation:fadeIn .6s ease-out forwards; }
    .n1{animation-delay:.5s} .n2{animation-delay:.7s} .n3{animation-delay:.9s}
    .n4{animation-delay:1.1s} .n5{animation-delay:1.3s} .n6{animation-delay:1.5s}
    .core-ring { animation:pulse 3s ease-in-out infinite; }
    .core-glow { animation:glowPulse 3s ease-in-out infinite; }
    .orbit-ring { animation:ringPulse 4s ease-in-out infinite; }
    .orbit { transform-origin:240px 200px; animation:orbitSpin 20s linear infinite; }
  </style>

  <!-- Orbit ring. -->
  <circle cx="240" cy="200" r="130" fill="none" stroke="#1F2937" stroke-width="0.5" stroke-dasharray="4,6" class="orbit-ring"/>

  <!-- Edges: solid. -->
  <line x1="100" y1="70" x2="240" y2="200" stroke="#1F2937" stroke-width="1" class="edge ed1"/>
  <line x1="380" y1="60" x2="240" y2="200" stroke="#1F2937" stroke-width="1" class="edge ed2"/>
  <line x1="420" y1="220" x2="240" y2="200" stroke="#1F2937" stroke-width="1" class="edge ed3"/>
  <line x1="360" y1="340" x2="240" y2="200" stroke="#1F2937" stroke-width="1" class="edge ed4"/>
  <line x1="80" y1="300" x2="240" y2="200" stroke="#1F2937" stroke-width="1" class="edge ed5"/>
  <line x1="60" y1="180" x2="240" y2="200" stroke="#1F2937" stroke-width="0.8" class="edge ed6"/>
  <line x1="100" y1="70" x2="380" y2="60" stroke="#1F2937" stroke-width="0.5" class="edge ed7"/>
  <line x1="80" y1="300" x2="360" y2="340" stroke="#1F2937" stroke-width="0.5" class="edge ed8"/>

  <!-- Edges: dashed. -->
  <line x1="100" y1="70" x2="80" y2="300" stroke="#00E5B5" stroke-width="0.8" class="dashed" opacity="0.4"/>
  <line x1="380" y1="60" x2="420" y2="220" stroke="#00E5B5" stroke-width="0.8" class="dashed" opacity="0.4"/>
  <line x1="60" y1="180" x2="80" y2="300" stroke="#00E5B5" stroke-width="0.6" class="dashed" opacity="0.3"/>

  <!-- Data particles. -->
  <circle r="2.5" fill="#00E5B5" opacity="0">
    <animateMotion dur="2.5s" repeatCount="indefinite" path="M100,70 L240,200" begin="1.5s"/>
    <animate attributeName="opacity" values="0;1;1;0" dur="2.5s" repeatCount="indefinite" begin="1.5s"/>
  </circle>
  <circle r="2.5" fill="#00E5B5" opacity="0">
    <animateMotion dur="3s" repeatCount="indefinite" path="M380,60 L240,200" begin="2s"/>
    <animate attributeName="opacity" values="0;1;1;0" dur="3s" repeatCount="indefinite" begin="2s"/>
  </circle>
  <circle r="2" fill="#00E5B5" opacity="0">
    <animateMotion dur="3.5s" repeatCount="indefinite" path="M80,300 L240,200" begin="2.5s"/>
    <animate attributeName="opacity" values="0;1;1;0" dur="3.5s" repeatCount="indefinite" begin="2.5s"/>
  </circle>
  <circle r="2" fill="#00E5B5" opacity="0">
    <animateMotion dur="2.8s" repeatCount="indefinite" path="M420,220 L240,200" begin="1.8s"/>
    <animate attributeName="opacity" values="0;1;1;0" dur="2.8s" repeatCount="indefinite" begin="1.8s"/>
  </circle>
  <circle r="2" fill="#00E5B5" opacity="0">
    <animateMotion dur="3.2s" repeatCount="indefinite" path="M360,340 L240,200" begin="2.2s"/>
    <animate attributeName="opacity" values="0;1;1;0" dur="3.2s" repeatCount="indefinite" begin="2.2s"/>
  </circle>
  <circle r="1.5" fill="#00E5B5" opacity="0">
    <animateMotion dur="4s" repeatCount="indefinite" path="M60,180 L240,200" begin="3s"/>
    <animate attributeName="opacity" values="0;1;1;0" dur="4s" repeatCount="indefinite" begin="3s"/>
  </circle>

  <!-- Orbiting dot. -->
  <g class="orbit">
    <circle cx="370" cy="200" r="2" fill="#00E5B5" opacity="0.5"/>
  </g>

  <!-- CORE node. -->
  <circle cx="240" cy="200" r="50" fill="url(#coreFill)" class="core-glow" filter="url(#softGlow)"/>
  <circle cx="240" cy="200" r="32" fill="#0A0D14" stroke="#00E5B5" stroke-width="2" class="core-ring" filter="url(#glow)"/>
  <circle cx="240" cy="200" r="22" fill="none" stroke="#00E5B5" stroke-width="0.5" opacity="0.3"/>
  <text x="240" y="205" text-anchor="middle" fill="#00E5B5" font-family="Inter" font-size="11" font-weight="700">CORE</text>

  <!-- Outer nodes. -->
  <g class="nd n1">
    <circle cx="100" cy="70" r="18" fill="#0A0D14" stroke="#1F2937" stroke-width="1.5"/>
    <text x="100" y="75" text-anchor="middle" fill="#6B7280" font-family="Inter" font-size="9">N1</text>
  </g>
  <g class="nd n2">
    <circle cx="380" cy="60" r="18" fill="#0A0D14" stroke="#1F2937" stroke-width="1.5"/>
    <text x="380" y="65" text-anchor="middle" fill="#6B7280" font-family="Inter" font-size="9">N2</text>
  </g>
  <g class="nd n3">
    <circle cx="420" cy="220" r="14" fill="#0A0D14" stroke="#1F2937" stroke-width="1.5"/>
    <text x="420" y="224" text-anchor="middle" fill="#6B7280" font-family="Inter" font-size="8">N3</text>
  </g>
  <g class="nd n4">
    <circle cx="360" cy="340" r="16" fill="#0A0D14" stroke="#1F2937" stroke-width="1.5"/>
    <text x="360" y="344" text-anchor="middle" fill="#6B7280" font-family="Inter" font-size="9">N4</text>
  </g>
  <g class="nd n5">
    <circle cx="80" cy="300" r="16" fill="#0A0D14" stroke="#1F2937" stroke-width="1.5"/>
    <text x="80" y="304" text-anchor="middle" fill="#6B7280" font-family="Inter" font-size="9">N5</text>
  </g>
  <g class="nd n6">
    <circle cx="60" cy="180" r="12" fill="#0A0D14" stroke="#1F2937" stroke-width="1.5"/>
    <text x="60" y="184" text-anchor="middle" fill="#6B7280" font-family="Inter" font-size="7">N6</text>
  </g>
</svg>"""
    return f"""
<div style="display:flex; align-items:center; justify-content:space-between; padding:64px 48px 40px 48px;">
    <div style="flex:1; max-width:50%;">
        <h1 style="font-family:'Bebas Neue',sans-serif; font-size:72px; line-height:1.05;
            color:#e1e2ec; margin:0; letter-spacing:0.02em;">
            RAG-VIEW:<br/><span style="color:#00E5B5;">A PRODUCTION GRADE<br/>GRAPH BASED RAG<br/>PIPELINE</span>
        </h1>
        <p style="font-family:'Inter',sans-serif; font-size:11px; font-weight:600;
            letter-spacing:0.15em; color:#4B5563; margin-top:24px;">
            MAY &ndash; JUNE 2026 &middot; GRAPH RAG SYSTEMS
        </p>
    </div>
    <div style="flex:0 0 auto; margin-left:24px;">{svg}</div>
</div>"""


def pipeline_pills_html(active_step="GENERATION"):
    steps = ["INGESTION", "RETRIEVAL", "GENERATION", "EVALUATION", "API & DASHBOARD"]
    pills = []
    for i, step in enumerate(steps):
        if step == active_step:
            s = "color:#00E5B5; border-bottom:2px solid #00E5B5; padding-bottom:4px;"
        else:
            s = "color:#3d4250; border-bottom:2px solid transparent; padding-bottom:4px;"
        pill = (f'<span style="{s} font-family:Inter,sans-serif; font-size:10px; font-weight:600; '
                f'letter-spacing:0.1em; white-space:nowrap;">{step}</span>')
        pills.append(pill)
        if i < len(steps) - 1:
            pills.append('<span style="color:#1F2937; font-size:10px;">—</span>')
    return f"""
<div style="display:flex; justify-content:center; align-items:center; gap:12px;
    padding:16px 0 12px 0;">{chr(10).join(pills)}</div>"""


def _card(title, body_html):
    """Self-contained card with no nested div issues."""
    return f"""
<div style="background:#111318; border:1px solid #1a1d25; border-radius:10px;
    overflow:hidden; margin-bottom:20px;">
    <div style="padding:14px 18px; border-bottom:1px solid #1a1d25;">
        <span style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:#e1e2ec;
            letter-spacing:0.04em;">{title}</span>
    </div>
    <div style="padding:18px;">{body_html}</div>
</div>"""


def onehop_graph_card():
    return """
<div style="background:#111318; border:1px solid #1a1d25; border-radius:10px;
    overflow:hidden; margin-bottom:20px;">
    <div style="padding:14px 18px; border-bottom:1px solid #1a1d25;">
        <span style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:#e1e2ec;
            letter-spacing:0.04em;">1-HOP KNOWLEDGE GRAPH</span>
    </div>
    <div style="background:#080a0f; min-height:240px; display:flex; align-items:center;
        justify-content:center; padding:16px;">
        <svg viewBox="0 0 400 260" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:240px;">
            <line x1="200" y1="130" x2="80" y2="45" stroke="#1F2937" stroke-width="1"/>
            <line x1="200" y1="130" x2="320" y2="50" stroke="#1F2937" stroke-width="1"/>
            <line x1="200" y1="130" x2="85" y2="210" stroke="#00E5B5" stroke-width="0.8" stroke-dasharray="4" opacity="0.5"/>
            <line x1="200" y1="130" x2="325" y2="200" stroke="#1F2937" stroke-width="1"/>
            <circle cx="200" cy="130" r="24" fill="#0A0D14" stroke="#00E5B5" stroke-width="1.5"/>
            <text x="200" y="127" text-anchor="middle" fill="#00E5B5" font-family="Inter" font-size="10" font-weight="600">CORE</text>
            <text x="200" y="170" text-anchor="middle" fill="#4B5563" font-family="Inter" font-size="9">Policy_Aug24</text>
            <circle cx="80" cy="45" r="14" fill="#0A0D14" stroke="#1F2937" stroke-width="1"/>
            <text x="80" y="49" text-anchor="middle" fill="#6B7280" font-family="Inter" font-size="9">DOC</text>
            <circle cx="320" cy="50" r="14" fill="#0A0D14" stroke="#1F2937" stroke-width="1"/>
            <text x="320" y="54" text-anchor="middle" fill="#6B7280" font-family="Inter" font-size="9">MFG</text>
            <circle cx="85" cy="210" r="14" fill="#0A0D14" stroke="#00E5B5" stroke-width="1" opacity="0.6"/>
            <text x="85" y="214" text-anchor="middle" fill="#00E5B5" font-family="Inter" font-size="9">HUB</text>
            <text x="85" y="235" text-anchor="middle" fill="#4B5563" font-family="Inter" font-size="8">Hub_EU_04</text>
            <circle cx="325" cy="200" r="14" fill="#0A0D14" stroke="#1F2937" stroke-width="1"/>
            <text x="325" y="204" text-anchor="middle" fill="#6B7280" font-family="Inter" font-size="9">INV</text>
        </svg>
    </div>
</div>"""


def dynamic_graph_card(relationships: list):
    nodes = set()
    edges = []
    for rel in relationships:
        if " --[" in rel and "]--> " in rel:
            parts = rel.split(" --[")
            src = parts[0].strip()
            rest = parts[1].split("]--> ")
            pred = rest[0].strip()
            tgt = rest[1].strip()
            nodes.add(src)
            nodes.add(tgt)
            edges.append((src, pred, tgt))
    
    if not edges:
        return onehop_graph_card()
        
    degree = {}
    for src, pred, tgt in edges:
        degree[src] = degree.get(src, 0) + 1
        degree[tgt] = degree.get(tgt, 0) + 1
    root = sorted(degree.keys(), key=lambda k: degree[k], reverse=True)[0]
    
    others = [n for n in nodes if n != root]
    
    import math
    cx, cy = 200, 130
    r_spoke = 90
    n_others = len(others) if others else 1
    
    node_coords = {root: (cx, cy)}
    for i, n in enumerate(others):
        angle = i * (2 * math.pi / n_others) - math.pi / 2
        nx = cx + r_spoke * math.cos(angle)
        ny = cy + r_spoke * math.sin(angle)
        node_coords[n] = (nx, ny)
        
    lines_svg = ""
    for src, pred, tgt in edges:
        s_pos = node_coords.get(src, (cx, cy))
        t_pos = node_coords.get(tgt, (cx, cy))
        lines_svg += f'<line x1="{s_pos[0]}" y1="{s_pos[1]}" x2="{t_pos[0]}" y2="{t_pos[1]}" stroke="#1F2937" stroke-width="1.2"/>'
        mx, my = (s_pos[0] + t_pos[0])/2, (s_pos[1] + t_pos[1])/2
        lines_svg += f'<text x="{mx}" y="{my-4}" text-anchor="middle" fill="#00E5B5" font-family="Inter" font-size="8">{pred}</text>'
        
    nodes_svg = f'<circle cx="{cx}" cy="{cy}" r="26" fill="#0A0D14" stroke="#00E5B5" stroke-width="2" filter="url(#glow)"/>'
    nodes_svg += f'<text x="{cx}" y="{cy+4}" text-anchor="middle" fill="#00E5B5" font-family="Inter" font-size="11" font-weight="700">{root[:12]}</text>'
    
    for n in others:
        nx, ny = node_coords[n]
        nodes_svg += f'<circle cx="{nx}" cy="{ny}" r="16" fill="#0A0D14" stroke="#1F2937" stroke-width="1.5"/>'
        nodes_svg += f'<text x="{nx}" y="{ny+4}" text-anchor="middle" fill="#e1e2ec" font-family="Inter" font-size="9">{n[:10]}</text>'
        
    return f"""
<div style="background:#111318; border:1px solid #1a1d25; border-radius:10px;
    overflow:hidden; margin-bottom:20px;">
    <div style="padding:14px 18px; border-bottom:1px solid #1a1d25; display:flex; justify-content:space-between; align-items:center;">
        <span style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:#e1e2ec;
            letter-spacing:0.04em;">RETRIEVED KNOWLEDGE GRAPH</span>
        <span style="font-family:Inter,sans-serif; font-size:10px; color:#00E5B5; font-weight:600;">{len(nodes)} NODES &middot; {len(edges)} EDGES</span>
    </div>
    <div style="background:#080a0f; min-height:240px; display:flex; align-items:center;
        justify-content:center; padding:16px;">
        <svg viewBox="0 0 400 260" xmlns="http://www.w3.org/2000/svg" style="width:100%; height:240px;">
            <defs>
                <filter id="glow">
                    <feGaussianBlur stdDeviation="4" result="blur"/>
                    <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                </filter>
            </defs>
            {lines_svg}
            {nodes_svg}
        </svg>
    </div>
</div>"""


def chat_card_header():
    return ('<div style="display:flex; align-items:center; gap:10px;">'
            '<span class="material-symbols-outlined" style="color:#00E5B5; font-size:18px;">smart_toy</span>'
            '<span style="font-family:Bebas Neue,sans-serif; font-size:18px; color:#e1e2ec; '
            'letter-spacing:0.04em;">GRAPHRAG ASSISTANT</span>'
            '</div>')


def chat_card(title_html, badge, body_html):
    """Self-contained chat card."""
    return f"""
<div style="background:#111318; border:1px solid #1a1d25; border-radius:10px;
    overflow:hidden; margin-bottom:20px;">
    <div style="padding:14px 18px; border-bottom:1px solid #1a1d25;
        display:flex; justify-content:space-between; align-items:center;">
        {title_html}
        <span style="background:#101520; border:1px solid #1a1d25; color:#6B7280;
            font-family:Inter,monospace; font-size:10px; padding:3px 8px;
            border-radius:4px; font-weight:600;">{badge}</span>
    </div>
    <div style="padding:18px;">{body_html}</div>
</div>"""


def metrics_html(rec=0.92, cov=0.85, gro=0.96):
    def bar(label, value, color):
        pct = f"{value*100:.0f}%"
        return f"""
<div style="margin-bottom:16px;">
    <div style="display:flex; justify-content:space-between; font-family:Inter,sans-serif;
        font-size:12px; margin-bottom:6px;">
        <span style="color:#6B7280;">{label}</span>
        <span style="color:{color}; font-weight:600;">{pct}</span>
    </div>
    <div style="height:4px; width:100%; background:#1a1d25; border-radius:4px; overflow:hidden;">
        <div style="height:100%; width:{value*100}%; background:{color}; border-radius:4px;"></div>
    </div>
</div>"""
    content = bar("Vector Retrieval Confidence", rec, "#00E5B5")
    content += bar("Graph Structural Coverage", cov, "#00E5B5")
    content += bar("Final Grounding Score", gro, "#10B981")
    return f"""
<div style="background:#111318; border:1px solid #1a1d25; border-radius:10px; padding:18px;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <span style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:#e1e2ec;
            letter-spacing:0.04em;">HYBRID SEARCH METRICS</span>
        <span style="font-family:Inter,sans-serif; font-size:10px; color:#4B5563; font-weight:600;">RRF ACTIVE</span>
    </div>
    {content}
</div>"""


def chat_messages_html(messages):
    html = ""
    for msg in messages:
        if msg["role"] == "user":
            html += f"""
<div style="display:flex; justify-content:flex-end; margin-bottom:16px;">
    <div style="max-width:80%; background:#1a1d25; color:#e1e2ec; padding:14px;
        border-radius:12px 12px 4px 12px;
        font-family:Outfit,sans-serif; font-size:14px; line-height:1.5;">
        {msg['content']}
    </div>
</div>"""
        else:
            pills_html = ""
            for icon, label in msg.get("pills", []):
                pills_html += (f'<span style="display:inline-flex; align-items:center; gap:4px; '
                               f'background:#101520; border:1px solid rgba(0,229,181,0.2); '
                               f'color:#00E5B5; font-family:Inter,sans-serif; font-size:10px; '
                               f'padding:3px 8px; border-radius:4px; margin-right:6px; margin-top:10px;">'
                               f'<span class="material-symbols-outlined" style="font-size:12px;">{icon}</span>'
                               f'{label}</span>')
            paragraphs = msg['content'].replace('\n\n', '</p><p style="margin-bottom:10px;">')
            html += f"""
<div style="display:flex; justify-content:flex-start; margin-bottom:16px;">
    <div style="max-width:85%; background:#080a0f; color:#b9cac2; padding:16px;
        border-radius:12px 12px 12px 4px; border:1px solid #1a1d25;
        font-family:Outfit,sans-serif; font-size:14px; line-height:1.6;">
        <p style="margin-bottom:10px;">{paragraphs}</p>
        <div>{pills_html}</div>
    </div>
</div>"""
    return html


def pipeline_status_card():
    """Self-contained pipeline status card for Document Ingestion."""
    stages = [
        ("Entity Extraction", "Gemini Flash"),
        ("Deduplication", "EntityResolver"),
        ("Relationship Weighting", "Cypher Recalculator")
    ]
    rows = ""
    for i, (name, desc) in enumerate(stages):
        border = 'border-bottom:1px solid #1a1d25;' if i < len(stages) - 1 else ''
        rows += f"""
<div style="display:flex; justify-content:space-between; align-items:center;
    padding:12px 0; {border}">
    <span style="font-family:Outfit,sans-serif; font-size:13px; color:#e1e2ec;">
        <strong style="color:#00E5B5;">{name}</strong> &mdash; {desc}
    </span>
    <span style="color:#00E5B5; font-family:Inter,sans-serif; font-size:10px;
        font-weight:600; letter-spacing:0.05em;">● ONLINE</span>
</div>"""
    return f"""
<div style="background:#111318; border:1px solid #1a1d25; border-radius:10px;
    overflow:hidden; margin-bottom:20px;">
    <div style="padding:14px 18px; border-bottom:1px solid #1a1d25;">
        <span style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:#e1e2ec;
            letter-spacing:0.04em;">PIPELINE STATUS</span>
    </div>
    <div style="padding:12px 18px;">{rows}</div>
</div>"""


def raw_storage_card(files):
    """Self-contained raw storage card for Document Ingestion."""
    if files:
        items = "".join(f'<div style="padding:6px 0; font-size:13px; color:#b9cac2; '
                        f'border-bottom:1px solid #1a1d25;">'
                        f'<span style="color:#4B5563; margin-right:6px;">📄</span>{f}</div>'
                        for f in files)
    else:
        items = '<p style="color:#4B5563; font-size:13px;">No files found.</p>'
    return f"""
<div style="background:#111318; border:1px solid #1a1d25; border-radius:10px;
    overflow:hidden; margin-bottom:20px;">
    <div style="padding:14px 18px; border-bottom:1px solid #1a1d25;">
        <span style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:#e1e2ec;
            letter-spacing:0.04em;">RAW STORAGE</span>
    </div>
    <div style="padding:12px 18px;">{items}</div>
</div>"""


def node_card(title, body_html):
    """Self-contained node inspection card."""
    return f"""
<div style="background:#111318; border:1px solid #1a1d25; border-radius:10px;
    overflow:hidden; margin-bottom:20px;">
    <div style="padding:14px 18px; border-bottom:1px solid #1a1d25;">
        <span style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:#00E5B5;
            letter-spacing:0.04em;">{title}</span>
    </div>
    <div style="padding:14px 18px; font-size:13px; color:#b9cac2; line-height:1.7;">{body_html}</div>
</div>"""


def findings_card(body_html):
    """Self-contained findings card for Benchmark."""
    return f"""
<div style="background:#111318; border:1px solid #1a1d25; border-radius:10px;
    overflow:hidden; margin-bottom:20px;">
    <div style="padding:14px 18px; border-bottom:1px solid #1a1d25;">
        <span style="font-family:'Bebas Neue',sans-serif; font-size:18px; color:#e1e2ec;
            letter-spacing:0.04em;">KEY FINDINGS</span>
    </div>
    <div style="padding:18px;">{body_html}</div>
</div>"""


def footer_html():
    brands = ["Neo4j", "Gemini 2.0 Flash", "ChromaDB", "FastAPI", "Streamlit", "Python 3.11"]
    pills = " &middot; ".join(
        f'<span style="color:#4B5563;">{b}</span>' for b in brands
    )
    return f"""
<div style="padding:32px 48px; border-top:1px solid #1a1d25; text-align:center; margin-top:60px;">
    <p style="font-family:Inter,sans-serif; font-size:11px; font-weight:600; color:#2d3038;
        letter-spacing:0.1em;">POWERED BY &nbsp;{pills}</p>
</div>"""

