# gang_scheduling_dag.py (Revised)
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.utils.dates import days_ago
import pendulum
from kubernetes.client import models as k8s # Import Kubernetes models

# Define a unique group name for your gang
GANG_GROUP_NAME = "my-simulated-distributed-job-workers" # Name specific to workers
GANG_MIN_WORKERS = 3 # NOW this refers ONLY to the minimum number of worker pods in the gang

# Define your volume and volume mount configuration for the coordinator pod
volume_name = "scripts-pvc-volume"
volume_mount_path = "/opt/mounted_scripts"

volume = k8s.V1Volume(
    name=volume_name,
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(claim_name="airflow-scripts-pvc")
)

volume_mount = k8s.V1VolumeMount(
    name=volume_name,
    mount_path=volume_mount_path,
    read_only=True
)

with DAG(
    dag_id='yunikorn_gang_scheduling_poc_mounted_script_revised', # Changed DAG ID
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    tags=['yunikorn', 'kubernetes', 'poc', 'gang_scheduling', 'mounted_script', 'revised'],
) as dag:
    
    launch_gang_coordinator = KubernetesPodOperator(
        task_id='launch_gang_coordinator',
        namespace='airflow',
        image='python:3.9-slim-buster',
        cmds=["python"],
        arguments=[f"{volume_mount_path}/coordinator_script.py"],
        
        volumes=[volume],
        volume_mounts=[volume_mount],

        # The Coordinator Pod is scheduled by Yunikorn, but it's NOT part of the gang's atomic minimum.
        # It just uses Yunikorn as its scheduler and belongs to a specific queue.
        scheduler_name='yunikorn',
        labels={
            "yunikorn.apache.org/queue": "root.launch_pods", # A queue for launcher/coordinator pods
            "app": "gang-coordinator" # General label
            # IMPORTANT: REMOVED GANG_GROUP_NAME and GANG_MIN_MEMBERS from here
        },
        container_resources={
            "requests": {"cpu": "50m", "memory": "64Mi"},
            "limits": {"cpu": "100m", "memory": "128Mi"},
        },
        env_vars={
            "POD_NAMESPACE": "airflow",
            "GANG_GROUP_NAME": GANG_GROUP_NAME,
            "GANG_MIN_WORKERS": str(GANG_MIN_WORKERS), # Renamed for clarity
            "YUNIKORN_QUEUE_WORKERS": "root.gang_jobs", # Queue for workers
        },
        do_xcom_push=False,
    )