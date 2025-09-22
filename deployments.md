# Slide 1: What is an OCP Deployment?

An **OpenShift Container Platform (OCP) Deployment** is a higher-level object that manages the life cycle of your application pods.  
While a **Pod** is the smallest unit of deployment, a **Deployment** is the object you use to manage pods in a production environment.  

It provides a **declarative way** to define the desired state of your application, such as:
- How many replicas (pods) should be running  
- What container image they should use  

---

## Key Functions ⚙️

- **Self-Healing**  
  A Deployment continuously monitors the health of its pods.  
  If a pod fails or is deleted, the Deployment automatically creates a new one to maintain the desired replica count.

- **Scalability**  
  You can easily scale your application up or down by changing the number of replicas in the Deployment configuration.

- **Version Control**  
  Deployments are versioned. Every time you make a change, a new revision is created.  
  This allows easy rollback to a previous, stable version if an update fails.

---

## Deployment vs. Pod 🤼

Think of it this way:

- **Pod**:  
  A Pod is like a single running instance of your application.  
  If it crashes, it’s gone for good. You would rarely use a standalone pod in a real-world scenario.

- **Deployment**:  
  A Deployment is the *manager* that ensures your application is always running.  
  It uses a **ReplicaSet** (another Kubernetes object) behind the scenes to create and maintain the pods, guaranteeing high availability and reliability.

---

# Slide 2: Common Deployment Strategies

OCP Deployments offer several strategies to update your application with minimal or zero downtime.  
The choice of strategy depends on your application’s needs and tolerance for downtime.

---

## Key Strategies 🚀

- **Rolling Update (Default)**  
  Most common and recommended.  
  Gradually replaces old pods with new ones.  
  New pods are created one by one, and old pods are terminated only after the new ones are ready.  
  ✅ Ensures the application remains available throughout the update.

- **Recreate**  
  Simple but causes downtime.  
  First terminates all existing pods, then creates the new version.  
  ✅ Suitable for development/testing where brief outages are acceptable.

- **Blue/Green**  
  Runs two identical environments: **Blue** (current production) and **Green** (new version).  
  Once Green is tested and ready, the router instantly switches all traffic to Green.  
  ✅ Zero-downtime switch, easy rollback by switching back to Blue.

- **Canary**  
  A progressive deployment strategy.  
  Release the new version to a small, controlled group (e.g., 5% of traffic).  
  Monitor performance, then gradually increase traffic until fully rolled out.  
  ✅ Minimizes risk of a bad deployment impacting all users.

---

These strategies provide the **flexibility needed for modern DevOps workflows**, allowing you to safely and efficiently update your applications.

``` yaml
#--- Mandatory Section 1: API Version, Kind, and Metadata ---

# apiVersion: Specifies the Kubernetes API version.
# For Deployments, this is typically 'apps/v1'.
apiVersion: apps/v1

# kind: The type of resource you are creating.
# This must be 'Deployment' for a Deployment object.
kind: Deployment

# metadata: Contains data that uniquely identifies this object.
metadata:
  # name: A mandatory name for the Deployment. This must be unique within its namespace.
  name: my-app-deployment
  # namespace: (Optional but recommended) The Kubernetes namespace to deploy to.
  # If not specified, it will be deployed to the 'default' namespace.
  namespace: my-app-namespace

#--- Mandatory Section 2: Spec (Deployment Specification) ---

# spec: The desired state of the Deployment.
spec:
  # replicas: (Mandatory) The number of identical pods to run.
  # The Deployment controller will ensure this many pods are always running.
  replicas: 3

  # selector: (Mandatory) A label selector that defines which pods the Deployment manages.
  # The labels in the pod template below must match this selector.
  selector:
    matchLabels:
      app: my-app

  # template: (Mandatory) The pod template.
  # This is the blueprint for the pods that the Deployment will create.
  template:
    # metadata: The metadata for the pods created by this template.
    metadata:
      # labels: (Mandatory) The labels that must match the Deployment's selector.
      labels:
        app: my-app
        version: v1.0.0

    # spec: The specification for the pod's containers and other pod-level configurations.
    spec:
      # containers: (Mandatory) A list of containers to run in the pod.
      containers:
        # name: (Mandatory) A unique name for the container within the pod.
        - name: my-app-container
          # image: (Mandatory) The container image to use.
          # You can specify a tag, e.g., 'nginx:1.23.0'.
          image: nginx:1.23.0
          # ports: (Optional) Exposes ports from the container.
          ports:
            - containerPort: 80
          # resources: (Optional) Specifies resource requests and limits for the container.
          # This is highly recommended for production deployments.
          resources:
            requests:
              memory: "64Mi"
              cpu: "250m"
            limits:
              memory: "128Mi"
              cpu: "500m"
```

``` mermaid
graph TD
    A[OCP Deployment] -->|Manages| B(ReplicaSet)
    B -->|Creates & Maintains| C[Pods]
    C -->|Run on| D[Worker Node]
    A -- Scalability, Self-Healing, Rollbacks --> A
```
## Rolling Update deployment
``` mermaid
graph TD
    subgraph "Rolling Update"
        direction LR
        A[Old Pods] -->|Gradually replaced by| B(New Pods)
        B -->|Wait for readiness| C{Ready?}
        C -->|Yes| D[Old Pods Terminated]
        C -->|No| E[Wait]
    end
```
