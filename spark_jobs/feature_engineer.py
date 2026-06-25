from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, avg, count, sum as spark_sum,
    when, round as spark_round, rank
)
from pyspark.sql.window import Window

def create_spark():
    return SparkSession.builder \
        .appName("OlistFeatureEngineer") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()

def engineer_features(master):

    # --- ORDER LEVEL FEATURES ---
    order_features = master.groupBy("order_id").agg(
        spark_sum("price").alias("order_total_price"),
        spark_sum("freight_value").alias("order_total_freight"),
        count("product_id").alias("order_item_count"),
        avg("avg_review_score").alias("order_review_score"),
        avg("delivery_delay_days").alias("order_delay_days"),
        avg("is_late").alias("order_is_late"),
        avg("total_payment").alias("order_payment_value"),
    )

    # --- SELLER LEVEL FEATURES ---
    seller_window = Window.partitionBy("seller_id")

    seller_features = master.withColumn(
        "seller_avg_review", avg("avg_review_score").over(seller_window)
    ).withColumn(
        "seller_late_rate", avg("is_late").over(seller_window)
    ).withColumn(
        "seller_total_orders", count("order_id").over(seller_window)
    ).withColumn(
        "seller_avg_price", avg("price").over(seller_window)
    ).select(
        "seller_id",
        "seller_city",
        "seller_state",
        "seller_avg_review",
        "seller_late_rate",
        "seller_total_orders",
        "seller_avg_price",
    ).dropDuplicates(["seller_id"])

    # --- PRODUCT CATEGORY FEATURES ---
    category_features = master.groupBy("product_category_name_english").agg(
        avg("price").alias("category_avg_price"),
        avg("avg_review_score").alias("category_avg_review"),
        count("order_id").alias("category_total_orders"),
        avg("is_late").alias("category_late_rate"),
    )

    # --- CUSTOMER FEATURES ---
    customer_features = master.groupBy("customer_state").agg(
        count("order_id").alias("state_total_orders"),
        avg("total_payment").alias("state_avg_payment"),
        avg("is_late").alias("state_late_rate"),
    )

    return order_features, seller_features, category_features, customer_features

if __name__ == "__main__":
    spark = create_spark()

    master = spark.read.parquet("data/processed/master.parquet")
    print(f"Loaded master: {master.count()} rows")

    order_f, seller_f, category_f, customer_f = engineer_features(master)

    order_f.write.mode("overwrite").parquet("data/processed/order_features.parquet")
    seller_f.write.mode("overwrite").parquet("data/processed/seller_features.parquet")
    category_f.write.mode("overwrite").parquet("data/processed/category_features.parquet")
    customer_f.write.mode("overwrite").parquet("data/processed/customer_features.parquet")

    print(f"Order features:    {order_f.count()} rows")
    print(f"Seller features:   {seller_f.count()} rows")
    print(f"Category features: {category_f.count()} rows")
    print(f"Customer features: {customer_f.count()} rows")
    print("All feature tables saved.")

    spark.stop()