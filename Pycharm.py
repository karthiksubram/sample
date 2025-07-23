# my_pyspark_app.py
from pyspark.sql import SparkSession
import os

if __name__ == "__main__":
    spark = SparkSession.builder \
        .appName("PySpark-PyCharm-OCP-Example") \
        .getOrCreate()

    print("Spark application started!")
    print(f"Running on Spark version: {spark.version}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Pod name (if in K8s): {os.environ.get('KUBERNETES_POD_NAME', 'Not-in-K8s')}")

    data = [("Alice", 1), ("Bob", 2), ("Charlie", 3)]
    df = spark.createDataFrame(data, ["Name", "ID"])

    print("DataFrame content:")
    df.show()

    # Perform a simple aggregation
    count = df.count()
    print(f"Total rows in DataFrame: {count}")

    spark.stop()
    print("Spark application finished.")
