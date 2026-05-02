#!/usr/bin/env python3
import sys
import argparse
import os
import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from build_portable import build_portable
from build_installer import build_installer
from loguru import logger

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

def update_release_info(release_dir, version, platform, timestamp, arch=None):
    """更新发布信息"""
    try:
        release_info = {
            'version': version,
            'platform': platform,
            'arch': arch,
            'timestamp': timestamp,
            'files': []
        }

        # 收集发布文件信息
        for file in os.listdir(release_dir):
            file_path = os.path.join(release_dir, file)
            if os.path.isfile(file_path) and not file.endswith('.sha256'):
                # 计算文件哈希值
                hash_value = calculate_file_hash(file_path)
                if hash_value:
                    # 生成哈希值文件
                    generate_hash_file(file_path, hash_value)
                    # 添加文件信息
                    file_info = {
                        'name': file,
                        'platform': platform,
                        'arch': arch,
                        'size': os.path.getsize(file_path),
                        'sha256': hash_value
                    }
                    release_info['files'].append(file_info)

        # 保存发布信息
        release_file = os.path.join(release_dir, 'release.json')
        with open(release_file, 'w', encoding='utf-8') as f:
            json.dump(release_info, f, indent=4, ensure_ascii=False)
        logger.info(f"生成发布信息: {release_file}")

        return True
    except Exception as e:
        logger.error(f"更新发布信息失败: {str(e)}")
        return False

def detect_current_platform():
    """检测当前平台"""
    if sys.platform.startswith('win'):
        return 'windows'
    if sys.platform.startswith('linux'):
        return 'linux'
    if sys.platform.startswith('darwin'):
        return 'macos'
    return None


def detect_current_arch():
    """检测当前机器架构，归一化为 x64 / arm64"""
    import platform as _plat
    machine = (_plat.machine() or '').lower()
    if machine in ('x86_64', 'amd64', 'x64'):
        return 'x64'
    if machine in ('arm64', 'aarch64'):
        return 'arm64'
    # 其他架构原样返回，便于排查
    return machine or 'unknown'


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='JVMan 打包工具')
    parser.add_argument('--type', choices=['portable', 'installer', 'all'], default='all',
                      help='打包类型: portable(免安装版), installer(安装包), all(两者都构建)')
    parser.add_argument('--platform', choices=['windows', 'linux', 'macos', 'current'], default='current',
                      help='目标平台: windows, linux, macos, current(当前平台)')
    parser.add_argument('--arch', choices=['x64', 'arm64', 'current'], default='current',
                      help='目标架构: x64, arm64, current(当前架构)')
    
    args = parser.parse_args()
    
    # 确定目标平台
    if args.platform == 'current':
        platform = detect_current_platform()
        if platform is None:
            print(f"Unsupported platform: {sys.platform}")
            sys.exit(1)
    else:
        platform = args.platform

    # 确定目标架构
    arch = detect_current_arch() if args.arch == 'current' else args.arch
    
    # 生成时间戳，确保便携版和安装版使用相同的时间戳
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    try:
        # 获取项目根目录
        root_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(root_dir)  # 上一级目录
        
        # 获取版本号
        config_file = os.path.join(root_dir, "config", "app.json")
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            version = config.get('version', '1.0.0')

        # 构建目录（build_portable / build_installer 使用的临时输出目录）
        build_output_dir = os.path.join(root_dir, 'release', f'jvman_{version}_{platform}_{timestamp}')

        # 最终发布目录（按平台+架构区分，方便 CI 上传）
        release_dir = os.path.join(root_dir, 'release', f'jvman_{version}_{platform}_{arch}_{timestamp}')
        os.makedirs(release_dir, exist_ok=True)

        print(f"Target platform: {platform}")
        print(f"Target arch: {arch}")
        print(f"Version: {version}")
        
        # 构建免安装版
        if args.type in ['portable', 'all']:
            print(f"\n=== Building portable version for {platform}-{arch} ===")
            build_portable(platform, timestamp, arch=arch)
            # macOS 平台 build_portable 不产出 zip，DMG 在安装包步骤中生成
            if platform != 'macos':
                # 复制便携版到发布目录（build_portable 生成名: jvman-{version}-{platform}-{arch}.zip）
                portable_name = f'jvman-{version}-{platform}-{arch}.zip'
                src_file = os.path.join(build_output_dir, portable_name)
                dst_file = os.path.join(release_dir, portable_name)
                if os.path.exists(src_file):
                    shutil.copy2(src_file, dst_file)
                else:
                    print(f"Warning: portable artifact not found: {src_file}")
        
        # 构建安装包
        if args.type in ['installer', 'all']:
            print(f"\n=== Building installer for {platform}-{arch} ===")
            build_installer(platform, timestamp, arch=arch)
            # 根据平台定位源文件
            if platform == 'windows':
                installer_name = f'jvman-{version}-{platform}-{arch}-setup.exe'
                src_file = os.path.join(build_output_dir, installer_name)
                dst_file = os.path.join(release_dir, installer_name)
            elif platform == 'macos':
                installer_name = f'jvman-{version}-{platform}-{arch}-setup.dmg'
                src_file = os.path.join(build_output_dir, installer_name)
                dst_file = os.path.join(release_dir, installer_name)
            else:  # linux
                installer_name = f'jvman-{version}-{platform}-{arch}-setup.deb'
                src_file = os.path.join(build_output_dir, installer_name)
                dst_file = os.path.join(release_dir, installer_name)

            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
            else:
                print(f"Warning: installer artifact not found: {src_file}")
        
        # 更新发布信息（生成哈希值文件和release.json）
        update_release_info(release_dir, version, platform, timestamp, arch=arch)
        
        print("\nBuild process completed successfully!")
        print(f"Release directory: {release_dir}")
        
    except Exception as e:
        print(f"Error during build: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 