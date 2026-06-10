# BIT Web AutoLogin

北京理工大学校园网自动登录守护脚本。基于 [bitsrun](https://github.com/BITNP/bitsrun) 实现，每 30 秒检测一次网络连接状态，离线时自动重新登录。

## 项目结构

```
BIT-Web-AutoLogin/
├── auto_login.py       # 自动登录守护脚本
├── helper.py           # CLI 桥接层 (settings.json → bitsrun)
├── test_auto_login.py  # pytest 测试用例 (14 项)
├── settings.json       # 凭据配置
├── Taskfile.yml        # task 任务入口
├── README.md           # 项目说明书
└── venv/               # Python 虚拟环境 (含 bitsrun + pytest)
```

## 环境要求

- Python3.10
- [bitsrun](https://pypi.org/project/bitsrun/) >= 3.7.1 (安装在 venv)
- [go-task](https://taskfile.dev/) (可选，用于快捷命令)
- pytest >= 9.0 (安装在 venv，用于测试)

## 快速开始

### 1. 配置凭据

编辑 `settings.json`，填入校园网账号：

```json
{
    "username": "你的学号",
    "password": "你的密码"
}
```

### 2. 启动自动登录

```powershell
python -m venv venv
./venv/Scripts/activate.ps1
pip install -r requirements.txt
./venv/Scripts/python.exe auto_login.py

# 或使用 task
task
```

启动后脚本进入守护模式，每 30 秒输出一次状态：

```
[2026-06-07 10:30:00] BIT Web AutoLogin 已启动
[2026-06-07 10:30:00] 用户: 3120250947  检测间隔: 30s
[2026-06-07 10:30:00] 按 Ctrl+C 退出

[2026-06-07 10:30:00] 在线 — 用户: 3120250947  IP: 10.0.0.123  已用流量: 879.3 MiB
[2026-06-07 10:30:30] 在线 — 用户: 3120250947  IP: 10.0.0.123  已用流量: 880.1 MiB
[2026-06-07 10:31:00] 已离线 (IP: 10.0.0.123), 尝试重新登录...
[2026-06-07 10:31:00] 登录成功 — 3120250947 (10.0.0.123) 已上线
```

按 `Ctrl+C` 退出守护进程。

## task 测试命令

| 命令 | 说明 |
|------|------|
| `task` | 启动自动登录守护 |
| `task status` | 检查当前网络状态 |
| `task status-json` | JSON 格式状态 |
| `task login` | 使用 settings.json 凭据登录 |
| `task login-verbose` | 登录并显示原始 API 响应 |
| `task logout` | 使用 settings.json 凭据登出 |
| `task test` | 完整测试流程：状态 → 登出 → 状态 → 登录 → 状态 |

## 运行 pytest

```powershell
./venv/Scripts/python.exe -m pytest test_auto_login.py -v
```

测试覆盖：

| 测试类 | 项数 | 内容 |
|--------|------|------|
| TestSettings | 3 | settings.json 存在性、字段校验 |
| TestHelperStatus | 3 | status / status-json / offline 输出 |
| TestHelperLoginLogout | 4 | login/logout 成功与失败处理 |
| TestAutoLoginLoop | 4 | 配置加载、时间格式、在线/离线循环逻辑 |

## 架构说明

```
settings.json ──→ helper.py ──→ bitsrun ──→ 10.0.0.55
                       ↑
Taskfile.yml ──────────┘  (task 命令统一走 helper.py)

auto_login.py (独立运行，直接调用 bitsrun)
```

- **helper.py** — CLI 桥接层，负责从 `settings.json` 读取凭据，封装 `status/login/logout/test` 四个子命令。所有 `task` 命令都通过它访问 bitsrun，避免 Taskfile.yml 中出现 shell 内联代码。
- **auto_login.py** — 守护进程，直接使用 bitsrun 库，不依赖 helper。
- **Taskfile.yml** — 只包含可执行文件调用，无 shell 内置命令（如 echo），兼容 PowerShell 7。

## 工作原理

```
┌──────────────┐    每 30s     ┌──────────────────┐
│  auto_login  │ ────────────→ │ get_login_status │
│    .py       │               │ (bitsrun API)    │
└──────┬───────┘               └────────┬─────────┘
       │                                │
       │  ┌─────────────────────┐       │
       │  │  user_name 非空?     │←──────┘
       │  └─────────┬───────────┘
       │            │
       │     ┌──────┴──────┐
       │     │             │
       │   [是]          [否]
       │     │             │
       │     ▼             ▼
       │  打印在线    User.login()
       │  状态信息    ───────────→ 10.0.0.55
       │                  API 认证
       │                      │
       │               ┌──────┴──────┐
       │               │             │
       │            error=ok      其他
       │               │             │
       │               ▼             ▼
       │           打印成功      打印失败
       │                         原因
       │
       ▼
    time.sleep(30)
```

核心流程：
1. 从 `settings.json` 读取用户名和密码
2. 调用 bitsrun 的 `get_login_status()` 查询 10.0.0.55 认证网关
3. 如果 `user_name` 字段存在 → 已在线，打印流量/时长等状态
4. 如果 `user_name` 为 None → 已离线，立即调用 `User.login()` 重新认证
5. 等待 30 秒后重复

## bitsrun 库架构

依赖的 bitsrun 包核心模块：

| 模块 | 文件 | 职责 |
|------|------|------|
| User | `user.py:40` | 网络用户实体，含 login/logout 方法 |
| get_login_status | `user.py:17` | 查询 10.0.0.55 在线状态 |
| read_config | `config.py:67` | 读取 bit-user.json 配置文件 |
| LoginStatusRespType | `models.py` | 登录状态响应类型定义 |
| print_status_table | `utils.py:12` | rich 表格美化输出 |

## 许可证

WTFPL — 与 bitsrun 保持一致。
