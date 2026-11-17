# LISFLOOD-FP 8.2 (official release, Zenodo 10.5281/zenodo.13121102, GPL-2.0), CPU build, for flood run 1
# (docs/model_design_flood_run1.md). Built from the release archive, checked against Zenodo's MD5:
#
#   https://zenodo.org/api/records/13121102/files/LISFLOOD-FP-v8.2.zip/content
#   LISFLOOD-FP-v8.2.zip, 348,144,517 bytes
#   MD5     a0a607cf68078b56a9c50c7013cafa95  (as published by Zenodo)
#   SHA-256 7982072150fde0ad96c5e54f3535636e0756152b52cc45b676c45dd8cdc6bae3
#
# The archive is not in git (348 MB). Put it in a folder of its own and build with that folder as context:
#   docker build -f envs/lisflood-fp.Dockerfile -t atibaia/lisflood-fp:8.2 <folder with the zip>
# Run a model:
#   docker run --rm -v <model folder>:/data atibaia/lisflood-fp:8.2 <file>.par
# No CUDA compiler is in the image, so CMake builds the CPU solvers only (the acceleration solver with
# the subgrid channel, which is what the design uses).
FROM ubuntu:24.04
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential cmake unzip libnuma-dev libnetcdf-dev \
 && rm -rf /var/lib/apt/lists/*
COPY LISFLOOD-FP-v8.2.zip /tmp/lisflood.zip
RUN cd /tmp \
 && echo "a0a607cf68078b56a9c50c7013cafa95  lisflood.zip" | md5sum -c - \
 && unzip -q lisflood.zip -x 'LISFLOOD-FP/testing/*' 'LISFLOOD-FP/.git/*' 'LISFLOOD-FP/windep/*' \
      'LISFLOOD-FP/DLL*' 'LISFLOOD-FP/dll_intel/*' \
 && cd LISFLOOD-FP \
 && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build -j 8 \
 && cp build/lisflood /usr/local/bin/lisflood \
 && cd / && rm -rf /tmp/LISFLOOD-FP /tmp/lisflood.zip
WORKDIR /data
ENTRYPOINT ["lisflood"]
