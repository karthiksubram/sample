# What is an OCP Pod?

An **OpenShift Container Platform (OCP) pod** is the smallest, most fundamental unit you can deploy and manage on the OpenShift platform.  
It is a concept adopted directly from **Kubernetes**.  

A pod is a collection of one or more containers that are deployed together on a single host machine, known as a **node**.

---

## Key Characteristics 

- **Shared Resources**  
  Containers within the same pod share the same network namespace, internal IP address, and port space.  
  They can also share local storage volumes.

- **Immutable and Expendable**  
  Pods are treated as largely immutable. Once a pod is running, you cannot change its definition.  
  To apply changes, OCP terminates the existing pod and creates a new one with the updated configuration.  
  Pods are also considered "expendable" and do not maintain state, which is why they are typically managed by higher-level controllers like **Deployments**.

- **Single IP per Pod**  
  Each pod is assigned its own internal IP address.  
  This means all containers within that pod use that same IP.

---

# Pod Architecture and Components

A pod is a **logical grouping** that runs containers. It can contain:

- **One or more containers**  
  Core components that run your application code and dependencies.  
  Example: A pod might contain a main application container and a *sidecar* container for logging or monitoring.

- **Storage volumes**  
  Shared among containers in the pod, allowing data sharing or persistent storage.

- **Init Containers**  
  Special containers that run **to completion before** the main application containers start.  
  Used for setup tasks (e.g., waiting for a service, fetching configuration).

---

## How it works 

1. **Pod Definition**  
   Defined using a YAML or JSON file.  
   Specifies container images, attached volumes, and other configs.

2. **Scheduling**  
   The OpenShift scheduler assigns the pod to an available worker node based on resource availability (CPU, memory, etc.).

3. **Execution**  
   The **kubelet** service on the worker node ensures containers are running and healthy.  
   It also manages **liveness** and **readiness probes** to monitor app health.



```
# Sample Pod YAML for OpenShift

Below is an example of a Pod configuration YAML file for OpenShift Container Platform (OCP):

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: sample-pod
  namespace: default
  labels:
    app: sample-app
spec:
  initContainers:
  - name: init-setup
    image: busybox:latest
    command: ['sh', '-c', 'echo "Initialized by init container" > /mnt/data/init.txt']
    volumeMounts:
    - name: sample-storage
      mountPath: /mnt/data
  containers:
  - name: sample-container
    image: nginx:latest
    command: ['nginx']
    args: ['-g', 'daemon off;']
    ports:
    - containerPort: 80
      protocol: TCP
    resources:
      requests:
        memory: "64Mi"
        cpu: "250m"
      limits:
        memory: "128Mi"
        cpu: "500m"
    env:
    - name: EXAMPLE_ENV
      value: "test"
    volumeMounts:
    - name: sample-storage
      mountPath: /usr/share/nginx/html/data
  volumes:
  - name: sample-storage
    persistentVolumeClaim:
      claimName: sample-pvc
  restartPolicy: Always
```
# Diagram

``` mermaid
graph TD
    A[Pod: sample-pod] --> B[Init Container: init-setup]
    A --> C[Container: sample-container]
    A --> D[Volume: sample-storage]
    D --> E[PVC: sample-pvc]
    B -->|Mount| D
    C -->|Mount| D

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bfb,stroke:#333,stroke-width:2px
    style D fill:#ffb,stroke:#333,stroke-width:2px
    style E fill:#fbf,stroke:#333,stroke-width:2px


![Pods](./pods.jpg)
