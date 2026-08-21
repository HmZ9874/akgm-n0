# AKGM-N0

[![Research prototype](https://img.shields.io/badge/status-research_prototype-orange)](https://github.com/HmZ9874/akgm-n0)
[![Help wanted](https://img.shields.io/badge/help-wanted-brightgreen)](https://github.com/HmZ9874/akgm-n0/issues)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

> 我们正在寻找愿意共同审查冷启动边界、程序合成、形式化证明、搜索效率和真实物理实验的人。
> 如果你发现目标泄漏、伪普适公式、无效证明或更好的实验设计，请直接[提交 Issue](https://github.com/HmZ9874/akgm-n0/issues/new)。

AKGM-N0（Autonomous Knowledge Generation Model, N0）是一个可审计的数值知识生成研究原型。它尝试让系统从匿名数值、极少的底层计算原语和可执行反馈出发，构造程序、压缩重复计算、形成可复用语义、主动寻找反例，并把结论限制在证据真正支持的范围内。

它不是 Transformer，也不是在网页里训练的大语言模型。网页只负责显示实验、程序、证据、反例和声明边界；实际搜索与验证由本地 Python 程序运行。

## 项目要回答的问题

我们研究的不是“给定一串数字，猜下一个数字”，而是下面几个更严格的问题：

1. 不告诉数学名称和目标公式时，系统能否找到数字之间可执行的关系？
2. 系统能否把反复出现的底层指令压缩成一个自己命名的新运算？
3. 新运算能否在未见数据、不同数值尺度或不同物理轨迹上复用？
4. 反例出现时，系统能否拒绝、降级或缩小声明范围，而不是坚持错误结论？
5. 系统能否自己识别知识缺口、生成下一组实验，并在连续无新语义时停止？
6. 在真实公开物理数据上，匿名程序能否形成有记忆的动态计算方式？

## 诚实边界

目前代码证明的是“在明确有限的语言、实验和验证协议内，系统可以搜索并验证程序语义”，不是以下更强结论：

- 不是通用人工智能；
- 不是已经掌握全部数学或完整力学；
- 不是从绝对零先验产生数学，因为任何可运行系统都必须有表示、状态和执行规则；
- 不是仅凭有限样本证明公式对所有数学对象普适；
- 不是发现了人类未知的自然定律；
- V41 使用 NASA 历史实验档案，不是本项目自行完成的实时电池实验；
- V41 创建的 STATE_FOLD 是系统内部的新可复用语义，不代表循环状态模型对人类是新的。

仓库中的“发现”默认表示：对学习器的可见输入而言没有提供目标名称或目标公式，候选程序由受限搜索产生，并通过当前协议的验证门。它不自动等于人类数学史上的首次发现。

## 总体架构

~~~mermaid
flowchart LR
    A[匿名观察或底层工作负载] --> B[候选程序与片段枚举]
    B --> C[参数拟合与复杂度评分]
    C --> D[独立验证器]
    D -->|全部必要门通过| E[成功公式/语义库]
    D -->|非必要挑战失败| F[有界知识]
    D -->|必要门失败| G[错题库与反例]
    E --> H[复用与组合]
    F --> H
    G --> I[知识缺口分析]
    H --> I
    I --> J[生成下一实验或世界]
    J --> A
    E --> K[报告与网页证据面板]
    F --> K
    G --> K
~~~

主要边界：

- <code>src/akgm_n0/learner/</code>：学习器可执行程序、搜索器、语义创造器和自主实验规划器。
- <code>src/akgm_n0/evaluator/</code>：独立验证、隐藏数据、证明义务和声明边界。
- <code>configs/</code>：学习器可见契约和原语清单。
- <code>evaluator/</code>：封闭基准信息，不应挂载到学习器进程。
- <code>reports/data/</code>：实验摘要和审计证据。
- <code>dashboard/</code>：本地汇报页面。
- <code>tests/</code>：回归测试、反例测试和声明边界测试。

## 冷启动时到底提供了什么

项目包含多个逐步收紧的实验协议，必须区分它们，不能把后期结果倒灌成早期先验。

### Gen 0 数值程序协议

学习器可见：

- 匿名数值序列；
- 顺序和序列边界；
- 显式有效性掩码；
- 有边界检查的相对位置读取；
- 程序组合；
- <code>p_read_offset</code>、<code>p_add</code>、<code>p_subtract</code>、<code>p_scalar_parameter</code>、<code>p_compose</code>。

学习器不可见：

- 自然语言；
- 数学名称和公式名称；
- 数据生成器源代码及参数；
- 训练/验证/盲测标签；
- 预训练模型；
- 网络访问；
- 封闭评测中的人类目标解释。

Gen 0 确实给了加法和减法，因此它不能用于证明“加减法从绝对零原语中产生”。它用于验证最初的程序搜索、信息边界、独立验证和账本流程。

### V16 严格冷启动语义协议

V16 不加载成功程序、公式名称或动态运算符。运行时只有八个固定 opcode：

- 数据原语：<code>u_zero</code>、<code>u_unit</code>、<code>u_inc</code>、<code>u_dec</code>；
- 控制原语：<code>u_jz</code>、<code>u_jump</code>、<code>u_emit</code>、<code>u_halt</code>。

语义挖掘只从四个数据原语组成的匿名工作负载开始。这里仍然提供了计数器、寄存器、程序计数器和跳转等计算基底；研究目标是从基底中形成新的可复用运行时运算，而不是声称没有任何计算先验。

## 核心算法

### A. Gen 0 表达式程序搜索

候选程序是可执行 AST。例如：

~~~json
{
  "op": "p_subtract",
  "args": [
    {"op": "p_read_offset", "offset": 0},
    {"op": "p_scalar_parameter", "parameter_slot": 0}
  ]
}
~~~

搜索过程：

1. 按节点数从小到大枚举表达式树。叶节点是相对读取、标量参数或已验证语义调用；内部节点是加法或减法。
2. 对交换性的加法参数排序并对序列化 AST 去重，保证相同结构只有一个候选。
3. 只允许读取过去和当前位置，候选结构不能读取目标位置。
4. 按时间顺序把有效样本分为开发段和验证段，默认验证比例为 0.4。
5. 若程序包含一个线性标量参数 θ，执行器分别计算 θ=0 和 θ=1，从而得到 pᵢ(θ)=bᵢ+cᵢθ，再用一维最小二乘拟合：

   θ* = Σ cᵢ(yᵢ-bᵢ) / Σ cᵢ²

6. 使用验证误差和程序复杂度排序。当前目标函数是：

   J(P) = MSE_val(P) / max(Var(y), 10^-12) + λ · nodes(P)

   默认 λ=10^-3。排序还依次考虑原始验证 MSE、节点数和稳定候选 ID。
7. 执行器限制最大节点数、最大深度、有限数值、数值幅度、合法索引和有效性掩码。越界、NaN、无穷或未注册运算直接拒绝。

这是一种确定性的枚举式程序合成，不是梯度训练神经网络。

### B. 独立验证、反例和知识状态

候选搜索完成后，独立验证器重新执行程序。每个验证 case 指定：

- 数据范围：源数据留出、注册 OOD 或对抗挑战；
- 可用于重新拟合参数的前缀长度；
- 绝对误差容忍度；
- 该 case 是否是有效性的必要条件。

验证器只在前缀上拟合参数，在剩余位置逐点验证，并记录：

- MSE；
- 归一化 MSE；
- 最大绝对误差；
- 每一个超过容忍度的输入、预测、观测和误差。

状态规则：

| 状态 | 条件 |
| --- | --- |
| <code>verified</code> | 所有必要和非必要 case 都通过 |
| <code>bounded</code> | 所有必要 case 通过，但至少一个扩展挑战失败 |
| <code>rejected</code> | 任一必要 case 失败 |

因此，失败不会被删除历史证据；它会形成反例并限制知识的有效域。只有验证状态和证据允许的程序才能进入成功语义库，重复犯错由错题/反例记录阻止。

### C. 从重复操作创造新运算符

V16 的冷启动语义创造使用跨任务最小描述长度思想：

1. 在匿名指令流中枚举长度 2 到 4 的连续片段。
2. 把具体寄存器编号归一化成参数角色。例如，对寄存器 3 连续执行两次递增，会被归一为“对角色 0 执行两次 <code>u_inc</code>”。
3. 统计片段在不同 workload family 中的出现次数。候选至少要在 3 个 family 中获得支持，每个被计入的 family 至少出现 5 次。
4. 设片段编码成本为 T_body，调用成本为 T_call=1+arity，出现次数为 n：

   gain_per_use = T_body - T_call

   net_reward = n · gain_per_use - T_body

   只有单次有压缩增益且总体净收益为正的候选才保留。
5. 对候选在小型完整状态网格上执行，生成行为签名。与已有原语行为等价、恒等无状态效果或非法的候选进入拒绝记录。
6. 合格片段安装为不含语义名称的 opcode，例如 <code>nu_a1b2c3d4e5f6</code>。ID 绑定结构哈希，定义保存展开后的原语体和证书摘要。
7. 用新 opcode 重新压缩所有工作负载，再从压缩后的流中寻找更高代组合。依赖表必须无环，并受最大代数、arity 和原语展开跨度限制。

这里的“创造”具有明确含义：系统创建了此前注册表中不存在、可执行、可展开、跨工作负载有压缩价值的新运行时语义。它不保证该运算在人类理论中没有等价物。

### D. 正确性优先的 token 奖励

基础程序阶段的奖励是：

- 精确完成奖励：1,000,000；
- 非精确候选：每通过一个 case 奖励 1,000；
- 成本：展开后的原语执行 token + 存储程序 token；
- 最终 reward = correctness_reward - total_token_cost。

宏调用不能把真实工作隐藏成一个 token：执行成本按展开后的原语调度计数。这里的 token 是可执行程序编码和执行成本，不是大语言模型上下文 token。

### E. 自主知识缺口与实验循环

V17 的循环是：

1. 统计已知运算定义中的原语转移对和 arity。
2. 选择证据最少的原语转移，以及证据最少的 1 元或 2 元 arity，形成知识缺口。
3. 用缺口、轮次和随机种子生成承诺哈希。
4. 每轮生成 4 个匿名 family，每个 family 48 个 workload，每个 workload 36 条底层指令。
5. 运行 V16 语义扩展；新语义通过则加入注册表，等价或无收益候选进入拒绝记录。
6. 若本轮没有新语义，累计 sterile round；默认连续 4 轮无新语义时以 <code>semantic_saturation</code> 停止，另有 32 轮硬上限。

这个循环已经能自己选择下一项合成实验，但当前“新世界”仍是由已知计数器原语生成的合成世界，不等于开放式现实世界建模。把缺口选择扩展到未知真实装置，是我们最需要外部帮助的方向之一。

### F. 程序构造、证明与普适性

后续实验把候选程序与证明义务绑定，包括：

- 结构哈希与语义 ID 一致；
- 程序可展开到允许的底层原语；
- 隐藏输入和 OOD 输入通过；
- 依赖语义已被承认；
- 代数不变量或循环不变量成立；
- 变异版本必须被验证器拒绝；
- 声明域必须显式记录。

有限采样只能支持有限经验声明。只有提供了符号不变量、归纳步骤或等价变换证明的模块，才允许作相应范围的普适声明。当前仓库由多个专用证明器组成，不是一个已经覆盖现代数学的通用定理证明器。

## V41：NASA 匿名动态状态实验

V41 使用 NASA Ames Randomized Battery Usage 2 数据。适配器把字段匿名化为 Q0、Q1、Q2、Q3；学习器看不到电流、电压、温度或时间名称。人类含义只在实验结束后的评估报告中翻译。

候选动态程序：

1. <code>persistence</code>：保持上一状态；
2. <code>stateless</code>：只用当前匿名输入的仿射程序；
3. <code>state_fold</code>：把上一预测状态带入下一步。

STATE_FOLD 的实际递推结构是：

sₜ = w₀ + w₁sₜ₋₁ + w₂Q0ₜ + w₃Q2ₜ + w₄(Q3ₜ-Q3ₜ₋₁) + w₅Q3ₜ

初始状态取轨迹首个 Q1。系数在训练轨迹上用最小二乘拟合，候选按：

validation_RMSE + 10^-5 · node_count

选择。程序及系数先生成 SHA-256 commitment，随后封闭进程才释放 future holdout 和 cross-cell replication，从协议上阻止看到未来数据后改程序。

已记录结果：

- 在 RW3 训练/验证及 RW4 同批次跨电芯复现协议中，STATE_FOLD 通过既定门；
- 冻结程序随后用于未参与拟合的 RW5、RW6；
- 早期和中期寿命轨迹通过当前阈值；
- 晚期寿命 RMSE 超过阈值，最终状态为 <code>bounded</code>；
- 系统记录反例 <code>V41-CHALLENGE-LATE-LIFE-EXTRAPOLATION</code>，撤销“全寿命通用”声明，并要求未来创建显式 aging state。

这是项目希望坚持的行为：失败不是隐藏掉，而是缩小结论并决定下一项研究。

## 当前阶段地图

| 阶段 | 代码中的含义 | 当前边界 |
| --- | --- | --- |
| Gen 0 | 可审计 AST 搜索、验证器、账本 | 给定加减法，不代表自发现基础算术 |
| V8–V14 | 计数、符号、分割、折叠、代数闭包实验 | 多为受限任务和专用证明器 |
| V15–V17 | 自扩展运行时、冷启动语义、自主实验循环 | 世界仍由有限计数器基底生成 |
| V18–V21 | 目标驱动程序规划、程序构造和有理边界 | 不是通用数学规划器 |
| V22–V35 | 匿名物理与力学重构实验 | 主要是合成世界中的结构再发现 |
| V36–V40 | 科学发现协议、干预、实时 apparatus 接口 | 仍需独立装置和跨实验室复现 |
| V41 | NASA 历史物理轨迹上的匿名动态状态发现 | 晚期寿命外推失败，结论已限制 |

页面中的“高中”“力学”“科学”等标签表示某一组基准实验入口，不表示系统拥有与人类课程完全等价的综合能力。

## 快速开始

要求：

- Python 3.11 或更新版本；
- Node.js 22.13 或更新版本（汇报页面）；
- Python 依赖由 <code>pyproject.toml</code> 声明。

~~~powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
~~~

运行基础审计和实验：

~~~powershell
.\.venv\Scripts\python.exe scripts/audit_contracts.py
.\.venv\Scripts\python.exe scripts/run_search_smoke.py
.\.venv\Scripts\python.exe scripts/run_verification_smoke.py
.\.venv\Scripts\python.exe scripts/run_cold_start_semantics_v16.py
.\.venv\Scripts\python.exe scripts/run_autonomous_research_loop_v17.py
~~~

运行网页：

~~~powershell
cd dashboard
npm install
npm run dev
~~~

打开 <http://localhost:5173/>。网页是证据与实验报告界面，不是模型训练位置。

## NASA V41 数据复现

GitHub 仓库不包含 120 MB 官方 ZIP 和解压后的 MATLAB 文件。仓库保留紧凑快照、来源 URL、SHA-256 和实验报告。

官方资源：

<https://data.nasa.gov/docs/legacy/ames/2.Battery_Uniform_Distribution_Discharge_Room_Temp_DataSet_2Post.zip>

期望 archive SHA-256：

<code>18bf47337577e07872919327a6ee994adc59e33fd2901d69c5911c26102837b8</code>

在仓库根目录执行：

~~~powershell
$archive = "data\nasa_v41\Battery_Random_Walk_Room_Temp_2Post.zip"
Invoke-WebRequest -Uri "https://data.nasa.gov/docs/legacy/ames/2.Battery_Uniform_Distribution_Discharge_Room_Temp_DataSet_2Post.zip" -OutFile $archive
Get-FileHash $archive -Algorithm SHA256
Expand-Archive -Path $archive -DestinationPath "data\nasa_v41\official"
.\.venv\Scripts\python.exe scripts/build_nasa_battery_v41_snapshot.py
.\.venv\Scripts\python.exe scripts/run_official_dynamic_science_v41.py
.\.venv\Scripts\python.exe scripts/build_nasa_battery_v41_challenge.py
.\.venv\Scripts\python.exe scripts/run_nasa_blind_challenge_v41.py
~~~

必须先人工核对哈希与上述期望值一致。原始 ZIP 和解压目录不应提交到 Git。

## 我们希望得到哪些帮助

这是当前最重要的部分。欢迎研究者、工程师、数学家和实验人员参与：

1. 冷启动审计：寻找任何从文件名、配置、测试、数据分区或评价器泄漏到学习器的目标语义。
2. 形式化验证：把更多专用 Python 证明义务迁移到可机检的形式系统，并区分“有限测试”与“普适证明”。
3. 运算等价判定：改进跨程序、跨表示的行为等价与非平凡性判断，减少重复运算符。
4. 搜索扩展：用 e-graph、约束求解、归纳程序合成或更好的 MDL 搜索替代组合爆炸。
5. 真实科学实验：设计低成本、可重复、盲化的数据采集装置和跨实验室复现协议。
6. V41 aging state：针对 RW5/RW6 晚期寿命反例，设计不泄漏物理名称的状态扩展与预注册盲测。
7. 基准与反例：提交能击败当前候选的新数字世界、对抗数据和负结果。
8. 报告界面：让证据链、程序 AST、证明义务和失败边界更容易独立审查。
9. 安全与资源边界：审查生成程序的停机、内存、数值范围和沙箱隔离。

参与方式：

- 先创建 [Issue](https://github.com/HmZ9874/akgm-n0/issues/new)，说明要解决的知识缺口和验证方法；
- Pull Request 必须包含测试、复现命令和声明边界；
- 新公式或运算必须给出可执行定义、适用域、独立验证和至少一个反例搜索；
- 不接受只根据几个样本命名为“普适规律”的提交；
- 失败实验同样有价值，请保留负结果和反例。

## 可重复性检查清单

一个可承认的结果至少应记录：

- 输入快照和来源哈希；
- 学习器可见字段；
- evaluator-only 字段；
- 候选程序 AST 或 opcode 定义；
- 参数拟合范围；
- 程序 commitment；
- 留出/OOD/对抗 case；
- 复杂度或 token 成本；
- 反例；
- <code>verified</code>、<code>bounded</code> 或 <code>rejected</code> 状态；
- 明确写出的“未证明内容”。

## 许可证状态

本仓库当前公开用于审阅和协作，但尚未附带开源许可证。这意味着再分发和改作授权尚未声明。欢迎在 Issue 中建议适合科学研究、代码和数据来源边界的许可证；在仓库正式选择许可证前，请先联系项目所有者讨论大规模复用。

## 联系与讨论

- 项目问题、反例和合作建议：[GitHub Issues](https://github.com/HmZ9874/akgm-n0/issues)
- 代码贡献：[Pull Requests](https://github.com/HmZ9874/akgm-n0/pulls)

如果这个方向值得继续，我们最需要的不是更多漂亮的公式数量，而是更严格的盲测、更强的证明、更好的失败记录，以及真正独立的外部实验。
# bounty-fix-ref: https://github.com/HmZ9874/akgm-n0/issues/1
