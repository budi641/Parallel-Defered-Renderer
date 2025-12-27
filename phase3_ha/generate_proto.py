"""
Phase 3: High Availability Rendering Service
Setup script to generate Protocol Buffer code from .proto files
"""

import subprocess
import sys
import os

def main():
    """Generate Python code from proto files."""
    
    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    proto_dir = os.path.join(script_dir, 'protos')
    
    # Proto file
    proto_file = os.path.join(proto_dir, 'rendering_service.proto')
    
    if not os.path.exists(proto_file):
        print(f"Error: Proto file not found: {proto_file}")
        sys.exit(1)
    
    # Generate Python code
    print(f"Generating Python code from {proto_file}...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'grpc_tools.protoc',
            f'--proto_path={proto_dir}',
            f'--python_out={script_dir}',
            f'--grpc_python_out={script_dir}',
            proto_file
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error generating proto code: {result.stderr}")
            sys.exit(1)
        
        print("Successfully generated:")
        print(f"  - {os.path.join(script_dir, 'rendering_service_pb2.py')}")
        print(f"  - {os.path.join(script_dir, 'rendering_service_pb2_grpc.py')}")
        
    except FileNotFoundError:
        print("Error: grpcio-tools not installed.")
        print("Install with: pip install grpcio-tools")
        sys.exit(1)


if __name__ == '__main__':
    main()
