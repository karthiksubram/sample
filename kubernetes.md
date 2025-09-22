# Kubernetes Architecture

Kubernetes uses a **client-server architecture**, organizing machines into a **cluster**.  
This cluster is comprised of:

- **Control Plane** → the "brain" of the cluster, making decisions and orchestrating the system.  
- **Worker Nodes** → the "muscles" where your applications and workloads actually run.  

The goal of this architecture is to provide a **highly available and self-healing environment** for containerized applications.

---

## Control Plane Components

- **API Server**  
  The front-end of the Control Plane.  
  It’s the central hub for all communication and provides the **Kubernetes API**.  
  All other components, including `kubectl`, communicate with the cluster through this server.

- **etcd**  
  A consistent and highly available key-value store.  
  It serves as the **single source of truth** for the cluster’s state, storing all configuration data.

- **Scheduler**  
  Watches for new pods that have no assigned node and selects the best node for them to run on,  
  based on resource availability and other constraints.

- **Controller Manager**  
  Runs various controllers that continuously monitor the state of the cluster  
  and ensure it matches the **desired state**.  
  Example: A **Replication Controller** ensures the correct number of pod replicas are running.

---

## Worker Node Components

- **Kubelet**  
  An agent that runs on each worker node.  
  Communicates with the API server, ensuring containers are running in a pod and remain healthy.

- **Kube-Proxy**  
  A network proxy that runs on each node.  
  Maintains network rules, allowing communication **between pods** and from **external sources** to pods.

- **Container Runtime**  
  The software responsible for running the containers.  
  Examples: **containerd, CRI-O, or Docker**.

``` mermaid
graph TD
    subgraph "Kubernetes Cluster"
        subgraph "Control Plane (Master)"
            API[API Server] -->|Reads & Writes| etcd[(etcd)]
            Scheduler[Scheduler] -->|Watches Pods| API
            Controller[Controller Manager] -->|Watches Cluster State| API
        end

        subgraph "Worker Node (1)"
            Kubelet1[Kubelet]
            KubeProxy1[Kube-Proxy]
            ContainerRuntime1[Container Runtime]
            Kubelet1 -->|Manages| Pod1[Pod]
            KubeProxy1 -->|Proxies Traffic| Pod1
        end

        subgraph "Worker Node (2)"
            Kubelet2[Kubelet]
            KubeProxy2[Kube-Proxy]
            ContainerRuntime2[Container Runtime]
            Kubelet2 -->|Manages| Pod2[Pod]
            KubeProxy2 -->|Proxies Traffic| Pod2
        end

        API -->|Communicates with| Kubelet1
        API -->|Communicates with| Kubelet2
    end
```
