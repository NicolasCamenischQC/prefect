from pathlib import Path
from typing import TYPE_CHECKING, Dict, Type

import yaml
from typing_extensions import Self

from prefect.blocks.core import Block, register_block
from prefect.utilities.collections import listrepr
from prefect.utilities.importtools import lazy_import

if TYPE_CHECKING:
    import kubernetes.config.kube_config as kube_config
    from kubernetes.client.api_client import ApiClient
else:
    # Lazily import from kubernetes
    kube_config = lazy_import("kubernetes.config.kube_config")


@register_block
class KubernetesClusterConfig(Block):
    """
    Stores configuration for interaction with Kubernetes clusters.

    See `from_file` for creation.

    Args:
        config: The entire loaded YAML contents of a kubectl config file
        context_name: The name of the context to use
    """

    config: Dict
    context_name: str

    @classmethod
    def from_file(cls: Type[Self], path: Path = None, context_name: str = None) -> Self:
        """
        Create a cluster config from the a Kubernetes config file.

        By default, the current context in the default Kubernetes config file will be
        used.

        An alternative file or context may be specified.

        The entire config file will be loaded and stored.
        """
        path = Path(path or kube_config.KUBE_CONFIG_DEFAULT_LOCATION)
        path = path.expanduser().resolve()

        # Determine the context
        existing_contexts, current_context = kube_config.list_kube_config_contexts(
            config_file=str(path)
        )
        context_names = {ctx["name"] for ctx in existing_contexts}
        if context_name:
            if context_name not in context_names:
                raise ValueError(
                    f"Context {context_name!r} not found. "
                    f"Specify one of: {listrepr(context_names, sep=', ')}."
                )
        else:
            context_name = current_context["name"]

        # Load the entire config file
        config_file_contents = path.read_text()
        config_dict = yaml.safe_load(config_file_contents)

        return cls(config=config_dict, context_name=context_name)

    def get_api_client(self) -> "ApiClient":
        """
        Returns a Kubernetes API client for this cluster config.
        """
        return kube_config.new_client_from_config_dict(
            config_dict=self.config, context=self.context_name
        )

    def configure_client(self) -> None:
        """
        Activates this cluster configuration by loading the configuration into the
        Kubernetes Python client. After calling this, Kubernetes API clients can use
        this config's context.
        """
        kube_config.load_kube_config_from_dict(
            config_dict=self.config, context=self.context_name
        )
