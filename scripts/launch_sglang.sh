#!/bin/bash
export PATH=/data/xbw/turnstile/envs/main/bin:$PATH
export CUDA_VISIBLE_DEVICES=3
export CUDA_HOME=/usr/local/cuda-12.1
export PATH=/data/xbw/turnstile/envs/cxx/compiler-bin:$PATH
export PATH=$CUDA_HOME/bin:$PATH
export CC=/data/xbw/turnstile/envs/cxx/bin/x86_64-conda-linux-gnu-gcc
export CXX=/data/xbw/turnstile/envs/cxx/bin/x86_64-conda-linux-gnu-g++
export CCACHE_DISABLE=1
export NVCC_CCBIN=/data/xbw/turnstile/envs/cxx/bin/x86_64-conda-linux-gnu-g++
exec python -m sglang.launch_server \
  --model-path /data/xbw/turnstile/models/qwen25-coder-7b-yarn96k \
  --context-length 98304 \
  --mem-fraction-static 0.88 \
  --port 30000 \
  --host 0.0.0.0 \
  --enable-metrics --enable-cache-report
