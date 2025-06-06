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

# Define KubernetesExecutor resource requirements
executor_config = {
    "KubernetesExecutor": {
        "request_memory": "128Mi",
        "request_cpu": "100m",
        "limit_memory": "256Mi",
        "limit_cpu": "200m",
    }
}

# Define the DAG
with DAG(
    dag_id='abcd_dag',  # Your new dag_id
    default_args=default_args,
    description='A simple example DAG with KubernetesExecutor resource config',
    schedule_interval=None,  # Manual triggering
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['example'],
) as dag:

    start = PythonOperator(
        task_id='start_task',
        python_callable=print_message,
        op_kwargs={'message': 'This is the start task!'},
        executor_config=executor_config,
    )

    end = PythonOperator(
        task_id='end_task',
        python_callable=print_message,
        op_kwargs={'message': 'This is the end task!'},
        executor_config=executor_config,
    )

    start >> end
