# Red Hat Enterprise Linux (RHEL)

## RHEL Support Subscription Registration

In order to install packages via yum or dnf, RHEL 7/8 hosts are required to be registered for a valid Red Hat support subscription.

You can apply for a 1-year Development support subscription by creating a [Red Hat Developers](https://developers.redhat.com/) account. Be aware though that as the Red Hat Developers subscription is limited to only 1 year, it should not be used to register RHEL 7/8 hosts provisioned in Production environments.

Once you have a Red Hat support account, simply add the credentials to the Ansible inventory parameters `rh_subscription_username` and `rh_subscription_password` prior to deploying Kubespray. If your company has a Corporate Red Hat support account, then obtain an **Organization ID** and **Activa