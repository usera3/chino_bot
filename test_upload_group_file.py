"""
测试群文件上传功能
直接调用 OneBot API
"""
import asyncio
import os
from nonebot import get_driver, get_bot
from nonebot.adapters.onebot.v11 import Bot


async def test_upload():
    """测试上传群文件"""
    print("\n" + "=" * 60)
    print("测试群文件上传功能")
    print("=" * 60)
    
    try:
        # 获取 Bot 实例
        bot = get_bot("2509109290")
        print(f"✅ 获取 Bot 实例成功: {bot}")
        
        # 创建测试文件
        test_file = "test_upload.txt"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("这是一个测试文件\n")
            f.write("用于测试群文件上传功能\n")
            f.write("创建时间：2026-01-19\n")
        
        file_size = os.path.getsize(test_file)
        print(f"✅ 创建测试文件: {test_file} ({file_size} bytes)")
        
        # 测试群号
        group_id = 878812866
        
        # 方法 1：使用绝对路径
        print(f"\n🧪 测试 1: 使用绝对路径")
        abs_path = os.path.abspath(test_file)
        print(f"   文件路径: {abs_path}")
        
        try:
            result = await bot.call_api(
                "upload_group_file",
                group_id=group_id,
                file=abs_path,
                name="测试文件.txt"
            )
            print(f"   ✅ 上传成功: {result}")
        except Exception as e:
            print(f"   ❌ 上传失败: {e}")
            print(f"   错误类型: {type(e).__name__}")
            if hasattr(e, 'retcode'):
                print(f"   错误码: {e.retcode}")
        
        # 方法 2：使用 file:// 协议
        print(f"\n🧪 测试 2: 使用 file:// 协议")
        file_url = f"file:///{abs_path}"
        print(f"   文件 URL: {file_url}")
        
        try:
            result = await bot.call_api(
                "upload_group_file",
                group_id=group_id,
                file=file_url,
                name="测试文件2.txt"
            )
            print(f"   ✅ 上传成功: {result}")
        except Exception as e:
            print(f"   ❌ 上传失败: {e}")
            print(f"   错误类型: {type(e).__name__}")
            if hasattr(e, 'retcode'):
                print(f"   错误码: {e.retcode}")
        
        # 方法 3：使用相对路径
        print(f"\n🧪 测试 3: 使用相对路径")
        print(f"   文件路径: {test_file}")
        
        try:
            result = await bot.call_api(
                "upload_group_file",
                group_id=group_id,
                file=test_file,
                name="测试文件3.txt"
            )
            print(f"   ✅ 上传成功: {result}")
        except Exception as e:
            print(f"   ❌ 上传失败: {e}")
            print(f"   错误类型: {type(e).__name__}")
            if hasattr(e, 'retcode'):
                print(f"   错误码: {e.retcode}")
        
        # 方法 4：测试 base64 编码
        print(f"\n🧪 测试 4: 使用 base64 编码")
        import base64
        with open(test_file, "rb") as f:
            file_data = f.read()
            file_base64 = base64.b64encode(file_data).decode()
        
        print(f"   Base64 长度: {len(file_base64)}")
        
        try:
            result = await bot.call_api(
                "upload_group_file",
                group_id=group_id,
                file=f"base64://{file_base64}",
                name="测试文件4.txt"
            )
            print(f"   ✅ 上传成功: {result}")
        except Exception as e:
            print(f"   ❌ 上传失败: {e}")
            print(f"   错误类型: {type(e).__name__}")
            if hasattr(e, 'retcode'):
                print(f"   错误码: {e.retcode}")
        
        # 清理测试文件
        os.remove(test_file)
        print(f"\n✅ 清理测试文件")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


async def test_get_group_files():
    """测试获取群文件列表"""
    print("\n" + "=" * 60)
    print("测试获取群文件列表")
    print("=" * 60)
    
    try:
        bot = get_bot("2509109290")
        group_id = 878812866
        
        print(f"🧪 获取群 {group_id} 的文件列表")
        
        try:
            result = await bot.call_api(
                "get_group_root_files",
                group_id=group_id
            )
            print(f"✅ 获取成功:")
            print(f"   文件数: {len(result.get('files', []))}")
            print(f"   文件夹数: {len(result.get('folders', []))}")
            
            # 显示文件列表
            files = result.get('files', [])
            if files:
                print(f"\n📄 文件列表:")
                for file in files[:5]:  # 只显示前5个
                    name = file.get('file_name', '未知')
                    size = file.get('file_size', 0) / (1024 * 1024)
                    print(f"   - {name} ({size:.2f} MB)")
            
        except Exception as e:
            print(f"❌ 获取失败: {e}")
            print(f"错误类型: {type(e).__name__}")
            if hasattr(e, 'retcode'):
                print(f"错误码: {e.retcode}")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)


async def main():
    """主函数"""
    # 等待 Bot 连接
    await asyncio.sleep(2)
    
    # 测试获取文件列表
    await test_get_group_files()
    
    # 测试上传文件
    await test_upload()


if __name__ == "__main__":
    # 需要在 NoneBot 环境中运行
    print("⚠️ 此脚本需要在 NoneBot 运行时执行")
    print("请使用: nb run 或在机器人运行时执行")
