# JDK Version Manager (JVMAN)

![Version](https://img.shields.io/badge/version-1.0.3-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

A user-friendly JDK version management tool for Windows, supporting online downloads and local JDK management.

[中文文档](README.md)

## Features

- 🚀 Online JDK Downloads: Support multiple JDK distributions (Oracle JDK, OpenJDK, Adoptium, Amazon Corretto, Zulu OpenJDK)
- 📂 Local JDK Management: Easily import and manage installed JDKs
- 🔄 Smart Version Switching: Quick switching between different JDK versions with multi-platform support
- 🛠 Environment Variable Management: Automatic configuration of JAVA_HOME, PATH, and CLASSPATH
- 💡 System Tray: Quick view and switch current JDK version
- 🎨 Theme Switching: Support light, dark, and cyan themes
- 🌐 Internationalization: Support for Chinese and English interfaces (not supported yet)

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

### Notes
- Recommended to use ZIP version of JDK to avoid conflicts with installed versions
- First-time use requires administrator privileges for environment variable configuration
- If download fails, try manual download option

## Changelog

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
└── requirements/      # Dependency configuration files
```

## FAQ

### Q: How to resolve environment variable setup failure?
A: Ensure running the program with administrator privileges or manually copy and set environment variable values.

### Q: What to do if download speed is slow?
A: Configure proxy server in settings or use manual download feature.

### Q: How to backup current configuration?
A: Program configuration files are stored in `%APPDATA%/jvman` directory, you can directly copy this directory for backup.

## Related Projects
- [SDKMAN](https://github.com/sdkman/sdkman-cli) - SDK Manager for Unix-based Systems
- [Jabba](https://github.com/shyiko/jabba) - Cross-platform Java Version Manager

## Security
Please report security vulnerabilities to [security@example.com](mailto:security@example.com).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 