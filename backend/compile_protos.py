"""
Script to compile Cline proto files into Python gRPC code.

Run this script to generate the gRPC client stubs from the proto files.
"""

import subprocess
import sys
from pathlib import Path

def compile_protos():
    """Compile proto files to Python gRPC code."""
    
    # Get the backend directory
    backend_dir = Path(__file__).parent
    proto_dir = backend_dir / "proto"
    
    print("Compiling Cline proto files...")
    print(f"Proto directory: {proto_dir}")
    
    # Find all proto files in cline directory
    proto_files = list((proto_dir / "cline").glob("*.proto"))
    
    if not proto_files:
        print("ERROR: No proto files found in proto/cline/")
        sys.exit(1)
    
    print(f"Found {len(proto_files)} proto files:")
    for proto_file in proto_files:
        print(f"  - {proto_file.name}")
    
    # Compile each proto file
    for proto_file in proto_files:
        relative_path = proto_file.relative_to(proto_dir)
        
        cmd = [
            sys.executable,
            "-m", "grpc_tools.protoc",
            f"--proto_path={proto_dir}",
            f"--python_out={proto_dir}",
            f"--grpc_python_out={proto_dir}",
            str(relative_path)
        ]
        
        print(f"\nCompiling {proto_file.name}...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"ERROR compiling {proto_file.name}:")
            print(result.stderr)
            sys.exit(1)
        else:
            print(f"✓ Successfully compiled {proto_file.name}")
    
    # Create __init__.py files for the package
    (proto_dir / "cline" / "__init__.py").touch()
    (proto_dir / "__init__.py").touch()
    
    print("\n✓ All proto files compiled successfully!")
    print(f"\nGenerated files are in: {proto_dir / 'cline'}")
    print("You can now use the gRPC client in your Python code.")

if __name__ == "__main__":
    try:
        compile_protos()
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
