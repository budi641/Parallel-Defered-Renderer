# -*- coding: utf-8 -*-
"""
Type stubs for rendering_service_pb2
Generated for Pylance type checking support
"""

from typing import Optional, List
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message

DESCRIPTOR: _descriptor.FileDescriptor

class CameraParams(_message.Message):
    position_x: float
    position_y: float
    position_z: float
    yaw: float
    pitch: float
    fov: float
    aperture: float
    shutter_speed: float
    iso: float
    
    def __init__(
        self,
        position_x: float = ...,
        position_y: float = ...,
        position_z: float = ...,
        yaw: float = ...,
        pitch: float = ...,
        fov: float = ...,
        aperture: float = ...,
        shutter_speed: float = ...,
        iso: float = ...
    ) -> None: ...

class LightParams(_message.Message):
    point1_x: float
    point1_y: float
    point1_z: float
    point1_radius: float
    point2_x: float
    point2_y: float
    point2_z: float
    point2_radius: float
    point3_x: float
    point3_y: float
    point3_z: float
    point3_radius: float
    point_mode: bool
    directional_mode: bool
    ibl_mode: bool
    
    def __init__(
        self,
        point1_x: float = ...,
        point1_y: float = ...,
        point1_z: float = ...,
        point1_radius: float = ...,
        point2_x: float = ...,
        point2_y: float = ...,
        point2_z: float = ...,
        point2_radius: float = ...,
        point3_x: float = ...,
        point3_y: float = ...,
        point3_z: float = ...,
        point3_radius: float = ...,
        point_mode: bool = ...,
        directional_mode: bool = ...,
        ibl_mode: bool = ...
    ) -> None: ...

class MaterialParams(_message.Message):
    roughness: float
    metallicity: float
    f0_r: float
    f0_g: float
    f0_b: float
    
    def __init__(
        self,
        roughness: float = ...,
        metallicity: float = ...,
        f0_r: float = ...,
        f0_g: float = ...,
        f0_b: float = ...
    ) -> None: ...

class PostProcessParams(_message.Message):
    sao_mode: bool
    sao_samples: int
    sao_radius: float
    fxaa_mode: bool
    motion_blur_mode: bool
    tonemapping_mode: int
    
    def __init__(
        self,
        sao_mode: bool = ...,
        sao_samples: int = ...,
        sao_radius: float = ...,
        fxaa_mode: bool = ...,
        motion_blur_mode: bool = ...,
        tonemapping_mode: int = ...
    ) -> None: ...

class ModelTransform(_message.Message):
    position_x: float
    position_y: float
    position_z: float
    rotation_angle: float
    rotation_axis_x: float
    rotation_axis_y: float
    rotation_axis_z: float
    scale_x: float
    scale_y: float
    scale_z: float
    
    def __init__(
        self,
        position_x: float = ...,
        position_y: float = ...,
        position_z: float = ...,
        rotation_angle: float = ...,
        rotation_axis_x: float = ...,
        rotation_axis_y: float = ...,
        rotation_axis_z: float = ...,
        scale_x: float = ...,
        scale_y: float = ...,
        scale_z: float = ...
    ) -> None: ...

class RenderRequest(_message.Message):
    request_id: int
    timestamp: int
    frame_number: int
    width: int
    height: int
    camera: CameraParams
    lighting: LightParams
    material: MaterialParams
    post_process: PostProcessParams
    model_transform: ModelTransform
    is_streaming: bool
    delta_time: float
    
    def __init__(
        self,
        request_id: int = ...,
        timestamp: int = ...,
        frame_number: int = ...,
        width: int = ...,
        height: int = ...,
        camera: Optional[CameraParams] = ...,
        lighting: Optional[LightParams] = ...,
        material: Optional[MaterialParams] = ...,
        post_process: Optional[PostProcessParams] = ...,
        model_transform: Optional[ModelTransform] = ...,
        is_streaming: bool = ...,
        delta_time: float = ...
    ) -> None: ...

class RenderResponse(_message.Message):
    request_id: int
    timestamp_received: int
    timestamp_completed: int
    frame_number: int
    frame_data: bytes
    width: int
    height: int
    encoding: str
    geometry_time_ms: float
    lighting_time_ms: float
    postprocess_time_ms: float
    total_time_ms: float
    success: bool
    error_message: str
    replica_id: str
    
    def __init__(
        self,
        request_id: int = ...,
        timestamp_received: int = ...,
        timestamp_completed: int = ...,
        frame_number: int = ...,
        frame_data: bytes = ...,
        width: int = ...,
        height: int = ...,
        encoding: str = ...,
        geometry_time_ms: float = ...,
        lighting_time_ms: float = ...,
        postprocess_time_ms: float = ...,
        total_time_ms: float = ...,
        success: bool = ...,
        error_message: str = ...,
        replica_id: str = ...
    ) -> None: ...

class HealthCheckRequest(_message.Message):
    client_id: str
    
    def __init__(
        self,
        client_id: str = ...
    ) -> None: ...

class HealthCheckResponse(_message.Message):
    healthy: bool
    replica_id: str
    uptime_seconds: int
    frames_rendered: int
    avg_latency_ms: float
    load_percentage: float
    
    def __init__(
        self,
        healthy: bool = ...,
        replica_id: str = ...,
        uptime_seconds: int = ...,
        frames_rendered: int = ...,
        avg_latency_ms: float = ...,
        load_percentage: float = ...
    ) -> None: ...

class StatsRequest(_message.Message):
    client_id: str
    include_history: bool
    
    def __init__(
        self,
        client_id: str = ...,
        include_history: bool = ...
    ) -> None: ...

class StatsResponse(_message.Message):
    replica_id: str
    total_frames_rendered: int
    avg_frame_time_ms: float
    min_frame_time_ms: float
    max_frame_time_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_fps: float
    uptime_seconds: int
    frame_history: List[FrameMetric]
    
    def __init__(
        self,
        replica_id: str = ...,
        total_frames_rendered: int = ...,
        avg_frame_time_ms: float = ...,
        min_frame_time_ms: float = ...,
        max_frame_time_ms: float = ...,
        p95_latency_ms: float = ...,
        p99_latency_ms: float = ...,
        throughput_fps: float = ...,
        uptime_seconds: int = ...,
        frame_history: Optional[List[FrameMetric]] = ...
    ) -> None: ...

class FrameMetric(_message.Message):
    timestamp: int
    frame_number: int
    latency_ms: float
    success: bool
    
    def __init__(
        self,
        timestamp: int = ...,
        frame_number: int = ...,
        latency_ms: float = ...,
        success: bool = ...
    ) -> None: ...
