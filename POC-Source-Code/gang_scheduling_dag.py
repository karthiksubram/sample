# gang_scheduling_dag.py (Direct Worker Creation - Complete File)
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.utils.dates import days_ago
import pendulum
from kubernetes.client import models as k8s # Import Kubernetes models

# --- Gang Scheduling Parameters ---
GANG_GROUP_NAME = "my-direct-worker-gang" # Unique name for this gang
GANG_MIN_WORKERS = 3 # The total number of worker pods that must start atomically
YUNIKORN_QUEUE_WORKERS = "root.gang_jobs" # Yunikorn queue for these workers

# --- Define the base pod spec for a worker ---
# This will be copied and customized for each worker
def create_worker_base_pod_spec(worker_id: int):
    return k8s.V1Pod(
        api_version="v1",
        kind="Pod",
        metadata=k8s.V1ObjectMeta(
            # Name will be overridden by Airflow's task_id, but define a base for clarity
            labels={
                "app": "gang-worker",
                "gang-member-id": str(worker_id),
                # Yunikorn Gang Scheduling Labels (same for all workers in the gang)
                "yunikorn.apache.org/queue": YUNIKORN_QUEUE_WORKERS,
                "scheduling.k8s.io/group-name": GANG_GROUP_NAME,
                "scheduling.k8s.io/group-min-members": str(GANG_MIN_WORKERS),
            }
        ),
        spec=k8s.V1PodSpec(
            scheduler_name='yunikorn', # Ensure Yunikorn is the scheduler
            restart_policy="Never", # Or 'OnFailure' if you want K8s to retry
            containers=[
                k8s.V1Container(
                    name=f"worker-container-{worker_id}", # Unique name for clarity
                    image="busybox", # Using busybox for simple worker tasks
                    command=["sh", "-c", f"echo 'Worker {worker_id} starting'; sleep 30; echo 'Worker {worker_id} finished'"],
                    resources=k8s.V1ResourceRequirements(
                        requests={"cpu": "100m", "memory": "128Mi"},
                        limits={"cpu": "200m", "memory": "256Mi"},
                    ),
                )
            ]
        )
    )

with DAG(
    dag_id='yunikorn_gang_scheduling_direct_workers', # New DAG ID
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    tags=['yunikorn', 'kubernetes', 'direct_workers', 'gang_scheduling'],
) as dag:
    
    worker_tasks = []
    # Create GANG_MIN_WORKERS KubernetesPodOperator tasks
    for i in range(1, GANG_MIN_WORKERS + 1):
        worker_pod_spec = create_worker_base_pod_spec(i)
        
        # Override the pod's name for unique task_id and clarity in K8s
        # Airflow usually assigns a unique name, but you can influence it
        # This is optional, but helps with clarity in K8s UI/logs
        worker_pod_spec.metadata.name = f"gang-worker-{i}-{{{{ ts_nodash }}}}" 
        
        worker_task = KubernetesPodOperator(
            task_id=f'gang_worker_{i}', # Unique task ID for each worker
            namespace='airflow', # Or your target namespace
            full_pod_spec=worker_pod_spec,
            do_xcom_push=False,
        )
        worker_tasks.append(worker_task)

    # In this direct approach, all worker tasks are launched concurrently by Airflow.
    # Yunikorn's gang scheduling logic will ensure they don't *start running*
    # until GANG_MIN_WORKERS pods are ready for placement.
    # No explicit dependencies are needed here for them to run in parallel.

