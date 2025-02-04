import os
import json
import requests
from loguru import logger
from typing import Dict, List, Optional


class DownloadMirrors:
    """JDK 下载镜像源管理"""

    def __init__(self, config_dir: str):
        self.mirrors_file = os.path.join(config_dir, "download_mirrors.json")
        self.mirrors = self._load_default_mirrors()
        self._load_custom_mirrors()

    def _load_default_mirrors(self) -> Dict:
        """加载默认镜像源配置"""
        return {
            "adoptium": {
                "official": "https://api.adoptium.net/v3/assets/latest/",
                "mirrors": {
                    "tencent": "https://mirrors.cloud.tencent.com/Adoptium/",
                    "huawei": "https://repo.huaweicloud.com/adoptium/",
                    "aliyun": "https://mirrors.aliyun.com/adoptium/",
                    "tsinghua": "https://mirrors.tuna.tsinghua.edu.cn/Adoptium/",
                },
            },
            "microsoft": {
                "official": "https://aka.ms/download-jdk/",
                "mirrors": {"azure_cn": "https://mirror.azure.cn/microsoft/OpenJDK/"},
            },
            "corretto": {
                "official": "https://corretto.aws/downloads/latest/",
                "mirrors": {
                    "tencent": "https://mirrors.cloud.tencent.com/corretto/",
                    "huawei": "https://repo.huaweicloud.com/amazonjdk/",
                    "aliyun": "https://mirrors.aliyun.com/amazonjdk/",
                },
            },
            "zulu": {
                "official": "https://api.azul.com/zulu/download/community/v1.0/",
                "mirrors": {
                    "tencent": "https://mirrors.cloud.tencent.com/zulu/",
                    "huawei": "https://repo.huaweicloud.com/zulu/",
                    "aliyun": "https://mirrors.aliyun.com/zulu/",
                },
            },
            "openjdk": {
                "official": "https://jdk.java.net/",
                "mirrors": {
                    "tencent": "https://mirrors.cloud.tencent.com/openjdk/",
                    "huawei": "https://repo.huaweicloud.com/openjdk/",
                    "aliyun": "https://mirrors.aliyun.com/openjdk/",
                    "tsinghua": "https://mirrors.tuna.tsinghua.edu.cn/openjdk/",
                },
            },
        }

    def _load_custom_mirrors(self):
        """加载用户自定义镜像源配置"""
        try:
            if os.path.exists(self.mirrors_file):
                with open(self.mirrors_file, "r", encoding="utf-8") as f:
                    custom_mirrors = json.load(f)
                    # 合并自定义镜像源
                    for vendor, mirrors in custom_mirrors.items():
                        if vendor in self.mirrors:
                            self.mirrors[vendor]["mirrors"].update(
                                mirrors.get("mirrors", {})
                            )
                        else:
                            self.mirrors[vendor] = mirrors
        except Exception as e:
            logger.error(f"加载自定义镜像源配置失败: {str(e)}")

    def save_custom_mirrors(self):
        """保存自定义镜像源配置"""
        try:
            os.makedirs(os.path.dirname(self.mirrors_file), exist_ok=True)
            with open(self.mirrors_file, "w", encoding="utf-8") as f:
                json.dump(self.mirrors, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存自定义镜像源配置失败: {str(e)}")
            return False

    def add_mirror(self, vendor: str, name: str, url: str) -> bool:
        """添加自定义镜像源

        Args:
            vendor: JDK 发行商
            name: 镜像源名称
            url: 镜像源地址

        Returns:
            是否添加成功
        """
        try:
            if vendor not in self.mirrors:
                self.mirrors[vendor] = {"official": "", "mirrors": {}}
            self.mirrors[vendor]["mirrors"][name] = url
            return self.save_custom_mirrors()
        except Exception as e:
            logger.error(f"添加自定义镜像源失败: {str(e)}")
            return False

    def remove_mirror(self, vendor: str, name: str) -> bool:
        """移除自定义镜像源

        Args:
            vendor: JDK 发行商
            name: 镜像源名称

        Returns:
            是否移除成功
        """
        try:
            if vendor in self.mirrors and name in self.mirrors[vendor]["mirrors"]:
                del self.mirrors[vendor]["mirrors"][name]
                return self.save_custom_mirrors()
            return False
        except Exception as e:
            logger.error(f"移除自定义镜像源失败: {str(e)}")
            return False

    def get_mirrors(self, vendor: str) -> Dict:
        """获取指定发行商的所有镜像源

        Args:
            vendor: JDK 发行商

        Returns:
            镜像源配置字典
        """
        return self.mirrors.get(vendor, {"official": "", "mirrors": {}})

    def get_best_mirror(self, vendor: str, test_url: Optional[str] = None) -> str:
        """获取最快的镜像源

        Args:
            vendor: JDK 发行商
            test_url: 测试文件的URL（可选）

        Returns:
            最快镜像源的基础URL
        """
        mirrors = self.get_mirrors(vendor)
        if not mirrors:
            return ""

        # 首先尝试国内镜像源
        for name, url in mirrors["mirrors"].items():
            try:
                if test_url:
                    test_path = test_url.replace(mirrors["official"], url)
                    response = requests.head(test_path, timeout=5)
                else:
                    response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    return url
            except Exception:
                continue

        # 如果国内镜像源都失败，返回官方源
        return mirrors["official"]

    def get_download_url(
        self, vendor: str, version: str, os_name: str, arch: str
    ) -> str:
        """获取下载URL

        Args:
            vendor: JDK 发行商
            version: JDK 版本
            os_name: 操作系统
            arch: 架构

        Returns:
            下载URL
        """
        base_url = self.get_best_mirror(vendor)
        if not base_url:
            return ""

        # 根据不同发行商构建下载URL
        if vendor == "adoptium":
            return f"{base_url}{version}/hotspot/{os_name}/{arch}/jdk/hotspot/normal/eclipse"
        elif vendor == "microsoft":
            return f"{base_url}microsoft-jdk-{version}-{os_name}-{arch}.zip"
        elif vendor == "corretto":
            return f"{base_url}amazon-corretto-{version}-{os_name}-{arch}.zip"
        elif vendor == "zulu":
            return f"{base_url}bundles/zulu{version}-{os_name}_{arch}.zip"
        elif vendor == "openjdk":
            return f"{base_url}openjdk-{version}_{os_name}-{arch}_bin.zip"

        return ""
