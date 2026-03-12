# Skills 仓库结构整理设计（双轨，最小侵入）

## 背景与目标

当前项目是一个可运行的 Python 工程（`src/` + `tests/` + `run_sync.py`），但希望将能力纳入全局 agent 的 skills 管理体系。现状下，技能目录与业务代码分离不清，导致放入全局 skills 配置时不便。

本次设计目标同时满足三点：

1. 可直接被全局 agent config 识别与引用。
2. 现有功能与命令保持不变（零功能变更）。
3. 维护成本尽可能低（避免双份源码）。

## 约束与决策

- 采用双轨结构：保留现有工程作为主源码，同时新增 skills 分发层。
- 主来源（source of truth）是根目录工程，而不是 skills 目录。
- 重构力度为最小侵入：不迁移业务代码，不改变 CLI 行为。
- 命名策略为英文 slug + 中文标题：
  - 目录名/skill id 使用英文 kebab-case。
  - `SKILL.md` 内可使用中文名称与中文说明。

## 方案对比（结论）

### 方案 A（采用）：新增 skills 分发层，不搬源码

- 保留 `src/`、`tests/`、`run_sync.py`。
- 新增 `skills/<skill-slug>/` 作为可分发技能壳。
- 通过文档与命令约定将 skill 调用映射到现有入口。

理由：在不改变运行逻辑的前提下，最稳地满足“可识别 + 零变更 + 低维护”。

## 目标结构

```text
.
├─ src/
├─ tests/
├─ run_sync.py
├─ docs/
│  ├─ plans/
│  └─ skills-mapping.md              # 新增，记录 skills 与代码入口映射
└─ skills/
   └─ onelap-strava-sync/            # 示例 slug
      ├─ SKILL.md                    # 技能元信息与触发/用法
      ├─ README.md                   # 可选，维护说明
      └─ resources/                  # 可选，示例与辅助材料
```

## 架构与组件职责

- `skills/<slug>/SKILL.md`：
  - 定义 skill 名称、用途、触发条件、前置依赖。
  - 固化可执行命令示例与参数约定。
  - 不承载业务实现代码。
- `docs/skills-mapping.md`：
  - 记录“skill -> 命令入口 -> 代码模块”映射。
  - 明确维护规则：业务逻辑只改根目录源码。
- 根目录代码（既有）：
  - 继续承载 OneLap/Strava 同步逻辑与状态管理。

## 数据流与调用流

1. 全局 agent 识别并加载 `skills/<slug>/SKILL.md`。
2. skill 按约定命令触发根目录入口（`run_sync.py`）。
3. 入口调用 `src/sync_onelap_strava/*` 完成业务处理。
4. 日志与状态仍落到既有路径（如 `logs/sync.log`、状态存储文件）。

该流程确保 skill 只是“发现与编排层”，核心逻辑仍单点维护。

## 错误处理与兼容策略

- 路径兼容：SKILL 内命令统一按仓库根目录执行约定书写。
- 环境兼容：继续依赖既有 `.env` 键，不新增必填项。
- 可诊断性：SKILL 中补充常见失败定位（环境、登录、上传、限流）。
- 回滚简易：如不再使用 skills 层，仅删除 `skills/<slug>/` 与映射文档，不影响运行。

## 测试与验收标准

### 验收 A：全局可识别

- skills 目录与 `SKILL.md` 结构完整。
- 英文 slug 可在全局 agent 配置中稳定引用。

### 验收 B：零功能变更

- 以下命令行为与整理前一致：
  - `python run_sync.py`
  - `python run_sync.py --since YYYY-MM-DD`
  - `python run_sync.py --download-only --since YYYY-MM-DD`

### 验收 C：低维护成本

- 无业务源码复制到 skills 目录。
- 文档明确“代码改动只在根目录主源码进行”。

## 中文 skill 名称结论

- 机器可读标识（目录名、skill id）建议保持英文 slug。
- 面向人类的展示内容（标题、描述、示例）可以中文。

该策略兼顾跨平台兼容性与中文可读性，是当前最稳妥方案。

## 非目标（YAGNI）

- 本次不改业务算法与同步逻辑。
- 本次不拆分多 skill。
- 本次不引入新的部署/发布工具链。

## 后续衔接

设计通过后，下一步仅执行 `writing-plans` 流程，输出详细实施计划，再进入实际结构调整。
