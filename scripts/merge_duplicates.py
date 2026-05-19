"""Merge duplicate entities and create missing relationships in Neo4j."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# pyrefly: ignore [missing-import].
from src.database import db

def transfer_and_delete(dup_name, main_name):
    """Transfer all relationships from dup to main, then delete dup."""
    # Outgoing.
    outs = db.query(
        "MATCH (dup:Entity)-[r]->(t:Entity) WHERE dup.name = $dup RETURN type(r) AS rel, t.name AS target",
        {"dup": dup_name}
    )
    for o in (outs or []):
        if o["target"] == dup_name:
            continue
        try:
            db.query(
                f"MATCH (main:Entity), (t:Entity) WHERE main.name = $main AND t.name = $target MERGE (main)-[r:{o['rel']}]->(t)",
                {"main": main_name, "target": o["target"]}
            )
            print(f"  OUT: {main_name} -[{o['rel']}]-> {o['target']}")
        except Exception as e:
            print(f"  SKIP OUT: {e}")

    # Incoming.
    ins = db.query(
        "MATCH (s:Entity)-[r]->(dup:Entity) WHERE dup.name = $dup RETURN type(r) AS rel, s.name AS source",
        {"dup": dup_name}
    )
    for i in (ins or []):
        if i["source"] == dup_name:
            continue
        try:
            db.query(
                f"MATCH (s:Entity), (main:Entity) WHERE s.name = $source AND main.name = $main MERGE (s)-[r:{i['rel']}]->(main)",
                {"source": i["source"], "main": main_name}
            )
            print(f"  IN: {i['source']} -[{i['rel']}]-> {main_name}")
        except Exception as e:
            print(f"  SKIP IN: {e}")

    # Delete dup.
    db.query("MATCH (dup:Entity) WHERE dup.name = $dup DETACH DELETE dup", {"dup": dup_name})
    print(f"  DELETED: {dup_name}")


# --- Step 1: Merge duplicates ---.
print("=== Merging Duplicates ===")
MERGES = [
    ("Shadwalsingh", "Shadwal Singh"),
    ("Whyschoolacademy", "Whyschool Academy"),
    ("Takshilaeducationalsociety", "Takshila Educational Society"),
]
for dup, main in MERGES:
    print(f"\nMerging '{dup}' -> '{main}'")
    transfer_and_delete(dup, main)

# --- Step 2: Create missing relationships for orphan nodes ---.
print("\n=== Creating Missing Relationships ===")

# Skills that Shadwal Singh uses (orphan SKILL nodes).
SKILLS_USED = [
    "Google Gemini Api", "Hugging Face Transformers", "Neo4J", "Chromadb",
    "Fastapi", "Docker", "React", "Typescript", "Figma", "Canva",
    "Tailwindcss", "Pydantic", "Bm25Index",
]
for skill in SKILLS_USED:
    try:
        db.query(
            f"MATCH (p:Entity), (s:Entity) WHERE p.name = 'Shadwal Singh' AND s.name = $skill MERGE (p)-[:USES]->(s)",
            {"skill": skill}
        )
        print(f"  Shadwal Singh -[USES]-> {skill}")
    except Exception as e:
        print(f"  SKIP: {skill}: {e}")

# Projects that Shadwal Singh built.
PROJECTS_BUILT = [
    ("Litchains", "BUILT"), ("Digitalchapbooks", "BUILT"),
    ("Rag-Read", "BUILT"), ("Rag-View", "BUILT"),
    ("Maskedposts", "BUILT"), ("Marginalia", "BUILT"),
    ("Applicant Targeting", "BUILT"), ("Frontend&Design", "BUILT"),
]
for proj, rel in PROJECTS_BUILT:
    try:
        db.query(
            f"MATCH (p:Entity), (pr:Entity) WHERE p.name = 'Shadwal Singh' AND pr.name = $proj MERGE (p)-[:{rel}]->(pr)",
            {"proj": proj}
        )
        print(f"  Shadwal Singh -[{rel}]-> {proj}")
    except Exception as e:
        print(f"  SKIP: {proj}: {e}")

# Org affiliations.
ORG_LINKS = [
    ("Shadwal Singh", "AFFILIATED_WITH", "Kalinga Institute Of Industrial Technology (Kiit)"),
    ("Shadwal Singh", "AFFILIATED_WITH", "Honeynet"),
    ("Shadwal Singh", "AFFILIATED_WITH", "Takshila Educational Society"),
    ("Shadwal Singh", "APPLIED_TO", "Google Summer Of Code 2026"),
    ("Shadwal Singh", "USES", "Vercel"),
    ("Shadwal Singh", "USES", "Linkedin"),
    ("Shadwal Singh", "USES", "Supabase"),
    ("Shadwal Singh", "USES", "Postgresql/Supabase"),
    ("Shadwal Singh", "USES", "Git/Github"),
    ("Shadwal Singh", "ROLE_AT", "L2Silver"),
    ("Shadwal Singh", "ROLE_AT", "Dsa"),
    ("Leadaiengineer", "ALIAS_OF", "Shadwal Singh"),
    ("Production Lead", "ROLE_OF", "Shadwal Singh"),
    ("Founding Team Member", "ROLE_OF", "Shadwal Singh"),
    ("Rag-View", "USES", "Neo4J"),
    ("Rag-View", "USES", "Chromadb"),
    ("Rag-View", "USES", "Gemini2.0Flash"),
    ("Rag-View", "USES", "Fastapi"),
    ("Rag-View", "USES", "Docker"),
    ("Rag-View", "USES", "Pydantic"),
    ("Rag-View", "USES", "Bm25Index"),
    ("Rag-Read", "USES", "Gemini1.5Flash"),
    ("Rag-Read", "USES", "Neo4Jvectorsearch"),
    ("Applicant Targeting", "USES", "Supabase"),
    ("Whyschool Academy", "USES", "Chromadb"),
    ("Google Summer Of Code 2026", "HOSTED_BY", "Honeynet"),
    ("Intel Owl", "BELONGS_TO", "Honeynet"),
]
for src, rel, tgt in ORG_LINKS:
    try:
        db.query(
            f"MATCH (s:Entity), (t:Entity) WHERE s.name = $src AND t.name = $tgt MERGE (s)-[:{rel}]->(t)",
            {"src": src, "tgt": tgt}
        )
        print(f"  {src} -[{rel}]-> {tgt}")
    except Exception as e:
        print(f"  SKIP: {src}->{tgt}: {e}")

# Fix the "Rag-Read|Leadaiengineer" compound node.
try:
    db.query("""
    MATCH (compound:Entity) WHERE compound.name = 'Rag-Read|Leadaiengineer'
    DETACH DELETE compound
    """)
    print("  Deleted compound node: Rag-Read|Leadaiengineer")
except Exception:
    pass

# Fix Munnegotiation -> MUN Negotiation (typo).
try:
    db.query("MATCH (n:Entity) WHERE n.name = 'Munnegotiation' SET n.name = 'Mun Negotiation', n.type = 'SKILL'")
    db.query("MATCH (p:Entity), (s:Entity) WHERE p.name = 'Shadwal Singh' AND s.name = 'Mun Negotiation' MERGE (p)-[:SKILL_IN]->(s)")
    print("  Fixed: Munnegotiation -> Mun Negotiation + linked to Shadwal Singh")
except Exception:
    pass

# --- Step 3: Verify ---.
print("\n=== Final Stats ===")
nodes = db.query("MATCH (n:Entity) RETURN count(n) AS c")
rels = db.query("MATCH ()-[r]->() RETURN count(r) AS c")
print(f"Nodes: {nodes[0]['c']}, Directed Edges: {rels[0]['c']}")

