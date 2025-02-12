# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.9] - 2025-02-09

### Added
- Added environment variable backup management functionality
- Added backup creation, restoration, and viewing features
- Added support for automatic and manual backups
- Added backup limits and automatic cleanup mechanism
- Added backup content comparison and preview features
- Added internationalization support for common operation buttons

### Changed
- Optimized environment variable settings interface layout
- Improved backup management user interaction experience
- Enhanced backup list display method
- Improved backup content presentation format
- Optimized internationalization text organization
- Enhanced common button styles and interactions

### Fixed
- Fixed environment variable setting permission issues
- Fixed symlink creation issues on macOS
- Fixed environment variable update issues on Linux
- Fixed version switching issues on Windows
- Fixed missing internationalization text issues
- Fixed status not updating after backup restoration

### Improved
- Environment variable management stability
- Cross-platform compatibility support
- User interface interaction experience
- Error handling and notification mechanism
- Internationalization support completeness
- Configuration file management mechanism

## [1.0.8] - 2025-02-04

### Added
- Added complete support for Microsoft OpenJDK
- Added detailed descriptions of JDK version features
- Added vendor-specific features and support policy descriptions
- Added LTS/STS version identification
- Added internationalization support for version information
- Added style optimization for version details

### Changed
- Optimized JDK version information display
- Improved version feature presentation
- Enhanced vendor information organization
- Improved version information caching mechanism
- Optimized internationalization text management
- Enhanced version detection stability

### Fixed
- Fixed Microsoft OpenJDK version fetch failure
- Fixed incomplete version information display
- Fixed missing translation texts
- Fixed information update after version switch
- Fixed feature description formatting errors
- Fixed display issues during language switching

### Improved
- JDK version management stability
- Version information presentation
- Internationalization support completeness
- User interface interaction experience
- Error handling reliability
- Version detection performance

## [1.0.7] - 2025-02-02

### Fixed
- Fixed `--add-data` parameter format error on Windows platform
- Fixed missing `.app` directory issue during macOS builds
- Fixed permissions and path issues when creating DMG files on macOS
- Fixed SSH authentication issues when syncing to Gitee
- Fixed cross-platform resource file path compatibility issues
- Fixed hidden imports issue in PyInstaller packaging

### Changed
- Optimized error handling and logging in build scripts
- Improved macOS platform build process with waiting mechanism
- Enhanced GitHub Actions configuration with more secure authentication
- Optimized CI/CD workflow triggers and execution order
- Improved multi-platform build resource management
- Optimized build artifact directory structure and naming conventions
- Enhanced version release and sync automation process

### Added
- Added detailed GitHub CI/CD workflow guide documentation
- Added detailed logging and status checks during build process
- Added complete support for DMG creation on macOS
- Added automatic synchronization of GitHub Releases to Gitee
- Added build artifact hash verification mechanism
- Added build environment automatic check and dependency installation
- Added parallel execution support for cross-platform builds

### Documentation
- Added CI/CD configuration explanations and best practices
- Added detailed key configuration and security recommendations
- Added automated build and release process documentation
- Added troubleshooting guide for common issues

### Security
- Enhanced GitHub Actions permission control
- Improved key management and usage security
- Optimized security checks during build process
- Added build artifact integrity verification

## [1.0.6] - 2025-01-06

### Added
- Optimized help documentation and internationalization support
- Improved IDE configuration guide content
- Enhanced Chinese and English translation quality
- Unified resource directory structure design
- Optimized portable and installer version resource management
- Improved symlink path settings and management mechanism
- Enhanced environment variable application and sync logic

### Changed
- Optimized documentation search functionality
- Improved documentation display style
- Unified Chinese and English text style
- Improved build script resource handling logic
- Optimized icon and resource file organization
- Enhanced environment variable settings interface interaction
- Optimized symlink path storage and reading methods

### Fixed
- Fixed internationalization switching issues
- Optimized documentation content formatting
- Fixed resource duplication in portable and installer versions
- Fixed post-build directory structure issues
- Fixed resource file path reference issues
- Fixed environment variable application status sync issues
- Fixed symlink path setting permission issues

### Improved
- Build system resource management mechanism
- Installation package resource organization
- Portable version resource directory layout
- Resource file access efficiency
- Build script maintainability
- Environment variable setting reliability and stability
- Cross-platform compatibility of symlink paths


[1.0.8]: https://github.com/l06066hb/jvman/releases/tag/v1.0.8
[1.0.7]: https://github.com/l06066hb/jvman/releases/tag/v1.0.7
[1.0.6]: https://github.com/l06066hb/jvman/releases/tag/v1.0.6
