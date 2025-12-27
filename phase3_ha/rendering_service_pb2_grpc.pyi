# -*- coding: utf-8 -*-
"""
Type stubs for rendering_service_pb2_grpc
Generated for Pylance type checking support
"""

from typing import Optional, Iterator, Any, Sequence, Tuple
import grpc
from . import rendering_service_pb2 as rendering_service_pb2

class RenderingServiceStub:
    """Client stub for RenderingService."""
    
    def __init__(self, channel: grpc.Channel) -> None: ...
    
    def RenderFrame(
        self,
        request: rendering_service_pb2.RenderRequest,
        timeout: Optional[float] = None,
        metadata: Optional[Sequence[Tuple[str, str]]] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None
    ) -> rendering_service_pb2.RenderResponse: ...
    
    def StreamFrames(
        self,
        request_iterator: Iterator[rendering_service_pb2.RenderRequest],
        timeout: Optional[float] = None,
        metadata: Optional[Sequence[Tuple[str, str]]] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None
    ) -> Iterator[rendering_service_pb2.RenderResponse]: ...
    
    def HealthCheck(
        self,
        request: rendering_service_pb2.HealthCheckRequest,
        timeout: Optional[float] = None,
        metadata: Optional[Sequence[Tuple[str, str]]] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None
    ) -> rendering_service_pb2.HealthCheckResponse: ...
    
    def GetStats(
        self,
        request: rendering_service_pb2.StatsRequest,
        timeout: Optional[float] = None,
        metadata: Optional[Sequence[Tuple[str, str]]] = None,
        credentials: Optional[grpc.CallCredentials] = None,
        wait_for_ready: Optional[bool] = None,
        compression: Optional[grpc.Compression] = None
    ) -> rendering_service_pb2.StatsResponse: ...


class RenderingServiceServicer:
    """Server servicer for RenderingService."""
    
    def RenderFrame(
        self,
        request: rendering_service_pb2.RenderRequest,
        context: grpc.ServicerContext
    ) -> rendering_service_pb2.RenderResponse: ...
    
    def StreamFrames(
        self,
        request_iterator: Iterator[rendering_service_pb2.RenderRequest],
        context: grpc.ServicerContext
    ) -> Iterator[rendering_service_pb2.RenderResponse]: ...
    
    def HealthCheck(
        self,
        request: rendering_service_pb2.HealthCheckRequest,
        context: grpc.ServicerContext
    ) -> rendering_service_pb2.HealthCheckResponse: ...
    
    def GetStats(
        self,
        request: rendering_service_pb2.StatsRequest,
        context: grpc.ServicerContext
    ) -> rendering_service_pb2.StatsResponse: ...


def add_RenderingServiceServicer_to_server(
    servicer: RenderingServiceServicer,
    server: grpc.Server
) -> None: ...
