#!/usr/bin/env python
import os
import json
import subprocess
from datetime import datetime

def update_version(version_type='patch'):
    """更新版本号
    version_type: major, minor, patch
    """
    with open('config/app.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 解析当前版本号
    current = config['version'].split('.')
    major, minor, patch = map(int, current)
    
    # 更新版本号
    if version_type == 'major':
        major += 1
        minor = patch = 0
    elif version_type == 'minor':
        minor += 1
        patch = 0
    else:  # patch
        patch += 1
    
    new_version = f"{major}.{minor}.{patch}"
    config['version'] = new_version
    
    # 写入新版本号
    with open('config/app.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    return new_version

def update_changelog(version, changes):
    """更新更新日志"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 读取现有的更新日志
    with open('CHANGELOG.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 添加新的更新记录
    new_entry = f"\n## [{version}] - {today}\n\n"
    for change_type, items in changes.items():
        new_entry += f"\n### {change_type}\n"
        for item in items:
            new_entry += f"- {item}\n"
    
    # 在第一个版本记录之前插入新记录
    insert_pos = content.find('## [')
    if insert_pos == -1:
        content += new_entry
    else:
        content = content[:insert_pos] + new_entry + content[insert_pos:]
    
    # 写入更新后的内容
    with open('CHANGELOG.md', 'w', encoding='utf-8') as f:
        f.write(content)

def build_packages(version):
    """构建安装包
    Args:
        version: 版本号
    """
    # 确保 release 目录存在
    release_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'release')
    os.makedirs(release_dir, exist_ok=True)
    
    platforms = {
        'windows': {
            'suffix': 'win',
            'arch': ['x64', 'x86'],
        },
        'macos': {
            'suffix': 'mac',
            'arch': ['x64', 'arm64'],
        },
        'linux': {
            'suffix': 'linux',
            'arch': ['x64', 'arm64'],
        }
    }
    
    for platform_name, platform_info in platforms.items():
        # 构建便携版
        portable_name = f"jvman-{version}-{platform_info['suffix']}-portable"
        subprocess.run([
            'python', 'scripts/build.py',
            '--platform', platform_name,
            '--type', 'portable',
            '--output', os.path.join(release_dir, portable_name)
        ])
        
        # 构建安装版
        installer_name = f"jvman-{version}-{platform_info['suffix']}-setup"
        subprocess.run([
            'python', 'scripts/build.py',
            '--platform', platform_name,
            '--type', 'installer',
            '--output', os.path.join(release_dir, installer_name)
        ])

def main():
    # 1. 更新版本号
    version_type = input("请选择版本更新类型 (major/minor/patch): ").lower()
    new_version = update_version(version_type)
    print(f"版本号已更新至: {new_version}")
    
    # 2. 收集更新内容
    changes = {
        "Added": [],
        "Changed": [],
        "Fixed": []
    }
    
    print("\n请输入更新内容（每行一条，输入空行结束当前类型）：")
    for change_type in changes:
        print(f"\n{change_type}:")
        while True:
            item = input("> ").strip()
            if not item:
                break
            changes[change_type].append(item)
    
    # 3. 更新更新日志
    update_changelog(new_version, changes)
    print("\n更新日志已更新")
    
    # 4. 构建安装包
    print("\n开始构建安装包...")
    build_packages(new_version)
    print("构建完成")
    
    print(f"\n发布 v{new_version} 准备就绪！")
    print("请检查以下文件：")
    print("1. config/app.json")
    print("2. CHANGELOG.md")
    print("3. release/ 目录下的安装包：")
    print("   - Windows:")
    print(f"     - jvman-{new_version}-win-portable.zip")
    print(f"     - jvman-{new_version}-win-setup.exe")
    print("   - macOS:")
    print(f"     - jvman-{new_version}-mac-portable.zip")
    print(f"     - jvman-{new_version}-mac-setup.dmg")
    print("   - Linux:")
    print(f"     - jvman-{new_version}-linux-portable.tar.gz")
    print(f"     - jvman-{new_version}-linux-setup.deb")
    print(f"     - jvman-{new_version}-linux-setup.rpm")

if __name__ == '__main__':
    main() 