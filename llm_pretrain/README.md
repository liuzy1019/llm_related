# llm-from-scratch-7b

> 从零复现 7B 类 LLaMA 大模型：Tokenizer → 预训练（Megatron-LM）→ HF 转换 → SFT（Verl）
> 参考：[KM #660614 — 一文了解从零开始预训练大语言模型技术实现](https://km.woa.com/articles/show/660614?jumpfrom=kmmcp)（作者 feelingzhou）

---

## 项目结构

```
llm-from-scratch-7b/
├── README.md                      # 当前文件
├── docs/                          # 原文整理（md + html）
│   ├── 从零开始预训练大语言模型技术实现.md
│   └── 从零开始预训练大语言模型技术实现.html
├── data/                          # 原始 + 预处理后语料
├── tokenizer/                     # Byte-level BPE 训练与产物（tokenizer.json）
├── pretrain/                      # Megatron-LM 预训练脚本与配置
├── convert_hf/                    # Megatron DistCP → HuggingFace 权重转换
├── sft/                           # Verl SFT 训练脚本与配置
└── scripts/                       # 一键拉起 / 监控 / 评测
```

---

## 复现里程碑（建议顺序）

- [ ] **M0 环境**
  - CUDA ≥ 12.1，PyTorch ≥ 2.3
  - 安装：`Megatron-LM`、`verl==0.8.0`、`tokenizers`、`transformers`、`flash-attn`
- [ ] **M1 数据**
  - 从 [ModelScope](https://www.modelscope.cn/) 拉取预训练语料 + SFT 对话语料
  - 跑 `Megatron-LM/tools/preprocess_data.py` 生成 `.bin / .idx`
- [ ] **M2 Tokenizer**
  - 训练 Byte-level BPE，词表 64000，输出 `tokenizer/tokenizer.json`
- [ ] **M3 预训练**
  - 8×H20 / 8×A100 跑 7B 类 LLaMA：32 层 / hidden 4096 / SwiGLU / RoPE / RMSNorm / BF16
  - 关注：loss 曲线、MFU、GPU 利用率
- [ ] **M4 Megatron → HF 转换**
  - 写 / 套用 `saver_hf.py`，注意拆分 QKV、SwiGLU 的 Gate/Up
  - 用 `transformers.AutoModelForCausalLM.from_pretrained` 验证加载
- [ ] **M5 SFT**
  - Verl 0.8.0 + FSDP，2 epoch、`lr=1e-5`、`warmup=0.03`、cosine
  - `model_merger merge` 输出 HF 格式 checkpoint
- [ ] **M6 评测**
  - base vs SFT：续写 vs 对话表现
  - 选跑 MMLU / C-Eval 子集，记录 zero-shot 分数

---

## 关键命令速查

### 训练 Tokenizer

```bash
python tokenizer/train_bpe.py \
  --corpus data/pretrain_text/*.txt \
  --vocab-size 64000 \
  --output tokenizer/tokenizer.json
```

### 启动 Megatron-LM 预训练

```bash
bash pretrain/run_pretrain_7b.sh
```

### Megatron → HF 转换

```bash
python convert_hf/saver_hf.py \
  --megatron-ckpt checkpoints/pretrain/iter_0050000 \
  --output-dir   checkpoints/hf_base_7b
```

### Verl SFT

```bash
bash sft/run_sft_verl.sh
```

### 合并 SFT checkpoint

```bash
python -m verl.model_merger merge \
  --backend fsdp \
  --local_dir  checkpoints/sft/global_step_xxx/actor \
  --target_dir checkpoints/hf_sft_7b
```

---

## 阅读建议

1. 先在浏览器里打开 [`docs/从零开始预训练大语言模型技术实现.html`](docs/从零开始预训练大语言模型技术实现.html) 通读一遍；
2. 按里程碑 M0 → M6 逐步打勾推进；
3. 把每一步遇到的坑写进 `docs/notes/` 下的小笔记，方便回顾。

---

## 数据 / 资料来源

- 原文：<https://km.woa.com/articles/show/660614?jumpfrom=kmmcp>
- 整理工具：KM MCP（`km.show-article`）
- 整理时间：2026-05-25
