# GitHub 推送指南

## 📦 推送 v3 版本到 GitHub

### 方法一：使用自动脚本（推荐）

```bash
# 在 zhinai-bot-v3 目录下执行
bash push_to_github.sh
```

脚本会自动完成：
1. ✅ 初始化 Git 仓库
2. ✅ 配置远程仓库
3. ✅ 创建 v3 分支
4. ✅ 添加所有文件
5. ✅ 提交更改
6. ✅ 推送到 GitHub

### 方法二：手动推送

```bash
# 1. 进入 v3 目录
cd zhinai-bot-v3

# 2. 初始化 Git（如果还没有）
git init

# 3. 添加远程仓库
git remote add origin https://github.com/usera3/chino_bot.git

# 4. 创建并切换到 v3 分支
git checkout -b v3

# 5. 添加所有文件
git add .

# 6. 提交
git commit -m "🎉 Release v3.0.0 - LangChain 企业级版本"

# 7. 推送到 GitHub
git push -u origin v3
```

## ⚠️ 推送前检查清单

### 必须检查的项目

- [ ] **删除敏感信息**
  ```bash
  # 确保 .env 文件不会被推送
  cat .gitignore | grep ".env"
  
  # 检查是否有敏感信息
  grep -r "API_KEY\|PASSWORD\|SECRET" . --exclude-dir=.git
  ```

- [ ] **清理测试数据**
  ```bash
  # 删除测试数据库
  rm -rf data/conversations/*
  rm -rf data/knowledge/*
  
  # 删除日志文件
  rm -rf logs/*.log
  ```

- [ ] **检查文件大小**
  ```bash
  # 查找大文件（>10MB）
  find . -type f -size +10M
  ```

- [ ] **验证 .gitignore**
  ```bash
  # 确保以下文件被忽略
  # - .env
  # - *.log
  # - data/
  # - __pycache__/
  # - *.pyc
  ```

### 推荐检查的项目

- [ ] 更新 README.md
- [ ] 更新 CHANGELOG.md
- [ ] 检查代码注释
- [ ] 运行测试
- [ ] 检查依赖版本

## 📝 提交信息规范

### 格式
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

### 示例
```bash
git commit -m "feat(memory): 添加双向量库记忆系统

- 实现对话向量库
- 实现知识向量库
- 添加知识自动提取
- 支持多用户隔离

Closes #123"
```

## 🌿 分支管理

### 分支说明

- `main` / `master`: 主分支（v2 版本）
- `v3`: v3 版本分支
- `dev`: 开发分支
- `feature/*`: 功能分支
- `hotfix/*`: 紧急修复分支

### 创建新分支

```bash
# 从 v3 创建功能分支
git checkout v3
git checkout -b feature/new-feature

# 开发完成后合并回 v3
git checkout v3
git merge feature/new-feature
```

## 🔄 更新代码

### 拉取最新代码

```bash
# 拉取 v3 分支最新代码
git checkout v3
git pull origin v3
```

### 解决冲突

```bash
# 如果有冲突
git status  # 查看冲突文件
# 手动解决冲突
git add .
git commit -m "fix: 解决合并冲突"
git push origin v3
```

## 📋 推送后的工作

### 1. 创建 Release

访问 GitHub 仓库：
1. 点击 "Releases"
2. 点击 "Create a new release"
3. 选择 v3 分支
4. 标签：`v3.0.0`
5. 标题：`v3.0.0 - LangChain 企业级版本`
6. 描述：复制 CHANGELOG.md 内容
7. 发布

### 2. 更新主 README

在仓库根目录的 README.md 中添加：

```markdown
## 版本说明

### v3.0 - LangChain 企业级版本（推荐）
- 📁 分支：`v3`
- 🚀 [查看代码](https://github.com/usera3/chino_bot/tree/v3)
- 📖 [使用文档](https://github.com/usera3/chino_bot/tree/v3/README.md)
- 🎯 企业级架构，功能强大

### v2.0 - 经典版本
- 📁 分支：`main`
- 🚀 [查看代码](https://github.com/usera3/chino_bot)
- 📖 [使用文档](https://github.com/usera3/chino_bot/blob/main/README.md)
- 🎯 简单易用，适合学习
```

### 3. 添加徽章

在 v3 的 README.md 顶部添加：

```markdown
![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-orange.svg)
![Stars](https://img.shields.io/github/stars/usera3/chino_bot?style=social)
```

### 4. 设置默认分支（可选）

如果希望 v3 成为默认分支：
1. 进入仓库 Settings
2. 点击 Branches
3. 修改 Default branch 为 `v3`

## 🐛 常见问题

### Q: 推送被拒绝？

```bash
# 强制推送（谨慎使用）
git push -f origin v3
```

### Q: 文件太大无法推送？

```bash
# 使用 Git LFS
git lfs install
git lfs track "*.db"
git add .gitattributes
git commit -m "chore: 添加 Git LFS"
```

### Q: 忘记添加 .gitignore？

```bash
# 删除已追踪的文件
git rm --cached .env
git commit -m "chore: 移除敏感文件"
```

### Q: 如何撤销推送？

```bash
# 撤销最后一次提交
git reset --hard HEAD~1
git push -f origin v3
```

## 📞 需要帮助？

- 📖 [Git 官方文档](https://git-scm.com/doc)
- 📖 [GitHub 帮助](https://docs.github.com/)
- 💬 [提交 Issue](https://github.com/usera3/chino_bot/issues)

---

祝推送顺利！🎉
