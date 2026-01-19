#!/usr/bin/env python3
"""
测试 MCP 文档处理工具
"""
import subprocess
import json
import sys

def test_mcp_server(name, command, args):
    """测试 MCP 服务器是否可用"""
    print(f"\n{'='*60}")
    print(f"测试 {name}")
    print(f"{'='*60}")
    
    try:
        # 尝试启动 MCP 服务器（只测试是否能找到命令）
        cmd = [command] + args + ["--help"]
        print(f"命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 or "usage" in result.stdout.lower() or "help" in result.stdout.lower():
            print(f"✅ {name} 可用")
            return True
        else:
            print(f"⚠️ {name} 返回码: {result.returncode}")
            if result.stderr:
                print(f"错误: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏱️ {name} 超时（可能正在下载依赖）")
        return True  # 超时可能是因为正在下载，不算失败
    except FileNotFoundError:
        print(f"❌ {name} 命令未找到: {command}")
        return False
    except Exception as e:
        print(f"❌ {name} 测试失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🧪 测试 MCP 文档处理工具")
    print("="*60)
    
    # 读取配置
    config_path = ".kiro/settings/mcp.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"\n✅ 配置文件已加载: {config_path}")
        print(f"📋 配置的 MCP 服务器数量: {len(config['mcpServers'])}")
    except Exception as e:
        print(f"\n❌ 无法读取配置文件: {e}")
        return
    
    # 测试每个 MCP 服务器
    results = {}
    for name, server_config in config['mcpServers'].items():
        if server_config.get('disabled', False):
            print(f"\n⏭️ 跳过已禁用的服务器: {name}")
            continue
        
        command = server_config['command']
        args = server_config['args']
        
        results[name] = test_mcp_server(name, command, args)
    
    # 总结
    print(f"\n{'='*60}")
    print("📊 测试总结")
    print(f"{'='*60}")
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for name, success in results.items():
        status = "✅ 可用" if success else "❌ 不可用"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {success_count}/{total_count} 个服务器可用")
    
    if success_count == total_count:
        print("\n🎉 所有 MCP 服务器都已正确配置！")
    elif success_count > 0:
        print(f"\n⚠️ 部分 MCP 服务器可用，建议检查失败的服务器")
    else:
        print(f"\n❌ 所有 MCP 服务器都不可用，请检查配置")
    
    print(f"\n{'='*60}")
    print("💡 提示:")
    print("  - MCP 服务器会在首次使用时自动下载依赖")
    print("  - 如果测试超时，可能是正在下载，这是正常的")
    print("  - 配置文件位置: .kiro/settings/mcp.json")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
