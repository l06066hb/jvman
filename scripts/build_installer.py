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
    installer_marker_path = os.path.join(root_dir, "scripts", ".installer").replace("\\", "/")
    
    # 创建空的 .installer 文件
    with open(installer_marker_path, 'w') as f:
        f.write(f"Created by installer build process - {datetime.now().isoformat()}")

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
Source: "{dist_dir}/*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 添加安装标记文件
Source: "{installer_marker_path}"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Parameters: "--admin"
Name: "{{commondesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon; Parameters: "--admin"

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent runascurrentuser
""")
    
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
    
    # 检查 app 是否存在
    app_path = os.path.join(output_dir, "jvman.app")
    if not os.path.exists(app_path):
        print(f"Error: {app_path} not found!")
        print("Please make sure the app was built successfully.")
        sys.exit(1)
    
    # 创建 .installer 文件
    installer_marker = os.path.join(app_path, 'Contents', 'MacOS', '.installer')
    with open(installer_marker, 'w') as f:
        f.write(f"Created by installer build process - {datetime.now().isoformat()}")
    
    # 创建临时目录用于构建 DMG
    dmg_temp = os.path.join(output_dir, "dmg_temp")
    if os.path.exists(dmg_temp):
        shutil.rmtree(dmg_temp)
    os.makedirs(dmg_temp)
    
    # 复制 app 到临时目录并设置正确的权限
    temp_app = os.path.join(dmg_temp, "JVMan.app")
    if os.path.exists(temp_app):
        shutil.rmtree(temp_app)
    
    # 使用 ditto 命令复制，这样可以保留所有元数据和权限
    subprocess.run(['ditto', app_path, temp_app], check=True)
    
    # 创建 Applications 链接
    subprocess.run(['ln', '-s', '/Applications', os.path.join(dmg_temp, 'Applications')])
    
    # 设置 DMG 文件路径
    dmg_path = os.path.join(output_dir, "JVMan_Installer.dmg")
    temp_dmg = os.path.join(output_dir, "JVMan_temp.dmg")
    if os.path.exists(dmg_path):
        os.remove(dmg_path)
    if os.path.exists(temp_dmg):
        os.remove(temp_dmg)
    
    try:
        # 创建临时 DMG
        subprocess.run([
            'hdiutil', 'create',
            '-srcfolder', dmg_temp,
            '-volname', 'JVMan Installer',
            '-fs', 'HFS+',
            '-fsargs', '-c c=64,a=16,e=16',
            '-format', 'UDRW',
            temp_dmg
        ], check=True)
        
        # 挂载 DMG
        mount_output = subprocess.check_output([
            'hdiutil', 'attach',
            temp_dmg,
            '-readwrite',
            '-noverify',
            '-noautoopen'
        ], text=True)
        
        # 获取挂载点
        mount_point = None
        device_path = None
        for line in mount_output.split('\n'):
            if 'JVMan Installer' in line:
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    device_path = parts[0].strip()
                    mount_point = parts[2].strip()
                    break
        
        if mount_point and device_path:
            try:
                # 设置卷图标
                icon_path = os.path.join(root_dir, "resources", "icons", "app.icns")
                if os.path.exists(icon_path):
                    icon_base = os.path.join(mount_point, '.VolumeIcon.icns')
                    shutil.copy2(icon_path, icon_base)
                    subprocess.run(['SetFile', '-a', 'C', mount_point], check=False)
                
                # 设置正确的权限
                subprocess.run(['chmod', '-R', '755', os.path.join(mount_point, 'JVMan.app')])
                
                # 等待文件系统同步
                time.sleep(2)
            finally:
                # 卸载 DMG
                for _ in range(3):  # 重试3次
                    try:
                        subprocess.run(['hdiutil', 'detach', device_path, '-force'], check=True)
                        break
                    except subprocess.CalledProcessError:
                        time.sleep(2)
        
        # 转换为压缩格式
        subprocess.run([
                'hdiutil', 'convert',
                temp_dmg,
                '-format', 'UDZO',
                '-imagekey', 'zlib-level=9',
                '-o', dmg_path
        ], check=True)
    
        # 签名 DMG
        try:
            subprocess.run([
                'codesign',
                '--force',
                '--sign', '-',
                '--timestamp',
                '--deep',
                '--options', 'runtime',
                '--entitlements', os.path.join(root_dir, "resources", "entitlements.plist"),
                dmg_path
            ], check=True)
        except Exception as e:
            print(f"Warning: DMG signing failed: {e}")
        
        print(f"\nInstaller build completed!")
        print(f"Output directory: {output_dir}")
        print(f"DMG file: {dmg_path}")
        print(f"Version: {version}")
        print(f"Timestamp: {timestamp}")
        
    except subprocess.CalledProcessError as e:
        print(f"\nError creating DMG: {e}")
        if e.stdout:
            print("\nCommand stdout:")
            print(e.stdout)
        if e.stderr:
            print("\nCommand stderr:")
            print(e.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
    finally:
        # 清理临时文件
        if os.path.exists(dmg_temp):
                shutil.rmtree(dmg_temp)
        if os.path.exists(temp_dmg):
            os.remove(temp_dmg)

def build_linux_installer(platform='linux', timestamp=None):
    """构建 Linux 安装包"""
    print("Building Linux installer...")
    root_dir = get_project_root()
    version = get_version()
    
    # 获取构建目录
    release_dir = os.path.join(root_dir, 'release')
    output_name = f"jvman_{version}_{platform}_{timestamp}"
    output_dir = os.path.join(release_dir, output_name)
    dist_dir = os.path.join(output_dir, 'jvman')
    
    # 创建 DEB 包目录结构
    deb_root = os.path.join(output_dir, 'deb_root')
    if os.path.exists(deb_root):
        shutil.rmtree(deb_root)
    
    # 创建必要的目录
    deb_dirs = {
        'DEBIAN': os.path.join(deb_root, 'DEBIAN'),
        'usr_bin': os.path.join(deb_root, 'usr', 'bin'),
        'usr_share_jvman': os.path.join(deb_root, 'usr', 'share', 'jvman'),
        'usr_share_applications': os.path.join(deb_root, 'usr', 'share', 'applications'),
        'usr_share_icons': os.path.join(deb_root, 'usr', 'share', 'icons', 'hicolor', '256x256', 'apps'),
    }
    
    for dir_path in deb_dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    # 复制应用程序文件
    shutil.copytree(dist_dir, deb_dirs['usr_share_jvman'], dirs_exist_ok=True)
    
    # 创建 .installer 文件
    installer_marker = os.path.join(deb_dirs['usr_share_jvman'], '.installer')
    with open(installer_marker, 'w') as f:
        f.write(f"Created by installer build process - {datetime.now().isoformat()}")
    
    # 创建启动脚本
    launcher_script = os.path.join(deb_dirs['usr_bin'], 'jvman')
    with open(launcher_script, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write('exec /usr/share/jvman/jvman "$@"\n')
    os.chmod(launcher_script, 0o755)
    
    # 复制图标
    icon_src = os.path.join(root_dir, 'resources', 'icons', 'app_256.png')
    icon_dst = os.path.join(deb_dirs['usr_share_icons'], 'jvman.png')
    shutil.copy2(icon_src, icon_dst)
    
    # 创建桌面文件
    desktop_file = os.path.join(deb_dirs['usr_share_applications'], 'jvman.desktop')
    with open(desktop_file, 'w') as f:
        f.write("""[Desktop Entry]
Name=JDK Version Manager
Comment=Manage multiple JDK versions
Exec=/usr/share/jvman/jvman
Icon=jvman
Terminal=false
Type=Application
Categories=Development;Java;
Keywords=Java;JDK;Development;
""")
    
    # 创建 control 文件
    control_file = os.path.join(deb_dirs['DEBIAN'], 'control')
    with open(control_file, 'w') as f:
        f.write(f"""Package: jvman
Version: {version}
Architecture: amd64
Maintainer: l06066hb <l06066hb@gmail.com>
Description: JDK Version Manager
 A tool for managing multiple JDK versions.
 Supports downloading, installing, and switching between different JDK versions.
Section: devel
Priority: optional
Homepage: https://github.com/l06066hb/jvman
Depends: python3 (>= 3.8)
""")
    
    # 创建 postinst 脚本
    postinst_file = os.path.join(deb_dirs['DEBIAN'], 'postinst')
    with open(postinst_file, 'w') as f:
        f.write("""#!/bin/bash
set -e

# 设置权限
chmod 755 /usr/share/jvman/jvman
chmod 755 /usr/bin/jvman

# 更新桌面数据库
if [ -x "$(command -v update-desktop-database)" ]; then
    update-desktop-database -q
fi

# 更新图标缓存
if [ -x "$(command -v gtk-update-icon-cache)" ]; then
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor
fi

exit 0
""")
    os.chmod(postinst_file, 0o755)
    
    # 创建 prerm 脚本
    prerm_file = os.path.join(deb_dirs['DEBIAN'], 'prerm')
    with open(prerm_file, 'w') as f:
        f.write("""#!/bin/bash
set -e

# 清理可能存在的临时文件
rm -rf /usr/share/jvman/temp/* || true
rm -rf /usr/share/jvman/logs/* || true

exit 0
""")
    os.chmod(prerm_file, 0o755)
    
    # 构建 DEB 包
    deb_name = f"jvman-{version}-linux-setup.deb"
    deb_file = os.path.join(output_dir, deb_name)
    
    try:
        subprocess.run(['fakeroot', 'dpkg-deb', '--build', deb_root, deb_file], check=True)
        print(f"Successfully created DEB package: {deb_file}")
        
        # 计算并生成哈希值
        hash_value = calculate_file_hash(deb_file)
        if hash_value:
            generate_hash_file(deb_file, hash_value)
    
    # 清理临时文件
        shutil.rmtree(deb_root)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to create DEB package: {str(e)}")
        return False

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