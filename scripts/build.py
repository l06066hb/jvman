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

def update_release_info(release_dir, version, platform, timestamp):
    """更新发布信息"""
    try:
        release_info = {
            'version': version,
            'platform': platform,
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

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='JVMan 打包工具')
    parser.add_argument('--type', choices=['portable', 'installer', 'all'], default='all',
                      help='打包类型: portable(免安装版), installer(安装包), all(两者都构建)')
    parser.add_argument('--platform', choices=['windows', 'linux', 'macos', 'current'], default='current',
                      help='目标平台: windows, linux, macos, current(当前平台)')
    
    args = parser.parse_args()
    
    # 确定目标平台
    if args.platform == 'current':
        if sys.platform.startswith('win'):
            platform = 'windows'
        elif sys.platform.startswith('linux'):
            platform = 'linux'
        elif sys.platform.startswith('darwin'):
            platform = 'macos'
        else:
            print(f"Unsupported platform: {sys.platform}")
            sys.exit(1)
    else:
        platform = args.platform
    
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
        
        # 创建发布目录
        release_dir = os.path.join(root_dir, 'release', f'jvman_{version}_{platform}_{timestamp}')
        os.makedirs(release_dir, exist_ok=True)
        
        # 构建免安装版
        if args.type in ['portable', 'all']:
            print(f"\n=== Building portable version for {platform} ===")
            build_portable(platform, timestamp)
            # 复制便携版到发布目录
            src_file = os.path.join(root_dir, 'release', f'jvman_{version}_{platform}_{timestamp}', 'jvman.zip')
            dst_file = os.path.join(release_dir, f'jvman-{version}-{platform}.zip')
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
        
        # 构建安装包
        if args.type in ['installer', 'all']:
            print(f"\n=== Building installer for {platform} ===")
            build_installer(platform, timestamp)
            # 复制安装包到发布目录
            if platform == 'windows':
                src_file = os.path.join(root_dir, 'release', f'jvman_{version}_{platform}_{timestamp}', 'JVMan_Setup.exe')
                dst_file = os.path.join(release_dir, f'jvman-{version}-{platform}-setup.exe')
            elif platform == 'macos':
                src_file = os.path.join(root_dir, 'release', f'jvman_{version}_{platform}_{timestamp}', 'JVMan_Installer.dmg')
                dst_file = os.path.join(release_dir, f'jvman-{version}-{platform}-setup.dmg')
            else:  # linux
                src_file = os.path.join(root_dir, 'release', f'jvman_{version}_{platform}_{timestamp}', 'jvman.deb')
                dst_file = os.path.join(release_dir, f'jvman-{version}-{platform}-setup.deb')
            
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
        
        # 更新发布信息（生成哈希值文件和release.json）
        update_release_info(release_dir, version, platform, timestamp)
        
        print("\nBuild process completed successfully!")
        print(f"Release directory: {release_dir}")
        
    except Exception as e:
        print(f"Error during build: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 