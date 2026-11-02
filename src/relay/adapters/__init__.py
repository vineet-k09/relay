from relay.adapters.base import BaseAdapters, FileMetaData
from relay.adapters.gcs import GCSTransportAdapter
from relay.adapters.local import LocalTransportAdapter
from relay.core.endpoint import Endpoint, EndPointType


def get_adapter(src: Endpoint, dst: Endpoint) -> BaseAdapters:
    """
    Factory function to instantiate the proper transport adapter for the given pair.
    """
    if src.type == EndPointType.LOCAL and dst.type == EndPointType.LOCAL:
        return LocalTransportAdapter(src.path, dst.path)

    if (src.type == EndPointType.LOCAL and dst.type == EndPointType.GCS) or (
        src.type == EndPointType.GCS and dst.type == EndPointType.LOCAL
    ):
        return GCSTransportAdapter(src, dst)

    raise NotImplementedError(
        f"Transport between {src.type.name} and {dst.type.name} "
        "is not implemented yet. Currently supported: LOCAL <-> LOCAL, LOCAL <-> GCS."
    )


__all__ = [
    "BaseAdapters",
    "FileMetaData",
    "GCSTransportAdapter",
    "LocalTransportAdapter",
    "get_adapter",
]
