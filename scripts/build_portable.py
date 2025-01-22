#!/usr/bin/env python3
import os
import sys
import json
import shutil
import subprocess
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
        'config_file': os.path.join(app_dir, 'config', 'jvman.json'),  # 配置文件路径
        'log_file': os.path.join(app_dir, 'logs', 'jvman.log')  # 日志文件路径
    }

def build_portable(platform='windows', timestamp=None):
    """构建免安装版"""
    print("Building portable version...")
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
        '--name=jvman',
        '--noconfirm',
        '--onedir',  # 生成文件夹模式
        '--noconsole',  # 不显示控制台窗口
        f'--distpath={output_dir}',  # 指定输出目录
        '--workpath=build/lib',  # 指定工作目录
        '--specpath=build',  # spec文件路径
        '--contents-directory=bin', #指定包含应用程序内容的目录
        '--uac-admin',  # 请求管理员权限
    ]
    
    # 平台特定配置
    if platform == 'windows':
        icon_file = os.path.join(root_dir, "resources", "icons", "app.ico")
    elif platform == 'macos':
        icon_file = os.path.join(root_dir, "resources", "icons", "app.icns")
        build_args.append("--osx-bundle-identifier=com.jvman.app")
    else:  # linux
        icon_file = os.path.join(root_dir, "resources", "icons", "app_256.png")
    
    # 添加图标
    if os.path.exists(icon_file):
        build_args.append(f'--icon={icon_file}')
    else:
        print(f"Warning: Icon file not found at: {icon_file}")
    
    # 添加Python路径和运行时钩子
    build_args.extend([
        f'--paths={os.path.join(root_dir, "src")}',
        f'--runtime-hook={os.path.join(root_dir, "src", "runtime", "runtime_hook.py")}',
    ])
    
    # 添加必要的资源文件
    build_args.extend([
        f'--add-data={os.path.join(root_dir, "resources", "icons")};resources/icons',
        f'--add-data={os.path.join(root_dir, "config", "app.json")};config',
        f'--add-data={os.path.join(root_dir, "src", "i18n")};i18n',
        f'--add-data={os.path.join(root_dir, "LICENSE")};.',
    ])
    
    # 添加隐藏导入
    hidden_imports = [
        'loguru',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        'requests',
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
        'loguru.handlers',
        'loguru._logger',
        'loguru._file_sink',
        'loguru._recattrs',
        'loguru._datetime',
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
    
    for imp in hidden_imports:
        build_args.append(f'--hidden-import={imp}')
    
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
    result = subprocess.run(build_args, capture_output=True, text=True)
    
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
    dist_dir = os.path.join(output_dir, 'jvman')
    
    # 创建必要的目录结构
    dirs_to_create = [
        os.path.join(dist_dir, 'jdk'),
        os.path.join(dist_dir, 'logs'),
        os.path.join(dist_dir, 'current'),  # 添加 current 目录
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
    
    # 清理构建文件
    build_dir = os.path.join(root_dir, 'build')
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    
    print("\nBuild completed successfully!")
    print(f"Output directory: {output_dir}")
    print(f"Version: {version}")
    print(f"Timestamp: {timestamp}")

if __name__ == '__main__':
    build_portable() 