from pyspark.sql import SparkSession

def main():
    # 1️⃣ Spark Session with Nessie + Iceberg + MinIO S3 + MySQL
    spark = SparkSession.builder \
        .appName("MySQL_to_Nessie_Example") \
        .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
        .config("spark.sql.catalog.nessie.uri", "http://nessie-service:19120/api/v1") \
        .config("spark.sql.catalog.nessie.ref", "main") \
        .config("spark.sql.catalog.nessie.warehouse", "s3a://mybucket/warehouse/") \
        .config("spark.sql.catalog.nessie.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio-service:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

    # 2️⃣ Read data from MySQL using JDBC
    mysql_url = "jdbc:mysql://mysql-service:3306/mydb"
    mysql_table = "customer_data"
    mysql_props = {
        "user": "myuser",
        "password": "mypassword",
        "driver": "com.mysql.cj.jdbc.Driver"
    }

    print("Reading data from MySQL...")
    df = spark.read.jdbc(url=mysql_url, table=mysql_table, properties=mysql_props)
    df.show()

    # 3️⃣ Create Nessie namespace if not exists
    spark.sql("CREATE DATABASE IF NOT EXISTS nessie.analytics")

    # 4️⃣ Create Nessie Iceberg table (if not exists)
    spark.sql("""
        CREATE TABLE IF NOT EXISTS nessie.analytics.customer_data (
            id INT,
            name STRING,
            email STRING,
            created_at TIMESTAMP
        )
        USING iceberg
    """)

    # 5️⃣ Write to Nessie Iceberg table
    print("Writing to Nessie...")
    df.writeTo("nessie.analytics.customer_data").append()

    # 6️⃣ Read back and verify
    print("Verifying written data...")
    spark.sql("SELECT * FROM nessie.analytics.customer_data").show()

    spark.stop()

if __name__ == "__main__":
    main()
