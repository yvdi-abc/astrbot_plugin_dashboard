"""astrbot_plugin_dashboard 插件测试。

验证：
1. /菜单 命令生成分类菜单
2. /状态 命令生成健康汇总
3. 系统信息读取
4. DSH 会话数查询（mock）
5. 命令收集逻辑
"""
import asyncio
import json
import os
import sys
import tempfile
import types

sys.path.insert(0, "/root/.local/share/uv/tools/astrbot")

import importlib.util

spec = importlib.util.spec_from_file_location(
    "dashboard",
    "/root/dsh_projects/astrbot_plugin_dashboard/main.py",
)
plugin_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin_mod)


def collect_agen(agen):
    out = []

    async def runner():
        async for item in agen:
            out.append(item)

    asyncio.get_event_loop().run_until_complete(runner())
    return out


class MockEvent:
    def __init__(self, message_str=""):
        self.message_str = message_str

    def plain_result(self, text):
        return types.SimpleNamespace(text=text)


def make_plugin(config_overrides=None):
    config = {"show_system": True, "show_dsh": True, "dsh_base_url": "http://127.0.0.1:3080"}
    if config_overrides:
        config.update(config_overrides)
    return plugin_mod.DashboardPlugin(None, config)


# ---------- 测试 1: 系统信息读取 ----------
def test_system_info():
    plugin = make_plugin()
    info = plugin._get_system_info()
    assert "内存" in info, "应读取内存"
    assert "磁盘" in info, "应读取磁盘"
    assert "负载" in info, "应读取负载"
    print(f"PASS 测试1: 系统信息读取（内存={info['内存']}, 磁盘={info['磁盘']}）")


# ---------- 测试 2: AstrBot 配置读取 ----------
def test_astrbot_config():
    plugin = make_plugin()
    cfg = plugin._get_astrbot_config()
    assert "provider_settings" in cfg, "应读取到 provider_settings"
    assert "platform" in cfg, "应读取到 platform"
    print("PASS 测试2: AstrBot 配置读取")


# ---------- 测试 3: /状态 命令 ----------
def test_status_cmd():
    plugin = make_plugin()
    event = MockEvent("/状态")
    results = collect_agen(plugin.cmd_status(event))
    assert len(results) == 1, "应产出 1 条结果"
    text = results[0].text
    assert "Bot 状态" in text, f"应包含标题: {text[:50]}"
    assert "模型" in text, "应包含模型"
    assert "人设" in text, "应包含人设"
    assert "插件" in text, "应包含插件统计"
    print("PASS 测试3: /状态 命令生成健康汇总")


# ---------- 测试 4: /菜单 命令 ----------
def test_menu_cmd():
    plugin = make_plugin()
    event = MockEvent("/菜单")
    results = collect_agen(plugin.cmd_menu(event))
    assert len(results) == 1, "应产出 1 条结果"
    text = results[0].text
    assert "Bot 命令菜单" in text, f"应包含标题: {text[:50]}"
    assert "▫️" in text, "应有分类标记"
    print(f"PASS 测试4: /菜单 命令生成分类菜单（{len(text)} 字符）")


# ---------- 测试 5: DSH 会话数查询（mock） ----------
def test_dsh_count():
    plugin = make_plugin()

    # 替换 _get_dsh_sessions 为 mock
    async def mock_get():
        return 12

    plugin._get_dsh_sessions = mock_get
    event = MockEvent("/状态")
    results = collect_agen(plugin.cmd_status(event))
    assert "DSH 会话: 12" in results[0].text, "应显示 DSH 会话数"
    print("PASS 测试5: /状态 显示 DSH 会话数")


# ---------- 测试 6: 关闭系统信息 ----------
def test_hide_system():
    plugin = make_plugin({"show_system": False})
    event = MockEvent("/状态")
    results = collect_agen(plugin.cmd_status(event))
    assert "内存" not in results[0].text, "关闭后不应显示系统信息"
    print("PASS 测试6: 可配置隐藏系统信息")


if __name__ == "__main__":
    test_system_info()
    test_astrbot_config()
    test_status_cmd()
    test_menu_cmd()
    test_dsh_count()
    test_hide_system()
    print("\n✅ 全部 6 项测试通过")
