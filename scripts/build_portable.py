#!/usr/bin/env python3
import os
import sys
import json
import shutil
import hashlib
import subprocess
import shlex
import time
from pathlib import Path
from loguru import logger
from datetime import datetime

def get_project_root():
    """获取项目根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_version():
    """从应用程序配置文件获取版本号"""
    # 首先尝试从项目根目录的 app.json 获取
    root_dir = get_project_root()
    config_paths = [
        os.path.join(root_dir, 'app.json'),  # 项目根目录
        os.path.join(root_dir, 'config', 'app.json'),  # config目录
    ]
    
    for config_path in config_paths:
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    version = config.get('version')
                    if version:
                        return version
        except Exception as e:
            print(f"Warning: Failed to read version from {config_path}: {e}")
            continue
    
    print("Error: Could not find valid app.json with version information")
    sys.exit(1)

def get_default_paths():
    """获取默认路径配置"""
    # 使用相对于应用程序目录的路径
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return {
        'jdk_path': os.path.join(app_dir, 'jdk'),  # JDK 存储目录
        'symlink_path': os.path.join(app_dir, 'current'),  # 当前使用的 JDK 软链接
        'config_file': os.path.join(app_dir, 'config', 'jvman.json') # 配置文件路径
        #, 'log_file': os.path.join(app_dir, 'logs', 'jvman.log')  # 日志文件路径
    }

def quote_path(path, platform='windows'):
    """根据平台对路径进行引用处理"""
    if platform == 'windows':
        # Windows 上不需要引号，因为使用列表形式的参数
        return path.replace('/', '\\')
    else:
        # Linux/macOS 上使用 shlex.quote
        return shlex.quote(path)

def normalize_path(path, platform='windows'):
    """标准化路径格式"""
    if platform == 'windows':
        # Windows 上使用反斜杠
        return path.replace('/', '\\')
    return path

def check_macos_build_environment():
    """检查 macOS 构建环境"""
    # 检查 Python 版本
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    # 检查必要的命令
    required_commands = ['codesign', 'chmod']
    for cmd in required_commands:
        try:
            subprocess.run(['which', cmd], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print(f"Error: {cmd} command not found")
            sys.exit(1)
    
    # 检查 PyInstaller 版本
    try:
        import PyInstaller
        version = PyInstaller.__version__
        if not version.startswith('5.'):
            print(f"Warning: PyInstaller version {version} might not be compatible. Version 5.x is recommended.")
    except ImportError:
        print("Error: PyInstaller not found")
        sys.exit(1)

def build_portable(platform='windows', timestamp=None):
    """构建免安装版"""
    print("Building portable version...")
    
    # 检查构建环境
    if platform == 'macos':
        check_macos_build_environment()
    
    root_dir = get_project_root()
    version = get_version()
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 创建release目录
    release_dir = os.path.join(root_dir, 'release')
    os.makedirs(release_dir, exist_ok=True)
    
    # 生成输出目录名
    output_name = f"jvman_{version}_{platform}_{timestamp}"
    output_dir = os.path.join(release_dir, output_name)
    
    # 基本参数
    build_args = [
        sys.executable,
        '-m',
        'PyInstaller',
        '--clean',
        '--noconfirm',
        '--onedir',  # 生成文件夹模式
        '--noconsole',  # 不显示控制台窗口
        '--distpath', output_dir,  # 指定输出目录
        '--workpath', 'build/lib',  # 指定工作目录
        '--specpath', 'build',  # spec文件路径
        '--contents-directory', 'bin', #指定包含应用程序内容的目录
        '--uac-admin',  # 请求管理员权限
        '--name', 'jvman',
    ]
    
    # 平台特定配置
    if platform == 'windows':
        icon_file = os.path.join(root_dir, "resources", "icons", "app.ico")
    elif platform == 'macos':
        icon_file = os.path.join(root_dir, "resources", "icons", "app.icns")
        build_args.extend([
            '--osx-bundle-identifier', 'com.jvman.app',
            '--codesign-identity', '-',  # 使用临时签名
            '--icon', icon_file,  # 直接在构建参数中指定图标
        ])
        
        # 确保图标文件存在
        if not os.path.exists(icon_file):
            print(f"Error: Icon file not found at: {icon_file}")
            sys.exit(1)
        
        # 创建 Info.plist 文件
        info_plist = os.path.join(root_dir, "resources", "Info.plist")
        if not os.path.exists(info_plist):
            with open(info_plist, 'w') as f:
                f.write('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>zh_CN</string>
    <key>CFBundleDisplayName</key>
    <string>JVMan</string>
    <key>CFBundleExecutable</key>
    <string>jvman</string>
    <key>CFBundleIconFile</key>
    <string>app.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.jvman.app</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>JVMan</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    <key>LSEnvironment</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>NSAppleEventsUsageDescription</key>
    <string>JVMan needs to control system events to manage JDK versions.</string>
    <key>NSSystemAdministrationUsageDescription</key>
    <string>JVMan needs administrator privileges to manage JDK installations.</string>
    <key>CFBundleIconName</key>
    <string>app</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.developer-tools</string>
</dict>
</plist>''')
        
        # 创建 entitlements.plist 文件
        entitlements_plist = os.path.join(root_dir, "resources", "entitlements.plist")
        if not os.path.exists(entitlements_plist):
            with open(entitlements_plist, 'w') as f:
                f.write('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    <key>com.apple.security.files.downloads.read-write</key>
    <true/>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    <key>com.apple.security.temporary-exception.apple-events</key>
    <array>
        <string>com.apple.systemevents</string>
        <string>com.apple.finder</string>
    </array>
</dict>
</plist>''')
        
        # 添加 Info.plist 和 entitlements.plist 作为资源文件
        build_args.extend([
            '--add-data', f'{info_plist}:.',
            '--add-data', f'{entitlements_plist}:.'
        ])
        
    else:  # linux
        icon_file = os.path.join(root_dir, "resources", "icons", "app_256.png")
    
    # 添加图标
    if os.path.exists(icon_file):
        build_args.extend(['--icon', icon_file])
    else:
        print(f"Warning: Icon file not found at: {icon_file}")
        
    # 添加Python路径和运行时钩子
    build_args.extend([
        '--paths', os.path.join(root_dir, "src"),
        '--runtime-hook', os.path.join(root_dir, "src", "runtime", "runtime_hook.py"),
    ])
    
    # 添加必要的资源文件
    # 定义资源文件列表
    resources = [
        (os.path.join(root_dir, "resources", "icons"), "resources/icons"),
        (os.path.join(root_dir, "config", "app.json"), "config"),
        (os.path.join(root_dir, "src", "i18n"), "i18n"),
        (os.path.join(root_dir, "LICENSE"), "."),
    ]
    
    # 根据平台设置默认分隔符和格式
    if platform == 'windows':
        sep = os.environ.get('PYINSTALLER_SEP', ';')
        # Windows 格式: --add-data "SOURCE;DEST"
        for src, dst in resources:
            build_args.extend(['--add-data', f"{src}{sep}{dst}"])
    else:
        sep = os.environ.get('PYINSTALLER_SEP', ':')
        # Linux/macOS 格式: --add-data="SOURCE:DEST"
        for src, dst in resources:
            build_args.append(f'--add-data={src}{sep}{dst}')
    
    # 添加隐藏导入
    hidden_imports = [
        'loguru',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        'requests',
        'ui',
        'ui.main_window',
        'ui.tabs',
        'ui.tabs.help_tab',
        'ui.tabs.local_tab',
        'ui.tabs.settings_tab',
        'ui.tabs.download_tab',
        'ui.tabs.docs_tab',
        'utils',
        'utils.config_manager',
        'utils.platform_manager',
        'utils.system_utils',
        'utils.jdk_downloader',
        'utils.version_utils',
        'utils.theme_manager',
        'utils.i18n_manager',
        'utils.update_manager',
        'subprocess',
        'ctypes',
        'platform',
        'logging',
        'json',
        'os',
        'sys',
        'shutil',
        'datetime',
    ]

    # Windows 特定的导入
    if platform == 'windows':
        windows_imports = [
            'win32api',
            'win32con',
            'win32gui',
            'win32process',
            'win32security',
            'win32pipe',
            'win32file',
            'win32event',
            'msvcrt',
            'winreg',
        ]
        hidden_imports.extend(windows_imports)
    
    for imp in hidden_imports:
        build_args.extend(['--hidden-import', imp])
    
    # 添加主程序
    main_script = os.path.join(root_dir, "src", "main.py")
    if not os.path.exists(main_script):
        print("Error: src/main.py not found!")
        sys.exit(1)
        
    build_args.append(main_script)
    
    print("Building with arguments:", ' '.join(build_args))
    
    # 切换到项目根目录
    os.chdir(root_dir)
    
    # 执行构建
    if platform == 'windows':
        # Windows 上使用列表形式传递参数
        result = subprocess.run(build_args, capture_output=True, text=True)
    else:
        # Linux/macOS 上使用字符串形式传递参数
        result = subprocess.run(' '.join(build_args), capture_output=True, text=True, shell=True)
    
    # 打印输出
    if result.stdout:
        print("\nOutput:")
        print(result.stdout)
    
    if result.stderr:
        print("\nErrors:")
        print(result.stderr)
    
    # 检查是否成功
    if result.returncode != 0:
        print("\nBuild failed!")
        sys.exit(1)
    
    # 创建必要的目录和文件
    if platform == 'macos':
        # macOS 上 PyInstaller 会自动创建 .app 目录结构
        dist_dir = os.path.join(output_dir, 'jvman.app', 'Contents', 'MacOS')
        resources_dir = os.path.join(output_dir, 'jvman.app', 'Contents', 'Resources')
        contents_dir = os.path.join(output_dir, 'jvman.app', 'Contents')
        
        # 等待 .app 目录创建完成
        max_retries = 10
        retry_interval = 1  # 秒
        
        for i in range(max_retries):
            if os.path.exists(dist_dir):
                break
            if i < max_retries - 1:
                print(f"Waiting for app bundle to be ready... ({i + 1}/{max_retries})")
                time.sleep(retry_interval)
        else:
            print(f"Error: {dist_dir} not found!")
            print("Please make sure the app was built successfully.")
            sys.exit(1)
            
        # 创建运行时钩子文件
        runtime_hook = os.path.join(root_dir, "src", "runtime", "runtime_hook.py")
        if not os.path.exists(runtime_hook):
            os.makedirs(os.path.dirname(runtime_hook), exist_ok=True)
            with open(runtime_hook, 'w') as f:
                f.write('''import os
import sys

def init_user_dirs():
    """初始化用户目录"""
    user_home = os.path.expanduser("~")
    app_dir = os.path.join(user_home, ".jvman")
    
    # 创建必要的目录
    os.makedirs(app_dir, exist_ok=True)
    os.makedirs(os.path.join(app_dir, "jdk"), exist_ok=True)
    # os.makedirs(os.path.join(app_dir, "logs"), exist_ok=True)
    
    # 创建 current 软链接（如果不存在）
    current_link = os.path.join(app_dir, "current")
    if not os.path.exists(current_link):
        # 创建一个临时的 JDK 目录结构
        temp_jdk_dir = os.path.join(app_dir, "jdk", "temp_jdk")
        os.makedirs(temp_jdk_dir, exist_ok=True)
        os.makedirs(os.path.join(temp_jdk_dir, "bin"), exist_ok=True)
        os.makedirs(os.path.join(temp_jdk_dir, "lib"), exist_ok=True)
        
        # 创建一个空的 java 可执行文件
        java_exe = os.path.join(temp_jdk_dir, "bin", "java")
        if not os.path.exists(java_exe):
            with open(java_exe, 'w') as f:
                f.write('#!/bin/bash\\necho "Placeholder java executable"\\n')
            os.chmod(java_exe, 0o755)
        
        # 创建软链接
        try:
            os.symlink(temp_jdk_dir, current_link)
        except FileExistsError:
            pass

# 初始化用户目录
init_user_dirs()
''')
        
        os.makedirs(resources_dir, exist_ok=True)
        
        # 移动 plist 文件到正确的位置
        info_plist_src = os.path.join(dist_dir, 'Info.plist')
        info_plist_dst = os.path.join(contents_dir, 'Info.plist')
        if os.path.exists(info_plist_src):
            shutil.move(info_plist_src, info_plist_dst)
        else:
            shutil.copy2(os.path.join(root_dir, "resources", "Info.plist"), info_plist_dst)
            
        # 移动 entitlements.plist
        entitlements_src = os.path.join(dist_dir, 'entitlements.plist')
        if os.path.exists(entitlements_src):
            os.remove(entitlements_src)  # 不需要在应用程序包中保留
            
        # 复制图标文件到 Resources 目录
        icon_src = os.path.join(root_dir, "resources", "icons", "app.icns")
        if os.path.exists(icon_src):
            # 确保 Resources 目录存在
            os.makedirs(resources_dir, exist_ok=True)
            
            # 复制图标文件
            icon_dst = os.path.join(resources_dir, "app.icns")
            shutil.copy2(icon_src, icon_dst)
            
            # 设置图标文件的权限
            subprocess.run(['chmod', '644', icon_dst])
            
            # 设置图标文件的属性
            try:
                subprocess.run(['xattr', '-cr', icon_dst], check=False)
                subprocess.run(['SetFile', '-a', 'C', icon_dst], check=False)
            except Exception as e:
                print(f"Warning: Failed to set icon attributes: {e}")
            
            # 刷新图标缓存
            subprocess.run(['touch', os.path.join(output_dir, 'jvman.app')])
            
            print(f"Icon file copied to: {icon_dst}")
        else:
            print(f"Warning: Icon file not found at: {icon_src}")
        
        # 复制所有资源文件到正确的位置
        resources_src = os.path.join(dist_dir, 'resources')
        if os.path.exists(resources_src):
            for item in os.listdir(resources_src):
                src = os.path.join(resources_src, item)
                dst = os.path.join(resources_dir, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            shutil.rmtree(resources_src)
        
        # 复制额外的资源文件
        icons_src = os.path.join(root_dir, "resources", "icons")
        icons_dst = os.path.join(resources_dir, "icons")
        if os.path.exists(icons_src):
            if os.path.exists(icons_dst):
                shutil.rmtree(icons_dst)
            shutil.copytree(icons_src, icons_dst)
            
            # 设置图标目录的权限
            subprocess.run(['chmod', '-R', '644', icons_dst])
        
        # 设置正确的权限
        subprocess.run(['chmod', '-R', '755', os.path.join(output_dir, 'jvman.app')])
        
        # 重新签名应用程序
        try:
            # 首先签名所有第三方库
            frameworks_path = os.path.join(dist_dir, 'lib')
            if os.path.exists(frameworks_path):
                for root, dirs, files in os.walk(frameworks_path):
                    for file in files:
                        if file.endswith('.so') or file.endswith('.dylib'):
                            file_path = os.path.join(root, file)
                            subprocess.run(['codesign', '--force', '--sign', '-', file_path])
            
            # 然后签名主程序
            subprocess.run([
                'codesign', '--force', '--deep', '--sign', '-',
                '--entitlements', os.path.join(root_dir, "resources", "entitlements.plist"),
                '--options', 'runtime',
                os.path.join(output_dir, 'jvman.app')
            ])
            
            # 验证签名
            subprocess.run([
                'codesign', '--verify', '--deep', '--strict',
                '--verbose=2',
                os.path.join(output_dir, 'jvman.app')
            ])
        except Exception as e:
            print(f"Warning: Code signing failed: {e}")
            print("The app will still work but might show security warnings.")
        
    else:
        dist_dir = os.path.join(output_dir, 'jvman')
        
        # 创建必要的目录结构
        dirs_to_create = [
            os.path.join(dist_dir, 'jdk'),
            #os.path.join(dist_dir, 'logs'),
            os.path.join(dist_dir, 'current'),
        ]
        
        # 创建所有必要的目录
        for dir_path in dirs_to_create:
            try:
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
                os.makedirs(dir_path)
                print(f"Created directory: {dir_path}")
            except Exception as e:
                print(f"Error creating directory {dir_path}: {str(e)}")
                sys.exit(1)
    
    # 创建ZIP文件
    if platform == 'macos':
        # macOS 上不创建 zip 文件，因为我们会创建 DMG
        print("Skipping ZIP creation on macOS...")
    else:
        # 创建一个临时目录来组织文件
        zip_name = f"jvman-{version}-{platform}"
        temp_dir = os.path.join(output_dir, "temp")
        final_dir = os.path.join(temp_dir, zip_name)
        
        # 清理可能存在的旧目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(final_dir)
        
        # 复制所有文件到临时目录
        for item in os.listdir(dist_dir):
            src = os.path.join(dist_dir, item)
            dst = os.path.join(final_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        
        # 删除 bin 目录下的 resources 文件夹
        bin_resources = os.path.join(final_dir, 'bin', 'resources')
        if os.path.exists(bin_resources):
            shutil.rmtree(bin_resources)
            print(f"Removed resources folder from bin directory")
                
        # 只复制 resources/icons 到根目录
        icons_src = os.path.join(root_dir, "resources", "icons")
        resources_dst = os.path.join(final_dir, "resources")
        icons_dst = os.path.join(resources_dst, "icons")
        
        if os.path.exists(icons_src):
            if os.path.exists(resources_dst):
                shutil.rmtree(resources_dst)
            os.makedirs(resources_dst)
            shutil.copytree(icons_src, icons_dst)
            print(f"Copied icons folder to: {icons_dst}")
        else:
            print(f"Warning: Icons folder not found at: {icons_src}")
        
        # 创建ZIP文件
        zip_file = os.path.join(output_dir, f"{zip_name}.zip")
        if os.path.exists(zip_file):
            os.remove(zip_file)
        
        # 从临时目录创建zip文件
        shutil.make_archive(os.path.join(output_dir, zip_name), 'zip', temp_dir)
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
    
    # 清理构建文件
    build_dir = os.path.join(root_dir, 'build')
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    
    print("\nBuild completed successfully!")
    print(f"Output directory: {output_dir}")
    print(f"Version: {version}")
    print(f"Timestamp: {timestamp}")

def calculate_file_hash(file_path, algorithm='sha256'):
    """计算文件哈希值"""
    try:
        hash_func = getattr(hashlib, algorithm)()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        logger.error(f"计算文件哈希值失败: {str(e)}")
        return None

def generate_hash_file(file_path, hash_value):
    """生成哈希值文件"""
    try:
        hash_file = f"{file_path}.sha256"
        with open(hash_file, 'w') as f:
            f.write(hash_value)
        logger.info(f"生成哈希值文件: {hash_file}")
        return True
    except Exception as e:
        logger.error(f"生成哈希值文件失败: {str(e)}")
        return False

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python build_portable.py <platform> <timestamp>")
        sys.exit(1)
        
    platform = sys.argv[1]
    timestamp = sys.argv[2]
    
    build_portable(platform, timestamp)
    sys.exit(0) 