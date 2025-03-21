# JDK 版本管理工具

[![Version](https://img.shields.io/badge/version-1.0.11-blue)](https://github.com/l06066hb/jvman/releases)
[![Platform](https://img.shields.io/badge/platform-Windows%20|%20macOS%20|%20Linux-lightgrey.svg)](https://github.com/l06066hb/jvman)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/l06066hb/jvman/actions)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20Project-ff5e5b?logo=ko-fi)](https://ko-fi.com/l06066hb)

一个简单易用的 JDK 版本管理工具，支持 Windows、macOS 和 Linux 平台。

[English](README.md) | [简体中文](README.zh-CN.md)

## 代码仓库
- GitHub: https://github.com/l06066hb/jvman
- Gitee: https://gitee.com/l06066hb/jvman

## 功能特点

- 🚀 在线下载 JDK：支持主流 JDK 发行版（Oracle JDK、OpenJDK、Eclipse Temurin、Microsoft OpenJDK、Amazon Corretto、Azul Zulu）
- 📂 本地 JDK 管理：支持导入和管理本地已安装的 JDK，包括包管理器安装的版本
- 🔄 智能版本切换：通过符号链接实现无缝切换，支持托盘菜单快速切换
- 🛠 环境变量管理：自动配置和同步环境变量（JAVA_HOME、PATH、CLASSPATH），支持备份和还原
- 💡 系统托盘：显示当前 JDK 版本，支持快速切换和状态查看
- 🎨 主题切换：内置浅色、深色和青色主题，支持自动跟随系统
- 🌐 国际化：完整的中英文界面支持，支持运行时切换
- 📚 帮助文档：内置详细的使用文档，支持搜索和快速导航
- 🖥 多平台支持：
  - Windows：支持 10/11 原生符号链接，自动配置系统环境变量
  - macOS：支持符号链接切换，自动更新 shell 配置（bash/zsh）
  - Linux：支持符号链接切换，自动更新 shell 配置文件（bash/zsh/fish）
- 🔧 便携模式：支持便携版（绿色版）和安装版双模式
- 🔄 自动更新：支持在线检查更新，可配置更新周期和通知方式

## 程序截图

### 主界面
![主界面](resources/screenshots/main_window_zh.png)

## 系统要求

- Windows 10/11、macOS 10.15+ 或 Linux（主流发行版）
- Python 3.8+
- PyQt6 >= 6.4.0
- 磁盘空间：至少 100MB（不含下载的 JDK）

## 安装使用

### 下载
- [GitHub Releases](https://github.com/l06066hb/jvman/releases) (国际)
- [Gitee 发行版](https://gitee.com/l06066hb/jvman/releases) (中国大陆)

### Windows
1. 安装版
   - 下载并运行最新的安装程序 (jvman-x.x.x-windows-setup.exe)
   - 按照安装向导完成安装
   - 从开始菜单或桌面快捷方式启动程序
2. 便携版
   - 下载最新的便携版 ZIP 文件
   - 解压到任意目录
   - 运行 jvman.exe

### macOS
1. 下载最新版本的 DMG 文件
2. 打开 DMG 文件并将应用拖到应用程序文件夹
3. 运行 jvman.app

### Linux (测试中)
1. 下载最新版本的 AppImage 或 deb/rpm 包
2. 安装对应的包或直接运行 AppImage

### 从源码安装
1. 克隆仓库：
```bash
git clone https://gitee.com/l06066hb/jvman.git 或 https://github.com/l06066hb/jvman.git
cd jvman
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行程序：
```bash
python src/main.py
```

## 使用说明

### 基础功能

#### 本地 JDK 管理
1. 添加本地 JDK
   - 点击"添加本地 JDK"
   - 选择 JDK 安装目录
   - 确认添加
2. 版本切换
   - 在列表中选择目标 JDK
   - 点击"切换版本"或使用托盘菜单快速切换
   - 等待切换完成

#### 在线下载 JDK
1. 选择 JDK 发行版和版本
2. 选择下载目录
3. 点击下载并等待完成

##### JDK 发行版说明
- Oracle JDK: 官方发行版，需要 Oracle 账号下载
- OpenJDK: 官方开源版本
- Eclipse Temurin: Eclipse 基金会维护，提供长期稳定支持
- Microsoft OpenJDK: 微软发行版，针对云环境优化
- Amazon Corretto: 亚马逊发行版，针对云环境优化
- Azul Zulu: Azul 发行版，提供全面的版本支持

##### 下载建议
- 建议选择 LTS（长期支持）版本用于生产环境
- 如遇下载失败，可尝试：
  1. 使用代理或 VPN
  2. 切换到其他发行版
  3. 直接从官方网站下载后手动导入
- 部分版本可能因官方停止支持而无法下载，建议查看各发行版的生命周期说明

### 高级功能

#### 环境变量管理
- 自动配置 JAVA_HOME、PATH 和 CLASSPATH
- 支持自动和手动两种配置模式
- 实时显示环境变量同步状态

#### IDE 集成
- 支持主流 IDE（IntelliJ IDEA、VS Code、Eclipse）
- 使用软链接路径实现自动版本同步
- 详细配置说明见 [IDE 集成指南](resources/docs/zh_CN/ide_integration.md)

#### 系统托盘
- 实时显示当前 JDK 版本
- 快速切换版本
- 最小化到托盘继续运行

### 平台特定说明

#### Windows
- 使用符号链接进行版本切换
- 需要管理员权限修改系统环境变量
- 支持 Windows 10/11 的原生符号链接
- 自动配置系统环境变量（JAVA_HOME、PATH）

#### macOS
- 使用符号链接进行版本切换
- 自动更新 shell 配置文件（~/.zshrc、~/.bash_profile）

#### Linux
- 使用符号链接进行版本切换
- 自动更新 shell 配置文件（~/.bashrc、~/.zshrc）

### 注意事项
- 建议使用 ZIP 版本的 JDK，避免与已安装版本的环境变量冲突
- 如遇下载失败，可尝试使用手动下载功能

### 下载源
- Oracle JDK: https://www.oracle.com/java/technologies/downloads/
- OpenJDK: https://jdk.java.net/
- Eclipse Temurin (Adoptium): https://adoptium.net/temurin/releases/
- Microsoft OpenJDK: https://learn.microsoft.com/en-us/java/openjdk/
- Amazon Corretto: https://aws.amazon.com/corretto/
- Azul Zulu: https://www.azul.com/downloads/

## 构建说明

### 构建便携版
```bash
python scripts/build.py --platform windows --type portable
```

### 构建安装版
```bash
python scripts/build.py --platform windows --type installer
```

### 构建全部
```bash
python scripts/build.py --platform windows --type all
```

## 最新版本

v1.0.11 的主要更新：
- ✨ [Added] macOS 原生菜单栏支持
- ✨ [Added] macOS Dock 菜单支持
- ✨ [Added] - 添加应用程序标准快捷键支持
- ✨ [Added] - 添加窗口管理相关的国际化支持
- 🔄 [Changed] macOS 平台下的窗口行为
- 🔄 [Changed] - 改进托盘图标的交互方式

完整的更新历史请查看 [CHANGELOG.md](CHANGELOG.md)


## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进这个项目。

#### 开发环境设置
1. 确保安装了 Python 3.8 或更高版本
2. 安装虚拟环境（推荐）：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```
3. 安装开发依赖：
```bash
pip install -r requirements-dev.txt
```

4. 安全注意事项：
- 不要在代码中硬编码任何密钥或敏感信息
- 使用 .env 文件存储本地配置（已在 .gitignore 中排除）
- 确保敏感信息不会被提交到代码库

#### 代码提交
1. Fork 项目到自己的仓库
2. 创建功能分支：
```bash
git checkout -b feature/your-feature-name
```
3. 提交更改：
```bash
git commit -am '添加新功能：功能描述'
```
4. 推送到你的仓库：
```bash
git push origin feature/your-feature-name
```
5. 创建 Pull Request

#### 代码规范
- 代码风格
  - 遵循 [PEP 8](https://peps.python.org/pep-0008/) 编码规范
  - 使用 [Black](https://black.readthedocs.io/) 进行代码格式化（行长度限制：88）
  - 使用 [isort](https://pycqa.github.io/isort/) 对导入进行排序
  - 使用 [flake8](https://flake8.pycqa.org/) 进行代码质量检查
  - 使用 [mypy](https://mypy.readthedocs.io/) 进行类型检查

- 提交规范
  - 提交前运行单元测试：`pytest tests/`
  - 提交信息格式：
    ```
    <类型>: <描述>

    <可选的详细描述>
    ```
  - 类型说明：
    - feat: 新功能（比如添加深色主题）
    - fix: 修复问题（比如修复环境变量设置）
    - docs: 文档变更（比如更新 README）
    - style: 代码格式修改（比如调整缩进）
    - refactor: 代码重构（比如重构配置管理）
    - perf: 性能优化（比如优化下载速度）
    - test: 测试用例相关（比如添加单元测试）
    - ci: 持续集成相关（比如修改 GitHub Actions）
    - chore: 其他修改（比如更新依赖）

## 项目结构
```
jvman/
├── src/                # 源代码目录
│   ├── ui/            # 用户界面相关代码
│   ├── utils/         # 工具类和辅助函数
│   └── i18n/          # 国际化资源文件
├── tests/             # 测试用例
├── docs/              # 文档
├── scripts/           # 构建和工具脚本
├── config/            # 配置文件
├── resources/         # 资源文件
│   └── icons/        # 图标资源
└── requirements/      # 依赖配置文件
```

## 常见问题

### Q: 如何解决环境变量设置失败？
A: 请确保以管理员权限运行程序，或手动复制环境变量值进行设置。

### Q: 下载速度较慢怎么办？
A: 可以在设置中配置代理服务器，或使用手动下载功能。

### Q: 如何备份当前配置？
A: 程序配置文件存储在 `%APPDATA%/jvman` 目录下，可直接复制该目录进行备份。

### Q: 如何处理版本切换失败？
A: 检查是否有足够的权限，确保目标 JDK 目录存在且完整。

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 支持项目

如果这个项目对你有帮助，你可以：

- ⭐ Star 这个项目
- 🐛 提交 Issue 或 Pull Request
- 💬 帮助解答其他用户的问题
- 💝 [打赏开发者](docs/sponsor.md)

你的支持将帮助项目持续维护和改进。感谢每一位贡献者！