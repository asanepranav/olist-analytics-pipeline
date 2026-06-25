import pandas as pd

print("=== PAYMENTS ===")
df = pd.read_csv('data/raw/olist_order_payments_dataset.csv')
print(df.dtypes)
print("Bad payment_value rows:")
print(df[pd.to_numeric(df['payment_value'], errors='coerce').isna()].head(5))

print("\n=== REVIEWS ===")
df2 = pd.read_csv('data/raw/olist_order_reviews_dataset.csv')
print(df2.dtypes)
print("Bad review_score rows:")
print(df2[pd.to_numeric(df2['review_score'], errors='coerce').isna()].head(5))

print("\n=== ORDER ITEMS ===")
df3 = pd.read_csv('data/raw/olist_order_items_dataset.csv')
print(df3.dtypes)
print("Bad price rows:")
print(df3[pd.to_numeric(df3['price'], errors='coerce').isna()].head(5))