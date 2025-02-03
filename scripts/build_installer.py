#!/usr/bin/env python3
import os
import sys
import json
import shutil
import hashlib
import subprocess
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

def find_iscc():
    """查找 Inno Setup 编译器"""
    # 首先检查 PATH
    try:
        subprocess.run(["iscc"], capture_output=True)
        return "iscc"
    except FileNotFoundError:
        pass
    
    # 检查默认安装路径
    possible_paths = [
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Inno Setup 5", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Inno Setup 5", "ISCC.exe"),
    ]
    
    for path in possible_paths:
        if os.path.isfile(path):
            return path
            
    print("Error: Inno Setup Compiler (iscc) not found!")
    print("Please install Inno Setup from: https://jrsoftware.org/isdl.php")
    print("Or add Inno Setup installation directory to PATH")
    sys.exit(1)

def build_windows_installer(platform='windows', timestamp=None):
    """构建Windows安装包"""
    print("Building Windows installer...")
    root_dir = get_project_root()
    version = get_version()
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 首先构建便携版
    from build_portable import build_portable
    build_portable(platform=platform, timestamp=timestamp)
    
    # 创建release目录
    release_dir = os.path.join(root_dir, 'release')
    os.makedirs(release_dir, exist_ok=True)
    
    # 生成输出目录名
    output_name = f"jvman_{version}_{platform}_{timestamp}"
    output_dir = os.path.join(release_dir, output_name)
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取 Inno Setup 编译器路径
    iscc_path = find_iscc()
    
    # 检查中文语言文件是否存在
    inno_dir = os.path.dirname(iscc_path)
    chinese_isl = os.path.join(inno_dir, "Languages", "ChineseSimplified.isl")
    has_chinese = os.path.isfile(chinese_isl)
    
    # 生成安装脚本
    installer_script = os.path.join(root_dir, "installer.iss")
    
    # 准备路径，使用正斜杠
    license_file = os.path.join(root_dir, "LICENSE").replace("\\", "/")
    icon_file = os.path.join(root_dir, "resources", "icons", "app.ico").replace("\\", "/")
    # 使用新构建的便携版目录
    dist_dir = os.path.join(output_dir, "jvman").replace("\\", "/")
    
    # 确保资源目录存在
    resources_dir = os.path.join(dist_dir, "resources")
    icons_dir = os.path.join(resources_dir, "icons")
    os.makedirs(icons_dir, exist_ok=True)
    
    # 复制所有图标文件
    src_icons_dir = os.path.join(root_dir, "resources", "icons")
    if os.path.exists(src_icons_dir):
        for icon_name in os.listdir(src_icons_dir):
            src_icon = os.path.join(src_icons_dir, icon_name)
            dst_icon = os.path.join(icons_dir, icon_name)
            if os.path.isfile(src_icon):
                shutil.copy2(src_icon, dst_icon)
    
    # 删除bin目录下的resources目录，避免重复
    bin_resources = os.path.join(dist_dir, "bin", "resources")
    if os.path.exists(bin_resources):
        shutil.rmtree(bin_resources)
        print(f"Removed duplicate resources directory: {bin_resources}")
    
    with open(installer_script, "w", encoding="utf-8") as f:
        f.write(f"""#define MyAppName "JVMan"
#define MyAppVersion "{version}"
#define MyAppPublisher "Your Company"
#define MyAppURL "https://gitee.com/jvman"
#define MyAppExeName "jvman.exe"

[Setup]
AppId={{{{8BE6E44F-3F36-4F3A-A3F9-C171A21B5F1A}}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
AppPublisherURL={{#MyAppURL}}
AppSupportURL={{#MyAppURL}}
AppUpdatesURL={{#MyAppURL}}
DefaultDirName={{autopf}}/{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
AllowNoIcons=yes
LicenseFile="{license_file}"
OutputDir="{output_dir}"
OutputBaseFilename=JVMan_Setup
SetupIconFile="{icon_file}"
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; 添加管理员权限要求
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
{'''Name: "chinesesimplified"; MessagesFile: "compiler:Languages/ChineseSimplified.isl"''' if has_chinese else ''}

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
Source: "{dist_dir}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Parameters: "--admin"
Name: "{{commondesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon; Parameters: "--admin"

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent runascurrentuser
""")
    
    if not has_chinese:
        print("Warning: Chinese language file not found. The installer will be English only.")
        print("To add Chinese support, please install Chinese language pack for Inno Setup.")
    
    # 编译安装包
    subprocess.run([iscc_path, installer_script], check=True)
    print(f"\nInstaller build completed!")
    print(f"Output directory: {output_dir}")
    print(f"Version: {version}")
    print(f"Timestamp: {timestamp}")

def build_macos_installer(platform='macos', timestamp=None):
    """构建macOS安装包"""
    print("Building macOS installer...")
    root_dir = get_project_root()
    version = get_version()
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 首先构建便携版
    from build_portable import build_portable
    build_portable(platform=platform, timestamp=timestamp)
    
    # 创建release目录
    release_dir = os.path.join(root_dir, 'release')
    os.makedirs(release_dir, exist_ok=True)
    
    # 生成输出目录名
    output_name = f"jvman_{version}_{platform}_{timestamp}"
    output_dir = os.path.join(release_dir, output_name)
    os.makedirs(output_dir, exist_ok=True)
    
    # 使用 create-dmg 工具创建 DMG 文件
    try:
        subprocess.run(["create-dmg", "--help"], capture_output=True)
    except FileNotFoundError:
        print("\nError: create-dmg not found!")
        print("\nTo install create-dmg, you can use one of the following methods:")
        print("1. Using Homebrew (recommended):")
        print("   brew install create-dmg")
        print("\n2. Using MacPorts:")
        print("   sudo port install create-dmg")
        print("\n3. Manual installation:")
        print("   git clone https://github.com/create-dmg/create-dmg.git")
        print("   cd create-dmg")
        print("   chmod +x create-dmg")
        print("   sudo make install")
        print("\nAfter installation, please try building again.")
        sys.exit(1)
    
    # 检查 app 是否存在，并等待一段时间以确保构建完成
    app_path = os.path.join(output_dir, "jvman.app")
    max_retries = 10
    retry_interval = 1  # 秒
    
    for i in range(max_retries):
        if os.path.exists(app_path) and os.path.exists(os.path.join(app_path, "Contents", "MacOS", "jvman")):
            break
        if i < max_retries - 1:
            print(f"Waiting for app bundle to be ready... ({i + 1}/{max_retries})")
            time.sleep(retry_interval)
    else:
        print(f"Error: {app_path} not found or incomplete!")
        print("Please make sure the app was built successfully.")
        sys.exit(1)
    
    # 创建临时目录用于构建 DMG
    dmg_temp = os.path.join(output_dir, "dmg_temp")
    os.makedirs(dmg_temp, exist_ok=True)
    
    # 复制 app 到临时目录
    temp_app = os.path.join(dmg_temp, "JVMan.app")
    if os.path.exists(temp_app):
        shutil.rmtree(temp_app)
    shutil.copytree(app_path, temp_app)
    
    # 设置 DMG 文件路径
    dmg_path = os.path.join(output_dir, "JVMan_Installer.dmg")
    if os.path.exists(dmg_path):
        os.remove(dmg_path)
    
    # 构建 DMG
    try:
        subprocess.run([
            "create-dmg",
            "--volname", "JVMan Installer",
            "--volicon", os.path.join(root_dir, "resources", "icons", "app.icns"),
            "--window-pos", "200", "120",
            "--window-size", "800", "400",
            "--icon-size", "100",
            "--icon", "JVMan.app", "200", "190",
            "--hide-extension", "JVMan.app",
            "--app-drop-link", "600", "185",
            "--no-internet-enable",
            dmg_path,
            dmg_temp
        ], check=True)
        
        print(f"\nInstaller build completed!")
        print(f"Output directory: {output_dir}")
        print(f"DMG file: {dmg_path}")
        print(f"Version: {version}")
        print(f"Timestamp: {timestamp}")
        
    except subprocess.CalledProcessError as e:
        print(f"\nError creating DMG: {e}")
        print("Command output:")
        if e.stdout:
            print(e.stdout.decode())
        if e.stderr:
            print(e.stderr.decode())
        sys.exit(1)
    finally:
        # 清理临时目录
        if os.path.exists(dmg_temp):
            shutil.rmtree(dmg_temp)

def build_linux_installer(platform='linux', timestamp=None):
    """构建Linux安装包"""
    print("Building Linux installer...")
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
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建 .deb 包
    try:
        subprocess.run(["dpkg-deb", "--help"], capture_output=True)
    except FileNotFoundError:
        print("Error: dpkg-deb not found!")
        print("Please install dpkg: sudo apt-get install dpkg")
        sys.exit(1)
    
    # 创建必要的目录结构
    deb_root = os.path.join(output_dir, "deb")
    os.makedirs(os.path.join(deb_root, "DEBIAN"), exist_ok=True)
    os.makedirs(os.path.join(deb_root, "usr", "local", "bin"), exist_ok=True)
    os.makedirs(os.path.join(deb_root, "usr", "share", "applications"), exist_ok=True)
    os.makedirs(os.path.join(deb_root, "usr", "share", "icons", "hicolor", "256x256", "apps"), exist_ok=True)
    
    # 创建控制文件
    with open(os.path.join(deb_root, "DEBIAN", "control"), "w") as f:
        f.write(f"""Package: jvman
Version: {version}
Section: utils
Priority: optional
Architecture: amd64
Depends: python3
Maintainer: Your Name <your.email@example.com>
Description: JDK Version Manager
 A tool to manage multiple JDK versions on your system.
""")
    
    # 复制文件
    dist_dir = os.path.join(root_dir, "dist", "jvman")
    target_dir = os.path.join(deb_root, "usr", "local", "bin", "jvman")
    if os.path.exists(dist_dir):
        shutil.copytree(dist_dir, target_dir, dirs_exist_ok=True)
        
        # 确保目标目录中存在必要的子目录（确保为空）
        dirs_to_create = [
            os.path.join(target_dir, 'jdk'),
            os.path.join(target_dir, 'logs'),
            os.path.join(target_dir, 'current'),  # 添加 current 目录
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
    
    # 复制图标
    icon_src = os.path.join(root_dir, "resources", "icons", "app.png")
    icon_dst = os.path.join(deb_root, "usr", "share", "icons", "hicolor", "256x256", "apps", "jvman.png")
    if os.path.exists(icon_src):
        shutil.copy2(icon_src, icon_dst)
    
    # 创建桌面文件
    with open(os.path.join(deb_root, "usr", "share", "applications", "jvman.desktop"), "w") as f:
        f.write("""[Desktop Entry]
Name=JVMan
Comment=JDK Version Manager
Exec=/usr/local/bin/jvman/jvman
Icon=jvman
Terminal=false
Type=Application
Categories=Development;Utility;
""")
    
    # 构建 .deb 包
    deb_file = os.path.join(output_dir, "jvman.deb")
    subprocess.run(["dpkg-deb", "--build", deb_root, deb_file], check=True)
    
    # 清理临时文件
    if os.path.exists(deb_root):
        shutil.rmtree(deb_root)
    
    print(f"\nInstaller build completed!")
    print(f"Output directory: {output_dir}")
    print(f"Version: {version}")
    print(f"Timestamp: {timestamp}")

def build_installer(platform='windows', timestamp=None):
    """构建安装包"""
    if platform == 'windows':
        build_windows_installer(platform, timestamp)
    elif platform == 'macos':
        build_macos_installer(platform, timestamp)
    elif platform == 'linux':
        build_linux_installer(platform, timestamp)
    else:
        print(f"Error: Unsupported platform: {platform}")
        sys.exit(1)

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
    # 构建当前平台的安装包
    if len(sys.argv) != 3:
        print("Usage: python build_installer.py <platform> <timestamp>")
        sys.exit(1)
        
    platform = sys.argv[1]
    timestamp = sys.argv[2]
    
    build_installer(platform, timestamp)
    sys.exit(0) 