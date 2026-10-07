# v3-P0：候选模型身份确认

**确认日期**：2026-09-24（本地）
**确认主体**：v3-P0（独立核验，不沿用聊天摘要）
**证据等级**：全文标注 `[实测]` / `[文件事实]` / `[官方声明]` / `[尚未验证]`

---

## 0. 结论先行

| 项 | 结论 |
|---|---|
| 此前描述「Qwen3.8，5.9GB，新出的小模型」 | **不是模型 ID，且「小模型」是误判** |
| 真实模型 ID | **Ternary Bonsai 2 27B**（`Ternary-Bonsai-2-27B-PTQ1_0.gguf`） |
| 发布方 / 底座 | **PrismML** / **Qwen/Qwen3.8-27B**（阿里，架构未改） |
| 本地权重是否完整 | **是**，两个 GGUF 均存在且 SHA256 与上游公布值一致 `[实测]` |
| 是否纯文本可用 | **是**。视觉塔是**独立可选**的 mmproj 文件，本阶段未加载 |
| 规模 | **27.36B 总参数**（不是小模型）。5.9 GB 来自**位宽**（1.72–1.75 bpw），不是参数量 |

> **最重要的一条纠正**：**不能由 5.9 GB 推断参数量**。这个体积 = 27.36B 参数 × 约 1.75 bit/权重。
> 同等参数量的 FP16 权重约 54 GB。体积小是**量化表示**的结果，与「小模型」无关。

---

## 1. 唯一性确认：为什么可以排除其他候选

| 判据 | 实测/文件证据 | 结论 |
|---|---|---|
| 本地目录名 `Qwen3.8-5.9GB` | 目录内文件名为 `Ternary-Bonsai-2-27B-PTQ1_0.gguf` | 目录名是**安装时的口语化命名**，非模型 ID |
| GGUF 元数据 `general.architecture` | `qwen35` | 与 Qwen3.8 系架构标记一致 |
| GGUF 元数据 `prism.hadamard.*` | 存在 `transform = normalized-sylvester-walsh-hadamard`、`block_size = 1024`、`sign_mode = explicit` 等 8 个键 | **PrismML 三值旋转基的专有声明**，非上游 Qwen GGUF 会出现 |
| GGUF 元数据 `general.size_label` | `27B` | 27B 级别 |
| `general.version` / `general.basename` | `v5` / `folded` | `folded` = 权重已折叠 Hadamard 旋转 |
| 权重文件字节数 | `5,946,648,928` | 与上游仓库公布的 PTQ1_0 对象大小**完全一致** |
| 权重 SHA256（本地复算） | `53107f53…33ee3` | 与上游 API 公布的 LFS 对象哈希**完全一致** |
| 运行时加载自报类型 | `file type = PTQ1_0 - 1.75 bpw ternary (group 128)` | 与文件名声明一致 |

**结论**：在本地现有文件、GGUF 元数据、上游仓库元数据三个独立来源上互相印证，
**不存在第二个候选**。无需向用户追加确认。

---

## 2. 完整模型 ID、来源与 revision

| 项 | 值 |
|---|---|
| 完整模型 ID | `Ternary-Bonsai-2-27B-PTQ1_0` |
| 正式名称 | Ternary Bonsai 2 27B |
| 发布方 | PrismML（Prism ML, Inc.） |
| 底座模型 | `Qwen/Qwen3.8-27B`（架构未改动，仅权重表示改变） |
| 权重仓库（本机所用源） | `https://modelscope.cn/models/prism-ml/Ternary-Bonsai-2-27B-gguf` |
| 仓库 revision | **`master`** `[实测]`（由 ModelScope API 返回 `Data.Revision = master`） |
| 权重文件名 | `Ternary-Bonsai-2-27B-PTQ1_0.gguf` |
| 视觉塔文件（本阶段不用） | `Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf` |
| 运行时仓库 | `https://github.com/PrismML-Eng/llama.cpp` release tag `prism-b10709-9a9394a` |
| 官方 demo / 启动脚本 | `https://github.com/PrismML-Eng/Bonsai-demo`（官方称其为 source of truth） |
| 官方模型卡 | 本地 `models/README.md`（随权重下载，22,785 字节） |

> **revision 的精度说明**：ModelScope 返回的 revision 是分支名 `master`，**不是 commit hash**。
> 本机文件的真实性由「字节数 + SHA256 与仓库公布的 LFS 对象哈希一致」保证，
> 而不依赖分支指针。若日后需要 commit 级钉死，需额外记录 git commit（本阶段**未做**）。

---

## 3. 参数量、模型类型与纯文本输入

### 3.1 参数量（官方模型卡 `[官方声明]`）

| 组成 | 参数量 |
|---|---:|
| 语言主干（64 blocks） | 24.35 B |
| embedding / LM head | 2.54 B |
| 视觉塔（27 blocks，可选） | 0.46 B |
| **合计** | **27.36 B** |

其中 **26.2 M 参数**（占语言模型 0.0976%：线性注意力层的 recurrent state 路径与归一化权重）
保持高精度，其余为三值。

### 3.2 模型类型

| 项 | 值 | 来源 |
|---|---|---|
| 架构族 | `qwen35`（Qwen3.8 系） | GGUF 元数据 `[实测]` |
| 层数 | `n_layer = 64` | 运行时 `print_info` `[实测]` |
| 隐藏维度 | `n_embd = 5120` | 同上 |
| FFN 维度 | `17408` | GGUF 元数据 |
| 注意力 | **混合注意力**：`full_attention_interval = 4` → 16 层全注意力 / 48 层线性注意力（约 75% 线性） | GGUF 元数据 `[实测]` |
| 注意力头 | `n_head = 24`，`n_head_kv = 4`（GQA），`n_embd_head_k/v = 256` | 运行时 `print_info` `[实测]` |
| 线性注意力实现 | Gated Delta Net（运行时日志：`fused Gated Delta Net`）+ 有 `RS buffer`（recurrent state） | 运行时日志 `[实测]` |
| RoPE | `rope.freq_base = 1e7`，`rope.dimension_sections = [11,11,10,0]` | GGUF 元数据 |
| 训练上下文 | `n_ctx_train = 262144`（256K，与模型卡一致） | 运行时 `print_info` `[实测]` |
| 词表 | 248,320 tokens | GGUF 元数据 |

### 3.3 是否支持纯文本输入

**支持，且纯文本是本阶段的正确用法。**

- 视觉能力由**独立文件** `Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf`（0.63 GB）提供；
  不加载它时运行时自报 `modalities = {vision: false, video: false, audio: false}` `[实测]`。
- 本阶段以 `--no-mmproj` 启动，**未加载视觉塔**，故不占显存、不影响文本推理。
- Task B 是纯文本任务（问题 + 文本证据），不需要视觉路径。

---

## 4. 权重精度与量化格式、文件大小

| 项 | 值 |
|---|---|
| 表示 | **三值 g128**：每个权重 ∈ {−1, 0, +1}，每 128 个权重共享 1 个 FP16 缩放系数 |
| 信息密度 | 理想 1.72 bit/权重；PTQ1_0 实测打包 **1.75 bpw** |
| 打包格式 | **PTQ1_0**（dense trits）。同仓库另有 PQ2_0（2-bit 槽位，2.13 bpw，7.21 GB） |
| 低比特覆盖范围 | embeddings、attention 投影、MLP 投影、LM head —— 无高精度「逃生口」 |
| 权重基 | 离线按块（block=1024）做 Hadamard 旋转后存储；推理时对激活做匹配变换 |

### 本机文件（`[实测]`，SHA256 由本阶段独立复算）

| 文件 | 字节数 | SHA256 | 上游公布哈希 | 一致 |
|---|---:|---|---|:--:|
| `Ternary-Bonsai-2-27B-PTQ1_0.gguf` | 5,946,648,928 | `53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3` | 同左 | ✅ |
| `Ternary-Bonsai-2-27B-mmproj-Q8_0.gguf` | 629,246,976 | `6807ede61d570bb86ba34b756a0fa109edc33668604de867c6ea6d8f1d631903` | 同左 | ✅ |

> 上游哈希取自 ModelScope 仓库 API（`Data.ModelInfos.gguf.gguf_file_list[*].sha256`），
> 本阶段重新下载该 API 响应并留档：`runs/P0-v3-feasibility-20260924/modelscope_repo_api.json`。
> 本机复算值留档：`runs/P0-v3-feasibility-20260924/model_sha256.txt`。
> **两个来源独立，比对一致 → 本地权重完整、未被截断或篡改。**

### 同仓库其他打包（**本阶段未下载**，仅登记）

| 文件 | 大小 | 说明 |
|---|---:|---|
| `Ternary-Bonsai-2-27B-PQ2_0.gguf` | 7,206,168,928 | Ampere 上解码可能更快，但显存更紧 |
| `Ternary-Bonsai-2-27B-mmproj-BF16.gguf` | 931,145,856 | 视觉塔参考精度 |
| `Ternary-Bonsai-2-27B-F16.gguf` | 53,808,408,928 | FP16 基线（本机不可能放下） |

> **防重复下载提示**：以上文件与已有 PTQ1_0 **是同一套权重的不同打包**，
> 体积差来自位宽而非内容。若日后要换，应先确认磁盘空间（C: 当前剩余 550 GB）与显存，
> 并注意 **PQ2_0 在 8 GB 显存上更紧**（文档实测 PQ2_0 为「显存最紧张时的次选」）。

---

## 5. 许可证与推理框架要求

| 项 | 值 |
|---|---|
| 许可证 | **Apache-2.0**（仓库 `Data.License = apache-2.0`；`NOTICE.txt` 明示可商用） |
| 底座许可 | Qwen3.8-27B 亦为 Apache-2.0（`NOTICE.txt` 明示） |
| 署名要求 | 无强制，官方「欢迎」的署名为 `Created using Bonsai by Prism ML.` |

### 推理框架：**必须用 PrismML 的 llama.cpp 分支**

官方模型卡原文：**stock llama.cpp 跑不了这些文件**——

- 会把 `PQ2_0` / `PTQ1_0` 当作未知类型**拒绝加载**；
- 更危险的是遇到 `Q2_0` 会**静默加载并输出乱码**，因为原版没有实现这些权重依赖的
  **Hadamard 激活变换**（权重存在旋转基里，推理时须对激活做匹配变换）。

因此本机使用 **PrismML 分支的预编译二进制**：

| 项 | 值 |
|---|---|
| 运行时版本 | `0.2.0-dev (build 10709, commit 9a9394a89)` `[实测]`（`llama-server.exe --version`） |
| 构建 | MSVC 19.44.35228.0 for Windows AMD64 |
| CUDA 构建 | `win-cuda-12.4-x64`（Windows 只有 12.4 与 13.3 两个 x64 构建；13.3 需要比本机 581.57 更新的驱动） |
| 位置 | `<model_root>\runtime\` |
| 是否需要 CUDA Toolkit | **不需要**，`cudart` 包已随运行时安装 |

> 补充说明（避免误用）：运行时包本身是经 GitHub 加速镜像取得的（`github.com/.../releases/download/...`
> 在本机不可达），但已用 `api.github.com` 公布的官方 SHA256 digest 逐字节校验通过。
> **来源是镜像，内容是官方哈希验证过的。**

---

## 6. 官方聊天模板、thinking 模式与配置方法

### 6.1 模板来自模型自身（不是推理框架内置）

- **模板位置**：GGUF 元数据键 `tokenizer.chat_template`，长 **8,952 字符** `[实测]`；
  已导出为 `runs/P0-v3-feasibility-20260924/chat_template.jinja`。
- **控制方式**：推理时由框架按该模板渲染 —— 因此 v3 适配层**只产出 `messages`**，
  不手工拼任何特殊 token。
- 模板结构：`<|im_start|>{role}\n{content}<|im_end|>\n`，以 `<|im_start|>assistant\n` 收尾。
- `tokenizer.ggml.add_bos_token = False`，BOS = PAD = 248044，EOS = 248046。

### 6.2 thinking 相关模板变量

模板显式读取两个变量 `[实测，见 chat_template.jinja:45-56, 163-169]`：

| 变量 | 取值 | 模板行为 |
|---|---|---|
| `enable_thinking` | `true` / 未定义 → **默认开启** | 在 system 段插入 `reasoning_instructions`；assistant 前缀为 `<think>\n`（**开放**，等待模型产出推理） |
| | `false` | 不插入 reasoning_instructions；assistant 前缀为 `<think>\n\n</think>\n\n`（**空块，已闭合**） |
| `reasoning_effort` | `xhigh`（默认）/ `medium` / `low` | 仅影响注入的 `reasoning_instructions` 文本；**`low` 官方说明其行为接近 `xhigh`** |

### 6.3 本阶段配置方法（**已开启关闭**）

- 启动参数：`--chat-template-kwargs '{"enable_thinking": false}'`
- **`[实测]` 已生效**，证据三选一即可确认，本阶段给了三条：
  1. 渲染提示（`/apply-template`）以 `<think>\n\n</think>\n\n` 结尾，且**不含** `Reasoning effort is set to`；
  2. 显式传 `enable_thinking=true` 时渲染提示变为以 `<think>\n` 结尾且**含** reasoning 指令
     → 说明该变量确实被模板读取，且当前默认值确为 `false`；
  3. 渲染提示 token 数 = **327**，与运行响应 `usage.prompt_tokens = 327` **完全一致**
     → 无法用「服务端事后剥离」解释。
- **`[实测]` 一个必须记录的行为**：即使 thinking 关闭，模型**仍会在回答开头生成一个空的
  `<think>\n\n</think>\n\n`**（内容 2 字符，仅换行）。这是模型自身行为，不是模板注入
  （模板注入的那份已在提示里，见第 3 条）。适配层为此保留 `think_block_present` / `think_chars`
  两个字段，**不做剥离**。
- **`[实测]` thinking 开启时的实际行为**（单次有界探测，非本阶段主配置）：
  模型产出 232 字符推理轨迹后仍输出完整四行，四字段解析成功；`finish_reason = stop`。
  → 即适配层的解析器对 thinking 开/关**两种形态都可用**（因为解析用行首锚点）。
  记录见 `runs/P0-v3-feasibility-20260924/thinking_probe.json`。

### 6.4 一个 API 变更（影响后续调用方式）

运行时会对 `--chat-template-kwargs` 里的 `enable_thinking` 发出**弃用告警**：

```
Setting 'enable_thinking' via --chat-template-kwargs is deprecated.
Use --reasoning on / --reasoning off instead.
```

- 本阶段仍使用 `--chat-template-kwargs`（因为要**直接证明**模板变量被设置，便于审计）。
- 后续阶段建议改用 `--reasoning off`（服务端另有 `--reasoning-effort`、`--reasoning-budget`）。
- **`[尚未验证]`**：`--reasoning off` 与 `--chat-template-kwargs {"enable_thinking": false}`
  是否在所有请求形态下**完全等价**，本阶段未做逐项对照（仅收到弃用提示）。

### 6.5 官方生成参数（模型卡 Best Practices，`[官方声明]`）

| 模式 | temperature | top_p | top_k | min_p | presence_penalty | repetition_penalty |
|---|---:|---:|---:|---:|---:|---:|
| Thinking（默认） | 1.0 | 0.95 | 20 | 0.0 | 0.0 | 1.0 |
| Instruct / 非思考 | **0.7** | **0.80** | 20 | 0.0 | **1.5** | 1.0 |

模型卡另注：这些值已写入 GGUF 的 `general.sampling.*`，**客户端不传也会用模型默认值**。
本机 GGUF 实测该三键为 `temp=1.0 / top_p=0.95 / top_k=20`（即 thinking 模式那一组）。

---

## 7. 本地是否已有完整权重

**是。** 三项独立证据：

1. **文件存在且体积正确**：两个 GGUF 字节数与上游公布值一致（见第 4 节表）。
2. **SHA256 逐字节复算一致**：5.9 GB 主体本地复算哈希 == 上游 LFS 对象哈希。
3. **运行时成功加载并推理**：`file type = PTQ1_0 - 1.75 bpw ternary (group 128)`，
   `offloaded 65/65 layers to GPU`，实际生成可用（见 `V3_P0_REPORT.md`）。

下载记录留档：`<model_root>\download\ptq1.log`
（开始 `Wed Sep 23 00:29:01 2026` → 结束 `00:34:28`，`curl_exit=0`）。
本机存在**静默截断**历史，因此「下载完成」本身不作为完整性证据，以哈希为准。

---

## 8. 尚未验证 / 需要用户补充的信息

| # | 项 | 状态 |
|---|---|---|
| 1 | 上游仓库的 **commit hash**（而非分支名 `master`） | `[尚未验证]`：ModelScope API 只返回分支名。若需 commit 级钉死请提供仓库页面或 commit id |
| 2 | 官方自报的 98.2% 能力保留 | `[官方声明]`，**无第三方复现**。本阶段**未做**任何能力评测，不对该数字背书 |
| 3 | 是否要保留视觉能力 | 本阶段按「纯文本任务」处理并**未加载**视觉塔。若后续需要图片输入，需显式加载 mmproj，并注意厂商记录的「视觉塔上显存 + 长上下文会挂死」 |
| 4 | PTQ1_0 vs PQ2_0 在本机的解码差异 | `[尚未验证]`：只装了 PTQ1_0。官方说明 Ampere 上 PTQ1_0 解码**慢于** PQ2_0，但 PQ2_0 显存更紧（本机 8 GB 属紧平衡） |
| 5 | `--reasoning off` 与 `--chat-template-kwargs` 的等价性 | `[尚未验证]`（见 6.4） |

**当前不需要用户补充任何信息即可继续本阶段**：模型身份已唯一确定。
仅在第 1 项（commit 级钉死）和第 3 项（视觉能力）上，需要用户在有需求时提供输入。
