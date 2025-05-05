# utils/generate_proto.py
import subprocess
import sys
import os

def main():
    proto_file = sys.argv[1]
    out_dir = sys.argv[2]
    subprocess.run([
        'python', '-m', 'grpc_tools.protoc',
        f'--proto_path={os.path.dirname(proto_file)}',
        f'--python_out={out_dir}',
        f'--grpc_python_out={out_dir}',
        proto_file
    ], check=True)

if __name__ == '__main__':
    main()