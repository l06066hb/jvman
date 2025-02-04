import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class VersionCache:
    """JDK版本信息缓存管理"""

    def __init__(self, cache_dir: str):
        self.cache_file = os.path.join(cache_dir, "jdk_versions_cache.json")
        self.cache_ttl = 24 * 60 * 60  # 24小时缓存有效期

    def get_cached_versions(self, vendor: str) -> Optional[List[str]]:
        """获取缓存的版本信息

        Args:
            vendor: JDK发行商名称

        Returns:
            版本列表，如果缓存不存在或已过期则返回None
        """
        if not os.path.exists(self.cache_file):
            return None

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
                if vendor not in cache:
                    return None

                # 检查缓存是否过期
                cache_time = cache[vendor].get("timestamp", 0)
                if time.time() - cache_time > self.cache_ttl:
                    return None

                return cache[vendor].get("versions")
        except Exception as e:
            logger.error(f"读取版本缓存失败: {str(e)}")
            return None

    def update_cache(self, vendor: str, versions: List[str]) -> bool:
        """更新版本缓存

        Args:
            vendor: JDK发行商名称
            versions: 版本列表

        Returns:
            更新是否成功
        """
        try:
            cache = {}
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)

            cache[vendor] = {
                "versions": versions,
                "timestamp": time.time(),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            # 确保缓存目录存在
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            return True

        except Exception as e:
            logger.error(f"更新版本缓存失败: {str(e)}")
            return False

    def clear_cache(self, vendor: Optional[str] = None) -> bool:
        """清除版本缓存

        Args:
            vendor: 指定发行商，如果为None则清除所有缓存

        Returns:
            清除是否成功
        """
        try:
            if not os.path.exists(self.cache_file):
                return True

            if vendor is None:
                os.remove(self.cache_file)
                return True

            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)

            if vendor in cache:
                del cache[vendor]

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            return True

        except Exception as e:
            logger.error(f"清除版本缓存失败: {str(e)}")
            return False

    def is_cache_valid(self, vendor: str) -> bool:
        """检查缓存是否有效

        Args:
            vendor: JDK发行商名称

        Returns:
            缓存是否有效
        """
        if not os.path.exists(self.cache_file):
            return False

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
                if vendor not in cache:
                    return False

                cache_time = cache[vendor].get("timestamp", 0)
                return time.time() - cache_time <= self.cache_ttl

        except Exception as e:
            logger.error(f"检查缓存有效性失败: {str(e)}")
            return False

    def get_cache_info(self, vendor: str) -> Optional[Dict]:
        """获取缓存信息

        Args:
            vendor: JDK发行商名称

        Returns:
            缓存信息字典，包含更新时间等信息
        """
        if not os.path.exists(self.cache_file):
            return None

        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
                if vendor not in cache:
                    return None

                return {
                    "update_time": cache[vendor].get("update_time"),
                    "version_count": len(cache[vendor].get("versions", [])),
                    "is_valid": self.is_cache_valid(vendor),
                }

        except Exception as e:
            logger.error(f"获取缓存信息失败: {str(e)}")
            return None
