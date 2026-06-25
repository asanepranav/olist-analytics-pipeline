import duckdb
import os

DB_PATH = "db/olist.duckdb"

def get_conn():
    os.makedirs("db", exist_ok=True)
    return duckdb.connect(DB_PATH)

def load_table(conn, name, path):
    conn.execute(f"""
        CREATE OR REPLACE TABLE {name} AS
        SELECT * FROM read_parquet('{path}/*.parquet')
    """)
    count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    print(f"Loaded {name}: {count} rows")

def load_all(conn):
    tables = {
        "master":            "data/processed/master.parquet",
        "order_features":    "data/processed/order_features.parquet",
        "seller_features":   "data/processed/seller_features.parquet",
        "category_features": "data/processed/category_features.parquet",
        "customer_features": "data/processed/customer_features.parquet",
    }
    for name, path in tables.items():
        load_table(conn, name, path)

def verify(conn):
    print("\n=== VERIFICATION ===")

    print("\nTop 5 sellers by avg review:")
    print(conn.execute("""
        SELECT seller_id, seller_state,
               ROUND(seller_avg_review, 2) as avg_review,
               seller_total_orders
        FROM seller_features
        ORDER BY seller_avg_review DESC
        LIMIT 5
    """).df().to_string())

    print("\nTop 5 categories by order volume:")
    print(conn.execute("""
        SELECT product_category_name_english,
               category_total_orders,
               ROUND(category_avg_price, 2) as avg_price,
               ROUND(category_avg_review, 2) as avg_review
        FROM category_features
        ORDER BY category_total_orders DESC
        LIMIT 5
    """).df().to_string())

    print("\nLate delivery rate by state (top 5 worst):")
    print(conn.execute("""
        SELECT customer_state,
               state_total_orders,
               ROUND(state_late_rate * 100, 1) as late_pct
        FROM customer_features
        ORDER BY state_late_rate DESC
        LIMIT 5
    """).df().to_string())

if __name__ == "__main__":
    conn = get_conn()
    load_all(conn)
    verify(conn)
    conn.close()
    print(f"\nDuckDB saved to {DB_PATH}")