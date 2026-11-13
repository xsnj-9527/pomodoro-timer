# 番茄钟 (Pomodoro Timer)

一个基于 Python 与 CustomTkinter 构建的现代化本地桌面番茄钟应用，默认采用深色卡片主题，核心倒计时状态机与 UI 解耦，支持长休息周期、白噪音、置顶迷你悬浮窗、7 日统计图表、系统托盘、专属图标及桌面快捷方式。

## 功能特点

- **三模式倒计时核心**：默认 `25 分钟` 专注 + `5 分钟` 短休息 + `15 分钟` 长休息（默认每 `4 轮` 专注自动进入长休息），支持 **开始 / 暂停 / 重置** 与可视化进度条。
- **自定义时长与周期**：支持随时调整专注、短休息、长休息时长（1 ~ 180 分钟）及长休息间隔轮数（1 ~ 20 轮）。
- **内置白噪音**：本地无损合成 `柔和白噪音`、`粉红雨声`、`深海褐噪音`、`微风暖噪` 四种无缝循环白噪音，支持开启「仅专注时播放」或自由试听。
- **置顶迷你悬浮窗**：一键开启紧凑型置顶悬浮窗，支持鼠标左键拖拽定位、快捷开始/暂停/重置及一键返回主窗口。
- **统计图表与任务记录**：支持输入当前任务名称（可选），专注完成后自动记录到 `data/task_history.json`，并提供「按分钟 / 按番茄数」切换的近 7 日自适应柱状图与汇总卡片。
- **系统托盘与桌面集成**：支持最小化至系统托盘（右键快捷控制计时与退出）、专属番茄表盘应用图标（`assets/pomodoro.ico`）以及一键生成 Windows 桌面快捷方式。
- **完成提醒与双主题**：倒计时结束自动播放轻快提示音并弹出 Windows 通知气泡；支持一键切换深色 / 浅色模式。

## 环境要求

- Python 3.10 或更高版本（Windows 下内置 `winsound` 与系统通知支持）
- 第三方依赖：`customtkinter >= 5.2.2`、`Pillow >= 10.0.0`、`pystray >= 0.19.5`

## 安装与运行

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 运行应用：

```bash
python main.py
```

3. 单独生成桌面快捷方式（也可在应用右上角点击 `🔗 桌面快捷方式`）：

```bash
python shortcut_helper.py
```

4. 运行自检测试：

```bash
python -m unittest discover -s tests -v
```

## 项目结构

```text
pomodoro-timer/
├── main.py               # 应用启动入口
├── config.py             # 窗口尺寸、默认时长、资源路径与配色配置
├── timer_engine.py       # 倒计时状态机与长休息周期逻辑
├── storage.py            # 本地 JSON 任务历史记录与多日统计数据源
├── notifier.py           # 后台线程声音提醒与系统通知
├── white_noise.py        # 无缝循环白噪音合成与播放控制
├── icon_helper.py        # 专属 PNG / 多尺寸 ICO 图标生成
├── tray_manager.py       # pystray 系统托盘图标与菜单管理
├── shortcut_helper.py    # Windows 桌面快捷方式生成工具
├── requirements.txt      # 依赖声明
├── README.md             # 项目说明文档
├── assets/               # 生成的专属应用图标 (pomodoro.ico / pomodoro.png)
├── ui/
│   ├── __init__.py
│   ├── app.py            # CustomTkinter 主界面实现
│   ├── mini_window.py    # 置顶迷你悬浮窗组件
│   └── stats_chart.py    # 近 7 日专注统计图表组件
└── tests/
    └── test_core.py      # 核心逻辑、白噪音、图标与 UI 冒烟测试
```
