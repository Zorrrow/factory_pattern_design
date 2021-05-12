# Cluster Hardening

If you want to improve the security on your cluster and make it compliant with the [CIS Benchmarks](https://learn.cisecurity.org/benchmarks), here you can find a configuration to harden your **kubernetes** installation.

To apply the hardening configuration, create a file (eg. `hardening.yaml`) and paste the content of the following code snippet into that.

## Minimum Requirements

The **kubernetes** version should be at least `v1.23.6` to have all the most recent security features (eg. the new `PodSecurity` admission plugin, etc).

**N.B.** Some of these configurations have just been added to **kubespray**, so ensure that you have the latest version to make it works properly. Also, ensure that other configurations doesn't override these.

`hardening.yaml`:

```yaml
# Hardening
---

## kube-apiserver
authorization_modes: ['Node', 'RBAC']
# AppArmor-based OS
# kube_apiserver_feature_gates: ['AppArmor=true']
kube_apiserver_request_timeout: 120s
kube_apiserver_service_account_lookup: true

# enable kubernetes audit
kubernetes_audit: true
audit_log_path: "/var/log/kube-apiserver-log.json"
audit_log_maxage: 30
audit_log_maxbackups: 10
audit_log_maxsize: 100

tls_min_version: VersionTLS12
tls_cipher_suites:
  - TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
  - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
  - TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305

# enable encryption at rest
kube_encrypt_secret_data: true
kube_encryption_resources: [secrets]
kube_encryption_algorithm: "secretbox"

kube_apiserver_enable_admission_plugins:
  - EventRateLimit
  - AlwaysPullImages
  - ServiceAccount
  - NamespaceLifecycle
  - NodeRestriction
  - LimitRanger
  - ResourceQuota
  - MutatingAdmissionWebhook
  - ValidatingAdmissionWebhook
  - PodNodeSelector
  - PodSecurity
kube_apiserver_admission_control_config_file: true
# EventRateLimit plugin configuration
kube_apiserver_admission_event_rate_limits:
  limit_1:
    type: Namespace
    qps: 50
    burst: 100
    cache_size: 2000
  limit_2:
    type: User
    qps: 50
    burst: 100
kube_profiling: false

## kube-controller-manager
kube_controller_manager_bind_address: 127.0.0.1
kube_controller_terminated_pod_g