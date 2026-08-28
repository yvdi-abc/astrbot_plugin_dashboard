# AstrBot Bot 面板插件（astrbot_plugin_dashboard）

[![Version](https://img.shields.io/badge/version-v1.0.0-blue.svg)](https://github.com/yvdi-abc/astrbot_plugin_dashboard)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![AstrBot](https://img.shields.io/badge/AstrBot-Plugin-orange.svg)](https://github.com/Soulter/AstrBot)

在 QQ 内快捷查看 bot 状态与命令菜单，解决"功能多、命令记不住"的问题。

## ✨ 功能特性

### 📖 `/菜单` —— 命令速查

按分类展示所有可用命令，一目了然：

- ▫️ 聊天：`/ask`、`/增强`、`/forget`...
- ▫️ 人设：`/人设切换`、`/人设随机`...
- ▫️ 娱乐：`/今日老婆`、`/强娶`、`/求婚`...
- ▫️ 实用：`/dsh`、`/mem`...
- ▫️ 创作：`/绘图`、`/看说说`...
- ▫️ 管理：`/helps`、`/plugin`、`/状态`...

### 📊 `/状态` —— bot 健康汇总

- 🤖 当前模型（如 `MiMo/mimo-v2.5`）
- 🎭 当前人设（如 `芙宁娜5.0`）
- 🧩 插件命令统计
- 📡 平台连接状态
- 🌉 DSH 会话数（桥接插件）
- 🖥 系统资源（内存/磁盘/负载）
- ⏱ 运行时间

## 📦 安装

```bash
git clone https://github.com/yvdi-abc/astrbot_plugin_dashboard.git
```

将 `astrbot_plugin_dashboard` 文件夹复制到 AstrBot 的 `data/plugins` 目录，重启 AstrBot 或在控制面板重载插件。

## 🚀 使用方法

```
/菜单   查看全部命令（按分类）
/状态   查看 bot 健康汇总
```

## ⚙️ 配置说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `show_system` | bool | true | `/状态` 是否显示系统资源 |
| `show_dsh` | bool | true | `/状态` 是否显示 DSH 会话数 |
| `dsh_base_url` | string | http://127.0.0.1:3080 | DSH 服务地址（留空不查询） |

## 📄 许可证

MIT License

## 👤 作者

**yvdi-abc**
