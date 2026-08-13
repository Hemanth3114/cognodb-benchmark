import os

import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase


load_dotenv()

uri = os.getenv("COGNODB_URI")
username = os.getenv("COGNODB_USERNAME")
password = os.getenv("COGNODB_PASSWORD")


df = pd.read_csv("data/email_edges_canonical.csv")

# Take the next 100 rows after the 66,000 already stored.
batch = df.iloc[66000:66100]

rows = [
    {
        "source_id": int(row.source_id),
        "target_id": int(row.target_id),
        "timestamp": int(row.timestamp),
    }
    for row in batch.itertuples(index=False)
]


driver = GraphDatabase.driver(
    uri,
    auth=(username, password),
)


try:
    with driver.session() as session:

        query = """
        UNWIND $rows AS row

        MERGE (source:Person {id: row.source_id})
        MERGE (target:Person {id: row.target_id})

        CREATE (source)-[:EMAILS {
            timestamp: row.timestamp
        }]->(target)
        """

        session.run(
            query,
            rows=rows,
        ).consume()

        relationship_count = session.run(
            """
            MATCH ()-[r:EMAILS]->()
            RETURN count(r) AS count
            """
        ).single()["count"]

        print("Test rows sent:", len(rows))
        print("Relationships now:", relationship_count)

finally:
    driver.close()
    