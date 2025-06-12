from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

import boto3
from botocore.client import Config

BUCKET_NAME = 'airflow-business-bucket'
OBJECT_KEY = 'example-data.txt'
MINIO_ENDPOINT = 'http://minio.airflow.svc.cluster.local:9000'
MINIO_ACCESS_KEY = 'minioadmin'
MINIO_SECRET_KEY = 'minioadmin'

def upload_file_to_minio():
    s3_client = boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

    # Create bucket if not exists
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
    except:
        print(f"Creating bucket: {BUCKET_NAME}")
        s3_client.create_bucket(Bucket=BUCKET_NAME)

    # Upload file
    content = b'Business data example from Airflow!'
    s3_client.put_object(Bucket=BUCKET_NAME, Key=OBJECT_KEY, Body=content)
    print(f"Uploaded {OBJECT_KEY} to bucket {BUCKET_NAME}")

def list_files_in_minio():
    s3_client = boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
    if 'Contents' in response:
        print("Files in bucket:")
        for obj in response['Contents']:
            print(f"- {obj['Key']}")
    else:
        print("Bucket is empty.")

with DAG(
    'minio_python_example_dag',
    schedule_interval=None,
    start_date=days_ago(1),
    catchup=False,
) as dag:

    upload_task = PythonOperator(
        task_id='upload_file_to_minio',
        python_callable=upload_file_to_minio,
    )

    list_task = PythonOperator(
        task_id='list_files_in_minio',
        python_callable=list_files_in_minio,
    )

    upload_task >> list_task
