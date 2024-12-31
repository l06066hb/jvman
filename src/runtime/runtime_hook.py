import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def runtime_hook():
    """
    运行时钩子，用于处理资源文件路径
    """
    if getattr(sys, 'frozen', False):
        # 运行在打包环境
        base_path = sys._MEIPASS
    else:
        # 运行在开发环境
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # 添加资源目录到 Python 路径
    resource_paths = [
        base_path,
        os.path.join(base_path, 'src'),
        os.path.join(base_path, 'resources'),
        os.path.join(base_path, 'resources', 'icons'),
        os.path.join(base_path, 'resources', 'tools'),
    ]

    for path in resource_paths:
        if path not in sys.path and os.path.exists(path):
            sys.path.append(path)
            logger.debug(f"Added to Python path: {path}")
        else:
            logger.warning(f"Path not found or already in sys.path: {path}")

    # 设置环境变量
    os.environ['JVMAN_ROOT'] = base_path  # 添加根目录环境变量
    os.environ['JVMAN_ICONS'] = os.path.join(base_path, 'resources', 'icons')  # 添加图标目录环境变量
    os.environ['JVMAN_TOOLS'] = os.path.join(base_path, 'resources', 'tools')  # 添加工具目录环境变量

    logger.debug(f"Environment variables set: JVMAN_ROOT={os.environ['JVMAN_ROOT']}")
    logger.debug(f"Environment variables set: JVMAN_ICONS={os.environ['JVMAN_ICONS']}")
    logger.debug(f"Environment variables set: JVMAN_TOOLS={os.environ['JVMAN_TOOLS']}")

    return base_path 