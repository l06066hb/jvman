# JDK 版本管理工具 (JDK Version Manager)

![Version](https://img.shields.io/badge/version-1.0.3-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

一个简单易用的 Windows JDK 版本管理工具，支持在线下载和本地 JDK 管理。

[English Document](README.en.md)

## 功能特点

- 🚀 在线下载 JDK：支持多个 JDK 发行版（Oracle JDK、OpenJDK、Adoptium、Amazon Corretto、Zulu OpenJDK）
- 📂 本地 JDK 管理：轻松导入和管理已安装的 JDK
- 🔄 智能版本切换：快速切换不同版本的 JDK
- 🛠 环境变量管理：自动配置 JAVA_HOME、PATH 和 CLASSPATH
- 💡 系统托盘：快速查看和切换当前 JDK 版本
- 🎨 主题切换：支持浅色、深色和青色主题
- 🌐 国际化：支持中文和英文界面（暂未开放）

## 系统要求

- Windows 10/11
- Python 3.8+
- PyQt6

## 安装使用

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/jvman.git
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

### 在线下载 JDK
1. 选择 JDK 发行版和版本
2. 选择下载目录
3. 点击下载并等待完成

### JDK 下载源
- Oracle JDK: https://www.oracle.com/java/technologies/downloads/
- OpenJDK: https://jdk.java.net/
- Eclipse Temurin (Adoptium): https://adoptium.net/temurin/releases/
- Amazon Corretto: https://aws.amazon.com/corretto/
- Zulu OpenJDK: https://www.azul.com/downloads/

### 下载源说明
- Oracle JDK: 官方发行版，需要 Oracle 账号下载
- OpenJDK: 官方开源版本，仅提供最新的三个 LTS 版本和最新开发版
- Eclipse Temurin: 由 Eclipse 基金会维护，提供长期稳定支持
- Amazon Corretto: 亚马逊发行版，针对云环境优化
- Zulu OpenJDK: Azul 发行版，提供全面的版本支持

### 下载建议
- 建议选择 LTS（长期支持）版本用于生产环境
- 如遇下载失败，可尝试：
  1. 使用代理或 VPN
  2. 切换到其他发行版
  3. 直接从官方网站下载后手动导入
- 部分版本可能因官方停止支持而无法下载，建议查看各发行版的生命周期说明

### 本地 JDK 管理
1. 点击"添加本地 JDK"
2. 选择 JDK 安装目录
3. 确认添加

### 切换 JDK 版本
1. 在列表中选择目标 JDK
2. 点击"切换版本"
3. 等待切换完成

### 注意事项
- 建议使用 ZIP 版本的 JDK，避免与已安装版本的环境变量冲突
- 首次使用时需要以管理员权限运行以配置环境变量
- 如遇下载失败，可尝试使用手动下载功能

## 更新日志

### v1.0.3 (2024-12-28)
- 修复主题切换保存问题
- 修复程序退出时配置保存问题
- 优化配置管理功能
- 提升程序稳定性

### v1.0.2 (2024-12-26)
- 优化界面布局和样式
- 改进环境变量设置面板
- 修复主题切换相关问题
- 优化版本信息显示
- 添加使用建议说明

### v1.0.1 (2024-12-25)
- 优化界面样式和用户体验
- 修复本地 JDK 重复添加问题
- 改进版本切换功能
- 优化下载进度显示
- 增加详细版本信息显示

### v1.0.0 (2024-01-01)
- 首次发布
- 基本功能实现

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进这个项目。

### 开发环境设置
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

### 代码规范
- 遵循 PEP 8 编码规范
- 使用 Black 进行代码格式化
- 提交前运行单元测试
- 编写清晰的提交信息

### 提交 Pull Request
1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 项目结构
```
jvman/
├── src/                # 源代码目录
│   ├── ui/            # 用户界面相关代码
│   ├── utils/         # 工具类和辅助函数
│   └── i18n/          # 国际化资源文件
├── tests/             # 测试用例
├── docs/              # 文档
└── requirements/      # 依赖配置文件
```

## 常见问题

### Q: 如何解决环境变量设置失败？
A: 请确保以管理员权限运行程序，或手动复制环境变量值进行设置。

### Q: 下载速度较慢怎么办？
A: 可以在设置中配置代理服务器，或使用手动下载功能。

### Q: 如何备份当前配置？
A: 程序配置文件存储在 `%APPDATA%/jvman` 目录下，可直接复制该目录进行备份。

## 相关项目
- [SDKMAN](https://github.com/sdkman/sdkman-cli) - 类 Unix 系统的 SDK 管理工具
- [Jabba](https://github.com/shyiko/jabba) - 跨平台 Java 版本管理器

## 安全说明
如发现任何安全漏洞，请发送邮件至 [security@example.com](mailto:security@example.com)。

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。 