from pyspark.sql import SparkSession
import os

RAW_PATH = "data/raw"

def create_spark():
    return SparkSession.builder \
        .appName("OlistIngest") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()

def load_all(spark):
    csvs = {
        "orders":        "olist_orders_dataset.csv",
        "order_items":   "olist_order_items_dataset.csv",
        "products":      "olist_products_dataset.csv",
        "customers":     "olist_customers_dataset.csv",
        "sellers":       "olist_sellers_dataset.csv",
        "reviews":       "olist_order_reviews_dataset.csv",
        "payments":      "olist_order_payments_dataset.csv",
        "geolocation":   "olist_geolocation_dataset.csv",
        "category":      "product_category_name_translation.csv",
    }

    dfs = {}
    for name, fname in csvs.items():
        path = os.path.join(RAW_PATH, fname)
        dfs[name] = spark.read.csv(path, header=True, inferSchema=True)
        print(f"Loaded {name}: {dfs[name].count()} rows")
    
    return dfs

if __name__ == "__main__":
    spark = create_spark()
    dfs = load_all(spark)
    spark.stop()