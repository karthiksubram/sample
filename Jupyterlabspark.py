from pyspark.sql import SparkSession

# Replace these values as per your setup
ocp_api = "https://api.your-cluster.example.com:6443"
image = "quay.io/your-team/spark-py-custom:latest"
namespace = "your-namespace"
service_account = "spark"

spark = SparkSession.builder \
    .appName("pyspark-interactive-ocp") \
    .master(f"k8s://{ocp_api}") \
    .config("spark.kubernetes.container.image", image) \
    .config("spark.kubernetes.namespace", namespace) \
    .config("spark.kubernetes.authenticate.driver.serviceAccountName", service_account) \
    .config("spark.kubernetes.container.image.pullPolicy", "IfNotPresent") \
    .config("spark.kubernetes.driver.request.cores", "500m") \
    .config("spark.driver.memory", "1g") \
    .config("spark.executor.instances", "2") \
    .config("spark.executor.memory", "1g") \
    .config("spark.kubernetes.executor.request.cores", "500m") \
    .getOrCreate()

# Test Spark job
df = spark.range(0, 1000000).toDF("number")
df.selectExpr("sum(number)").show()
