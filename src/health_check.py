import sys

from database import db


def check_connection():
    try:
        # Check basic connection.
        result = db.query("RETURN 1 as test")
        if not result or result[0]["test"] != 1:
            print("Failed to connect to Neo4j.")
            sys.exit(1)
        print("✅ Successfully connected to Neo4j.")

        # Check plugins (GDS) - Optional for Hybrid/AuraDB Free compatibility.
        try:
            plugins = db.query("CALL gds.version() YIELD gdsVersion")
            if plugins:
                print(f"✅ GDS Plugin active. Version: {plugins[0]['gdsVersion']}")
            else:
                print("⚠️ GDS Plugin not found. App will use Cypher fallback for community detection.")
        except Exception:
            print("⚠️ GDS Plugin not found or unavailable. App will use Cypher fallback for community detection.")
            
        # Check APOC.
        try:
            apoc = db.query("CALL apoc.help('apoc') YIELD name LIMIT 1")
            if apoc:
                print("✅ APOC Plugin active.")
            else:
                print("❌ APOC Plugin not found.")
                sys.exit(1)
        except Exception as e:
            print(f"❌ APOC Plugin check failed: {e}")
            sys.exit(1)

        # Apply schema.
        db.setup_schema()
        
        sys.exit(0)
    except Exception as e:
        print(f"Connection or health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_connection()

