from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, datediff, to_timestamp
from pyspark.sql.types import DoubleType, IntegerType

def create_spark():
    import os
    os.environ["HADOOP_HOME"] = "C:\\hadoop"
    os.environ["PATH"] = os.environ["PATH"] + ";C:\\hadoop\\bin"
    
    return SparkSession.builder \
        .appName("OlistClean") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()

def create_spark():
    return SparkSession.builder \
        .appName("OlistClean") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()

def load_all(spark):
    path = "data/raw"
    # Standard load for clean CSVs
    def std(fname):
        return spark.read.csv(f"{path}/{fname}", header=True, inferSchema=True)

    # Safe load for CSVs with free-text columns (multiline comments)
    def safe(fname):
        return spark.read.option("multiLine", True) \
                         .option("escape", '"') \
                         .csv(f"{path}/{fname}", header=True, inferSchema=False)

    return {
        "orders":      std("olist_orders_dataset.csv"),
        "order_items": std("olist_order_items_dataset.csv"),
        "products":    std("olist_products_dataset.csv"),
        "customers":   std("olist_customers_dataset.csv"),
        "sellers":     std("olist_sellers_dataset.csv"),
        "reviews":     safe("olist_order_reviews_dataset.csv"),
        "payments":    std("olist_order_payments_dataset.csv"),
        "category":    std("product_category_name_translation.csv"),
    }

def clean_orders(orders):
    return orders.filter(
        (col("order_status") == "delivered") &
        col("order_delivered_customer_date").isNotNull() &
        col("order_purchase_timestamp").isNotNull()
    )

def build_master(dfs):
    orders    = clean_orders(dfs["orders"])
    items     = dfs["order_items"]
    products  = dfs["products"]
    customers = dfs["customers"]
    sellers   = dfs["sellers"]
    reviews   = dfs["reviews"]
    payments  = dfs["payments"]
    category  = dfs["category"]

    # Payments agg
    pay_agg = payments.groupBy("order_id").agg(
        {"payment_value": "sum", "payment_installments": "avg"}
    ).withColumnRenamed("sum(payment_value)", "total_payment") \
     .withColumnRenamed("avg(payment_installments)", "avg_installments")

    # Reviews — cast after safe load
    rev_agg = reviews \
        .withColumn("review_score", col("review_score").cast(DoubleType())) \
        .filter(col("review_score").isNotNull()) \
        .groupBy("order_id").agg(
            {"review_score": "avg"}
        ).withColumnRenamed("avg(review_score)", "avg_review_score")

    # Translate product category
    products = products.join(category, on="product_category_name", how="left")

    # Join everything
    master = orders \
        .join(items,     on="order_id",    how="left") \
        .join(products,  on="product_id",  how="left") \
        .join(customers, on="customer_id", how="left") \
        .join(sellers,   on="seller_id",   how="left") \
        .join(pay_agg,   on="order_id",    how="left") \
        .join(rev_agg,   on="order_id",    how="left")

    # Delivery delay in days
    master = master.withColumn(
        "delivery_delay_days",
        datediff(
            to_timestamp(col("order_delivered_customer_date")),
            to_timestamp(col("order_estimated_delivery_date"))
        )
    )

    # Late flag
    master = master.withColumn(
        "is_late",
        when(col("delivery_delay_days") > 0, 1).otherwise(0)
    )

    return master

if __name__ == "__main__":
    spark = create_spark()
    dfs = load_all(spark)
    master = build_master(dfs)

    print(f"Master dataset: {master.count()} rows, {len(master.columns)} columns")
    master.printSchema()

    master.write.mode("overwrite").parquet("data/processed/master.parquet")
    print("Saved to data/processed/master.parquet")

    spark.stop()