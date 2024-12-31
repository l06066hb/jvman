#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path
from datetime import datetime
from build_portable import build_portable
from build_installer import build_installer

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
        # 构建免安装版
        if args.type in ['portable', 'all']:
            print(f"\n=== Building portable version for {platform} ===")
            build_portable(platform, timestamp)
        
        # 构建安装包
        if args.type in ['installer', 'all']:
            print(f"\n=== Building installer for {platform} ===")
            build_installer(platform, timestamp)
        
        print("\nBuild process completed successfully!")
        
    except Exception as e:
        print(f"Error during build: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 