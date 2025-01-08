# IDE Integration Guide

## Overview
The JDK Version Manager not only manages system JDK environments but also integrates seamlessly with mainstream IDEs, enabling synchronization between development and runtime environments. By configuring IDEs to use the symlink path, your IDE's JDK environment will automatically sync when switching system JDK versions.

## Benefits
- Maintain consistency between development and runtime environments
- Eliminate the need to configure multiple JDK versions in IDEs
- No IDE reconfiguration required when switching JDK versions
- Team members can maintain uniform JDK environment configurations

## IDE Configuration Guide

### IntelliJ IDEA
1. Open IDEA Settings (File > Settings or Ctrl+Alt+S)
2. Navigate to `Build, Execution, Deployment > Build Tools > Gradle` (or Maven settings for Maven projects)
3. In "Gradle JVM" option, select "Add JDK"
4. Click the "+" button and select "JDK"
5. In the path selection dialog, choose the JDK Version Manager's symlink path (default: `%LOCALAPPDATA%\\Programs\\jvman\\current`)
6. Click "OK" to save settings

### Visual Studio Code
1. Open VS Code Settings (File > Preferences > Settings or Ctrl+,)
2. Search for "java.jdt.ls.java.home"
3. Click "Edit in settings.json"
4. Add or modify the following configuration:
```json
{
    "java.jdt.ls.java.home": "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\jvman\\current",
    "java.configuration.runtimes": [
        {
            "name": "JavaSE-Current",
            "path": "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\jvman\\current",
            "default": true
        }
    ]
}
```

### Eclipse
1. Open Eclipse Preferences (Window > Preferences)
2. Navigate to `Java > Installed JREs`
3. Click "Add"
4. Select "Standard VM" and click "Next"
5. Choose the symlink path in "JRE home"
6. Click "Finish" to complete configuration
7. Check the newly added JRE as the default runtime

## Usage Recommendations
1. **Project Configuration**: Use relative paths to reference JDK in build configuration files (e.g., `build.gradle` or `pom.xml`):
```groovy
// Gradle example
java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(17) // Specify Java version
    }
}
```

2. **Team Collaboration**:
   - Standardize JDK Version Manager usage across the team
   - Document symlink path configuration in project documentation
   - Include IDE JDK configuration files in version control (e.g., Git)

3. **CI/CD Configuration**:
   - Use the same symlink path in CI/CD environments
   - Ensure JDK Version Manager is installed on build servers

## Common Issues
1. **Symlink Path Not Found**
   - Verify JDK Version Manager installation
   - Check if a JDK version is selected and activated

2. **IDE Cannot Recognize JDK**
   - Verify symlink functionality
   - Try restarting the IDE
   - Clear IDE cache and reconfigure

3. **IDE Not Updating After Version Switch**
   - Some IDEs may require project reload or restart
   - Check IDE auto-refresh settings

## Best Practices
1. Prioritize symlink path configuration for new projects
2. Regularly sync JDK versions among team members
3. Clearly document required JDK versions and configuration methods
4. Use project-level JDK configurations over global settings
5. Properly manage IDE configuration files with `.gitignore`

## Related Resources
- [IntelliJ IDEA JDK Configuration](https://www.jetbrains.com/help/idea/sdk.html)
- [VS Code Java Tutorial](https://code.visualstudio.com/docs/java/java-tutorial)
- [Eclipse JRE/JDK Configuration](https://help.eclipse.org/latest/topic/org.eclipse.jdt.doc.user/tasks/task-add_new_jre.htm) 