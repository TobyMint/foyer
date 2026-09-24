#!/bin/bash
# lab-A100 上的 SGLang 环境搭建 —— 方向 D（第二配置验证）的前置。
#
# 版本必须与 3090 上的实验环境对齐，否则"换配置"就变成了"换配置+换引擎"，
# 论文里那条"同一段代码路径在两个配置上给出同一种答案"的话就不成立：
#   3090:  python 3.11.16 / torch 2.9.1+cu128 / sglang 0.5.10.post1 / transformers 5.3.0
#
# 为什么不用现成的 env：vllm 那个是半拷贝过来的，lib/python3.10/encodings 都不在，
# 一跑就 ModuleNotFoundError。不修它，直接建新的。
#
# 装到 /data/xbw/sglang-env（/data 剩 225G；/ 只剩 154G，留给系统）。
# 网络：pip 走清华源（~/.pip/pip.conf 已配），torch 的 cu128 wheel 走 download.pytorch.org。
set -x
export PYTHONNOUSERSITE=1
source /opt/miniconda/etc/profile.d/conda.sh || exit 1
ENV=/data/xbw/sglang-env

echo "=== [$(date '+%F %T')] 创建 conda env ==="
conda create -p "$ENV" python=3.11 -y || exit 2

export PATH="$ENV/bin:$PATH"
export LD_LIBRARY_PATH="$ENV/lib:${LD_LIBRARY_PATH:-}"

echo "=== [$(date '+%F %T')] 装 torch 2.9.1+cu128 ==="
python -m pip install --no-cache-dir "torch==2.9.1" "torchvision" "torchaudio" \
  --index-url https://download.pytorch.org/whl/cu128 || exit 3

echo "=== [$(date '+%F %T')] 装 sglang 0.5.10.post1 ==="
python -m pip install --no-cache-dir "sglang==0.5.10.post1" || exit 4

echo "=== [$(date '+%F %T')] 对齐 transformers ==="
python -m pip install --no-cache-dir "transformers==5.3.0" || echo "（失败不致命，记下来）"

echo "=== [$(date '+%F %T')] 自检 ==="
python - <<'PY'
import sys
print("python", sys.version.split()[0])
try:
    import torch
    print("torch", torch.__version__, "cuda", torch.version.cuda,
          "avail", torch.cuda.is_available(), "count", torch.cuda.device_count())
except Exception as e:
    print("torch FAIL", e)
try:
    import sglang
    print("sglang", sglang.__version__)
except Exception as e:
    print("sglang FAIL", e)
try:
    import importlib.metadata as md
    print("transformers", md.version("transformers"))
except Exception as e:
    print("transformers ?", e)
PY
echo "=== [$(date '+%F %T')] 完成 ==="
