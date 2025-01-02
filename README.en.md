# JDK Version Manager

![Version](https://img.shields.io/badge/version-1.0.4-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20|%20macOS%20|%20Linux-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)

A user-friendly JDK version management tool that supports Windows, macOS, and Linux platforms.

[中文文档](README.md)

## Features

- 🚀 Online JDK Downloads: Support multiple JDK distributions (Oracle JDK, OpenJDK, Adoptium, Amazon Corretto, Zulu OpenJDK)
- 📂 Local JDK Management: Easily import and manage installed JDKs
- 🔄 Smart Version Switching: Quick switching between different JDK versions with multi-platform support
- 🛠 Environment Variable Management: Automatic configuration of JAVA_HOME, PATH, and CLASSPATH
- 💡 System Tray: Quick view and switch current JDK version
- 🎨 Theme Switching: Support light, dark, and cyan themes
- 🌐 Internationalization: Support for Chinese and English interfaces
- 🖥 Multi-platform Support:
  - Windows: Version switching using symbolic links
  - macOS: Support for Homebrew-installed JDKs, symbolic link switching
  - Linux: Support for apt/yum package managers, symbolic link switching
- 📝 Logging: Detailed operation logs with file recording support
- 🔧 Portable Support: No installation required, just extract and use
- 🔄 Auto Update: Support checking and downloading new versions

## System Requirements

- Windows 10/11, macOS 10.15+, or Linux (major distributions)
- Python 3.8+
- PyQt6 >= 6.4.0
- Disk Space: At least 100MB (excluding downloaded JDKs)

## Installation

### Windows
1. Download the latest installer (Recommended)
   - Download the latest installer from [Releases](https://gitee.com/l06066hb/jvman/releases)
   - Run the installer and follow the wizard
   - Launch the program from Start Menu or desktop shortcut
2. Portable Version
   - Download the latest portable ZIP file
   - Extract to any directory
   - Run jvman.exe

### macOS
1. Download the latest DMG file
2. Open the DMG and drag the app to Applications
3. Admin password required for first run

### Linux
1. Download the latest AppImage or deb/rpm package
2. Install the package or run the AppImage directly
3. Sudo privileges required for first run

### From Source
1. Clone the repository:
```bash
git clone https://gitee.com/l06066hb/jvman.git
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

### JDK Download Sources
- Oracle JDK: https://www.oracle.com/java/technologies/downloads/
- OpenJDK: https://jdk.java.net/
- Eclipse Temurin (Adoptium): https://adoptium.net/temurin/releases/
- Amazon Corretto: https://aws.amazon.com/corretto/
- Zulu OpenJDK: https://www.azul.com/downloads/

### Download Source Information
- Oracle JDK: Official distribution, requires Oracle account for download
- OpenJDK: Official open-source version, only provides latest three LTS versions and current development version
- Eclipse Temurin: Maintained by Eclipse Foundation, provides long-term stable support
- Amazon Corretto: Amazon's distribution, optimized for cloud environments
- Zulu OpenJDK: Azul's distribution, provides comprehensive version support

### Download Recommendations
- Recommend using LTS (Long Term Support) versions for production environments
- If download fails, try:
  1. Using proxy or VPN
  2. Switching to another distribution
  3. Downloading directly from official website and importing manually
- Some versions might be unavailable due to end of support, check each distribution's lifecycle policy

### Local JDK Management
1. Click "Add Local JDK"
2. Select JDK installation directory
3. Confirm addition

### Switch JDK Version
1. Select target JDK from the list
2. Click "Switch Version"
3. Wait for the switch to complete

### Platform-Specific Notes

#### Windows
- Version switching using symbolic links
- Administrator privileges required for system environment variables
- Native symbolic link support for Windows 10/11

#### macOS
- Support for Homebrew-installed JDKs
- Version switching using symbolic links
- Automatic shell config file updates (bash/zsh)
- Admin privileges required for symbolic links

#### Linux
- Support for apt/yum package manager installed JDKs
- Version switching using symbolic links
- Automatic shell config file updates (bash/zsh/fish)
- Sudo privileges required for symbolic links

### Notes
- Recommended to use ZIP version of JDK to avoid conflicts with installed versions
- First-time use requires administrator/sudo privileges for environment variable configuration
- If download fails, try manual download option
- Unix systems (macOS/Linux) need to reload shell config file for environment variables to take effect

## Build Instructions

### Build Portable Version
```bash
python scripts/build.py --platform windows --type portable
```

### Build Installer Version
```bash
python scripts/build.py --platform windows --type installer
```

### Build All
```bash
python scripts/build.py --platform windows --type all
```

## Changelog

### v1.0.5
- Added version switching in tray menu for quick JDK version changes
- Real-time display of current JDK version in tray icon
- Enhanced environment variable settings interface with sync status
- Improved UI styling with unified scrollbar appearance and interaction
- Fixed multiple interface synchronization and status update issues

### v1.0.4 (2024-01-05)
- Added installer support
- Added multi-platform support (Windows/macOS/Linux)
- Optimized version switching mechanism with cross-platform symbolic links
- Added package manager support (Homebrew/apt/yum)
- Improved shell configuration file management
- Enhanced environment variable setup
- Improved application stability
- Optimized build system, supporting portable and installer versions
- Unified version management using app.json for centralized configuration
- Improved icon display and resource management
- Enhanced logging system with file recording support

### v1.0.3 (2024-12-28)
- Fixed theme switching configuration saving
- Fixed configuration saving on program exit
- Optimized configuration management
- Improved program stability

### v1.0.2 (2024-12-26)
- Optimized interface layout and styles
- Improved environment variables settings panel
- Fixed theme switching issues
- Enhanced version information display
- Added usage recommendations

### v1.0.1 (2024-12-25)
- Optimized UI style and user experience
- Fixed local JDK duplicate addition issue
- Improved version switching functionality
- Enhanced download progress display
- Added detailed version information display

### v1.0.0 (2024-01-01)
- Initial release
- Basic functionality implementation

## Contributing

Issues and Pull Requests are welcome to help improve this project.

### Development Setup
1. Ensure Python 3.8 or higher is installed
2. Install virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```
3. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Coding Standards
- Follow PEP 8 coding conventions
- Use Black for code formatting
- Run unit tests before submitting
- Write clear commit messages

### Submitting Pull Requests
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Project Structure
```
jvman/
├── src/                # Source code directory
│   ├── ui/            # User interface related code
│   ├── utils/         # Utility classes and helper functions
│   └── i18n/          # Internationalization resources
├── tests/             # Test cases
├── docs/              # Documentation
├── scripts/           # Build and utility scripts
├── config/            # Configuration files
├── resources/         # Resource files
│   └── icons/        # Icon resources
└── requirements/      # Dependency configuration files
```

## FAQ

### Q: How to resolve environment variable setup failure?
A: Ensure running the program with administrator/sudo privileges or manually copy and set environment variable values.

### Q: What to do if download speed is slow?
A: Configure proxy server in settings or use manual download feature.

### Q: How to backup current configuration?
A: Program configuration files are stored in user directory, you can directly copy this directory for backup.

### Q: How to handle version switching failure?
A: Check if you have sufficient permissions and ensure the target JDK directory exists and is complete.

## Security
Please report security vulnerabilities to [security@example.com](mailto:security@example.com).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 