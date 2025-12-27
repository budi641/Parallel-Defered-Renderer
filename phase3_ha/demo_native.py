"""
Phase 3: Native Renderer Demo
Launches the actual C++ OpenGL renderer with gRPC health monitoring

This demo:
1. Starts the actual C++ Parallel-Deferred-Renderer with OpenGL window
2. Provides gRPC health check endpoints
3. Demonstrates fault tolerance with the real renderer
"""

import os
import sys
import time
import subprocess
import signal
import logging

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_renderer():
    """Find the C++ renderer executable."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    candidates = [
        os.path.join(base_dir, "build_Debug", "Debug", "Parallel-Deferred-Renderer.exe"),
        os.path.join(base_dir, "build", "Debug", "Parallel-Deferred-Renderer.exe"),
        os.path.join(base_dir, "build", "Parallel-Deferred-Renderer.exe"),
        os.path.join(base_dir, "build", "Release", "Parallel-Deferred-Renderer.exe"),
    ]
    
    for path in candidates:
        if os.path.exists(path):
            return path
    
    return None


def run_native_demo():
    """Run the native renderer demo."""
    print("=" * 60)
    print("PHASE 3: NATIVE RENDERER DEMO")
    print("=" * 60)
    print()
    
    # Find the renderer
    renderer_path = find_renderer()
    
    if not renderer_path:
        print("ERROR: Could not find the C++ renderer executable!")
        print()
        print("Please build the project first:")
        print("  1. Open build_Debug/Parallel-Deferred-Renderer.sln in Visual Studio")
        print("  2. Build the solution (Ctrl+Shift+B)")
        print("  3. Run this script again")
        return
    
    print(f"Found renderer: {renderer_path}")
    print()
    
    # Get working directory (project root)
    project_root = os.path.dirname(os.path.dirname(renderer_path))
    if "Debug" in renderer_path or "Release" in renderer_path:
        project_root = os.path.dirname(project_root)
    
    print(f"Working directory: {project_root}")
    print()
    print("Starting the renderer...")
    print("The OpenGL window should appear shortly.")
    print()
    print("Controls:")
    print("  - Mouse: Look around (when unlocked)")
    print("  - WASD: Move camera")
    print("  - ESC: Exit")
    print("  - F1: Toggle UI")
    print()
    print("-" * 60)
    
    try:
        # Start the renderer
        process = subprocess.Popen(
            [renderer_path],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        
        print(f"Renderer started (PID: {process.pid})")
        print()
        print("Press Ctrl+C to stop...")
        print()
        
        # Wait for the process or user interrupt
        while True:
            # Check if process is still running
            if process.poll() is not None:
                print(f"\nRenderer exited with code: {process.returncode}")
                break
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\nStopping renderer...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("Renderer stopped.")
    
    except Exception as e:
        print(f"Error: {e}")


def run_with_grpc():
    """Run the native renderer with gRPC server for monitoring."""
    print("=" * 60)
    print("PHASE 3: NATIVE RENDERER WITH GRPC MONITORING")
    print("=" * 60)
    print()
    
    from rendering_server_native import NativeRenderingServer, find_renderer_executable
    
    renderer_path = find_renderer_executable()
    
    if not renderer_path:
        print("ERROR: Could not find the C++ renderer executable!")
        print()
        print("Please build the project first.")
        return
    
    print(f"Found renderer: {renderer_path}")
    print()
    print("Starting native rendering server on port 50051...")
    print("The OpenGL window should appear shortly.")
    print()
    
    server = NativeRenderingServer(
        port=50051,
        renderer_path=renderer_path,
        replica_id="native-replica-1"
    )
    
    try:
        server.start()
        print()
        print("=" * 60)
        print("Server running! gRPC endpoints available on port 50051")
        print("=" * 60)
        print()
        print("You can test health check with:")
        print('  python -c "from rendering_client import RenderingClient; c = RenderingClient([\'localhost:50051\']); print(c.health_check())"')
        print()
        print("Press Ctrl+C to stop...")
        
        server.wait_for_termination()
        
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        server.stop()
        print("Server stopped.")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Native Renderer Demo')
    parser.add_argument('--grpc', action='store_true', help='Run with gRPC monitoring server')
    
    args = parser.parse_args()
    
    if args.grpc:
        run_with_grpc()
    else:
        run_native_demo()
