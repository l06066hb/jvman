import os
import re
import subprocess
from datetime import datetime, timedelta
from loguru import logger
from .platform_manager import platform_manager
from utils.i18n_manager import i18n_manager
import sys

# 初始化i18n管理器
_ = i18n_manager.get_text


class VersionCache:
    """版本信息缓存"""

    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(minutes=5)  # 缓存有效期5分钟

    def get(self, key):
        """获取缓存的版本信息"""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry["timestamp"] < self.cache_duration:
                return entry["value"]
            else:
                del self.cache[key]
        return None

    def set(self, key, value):
        """设置缓存"""
        self.cache[key] = {"value": value, "timestamp": datetime.now()}

    def clear(self):
        """清除缓存"""
        self.cache.clear()


class VersionUtils:
    """版本工具类"""

    def __init__(self):
        self.version_cache = VersionCache()

    def get_jdk_version(self, jdk_path, use_cache=True):
        """获取JDK版本信息"""
        try:
            if use_cache:
                cached_version = self.version_cache.get(jdk_path)
                if cached_version:
                    return cached_version

            java_executable = platform_manager.get_java_executable()
            java_path = os.path.join(jdk_path, "bin", java_executable)
            java_path = platform_manager.format_path(java_path)

            if not os.path.exists(java_path):
                return None

            result = self._run_java_version_cmd(java_path)
            if result and result.stderr:
                version = self._extract_version(result.stderr)
                if version and use_cache:
                    self.version_cache.set(jdk_path, version)
                return version
            return None
        except Exception as e:
            logger.error(f"{_('log.error.get_version_failed')}: {str(e)}")
            return None

    def get_vendor_info(self, jdk_path, use_cache=True):
        """获取JDK供应商信息"""
        try:
            cache_key = f"{jdk_path}_vendor"
            if use_cache:
                cached_info = self.version_cache.get(cache_key)
                if cached_info:
                    return cached_info

            java_executable = platform_manager.get_java_executable()
            java_path = os.path.join(jdk_path, "bin", java_executable)
            java_path = platform_manager.format_path(java_path)

            if not os.path.exists(java_path):
                return None

            result = self._run_java_version_cmd(java_path)
            if result and result.stderr:
                version_info = result.stderr.lower()
                vendor_info = {
                    "vendor": self._detect_vendor(version_info),
                    "version": self._extract_version(version_info),
                    "build": self._extract_build(version_info),
                }

                if use_cache:
                    self.version_cache.set(cache_key, vendor_info)
                return vendor_info
            return None
        except Exception as e:
            logger.error(f"{_('log.error.get_vendor_info_failed')}: {str(e)}")
            return None

    def get_system_java_version(self):
        """获取系统Java版本"""
        try:
            # 首先检查 JAVA_HOME
            java_home = os.environ.get("JAVA_HOME")
            if java_home:
                logger.debug(f"Checking JAVA_HOME: {java_home}")
                java_executable = platform_manager.get_java_executable()
                java_path = os.path.join(java_home, "bin", java_executable)
                if os.path.exists(java_path):
                    result = self._run_java_version_cmd(java_path)
                    if result and result.stderr:
                        return result.stderr.strip()

            # 如果 JAVA_HOME 无效或未设置，直接尝试 java -version
            logger.debug("JAVA_HOME not found or invalid, trying system java")
            result = self._run_java_version_cmd("java")
            if result and result.stderr:
                return result.stderr.strip()

            logger.debug("No Java installation found")
            return _("local.system_version.not_installed")
        except Exception as e:
            logger.error(f"{_('log.error.get_system_version_failed')}: {str(e)}")
            return _("local.system_version.unknown")

    @staticmethod
    def run_process(cmd, **kwargs):
        """通用的进程执行方法"""
        try:
            # 基础进程参数
            process_args = {
                "text": False,  # 改为 False 以获取原始字节
                "timeout": kwargs.pop("timeout", 5),
            }

            # Windows 特定设置
            if platform_manager.is_windows:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                process_args.update(
                    {
                        "startupinfo": startupinfo,
                        "creationflags": subprocess.CREATE_NO_WINDOW,
                        "capture_output": True,
                    }
                )
            else:
                process_args.update(
                    {
                        "stdout": subprocess.DEVNULL,
                        "stderr": subprocess.PIPE,
                        "stdin": subprocess.DEVNULL,
                    }
                )

            # 合并剩余的自定义参数
            process_args.update(kwargs)

            # 执行命令
            result = subprocess.run(cmd, **process_args)

            # 处理输出编码
            if result.stderr:
                try:
                    # 首先尝试 UTF-8
                    stderr_text = result.stderr.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        # Windows 中文系统通常使用 GBK
                        if platform_manager.is_windows:
                            stderr_text = result.stderr.decode("gbk")
                        else:
                            # 其他编码尝试
                            stderr_text = result.stderr.decode("latin1")
                    except UnicodeDecodeError:
                        # 如果都失败了，使用 errors='replace' 来替换无法解码的字符
                        stderr_text = result.stderr.decode("utf-8", errors="replace")

                # 创建一个新的 CompletedProcess 对象，包含解码后的文本
                return subprocess.CompletedProcess(
                    args=result.args,
                    returncode=result.returncode,
                    stdout=None,
                    stderr=stderr_text,
                )

            return result

        except subprocess.TimeoutExpired:
            logger.error(f"{_('log.error.process_timeout')}: {' '.join(cmd)}")
            return None
        except Exception as e:
            logger.error(f"{_('log.error.process_failed')}: {str(e)}")
            return None

    def _run_java_version_cmd(self, java_cmd):
        """运行java -version命令"""
        try:
            # 如果是 'java' 命令，尝试在 PATH 中查找完整路径
            if java_cmd == "java":
                if platform_manager.is_windows:
                    # Windows 下查找 java.exe
                    paths = os.environ.get("PATH", "").split(os.pathsep)
                    for path in paths:
                        java_exe = os.path.join(path, "java.exe")
                        if os.path.exists(java_exe):
                            java_cmd = java_exe
                            break
                else:
                    # Unix 系统下查找 java
                    try:
                        java_cmd = subprocess.check_output(
                            ["which", "java"], text=True
                        ).strip()
                    except:
                        pass

            # 如果找不到 java 命令，返回特定错误
            if java_cmd == "java" and not os.path.exists(java_cmd):
                return None

            # 格式化命令路径
            if not java_cmd == "java":
                java_cmd = platform_manager.format_path(java_cmd)

            return self.run_process([java_cmd, "-version"])
        except Exception as e:
            logger.error(f"{_('log.error.run_java_cmd_failed')}: {str(e)}")
            return None

    def get_version_type(self, version):
        """获取版本类型（LTS、Current等）"""
        try:
            version_info = self.parse_version(version)
            if not version_info:
                return _("local.version.type.unknown")

            major_version = version_info[0]

            # LTS 版本规律：从 JDK 8 开始，每隔 4 个大版本
            LTS_VERSIONS = [v for v in range(8, 100, 4)]  # 生成 LTS 版本列表
            LATEST_VERSION = max(LTS_VERSIONS)  # 最新的 LTS 版本

            if major_version in LTS_VERSIONS:
                return _("local.version.type.lts")
            elif major_version > LATEST_VERSION:
                return _("local.version.type.latest")
            elif major_version >= 17:
                return _("local.version.type.interim")
            elif major_version >= 11:
                return _("local.version.type.old")
            else:
                return _("local.version.type.legacy")
        except Exception as e:
            logger.error(f"获取版本类型失败: {str(e)}")
            return _("local.version.type.unknown")

    def get_version_color(self, version_type):
        """获取版本类型对应的颜色"""
        colors = {
            _("local.version.type.lts"): "#17a2b8",  # 蓝绿色
            _("local.version.type.latest"): "#28a745",  # 绿色
            _("local.version.type.interim"): "#ffc107",  # 黄色
            _("local.version.type.old"): "#6c757d",  # 灰色
            _("local.version.type.legacy"): "#dc3545",  # 红色
            _("local.version.type.unknown"): "#6c757d",  # 灰色
        }
        return colors.get(version_type, "#6c757d")

    def _detect_vendor(self, version_info):
        """检测JDK供应商"""
        if "openjdk" in version_info:
            if "corretto" in version_info:
                return "Corretto"
            elif "temurin" in version_info or "adoptium" in version_info:
                return "Temurin"
            elif "zulu" in version_info:
                return "Zulu"
            elif "microsoft" in version_info:
                return "Microsoft"
            else:
                return "OpenJDK"
        elif "java(tm)" in version_info or "oracle" in version_info:
            return "Oracle"
        elif "graalvm" in version_info:
            return "GraalVM"
        elif "semeru" in version_info:
            return "Semeru"
        return _("local.vendor.unknown")

    def _extract_version(self, version_info):
        """提取版本号"""
        match = re.search(r'version "([^"]+)"', version_info)
        return match.group(1) if match else None

    def _extract_build(self, version_info):
        """提取构建号"""
        match = re.search(r"build ([^\s]+)", version_info)
        return match.group(1) if match else None

    def compare_versions(self, version1, version2):
        """比较两个版本号的大小"""
        try:
            v1 = self.parse_version(version1)
            v2 = self.parse_version(version2)

            if not v1 or not v2:
                return 0

            return (v1 > v2) - (v1 < v2)
        except Exception as e:
            logger.error(f"比较版本号失败: {str(e)}")
            return 0

    def check_jdk_validity(self, jdk_path):
        """检查JDK路径是否有效"""
        try:
            java_executable = platform_manager.get_java_executable()
            java_path = os.path.join(jdk_path, "bin", java_executable)
            java_path = platform_manager.format_path(java_path)

            if not os.path.exists(java_path):
                return False, _("local.error.invalid_jdk_path")

            result = self._run_java_version_cmd(java_path)
            if result and result.stderr and self._extract_version(result.stderr):
                return True, None
            return False, _("local.error.invalid_jdk_version")
        except Exception as e:
            logger.error(f"{_('log.error.check_jdk_failed')}: {str(e)}")
            return False, str(e)

    def parse_version(self, version_str):
        """解析版本号
        支持的格式：
        - 1.8.0_392 或 8u392
        - 11.0.21
        - 17.0.9
        - 21.0.1
        返回: (major_version, minor_version, patch_version, update_version)
        """
        try:
            if not version_str:
                return None

            version_str = version_str.lower().strip()

            # 处理 1.8.0_392 格式
            if "_" in version_str:
                base_ver, update = version_str.split("_")
                parts = base_ver.split(".")
                if parts[0] == "1" and len(parts) > 1:  # 处理 1.8.0 这种旧格式
                    major = int(parts[1])  # 取第二个数字作为主版本号
                else:
                    major = int(parts[0])
                return (major, 0, 0, int(update))

            # 处理 8u392 格式
            if "u" in version_str:
                major, update = version_str.split("u")
                return (int(major), 0, 0, int(update))

            # 处理 11.0.21 格式
            parts = version_str.split(".")
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0

            return (major, minor, patch, 0)

        except Exception as e:
            logger.warning(f"解析版本号失败: {version_str}, {str(e)}")
            return None

    def format_version(self, version_str, include_update=True):
        """格式化版本号显示"""
        try:
            version_info = self.parse_version(version_str)
            if not version_info:
                return version_str

            major, minor, patch, update = version_info

            if update > 0 and include_update:
                if major <= 8:
                    return f"{major}u{update}"
                else:
                    return f"{major}.{minor}.{patch}"
            elif patch > 0:
                return f"{major}.{minor}.{patch}"
            elif minor > 0:
                return f"{major}.{minor}"
            else:
                return str(major)

        except Exception as e:
            logger.error(f"格式化版本号失败: {str(e)}")
            return version_str

    def get_version_release_type(self, version_str):
        """获取版本发布类型
        - GA: General Availability (正式发布版)
        - EA: Early Access (早期访问版)
        - Beta: 测试版
        """
        try:
            version_info = self.parse_version(version_str)
            if not version_info:
                return None

            major, minor, patch, update = version_info

            # EA 版本通常包含 ea 标记
            if "ea" in version_str.lower():
                return "EA"
            # Beta 版本通常包含 beta 标记
            elif "beta" in version_str.lower():
                return "Beta"
            # 其他情况视为 GA 版本
            else:
                return "GA"

        except Exception as e:
            logger.error(f"获取版本发布类型失败: {str(e)}")
            return None

    def is_version_compatible(self, required_version, current_version):
        """检查版本兼容性
        - required_version: 要求的最低版本
        - current_version: 当前版本
        返回: bool 是否兼容
        """
        try:
            req_ver = self.parse_version(required_version)
            cur_ver = self.parse_version(current_version)

            if not req_ver or not cur_ver:
                return False

            # 只比较主版本号和次版本号
            req_major, req_minor = req_ver[0], req_ver[1]
            cur_major, cur_minor = cur_ver[0], cur_ver[1]

            if cur_major > req_major:
                return True
            elif cur_major == req_major:
                return cur_minor >= req_minor
            else:
                return False

        except Exception as e:
            logger.error(f"检查版本兼容性失败: {str(e)}")
            return False


# 创建全局版本工具实例
version_utils = VersionUtils()
