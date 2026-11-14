#!/bin/bash
# CUDA forward compatibility, sourced by eval.sbatch on nodes whose driver is older than 575.
# Why: the cluster's H200 driver (570.x) supports CUDA <= 12.8, but vLLM 0.19.1 (PyPI, and Kaggle's wheelhouse copy) is
# built with CUDA 12.9 and no 12.8 build exists, so its 4-bit Marlin kernels die with
# "PTX was compiled with an unsupported toolchain". NVIDIA's cuda-compat package (newer user-space driver libraries,
# no root needed, supported on datacenter GPUs) fixes that; vLLM supports it via VLLM_ENABLE_CUDA_COMPATIBILITY.
# Downloads ~64 MB once into $GDA_ROOT/cuda-compat-12.9 and puts it first on LD_LIBRARY_PATH.
CC_DIR=$GDA_ROOT/cuda-compat-12.9
CC_DEB=cuda-compat-12-9_575.57.08-0ubuntu1_amd64.deb
if [ ! -e "$CC_DIR/libcuda.so.1" ]; then
  echo "fetching CUDA 12.9 compat libraries into $CC_DIR"
  mkdir -p "$GDA_ROOT/cache/compat-dl" "$CC_DIR"
  curl -fsSL -o "$GDA_ROOT/cache/compat-dl/$CC_DEB" "https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/$CC_DEB"
  # A .deb is an 'ar' archive holding data.tar.xz; unpack only usr/local/cuda-12.9/compat/ (no dpkg/root needed).
  "${PYX:-python3}" -I - "$GDA_ROOT/cache/compat-dl/$CC_DEB" "$CC_DIR" <<'PY'
import io, os, sys, tarfile
deb, out = sys.argv[1], sys.argv[2]
b = open(deb, "rb").read(); assert b[:8] == b"!<arch>\n", "not a .deb"
i = 8
while i < len(b):
    name, size = b[i:i + 16].decode().strip().rstrip("/"), int(b[i + 48:i + 58])
    data, i = b[i + 60:i + 60 + size], i + 60 + size + (size & 1)
    if name.startswith("data.tar"):
        t = tarfile.open(fileobj=io.BytesIO(data))
        for m in t.getmembers():
            if "/compat/" in m.name and (m.isfile() or m.issym()):
                m.name = os.path.basename(m.name)
                t.extract(m, out, filter="data")
print("compat libs:", sorted(os.listdir(out)))
PY
fi
export LD_LIBRARY_PATH=$CC_DIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
export VLLM_ENABLE_CUDA_COMPATIBILITY=1 VLLM_CUDA_COMPATIBILITY_PATH=$CC_DIR
