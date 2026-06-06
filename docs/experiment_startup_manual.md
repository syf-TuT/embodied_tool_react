# 实验启动用户手册

本文说明如何在本机 Docker Desktop 中启动 AI2-THOR 实验环境，并运行当前项目的最小闭环实验。

## 1. 确认运行位置

在 PowerShell 中进入项目根目录：

```powershell
cd F:\agent\embodied_tool_react
```

这一步是为了让 Docker Compose 能找到 `Dockerfile`、`docker-compose.yml`、代码目录和 `outputs/` 输出目录。

注意点：

- 后续命令都默认在项目根目录执行。
- 如果在其他目录执行，可能会出现找不到 compose 文件或输出目录不对的问题。

## 2. 确认 Docker Desktop 可用

执行：

```powershell
docker compose version
```

这一步是为了确认 Docker Desktop 和 Docker Compose 已经启动，并且当前终端可以访问 Docker。

注意点：

- 如果 Docker Desktop 没启动，先打开 Docker Desktop，等状态变为 running。
- 如果看到 Docker API permission denied，优先重启 Docker Desktop 或重新打开 PowerShell。

## 3. 构建 Linux 实验镜像

执行：

```powershell
docker compose build ai2thor
```

这一步会创建一个 Linux 容器镜像，安装 Python、AI2-THOR、Xvfb、Unity 运行所需的图形库等依赖。

注意点：

- 第一次构建会下载 Python 基础镜像、apt 依赖和 pip 包，耗时较长是正常的。
- 之后如果 Dockerfile 没变，构建会复用缓存，速度会快很多。

## 4. 启动默认最小实验

执行：

```powershell
docker compose run --rm ai2thor
```

这一步会在 Linux 容器中运行：

```bash
timeout 180s xvfb-run -a python scripts/run_ai2thor_minimal.py --platform linux64 --scene FloorPlan1 --instruction "put the apple in the fridge" --max-steps 8 --server-timeout 20
```

它会启动 AI2-THOR Unity 环境，并执行当前 rule-based planner 的闭环流程：

```text
search_object("Apple")
pick_object("Apple")
search_object("Fridge")
open_object("Fridge")
put_object("Fridge")
```

注意点：

- 第一次运行会下载 AI2-THOR 的 Linux64 Unity build，约数百 MB。
- 下载内容会缓存在 Docker volume `ai2thor_cache`，后续不需要重复下载。
- 当前默认命令使用 `linux64 + xvfb-run`，不要改回 `cloudrendering`；在 Docker Desktop 中 CloudRendering 下载到 100% 后可能卡在 Unity/Vulkan 握手。
- `timeout 180s` 是硬保护，避免 Unity action 偶发长时间不返回时一直挂住。

## 5. 查看运行结果

实验结束后，终端会打印 JSON 摘要，主要字段包括：

```json
{
  "success": false,
  "total_steps": 8,
  "replan_count": 3,
  "trajectory_path": "outputs/ai2thor_minimal/trajectories/ai2thor_minimal_001.json"
}
```

输出文件位于：

```text
outputs/ai2thor_minimal/
  trajectories/ai2thor_minimal_001.json
  summary.csv
  metrics.json
  skill_memory.json
```

这一步用于确认实验是否真正进入了闭环，而不只是启动了容器。

注意点：

- `success: false` 不一定表示仿真没启动；它可能只是当前策略没有完成任务。
- 判断仿真是否启动成功，优先看是否生成了 trajectory 文件和 metrics 文件。

## 6. 自定义场景或任务

执行：

```powershell
docker compose run --rm ai2thor xvfb-run -a python scripts/run_ai2thor_minimal.py --platform linux64 --scene FloorPlan1 --instruction "put the apple in the fridge" --max-steps 8 --server-timeout 20 --output-dir outputs/custom_run
```

这一步绕过 compose 默认 command，手动指定实验参数。

常用参数：

```text
--scene                 AI2-THOR 场景，例如 FloorPlan1
--instruction           任务指令，例如 "put the apple in the fridge"
--max-steps             最大工具调用步数
--server-timeout        单次 Unity action 等待超时秒数
--output-dir            输出目录
```

注意点：

- Docker Desktop 下建议保留 `--platform linux64` 和 `xvfb-run -a`。
- `--server-timeout 20` 可以避免单个 Unity action 卡太久。
- 如果想完整跑更长实验，可以调大 `--max-steps`，但运行时间也会变长。

## 7. 进入 Linux 容器调试

执行：

```powershell
docker compose --profile shell run --rm ai2thor-shell
```

进入容器后，可以手动运行：

```bash
python scripts/run_ai2thor_minimal.py --platform linux64 --scene FloorPlan1 --instruction "put the apple in the fridge" --max-steps 8 --server-timeout 20
```

如果要测试 AI2-THOR 基础动作链：

```bash
xvfb-run -a python scripts/probe_ai2thor_steps.py
```

如果要测试工具序列：

```bash
xvfb-run -a python scripts/probe_tool_sequence.py
```

注意点：

- 容器里的工作目录是 `/workspace`，对应宿主机项目目录。
- 容器里的 `/workspace/outputs` 会映射到宿主机的 `outputs/`。

## 8. 常见问题

### 下载到 100% 后长时间不动

如果日志停在类似：

```text
thor-CloudRendering-...zip: [ 100% ... ] of 797.MB
```

通常不是下载卡住，而是 CloudRendering 在 Docker Desktop 中启动 Unity/Vulkan 握手卡住。

处理方式：

```powershell
docker compose run --rm ai2thor
```

当前 compose 已经使用 `linux64 + xvfb-run`，不走 CloudRendering。

### 容器一直不退出

先用默认命令，它已经带了硬超时：

```powershell
docker compose run --rm ai2thor
```

如果手动运行，请加上：

```powershell
--server-timeout 20
```

必要时也可以在容器命令前加 Linux timeout：

```powershell
docker compose run --rm ai2thor timeout 180s xvfb-run -a python scripts/run_ai2thor_minimal.py --platform linux64
```

### 需要清理 AI2-THOR 下载缓存

一般不需要清理。只有在下载被强行中断、缓存 lock 状态异常时才考虑。

查看缓存 volume：

```powershell
docker volume ls
```

注意点：

- `ai2thor_cache` 保存 Unity build 下载结果。
- 删除该 volume 后，下次启动会重新下载 Unity build。

## 9. 推荐的最短启动流程

日常只需要执行：

```powershell
cd F:\agent\embodied_tool_react
docker compose build ai2thor
docker compose run --rm ai2thor
```

第一次运行重点看是否完成 Unity build 下载；后续运行重点看 JSON 摘要和 `outputs/ai2thor_minimal/` 下的结果文件。
