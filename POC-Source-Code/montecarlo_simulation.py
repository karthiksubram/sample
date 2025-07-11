# montecarlo_simulation.py

import numpy as np
import sys
from pyspark.sql import SparkSession

# Function to be executed on each Spark executor
def estimate_pi_spark(iterations_per_executor):
    """
    Performs a portion of the Monte Carlo simulation to estimate Pi.
    This function will be serialized and sent to Spark executors.
    """
    points_inside_circle = 0
    # Simulate throwing darts at a unit square (0 to 1 in x and y)
    # and checking if they fall within a quarter-circle of radius 1.
    for _ in range(iterations_per_executor):
        x = np.random.uniform(0, 1)
        y = np.random.uniform(0, 1)
        distance = np.sqrt(x**2 + y**2) # Distance from origin (0,0)
        if distance <= 1:
            points_inside_circle += 1
    return points_inside_circle

if __name__ == "__main__":
    # Initialize SparkSession on the driver
    spark = SparkSession.builder \
        .appName("MonteCarloPiEstimation") \
        .getOrCreate()

    sc = spark.sparkContext

    # Parse total_iterations from command-line arguments
    # The first argument (sys.argv[0]) is the script name itself
    if len(sys.argv) > 1:
        try:
            total_iterations = int(sys.argv[1])
            if total_iterations <= 0:
                raise ValueError("Number of iterations must be positive.")
        except ValueError:
            print("Usage: spark-submit montecarlo_simulation.py <total_iterations>")
            sys.exit(1)
    else:
        # Default iterations if not provided
        total_iterations = 10000000
        print(f"No iterations specified. Using default: {total_iterations}")


    print(f"Starting Monte Carlo Pi estimation with {total_iterations} total iterations...")

    # Determine desired number of partitions (often related to number of cores/executors)
    # Using spark.sparkContext.defaultParallelism provides a reasonable default
    num_partitions = sc.defaultParallelism
    # Ensure at least one partition for small workloads
    if num_partitions == 0:
        num_partitions = 1

    # Distribute the total iterations among the partitions (and thus executors)
    # The map call will distribute the `estimate_pi_spark` function and execute it
    # in parallel across the partitions.
    # We create an RDD with `num_partitions` elements. Each element represents
    # the number of iterations for a specific partition.
    iterations_per_partition = [total_iterations // num_partitions] * num_partitions
    # Distribute any remaining iterations to the first partitions
    for i in range(total_iterations % num_partitions):
        iterations_per_partition[i] += 1

    # Create an RDD from the list of iterations per partition
    # Each element in this RDD will be processed by a task on an executor
    rdd_iterations = sc.parallelize(iterations_per_partition, num_partitions)

    # Apply the Monte Carlo simulation function on each partition
    # and sum up the points inside the circle from all partitions
    total_points_inside_circle = rdd_iterations.map(estimate_pi_spark).sum()

    # Calculate Pi estimate
    estimated_pi = 4 * total_points_inside_circle / total_iterations

    print(f"Monte Carlo Pi Estimation Complete.")
    print(f"Total points inside circle: {total_points_inside_circle}")
    print(f"Estimated Pi: {estimated_pi}")

    # Stop the SparkSession
    spark.stop()
