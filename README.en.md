# JDK Version Manager (JVMAN)

![Version](https://img.shields.io/badge/version-1.0.1-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

A user-friendly JDK version management tool for Windows, supporting online downloads and local JDK management.

[中文文档](README.md)

## Features

- 🚀 Online JDK Downloads: Support multiple JDK distributions (Oracle JDK, OpenJDK, Adoptium, Amazon Corretto, Zulu OpenJDK)
- 📂 Local JDK Management: Easily import and manage installed JDKs
- 🔄 Quick Version Switching: Seamless JDK version switching using Junction
- 🛠 Environment Variable Management: Automatic configuration of JAVA_HOME, PATH, and CLASSPATH
- 💡 System Tray: Quick view and switch current JDK version
- 🎨 Theme Switching: Support light and dark themes

## System Requirements

- Windows 10/11
- Python 3.8+
- PyQt6

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/jvman.git
cd jvman
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python src/main.py
```

## Usage Guide

### Download JDK Online
1. Select JDK distribution and version
2. Choose download directory
3. Click download and wait for completion

### Local JDK Management
1. Click "Add Local JDK"
2. Select JDK installation directory
3. Confirm addition

### Switch JDK Version
1. Select target JDK from the list
2. Click "Switch Version"
3. Wait for the switch to complete

## Changelog

### v1.0.1 (2024-01-14)
- Optimized UI style and user experience
- Fixed local JDK duplicate addition issue
- Improved version switching functionality
- Enhanced download progress display
- Added detailed version information display

### v1.0.0 (2024-01-10)
- Initial release
- Basic functionality implementation

## Contributing

Issues and Pull Requests are welcome to help improve this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 