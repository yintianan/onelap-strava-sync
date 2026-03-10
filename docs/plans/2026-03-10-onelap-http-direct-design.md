# OneLap HTTP 直连接入设计（run_sync 实用化）

## 1. 目标与范围

- 目标：将当前占位版 `run_sync.py` 改为可直接执行的真实同步入口，接入 OneLap HTTP 客户端与 Strava 上传链路。
- 保持现有分层：`run_sync.py` -> `sync_engine` -> `onelap_client/strava_client/state_store/dedupe_service`。
- 本次范围仅限本地 CLI 场景，不引入服务化部署与 UI。

## 2. 架构与模块边界

- `run_sync.py`
  - 负责 `.env` 加载、参数解析、依赖组装、日志初始化、最终退出码。
  - 校验必填配置，缺失时快速失败并提示缺项（脱敏输出）。
- `onelap_client`
  - 提供真实 HTTP 适配器：`login()`、`list_fit_activities(since, limit)`、`download_fit(activity_id, output_dir)`。
  - 封装 OneLap 接口细节（URL、headers、cookie/token、响应解析）。
- `sync_engine`
  - 保持纯编排角色：拉取、下载、指纹、去重、上传、状态写入、汇总输出。
- `strava_client`
  - 继续负责 OAuth refresh、上传、轮询与 5xx 重试。
- `state_store` + `dedupe_service`
  - 继续提供增量去重与本地状态持久化，不做破坏性改动。

## 3. 数据流与运行行为

1. 启动：读取 `.env`，解析 `--since`，初始化日志。
2. OneLap 登录与拉取：登录后按 `since + limit` 获取候选活动。
3. 下载 FIT：逐条下载到本地目录。
4. 去重：`<sha256>|<start_time>` 与状态库比对。
5. 上传 Strava：上传并轮询结果。
6. 状态写入：仅成功上传后写入 `state.json`。
7. 输出汇总：`fetched X -> deduped Y -> success A -> failed B`。

## 4. 错误处理与一致性策略

- OneLap 登录失败：中止本轮并返回明确 `aborted_reason`。
- OneLap 风控/限流：安全终止本轮，避免高频重试。
- OneLap 单条下载失败：记失败并继续后续条目。
- Strava 5xx/网络错误：指数退避重试（有上限）。
- Strava 4xx：判定永久失败，不重试，记录原因。
- 一致性：只在 Strava 确认成功后更新状态，保证幂等与可恢复。

## 5. 配置与安全

- 配置来源：`.env`（配套 `.env.example`）。
- 必填：OneLap 账号密码、Strava 客户端参数与 refresh token。
- 日志安全：敏感字段脱敏；不输出明文密码/token。

## 6. 验收标准

- `python run_sync.py --help` 可用。
- `python run_sync.py --since YYYY-MM-DD` 在完整配置下可执行真实流程。
- 同一时间窗口重复执行不重复上传。
- 自动化测试覆盖并通过：CLI、OneLap adapter、retry、e2e summary。
