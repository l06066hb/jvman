# JDK 版本管理工具 (JDK Version Manager)

![Version](https://img.shields.io/badge/version-1.0.2-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

一个简单易用的 Windows JDK 版本管理工具，支持在线下载和本地 JDK 管理。

[English Document](README.en.md)

## 功能特点

- 🚀 在线下载 JDK：支持多个 JDK 发行版（Oracle JDK、OpenJDK、Adoptium、Amazon Corretto、Zulu OpenJDK）
- 📂 本地 JDK 管理：轻松导入和管理已安装的 JDK
- 🔄 快速版本切换：使用 Junction 实现无缝切换 JDK 版本
- 🛠 环境变量管理：自动配置 JAVA_HOME、PATH 和 CLASSPATH
- 💡 系统托盘：快速查看和切换当前 JDK 版本
- 🎨 主题切换：支持浅色、深色和青色主题
- 🌐 国际化：支持中文和英文界面

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

### v1.0.2 (2024-01-10)
- 优化界面布局和样式
- 改进环境变量设置面板
- 修复主题切换相关问题
- 优化版本信息显示
- 添加使用建议说明

### v1.0.1 (2024-01-05)
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

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。 