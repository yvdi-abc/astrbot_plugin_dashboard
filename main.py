import json
import os

import httpx

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api import logger, AstrBotConfig
from astrbot.api.star import Context, Star

# 内部 API 延迟导入（AstrBot 升级后可能变动，避免顶层导入导致插件加载失败）
try:
    from astrbot.core.star.star import star_map
    from astrbot.core.star.star_handler import star_handlers_registry, EventType
    _HAS_INTERNAL = True
except Exception:  # noqa: BLE001
    star_map = {}
    star_handlers_registry = None
    EventType = None
    _HAS_INTERNAL = False


class DashboardPlugin(Star):
    """Bot 面板插件。

    /菜单 —— 分类展示所有可用命令（解决"命令记不住"）
    /状态 —— QQ 内查看 bot 健康汇总（模型、人设、插件、DSH、系统资源）
    """

    # 命令分类映射（插件名 -> 分类）
    CATEGORIES = {
        "聊天": ["astrbot_plugin_ask", "astrbot_plugin_chat_enhancer", "astrbot_plugin_llm_amnesia"],
        "人设": ["astrbot_plugin_persona_switch"],
        "娱乐": ["astrbot_plugin_wifepicker", "astrbot_plugin_furry_zan", "astrbot_plugin_pokepro", "GUGUblack"],
        "实用": ["astrbot_plugin_dsh_bridge", "astrbot_plugin_simple_memory", "astrbot_plugin_link_resolver"],
        "创作": ["astrbot_plugin_omnidraw", "astrbot_plugin_qzone", "astrbot_plugin_qun_album"],
        "分析": ["astrbot_plugin_qq_group_daily_analysis", "astrbot_plugin_word_filter"],
        "管理": ["astrbot_plugin_help", "astrbot_plugin_server_ops", "builtin_commands", "builtin_commands_extension"],
    }

    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config if config is not None else {}

    # ------------------------------------------------------------------ #
    # 工具                                                               #
    # ------------------------------------------------------------------ #

    def _get_all_commands(self) -> dict[str, list[str]]:
        """获取所有插件的指令列表 {plugin_name: [cmds]}。"""
        from astrbot.core.star.filter.command import CommandFilter

        result = {}
        for handler in star_handlers_registry.get_handlers_by_event_type(
            EventType.AdapterMessageEvent, only_activated=True
        ):
            plugin_path = getattr(handler, "handler_module_path", "")
            # 提取插件名（data.plugins.xxx.main -> xxx）
            parts = plugin_path.split(".")
            plugin_name = ""
            for i, p in enumerate(parts):
                if p == "plugins" and i + 1 < len(parts):
                    plugin_name = parts[i + 1]
                    break
            if not plugin_name:
                plugin_name = plugin_path.split(".")[-2] if len(parts) >= 2 else plugin_path

            # 从 CommandFilter 提取真实命令名
            cmd = None
            for f in handler.event_filters:
                if isinstance(f, CommandFilter):
                    cmd = f.command_name
                    break
            if cmd and cmd != "未知":
                result.setdefault(plugin_name, [])
                if cmd not in result[plugin_name]:
                    result[plugin_name].append(cmd)
        return result

    def _get_plugin_display_name(self, plugin_name: str) -> str:
        """获取插件的显示名。"""
        # 尝试从 star_map 获取
        for path, md in star_map.items():
            if plugin_name in path and md.name:
                return md.name
        return plugin_name

    async def _get_dsh_sessions(self) -> int:
        """获取 DSH 会话数。"""
        base = str(self.config.get("dsh_base_url", "http://127.0.0.1:3080")).rstrip("/")
        if not base:
            return -1
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    f"{base}/api/session.list",
                    json={
                        "type": "client-request",
                        "rpcId": "dash-sessions",
                        "method": "session.list",
                        "payload": {},
                    },
                    headers={"Content-Type": "application/json"},
                )
                data = resp.json()
                if data.get("result", {}).get("ok"):
                    return len(data["result"]["value"].get("items", []))
        except Exception as e:
            logger.debug(f"获取 DSH 会话数失败: {e}")
        return -1

    def _get_astrbot_config(self) -> dict:
        """获取 AstrBot 配置。

        优先使用 context 注入的配置（真实运行环境），失败时读配置文件。
        """
        try:
            cfg = self.context.get_config()
            if cfg:
                return dict(cfg)
        except Exception:
            pass
        try:
            from astrbot.core.utils.astrbot_path import get_astrbot_data_path

            path = os.path.join(get_astrbot_data_path(), "cmd_config.json")
            with open(path, encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取配置失败: {e}")
            return {}

    def _get_system_info(self) -> dict:
        """获取系统资源信息。"""
        info = {}
        try:
            with open("/proc/meminfo") as f:
                meminfo = {}
                for line in f:
                    k, v = line.split(":")
                    meminfo[k.strip()] = int(v.strip().split()[0])
            total = meminfo.get("MemTotal", 0) / 1024 / 1024
            available = meminfo.get("MemAvailable", 0) / 1024 / 1024
            info["内存"] = f"{total - available:.1f}G/{total:.1f}G"
        except Exception:
            info["内存"] = "未知"
        try:
            st = os.statvfs("/")
            total = st.f_blocks * st.f_frsize / 1024**3
            free = st.f_bavail * st.f_frsize / 1024**3
            info["磁盘"] = f"{(total-free)/total*100:.0f}% 已用({free:.1f}G可用)"
        except Exception:
            info["磁盘"] = "未知"
        try:
            with open("/proc/loadavg") as f:
                info["负载"] = f.read().split()[0]
        except Exception:
            info["负载"] = "未知"
        return info

    # ------------------------------------------------------------------ #
    # 指令                                                               #
    # ------------------------------------------------------------------ #

    @filter.command("菜单")
    async def cmd_menu(self, event: AstrMessageEvent):
        """分类展示所有可用命令"""
        try:
            commands = self._get_all_commands()
            if not commands:
                yield event.plain_result("未获取到命令列表，可尝试 /help")
                return

            lines = ["📖 Bot 命令菜单", ""]

            # 按分类组织
            shown_plugins = set()
            for category, plugin_list in self.CATEGORIES.items():
                cat_lines = []
                for plugin_name in plugin_list:
                    cmds = commands.get(plugin_name, [])
                    if not cmds:
                        continue
                    display = self._get_plugin_display_name(plugin_name)
                    cat_lines.append(f"  {display}: {'、'.join('/'+c for c in cmds[:6])}")
                    shown_plugins.add(plugin_name)
                if cat_lines:
                    lines.append(f"▫️ {category}")
                    lines.extend(cat_lines)
                    lines.append("")

            # 未分类的插件
            uncategorized = []
            for plugin_name, cmds in commands.items():
                if plugin_name in shown_plugins or not cmds:
                    continue
                display = self._get_plugin_display_name(plugin_name)
                uncategorized.append(f"  {display}: {'、'.join('/'+c for c in cmds[:6])}")
            if uncategorized:
                lines.append("▫️ 其他")
                lines.extend(uncategorized)

            lines.append("")
            lines.append("💡 记不住？用 /菜单 随时查看；/状态 看 bot 健康")
            yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"生成菜单失败: {e}", exc_info=True)
            yield event.plain_result("❌ 生成菜单失败，请查看日志")

    @filter.command("状态")
    async def cmd_status(self, event: AstrMessageEvent):
        """查看 bot 健康汇总"""
        try:
            cfg = self._get_astrbot_config()
            ps = cfg.get("provider_settings", {})

            lines = ["📊 Bot 状态", ""]

            # 模型与人设
            default_provider = ps.get("default_provider_id", "未知")
            personality = ps.get("default_personality", "default")
            lines.append(f"🤖 模型: {default_provider}")
            lines.append(f"🎭 人设: {personality}")

            # 插件统计
            commands = self._get_all_commands()
            lines.append(f"🧩 插件命令: {sum(len(v) for v in commands.values())} 个 / {len(commands)} 插件")

            # 平台连接
            platforms = cfg.get("platform", [])
            for pl in platforms:
                if pl.get("enable"):
                    lines.append(f"📡 平台: {pl.get('type', '未知')} (已连接)")

            # DSH 桥接
            if self.config.get("show_dsh", True):
                dsh_count = await self._get_dsh_sessions()
                if dsh_count >= 0:
                    lines.append(f"🌉 DSH 会话: {dsh_count} 个")
                else:
                    lines.append("🌉 DSH: 查询失败")

            # 系统资源
            if self.config.get("show_system", True):
                sys_info = self._get_system_info()
                for k, v in sys_info.items():
                    lines.append(f"🖥 {k}: {v}")

            # 运行时间
            try:
                with open("/proc/uptime") as f:
                    uptime_s = float(f.read().split()[0])
                days = int(uptime_s // 86400)
                hours = int((uptime_s % 86400) // 3600)
                lines.append(f"⏱ 运行: {days}天{hours}小时")
            except Exception:
                pass

            yield event.plain_result("\n".join(lines))
        except Exception as e:
            logger.error(f"生成状态失败: {e}", exc_info=True)
            yield event.plain_result("❌ 生成状态失败，请查看日志")
