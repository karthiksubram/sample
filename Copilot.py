from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

# Define a simple Python function for the tasks
def print_message(message):
    print(f"Message: {message}")

# Define the default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

# Define the DAG
with DAG(
    dag_id='airflow_example_dag',  # Use this dag_id in UI to trigger
    default_args=default_args,
    description='A simple example DAG',
    schedule_interval=None,  # Manual triggering
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['example'],
) as dag:

    start = PythonOperator(
        task_id='start_task',
        python_callable=print_message,
        op_kwargs={'message': 'This is the start task!'},
    )

    end = PythonOperator(
        task_id='end_task',
        python_callable=print_message,
        op_kwargs={'message': 'This is the end task!'},
    )

    start >> end
