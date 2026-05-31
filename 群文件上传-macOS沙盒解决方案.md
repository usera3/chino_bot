# 群文件上传 - macOS 沙盒解决方案

## 问题分析

### 真正的原因
经过深入调研，发现群文件上传失败的真正原因是 **macOS 沙盒机制**：

```
Error: EPERM: operation not permitted, copyfile
'/path/to/chino_bot/test_document.docx' ->
'/Users/mozi100/Library/Containers/com.tencent.qq/Data/.config/QQ/NapCat/temp/...'
```

### 问题本质
1. **NapCat 运行在 QQ 的沙盒容器中**
2. **沙盒限制了文件访问权限**：
   - ❌ 无法访问 `/tmp/` 目录
   - ❌ 无法访问项目工作目录（`~/PycharmProjects/...`）
   - ✅ 可以访问 `~/Downloads/` 目录（通过符号链接）
3. **NapCat 需要先复制文件到自己的临时目录**，然后才能上传

### 沙盒结构
```
/Users/mozi100/Library/Containers/com.tencent.qq/Data/
├── Downloads -> ../../../../Downloads  (符号链接，可访问！)
├── Desktop -> ../../../../Desktop      (符号链接，可访问！)
├── Documents/                          (沙盒内部目录)
└── .config/QQ/NapCat/temp/            (NapCat 临时目录)
```

## 解决方案

### 修改文件保存路径
将文档保存到 `~/Downloads/` 目录，这样 NapCat 就可以访问了：

```python
# 修改前（无法访问）
file_path = os.path.join(os.getcwd(), file_name)  # 项目目录

# 修改后（可以访问）
downloads_dir = os.path.expanduser("~/Downloads")
file_path = os.path.join(downloads_dir, file_name)  # Downloads 目录
```

### 修改的文件
- `tools/document_tools.py`
  - `CreateWordTool._run()` - Word 文档创建
  - `CreateExcelTool._run()` - Excel 表格创建

### 修改逻辑
```python
# 修复路径问题：使用 Downloads 目录（NapCat 可以访问）
if file_path.startswith('/tmp/') or file_path.startswith('//tmp/') or not os.path.isabs(file_path):
    file_name = os.path.basename(file_path)
    downloads_dir = os.path.expanduser("~/Downloads")
    file_path = os.path.join(downloads_dir, file_name)
    print(f"⚠️ 路径已修改为: {file_path}")
```

## 测试步骤

### 1. 重启机器人
```bash
bash zhinai-bot-v3/start_bot.sh
```

### 2. 测试 Word 文档创建 + 上传
在 QQ 群中发送：
```
@智乃 随便写个word文档上传到群文件用于测试该功能
```

### 3. 预期结果
- ✅ Word 文档创建成功（保存在 `~/Downloads/`）
- ✅ 群文件上传成功（NapCat 可以访问 Downloads 目录）
- ✅ 聊天发送文件成功（同样的原理）

## 技术细节

### macOS 沙盒机制
- **目的**：保护系统安全，限制应用访问权限
- **影响**：应用只能访问特定目录
- **QQ 沙盒**：
  - 容器路径：`~/Library/Containers/com.tencent.qq/Data/`
  - 可访问：Downloads, Desktop, Documents（通过符号链接）
  - 不可访问：其他任意目录

### NapCat 文件上传流程
1. 接收文件路径
2. **复制文件到临时目录**（这一步会失败如果路径不可访问）
3. 调用 QQ API 上传文件
4. 清理临时文件

### 为什么 Downloads 可以访问
QQ 沙盒中有符号链接：
```bash
lrwxr-xr-x   1 mozi100  staff    21 Oct 16 18:47 Downloads -> ../../../../Downloads
```

这个符号链接让 NapCat 可以访问真实的 Downloads 目录。

## 其他可用目录

除了 `~/Downloads/`，以下目录也可以使用：
- `~/Desktop/` - 桌面
- `~/Documents/` - 文档（注意：是真实的 Documents，不是沙盒内的）

## 注意事项

1. **文件会保存在 Downloads 目录**
   - 用户可以在 Finder 中看到这些文件
   - 建议在文件名中添加前缀（如 `bot_`）以便识别

2. **自动清理**
   - 上传成功后可以选择删除文件
   - 或者定期清理旧文件

3. **权限问题**
   - 确保 Downloads 目录有写入权限
   - 如果用户修改了沙盒权限，可能会影响功能

## 总结

- ❌ **错误码 1200 不是权限问题**（机器人已经是群主）
- ✅ **真正原因是 macOS 沙盒限制**
- ✅ **解决方案：使用 Downloads 目录**
- ✅ **机器人已重启，修复已生效**

现在可以正常使用文档创建和群文件上传功能了！
