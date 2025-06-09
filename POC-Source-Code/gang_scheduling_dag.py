# gang_scheduling_dag.py (Revised - using full_pod_spec)
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.utils.dates import days_ago
import pendulum
from kubernetes.client import models as k8s # Import Kubernetes models

# Define a unique group name for your gang
GANG_GROUP_NAME = "my-simulated-distributed-job-workers"
GANG_MIN_WORKERS = 3

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

# --- Define the full pod spec for the Coordinator Pod ---
coordinator_pod_spec = k8s.V1Pod(
    api_version="v1",
    kind="Pod",
    metadata=k8s.V1ObjectMeta(
        # Name will be overridden by Airflow
        labels={
            "yunikorn.apache.org/queue": "root.launch_pods",
            "app": "gang-coordinator"
        }
    ),
    spec=k8s.V1PodSpec(
        # THIS IS WHERE schedulerName IS SET NOW
        scheduler_name='yunikorn',
        restart_policy='Never', # Or 'OnFailure', depending on desired retry behavior
        containers=[
            k8s.V1Container(
                name="base", # Name is typically "base" for KPO, but can be anything
                image='python:3.9-slim-buster',
                command=["python"],
                args=[f"{volume_mount_path}/coordinator_script.py"],
                resources=k8s.V1ResourceRequirements(
                    requests={"cpu": "50m", "memory": "64Mi"},
                    limits={"cpu": "100m", "memory": "128Mi"},
                ),
                env=[
                    k8s.V1EnvVar(name="POD_NAMESPACE", value="airflow"),
                    k8s.V1EnvVar(name="GANG_GROUP_NAME", value=GANG_GROUP_NAME),
                    k8s.V1EnvVar(name="GANG_MIN_WORKERS", value=str(GANG_MIN_WORKERS)),
                    k8s.V1EnvVar(name="YUNIKORN_QUEUE_WORKERS", value="root.gang_jobs"),
                ],
                volume_mounts=[volume_mount], # Mount the volume here
            )
        ],
        volumes=[volume], # Define the volume at the pod level
    )
)
# --- End of full pod spec definition ---


with DAG(
    dag_id='yunikorn_gang_scheduling_poc_mounted_script_full_spec', # Changed DAG ID
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    tags=['yunikorn', 'kubernetes', 'poc', 'gang_scheduling', 'full_spec'],
) as dag:
    
    launch_gang_coordinator = KubernetesPodOperator(
        task_id='launch_gang_coordinator',
        namespace='airflow',  # The namespace where the pod will be created
        
        # --- Use full_pod_spec instead of individual arguments ---
        full_pod_spec=coordinator_pod_spec,
        # --------------------------------------------------------
        
        # Other KPO arguments that are still valid (e.g., name, image) can be omitted
        # if they are defined in full_pod_spec.
        # However, some KPO arguments like 'namespace' are often used for convenience
        # and override what's in full_pod_spec if they conflict.
        # It's generally best to define it directly in full_pod_spec for consistency.
        
        do_xcom_push=False,
    )
