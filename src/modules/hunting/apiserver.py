import json
import logging

import requests

from ...core.events import handler
from ...core.events.types import Vulnerability, Event, OpenPortEvent
from ...core.types import Hunter, ActiveHunter, KubernetesCluster, RemoteCodeExec, AccessRisk, InformationDisclosure


""" Vulnerabilities """
class ServerApiAccess(Vulnerability, Event):
    """ Accessing the server API within a compromised pod would help an attacker gain full control over the cluster"""

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Accessed to server API", category=RemoteCodeExec)
        self.evidence = evidence


class ServiceAccountTokenAccess(Vulnerability, Event):
    """ Accessing the pod's service account token gives an attacker the option to use the server API """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Read access to pod's service account token",
                               category=AccessRisk)
        self.evidence = evidence


class PodListUnderDefaultNamespace(Vulnerability, Event):
    """ Accessing the pods list under default namespace within a compromised pod might grant an attacker a valuable
     information to harm the cluster """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Access to the pods list under default namespace",
                               category=InformationDisclosure)
        self.evidence = evidence


class PodListUnderAllNamespaces(Vulnerability, Event):
    """ Accessing the pods list under ALL of the namespaces within a compromised pod might grant an attacker a valuable
     information to harm the cluster """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Access to the pods list under ALL namespaces",
                               category=InformationDisclosure)
        self.evidence = evidence


class ListAllNamespaces(Vulnerability, Event):
    """ Accessing all of the namespaces within a compromised pod might grant an attacker a valuable information
    """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Access to the all namespaces list",
                               category=InformationDisclosure)
        self.evidence = evidence


class CreateARole(Vulnerability, Event):
    """ Creating a role might give an attacker the option to harm the normal routine of newly created pods
     within the specified namespaces.
    """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Created a role",
                               category=InformationDisclosure)
        self.evidence = evidence


class CreateAClusterRole(Vulnerability, Event):
    """ Creating a role might give an attacker the option to harm the normal routine of newly created pods within the
    whole cluster scope.
    """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Created a cluster role",
                               category=InformationDisclosure)
        self.evidence = evidence


class PatchARole(Vulnerability, Event):
    """ Patching a cluster role might give an attacker the option to create new pods with custom roles within the
    specific role's namespace scope
    """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Patched a role",
                               category=InformationDisclosure)
        self.evidence = evidence


class PatchAClusterRole(Vulnerability, Event):
    """ Patching a cluster role might give an attacker the option to create new pods with custom roles within the whole
    cluster scope.
    """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Patched a cluster role",
                               category=InformationDisclosure)
        self.evidence = evidence


class DeleteARole(Vulnerability, Event):
    """ Deleting a role might give an attacker the option to create new pods with custom roles within a specific role's
    namespace scope."""

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Deleted a role",
                               category=InformationDisclosure)
        self.evidence = evidence


class DeleteAClusterRole(Vulnerability, Event):
    """ Deleting a cluster role might give an attacker the option to create new pods with custom roles within the whole
    cluster scope."""

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Deleted a cluster role",
                               category=InformationDisclosure)
        self.evidence = evidence


# Passive Hunter
@handler.subscribe(OpenPortEvent, predicate=lambda x: x.port == 443 or x.port == 6443)
class AccessApiServerViaServiceAccountToken(Hunter):
    """ API Server Hunter
    Accessing the api server within a compromised pod might grant an attacker full control over the cluster
    """

    def __init__(self, event):
        self.event = event
        self.api_server_evidence = ''
        self.service_account_token_evidence = ''
        self.pod_list_under_default_namespace_evidence = ''
        self.pod_list_under_all_namespaces_evidence = ''

    def access_api_server(self):
        logging.debug(self.event.host)
        logging.debug('Passive Hunter is attempting to access the API server using the pod\'s service account token')
        try:
            res = requests.get("https://{host}:{port}/api".format(host=self.event.host, port=self.event.port),
                               headers={'Authorization': 'Bearer ' + self.service_account_token_evidence}, verify=False)
            self.api_server_evidence = res.content
            return res.status_code == 200 and res.content != ''
        except requests.exceptions.ConnectionError:  # e.g. DNS failure, refused connection, etc
            return False

    def get_service_account_token(self):
        logging.debug(self.event.host)
        logging.debug('Passive Hunter is attempting to access pod\'s service account token')
        try:
            with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as token:
                data = token.read()
                self.service_account_token_evidence = data
                return True
        except IOError:  # Couldn't read file
            return False

    def get_pods_list_under_default_namespace(self):
        logging.debug(self.event.host)
        logging.debug('Passive Hunter is attempting to list pods under default '
                      'namespace using the pod\'s service account token')
        try:
            res = requests.get("https://{host}:{port}/api/v1/namespaces/{namespace}/pods".format(host=self.event.host,
                                port=self.event.port, namespace='default'),
                               headers={'Authorization': 'Bearer ' + self.service_account_token_evidence}, verify=False)
            self.pod_list_under_default_namespace_evidence = res.content
            return res.status_code == 200 and res.content != ''
        except requests.exceptions.ConnectionError:  # e.g. DNS failure, refused connection, etc
            return False

    def get_pods_list_under_all_namespace(self):
        logging.debug(self.event.host)
        logging.debug('Passive Hunter is attempting to list pods under default '
                      'namespace using the pod\'s service account token')
        try:
            res = requests.get("https://{host}:{port}/api/v1/pods".format(host=self.event.host, port=self.event.port),
                               headers={'Authorization': 'Bearer ' + self.service_account_token_evidence}, verify=False)
            self.pod_list_under_all_namespaces_evidence = res.content
            return res.status_code == 200 and res.content != ''
        except requests.exceptions.ConnectionError:  # e.g. DNS failure, refused connection, etc
            return False

    def execute(self):
        if self.get_service_account_token():
            self.publish_event(ServiceAccountTokenAccess(self.service_account_token_evidence))
            if self.access_api_server():
                self.publish_event(ServerApiAccess(self.api_server_evidence))
            if self.get_pods_list_under_all_namespace():
                self.publish_event(PodListUnderAllNamespaces(self.pod_list_under_all_namespaces_evidence))
            if self.get_pods_list_under_default_namespace():
                self.publish_event(PodListUnderDefaultNamespace(self.pod_list_under_default_namespace_evidence))


# Active Hunter
@handler.subscribe(OpenPortEvent, predicate=lambda x: x.port == 443 or x.port == 6443)
class AccessApiServerViaServiceAccountTokenActive(ActiveHunter):
    """API server hunter
    Accessing the api server might grant an attacker full control over the cluster
    """

    def __init__(self, event):
        self.event = event
        self.api_server_evidence = ''
        self.service_account_token_evidence = ''
        self.all_namespaces_evidence = ''
        self.namespace_roles_evidence = ''
        self.all_roles_evidence = ''
        self.cluster_roles_evidence = ''

        self.namespaces_and_their_pod_names = {}

    def get_service_account_token(self):
        logging.debug(self.event.host)
        logging.debug('Passive Hunter is attempting to access pod\'s service account token')
        try:
            with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as token:
                data = token.read()
                self.service_account_token_evidence = data
                return True
        except IOError:  # Couldn't read file
            return False

    def get_pods_list_under_default_namespace(self):
        try:
            res = requests.get("https://{host}:{port}/api/v1/namespaces/{namespace}/pods".format(host=self.event.host,
                                port=self.event.port, namespace='default'),
                               headers={'Authorization': 'Bearer ' + self.service_account_token_evidence}, verify=False)

            parsed_response_content = json.loads(res.content)
            for item in parsed_response_content["items"]:
                self.namespaces_and_their_pod_names[item["metadata"]["namespace"]] = item["metadata"]["name"]

            return res.status_code == 200 and res.content != ''
        except requests.exceptions.ConnectionError:  # e.g. DNS failure, refused connection, etc
            return False

    def get_pods_list_under_all_namespace(self):
        try:
            res = requests.get("https://{host}:{port}/api/v1/pods".format(host=self.event.host, port=self.event.port),
                               headers={'Authorization': 'Bearer ' + self.service_account_token_evidence}, verify=False)
            parsed_response_content = json.loads(res.content)
            for item in parsed_response_content["items"]:
                self.namespaces_and_their_pod_names[item["metadata"]["namespace"]] = item["metadata"]["name"]

            return res.status_code == 200 and res.content != ''
        except requests.exceptions.ConnectionError:  # e.g. DNS failure, refused connection, etc
            return False

    def create_a_pod(self):
        pass

    #  would be used on our newly created pod only
    def delete_a_pod(self, pod_namespace, pod_name):
        try:
            res = requests.delete("https://{host}:{port}/api/v1/namespaces/{namespace}/pods/{name}".format(
                                 host=self.event.host, port=self.event.port, namespace=pod_namespace, name=pod_name),
                               headers={'Authorization': 'Bearer ' + self.service_account_token_evidence}, verify=False)
            return res.status_code == 200 and res.content != ''
        except requests.exceptions.ConnectionError:
            return False

    # would be used on our newly created pod only
    def patch_a_pod(self, pod_namespace, pod_name):
        try:
            patch_data = {}
            res = requests.patch("https://{host}:{port}/api/v1/namespaces/{namespace}/pods/{name}".format(
                                 host=self.event.host, port=self.event.port, namespace=pod_namespace, name=pod_name),
                               headers={'Authorization': 'Bearer ' + self.service_account_token_evidence}, verify=False, data=patch_data)
            return res.status_code == 200 and res.content != ''
        except requests.exceptions.ConnectionError:
            return False

    #Namespaces methods:

    def get_all_namespaces(self):
        try:
            res = requests.get("https://{host}:{port}/api/v1/namespaces".format(host=self.event.host,
                               port=self.event.port),
                               headers={'Authorization': 'Bearer ' + self.service_account_token_evidence}, verify=False)

            parsed_response_content = json.loads(res.content)
            # Parse content after creating RBAC roles that would return 200 OK so I can see the data myself and understand how to parse it
            # for item in parsed_response_content["items"]:
            #     self.namespaces_and_their_pod_names[item["metadata"]["namespace"]] = item["metadata"]["name"]

            return res.status_code == 200 and res.content != ''
        except requests.exceptions.ConnectionError:  # e.g. DNS failure, refused connection, etc
            return False

    def create_namespace(self):
        pass


    #Roles & Cluster roles Methods:

    def get_roles_for_namespace(self, namespace):
        try:
            res = requests.get("https://{host}:{port}/apis/rbac.authorization.k8s.io/v1/namespaces/{namespace}/roles".format(
                                 host=self.event.host, port=self.event.port, namespace=namespace),
                               headers={'Authorization': 'Bearer ' + self.service_account_token_evidence}, verify=False)
            self.namespace_roles_evidence = res.content
            return res.content if res.status_code == 200 and res.content != '' else False
        except requests.exceptions.ConnectionError:
            return False

    def get_cluster_roles(self):
        try:
            res = requests.get("https://{host}:{port}/apis/rbac.authorization.k8s.io/v1/clusterroles".format(
                                 host=self.event.host, port=self.event.port),
                               headers={'Authorization': 'Bearer ' + self.service_account_token_evidence}, verify=False)
            self.namespace_roles_evidence = res.content
            return res.content if res.status_code == 200 and res.content != '' else False
        except requests.exceptions.ConnectionError:
            return False

    def get_all_roles(self):
        try:
            res = requests.get("https://{host}:{port}/apis/rbac.authorization.k8s.io/v1/roles".format(
                                 host=self.event.host, port=self.event.port),
                               headers={'Authorization': 'Bearer ' + self.service_account_token_evidence}, verify=False)
            self.namespace_roles_evidence = res.content
            return res.content if res.status_code == 200 and res.content != '' else False
        except requests.exceptions.ConnectionError:
            return False

    def create_role(self):
        pass

    def create_cluster_role(self):
        pass

    # would be use on an newly create role only
    def delete_a_role(self):
        pass

    # would be use on an newly create cluster role only
    def delete_a_cluster_role(self):
        pass

    # would be use on an newly create role only
    def patch_a_role(self):
        pass

    # would be use on an newly create role only
    def patch_a_cluster_role(self):
        pass

    def execute(self):
        if self.get_service_account_token():
            # Do I need these data for other hunters (the onces that uses pod name or namespace as an argument)?
            self.get_pods_list_under_all_namespace()
            self.get_pods_list_under_default_namespace()


