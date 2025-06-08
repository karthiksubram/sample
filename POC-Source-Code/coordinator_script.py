# coordinator_script.py (Revised)
import os
import kubernetes
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kubernetes configuration
try:
    kubernetes.config.load_incluster_config()
except kubernetes.config.config_exception.ConfigException:
    kubernetes.config.load_kube_config()

v1 = kubernetes.client.CoreV1Api()

NAMESPACE = os.getenv("POD_NAMESPACE", "airflow")
GANG_GROUP_NAME = os.getenv("GANG_GROUP_NAME", "default-gang-workers") # Updated default
GANG_MIN_WORKERS = int(os.getenv("GANG_MIN_WORKERS", "1")) # Renamed env var
YUNIKORN_QUEUE_WORKERS = os.getenv("YUNIKORN_QUEUE_WORKERS", "root.gang_jobs") # Queue for workers

logger.info(f"Coordinator script started. Namespace: {NAMESPACE}, Gang Group: {GANG_GROUP_NAME}, Min Workers: {GANG_MIN_WORKERS}, Yunikorn Queue (Workers): {YUNIKORN_QUEUE_WORKERS}")

def create_worker_pod_spec(worker_id: int):
    """Creates a Kubernetes Pod spec for a worker."""
    return kubernetes.client.V1Pod(
        api_version="v1",
        kind="Pod",
        metadata=kubernetes.client.V1ObjectMeta(
            name=f"gang-worker-{worker_id}-{int(time.time())}",
            labels={
                "app": "gang-worker",
                "gang-member-id": str(worker_id),
                # Yunikorn Gang Scheduling Annotations for WORKER PODS
                "yunikorn.apache.org/queue": YUNIKORN_QUEUE_WORKERS,
                "scheduling.k8s.io/group-name": GANG_GROUP_NAME,
                "scheduling.k8s.io/group-min-members": str(GANG_MIN_WORKERS), # MINIMUM WORKERS
            }
        ),
        spec=kubernetes.client.V1PodSpec(
            scheduler_name='yunikorn', # IMPORTANT: Still schedule workers via Yunikorn
            restart_policy="Never",
            containers=[
                kubernetes.client.V1Container(
                    name="worker-container",
                    image="busybox",
                    command=["sh", "-c", f"echo 'Worker {worker_id} starting'; sleep 30; echo 'Worker {worker_id} finished'"],
                    resources=kubernetes.client.V1ResourceRequirements(
                        requests={"cpu": "100m", "memory": "128Mi"},
                        limits={"cpu": "200m", "memory": "256Mi"},
                    ),
                )
            ]
        )
    )

worker_pods = []
# Create exactly GANG_MIN_WORKERS for the gang demo
# If you want to create more than min workers, you'd adjust this loop
for i in range(1, GANG_MIN_WORKERS + 1): # Loop from 1 to GANG_MIN_WORKERS (inclusive)
    worker_pod_spec = create_worker_pod_spec(i)
    try:
        logger.info(f"Creating worker pod: {worker_pod_spec.metadata.name}")
        api_response = v1.create_namespaced_pod(body=worker_pod_spec, namespace=NAMESPACE)
        worker_pods.append(api_response)
        logger.info(f"Worker pod '{api_response.metadata.name}' created.")
    except kubernetes.client.ApiException as e:
        logger.error(f"Error creating worker pod {worker_pod_spec.metadata.name}: {e}")
        raise

logger.info(f"Waiting for {len(worker_pods)} worker pods to complete...")
for pod in worker_pods:
    name = pod.metadata.name
    while True:
        try:
            pod_status = v1.read_namespaced_pod_status(name=name, namespace=NAMESPACE)
            if pod_status.status.phase == "Succeeded":
                logger.info(f"Pod '{name}' Succeeded.")
                break
            elif pod_status.status.phase == "Failed":
                logger.error(f"Pod '{name}' Failed!")
                raise Exception(f"Worker pod {name} failed.")
            else:
                logger.info(f"Pod '{name}' status: {pod_status.status.phase}. Waiting...")
                time.sleep(5)
        except kubernetes.client.ApiException as e:
            if e.status == 404:
                logger.warning(f"Pod '{name}' not found. It might have been deleted. Assuming failure.")
                raise Exception(f"Worker pod {name} not found.")
            else:
                logger.error(f"Error checking status for pod '{name}': {e}")
                raise
logger.info("All worker pods completed successfully. Coordinator script finished.")