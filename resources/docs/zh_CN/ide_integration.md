# IDE 集成指南

## 概述
JDK 版本管理器不仅可以管理系统的 JDK 环境，还可以与主流 IDE 完美集成，实现开发环境与运行环境的 JDK 版本同步。通过配置 IDE 使用软链接路径，您可以在切换系统 JDK 版本时，IDE 中的 JDK 环境也会自动同步切换。

## 优势
- 开发环境与运行环境保持一致，避免环境不一致导致的问题
- 无需在 IDE 中重复配置多个 JDK 版本
- 切换 JDK 版本时无需重新配置 IDE
- 团队成员可以保持统一的 JDK 环境配置

## IDE 配置指南

### IntelliJ IDEA
1. 打开 IDEA 设置（File > Settings 或 Ctrl+Alt+S）
2. 导航到 `Build, Execution, Deployment > Build Tools > Gradle`（如果是 Maven 项目则选择相应的 Maven 设置）
3. 在 "Gradle JVM" 选项中选择 "Add JDK"
4. 点击 "+" 按钮，选择 "JDK"
5. 在路径选择对话框中，选择 JDK 版本管理器的软链接路径（默认为 `%LOCALAPPDATA%\\Programs\\jvman\\current`）
6. 点击 "OK" 保存设置

### Visual Studio Code
1. 打开 VS Code 设置（File > Preferences > Settings 或 Ctrl+,）
2. 搜索 "java.jdt.ls.java.home"
3. 点击 "Edit in settings.json"
4. 添加或修改以下配置：
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
1. 打开 Eclipse 首选项（Window > Preferences）
2. 导航到 `Java > Installed JREs`
3. 点击 "Add"
4. 选择 "Standard VM" 并点击 "Next"
5. 在 "JRE home" 中选择软链接路径
6. 点击 "Finish" 完成配置
7. 勾选新添加的 JRE 作为默认运行环境

## 使用建议
1. **项目配置**：建议在项目的构建配置文件（如 `build.gradle` 或 `pom.xml`）中使用相对路径引用 JDK：
```groovy
// Gradle 示例
java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(17) // 指定 Java 版本
    }
}
```

2. **团队协作**：
   - 在团队中统一使用 JDK 版本管理器
   - 在项目文档中说明软链接路径的配置方法
   - 使用版本控制系统（如 Git）时，将 IDE 的 JDK 配置文件加入版本控制

3. **CI/CD 配置**：
   - 在 CI/CD 环境中也可以使用相同的软链接路径
   - 确保构建服务器上也安装了 JDK 版本管理器

## 常见问题
1. **软链接路径不存在**
   - 确保已正确安装 JDK 版本管理器
   - 检查是否已选择并切换到某个 JDK 版本

2. **IDE 无法识别 JDK**
   - 检查软链接是否正常
   - 尝试重启 IDE
   - 清除 IDE 的缓存并重新配置

3. **版本切换后 IDE 不更新**
   - 某些 IDE 可能需要重新加载项目或重启
   - 检查 IDE 的自动刷新设置

## 最佳实践
1. 在开发新项目时，优先考虑使用软链接路径配置 JDK
2. 定期同步团队成员使用的 JDK 版本
3. 在项目文档中明确说明所需的 JDK 版本和配置方法
4. 使用项目级别的 JDK 配置，而不是全局配置
5. 配合 `.gitignore` 正确管理 IDE 配置文件

## 相关资源
- [IntelliJ IDEA JDK 配置文档](https://www.jetbrains.com/help/idea/sdk.html)
- [VS Code Java 教程](https://code.visualstudio.com/docs/java/java-tutorial)
- [Eclipse JRE/JDK 配置](https://help.eclipse.org/latest/topic/org.eclipse.jdt.doc.user/tasks/task-add_new_jre.htm) 