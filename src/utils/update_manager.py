import os
import sys
import json
import requests
from datetime import datetime, timedelta
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal
import time
import re

from .config_manager import ConfigManager
from .i18n_manager import i18n_manager
from .security_manager import SecurityManager

# 使用正确的国际化方法
_ = i18n_manager.get_text


class UpdateManager(QObject):
    """更新管理器（单例）"""

    _instance = None

    # 定义信号
    update_available = pyqtSignal(dict)  # 有更新可用时发出
    update_not_available = pyqtSignal()  # 没有更新时发出
    download_progress = pyqtSignal(int)  # 下载进度
    download_complete = pyqtSignal(str)  # 下载完成，参数为下载文件路径
    download_error = pyqtSignal(str)  # 下载错误，参数为错误信息
    check_update_complete = pyqtSignal(bool, str)  # 检查更新完成信号（是否成功，消息）

    def __new__(cls):
        if cls._instance is None:
            # 创建实例时就调用父类的 __init__
            cls._instance = super(UpdateManager, cls).__new__(cls)
            # 立即调用父类的 __init__
            QObject.__init__(cls._instance)
        return cls._instance

    def __init__(self):
        # 不需要再调用 super().__init__()，因为在 __new__ 中已经调用了
        if not hasattr(self, "initialized"):
            self.config_manager = ConfigManager()
            self.security = SecurityManager()
            self.last_check_time = None
            self.is_manual_check = False  # 是否是手动检查
            self.initialized = True

    def _get_installation_type(self):
        """获取当前安装类型（便携版/安装版）"""
        try:
            # 通过特定文件或注册表项来判断是否为安装版
            if sys.platform == "win32":
                # Windows下检查是否存在注册表项
                import winreg

                try:
                    with winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\JVMan", 0, winreg.KEY_READ
                    ) as key:
                        return "installer"
                except WindowsError:
                    return "portable"
            else:
                # Linux/macOS下检查是否在系统目录
                exe_path = sys.executable
                system_paths = ["/usr/bin", "/usr/local/bin", "/opt"]
                return (
                    "installer"
                    if any(path in exe_path for path in system_paths)
                    else "portable"
                )
        except Exception as e:
            logger.warning(f"无法确定安装类型，默认使用便携版: {str(e)}")
            return "portable"

    def _test_source_availability(self, source):
        """测试更新源的可用性"""
        try:
            urls = self.config_manager.get(f"update.{source}", {})
            if not urls or not urls.get("api_url"):
                return False, float("inf"), None

            start_time = time.time()
            response = requests.head(  # 使用 HEAD 请求替代 GET，更轻量
                urls["api_url"],
                timeout=self.config_manager.get("update.source_timeout", 5000) / 1000,
                verify=True,
            )
            response_time = time.time() - start_time

            if response.status_code != 200:
                return False, float("inf"), None  # 不返回具体错误，避免重复提示

            return True, response_time, None
        except requests.exceptions.Timeout:
            return False, float("inf"), None
        except requests.exceptions.ConnectionError:
            return False, float("inf"), None
        except Exception as e:
            return False, float("inf"), None

    def _select_best_source(self):
        """选择最佳更新源"""
        # 获取配置的平台设置
        platform = self.config_manager.get("update.platform", "auto")
        if platform != "auto":
            return platform, None

        # 获取最后成功的源
        last_success = self.config_manager.get("update.last_success_source")
        if last_success:
            # 先尝试最后成功的源
            success, _, error = self._test_source_availability(last_success)
            if success:
                return last_success, None

        # 测试所有源的可用性
        sources = ["github", "gitee"]
        max_retries = self.config_manager.get("update.source_retry", 2)
        best_source = None
        best_time = float("inf")
        errors = []

        for source in sources:
            source_error = None
            for _ in range(max_retries):
                success, response_time, error = self._test_source_availability(source)
                if success:
                    if response_time < best_time:
                        best_source = source
                        best_time = response_time
                    break
                source_error = error
            if source_error:
                errors.append(f"{source.title()}: {source_error}")

        if best_source:
            # 更新最后成功的源
            self.config_manager.set("update.last_success_source", best_source)
            self.config_manager.save()
            return best_source, None

        # 所有源都失败时，返回错误信息
        error_msg = _("update.error.all_sources_failed").format(
            details="\n".join(errors)
        )
        return None, error_msg

    def _get_update_urls(self):
        """获取更新相关的URL"""
        try:
            # 选择最佳源
            platform, error = self._select_best_source()
            if error:
                return None, error

            if not platform:
                return None, _("update.error.no_available_source")

            urls = self.config_manager.get(f"update.{platform}", {})
            if not urls:
                return None, f"未找到平台 {platform} 的配置"

            result = {
                "api_url": urls.get("api_url", ""),
                "raw_url": urls.get("raw_url", ""),
                "download_url": urls.get("download_url", ""),
                "releases_url": urls.get("releases_url", ""),
                "changelog_url": f"{urls.get('raw_url', '')}/{self.config_manager.get('update.changelog_path', '')}",
            }
            return result, None
        except Exception as e:
            logger.error(f"获取更新URL失败: {str(e)}")
            return None, str(e)

    def _get_changelog_path(self, locale=None):
        """获取对应语言的更新日志路径"""
        if not locale:
            locale = i18n_manager.current_locale

        changelog_config = self.config_manager.get("update.changelog", {})
        if not changelog_config:
            return "CHANGELOG.md"

        if locale in changelog_config.get("i18n", {}):
            return changelog_config["i18n"][locale]
        return changelog_config.get("default", "CHANGELOG.md")

    def _parse_changelog(self, content, version):
        """解析更新日志获取指定版本的更新内容"""
        try:
            # 查找指定版本的更新内容
            version_pattern = rf"## \[{version}\][^\n]*\n\n(.*?)(?=\n## \[|$)"
            match = re.search(version_pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()
            return None
        except Exception as e:
            logger.error(f"解析更新日志失败: {str(e)}")
            return None

    def _get_changelog_content(self, urls, version, locale=None):
        """获取更新日志内容"""
        try:
            # 获取对应语言的更新日志路径
            changelog_path = self._get_changelog_path(locale)

            # 构建更新日志URL
            changelog_url = f"{urls['raw_url']}/{changelog_path}"

            # 验证URL
            if not self.security.validate_url(changelog_url):
                logger.warning(f"无效的更新日志 URL: {changelog_url}")
                return None

            # 获取更新日志内容
            response = requests.get(
                changelog_url,
                timeout=self.config_manager.get("update.source_timeout", 5000) / 1000,
                verify=True,
            )

            if response.status_code != 200:
                logger.warning(f"获取更新日志失败: {response.status_code}")
                return None

            # 使用配置的编码读取内容
            encoding = self.config_manager.get("update.changelog.encoding", "utf-8")
            content = response.content.decode(encoding)

            # 解析指定版本的更新内容
            return self._parse_changelog(content, version)

        except Exception as e:
            logger.error(f"获取更新日志内容失败: {str(e)}")
            return None

    def check_update(self):
        """检查更新"""
        try:
            urls, error = self._get_update_urls()
            if error:
                self.check_update_complete.emit(False, error)
                return

            if not urls or not urls.get("api_url"):
                self.check_update_complete.emit(False, _("update.error.invalid_urls"))
                return

            # 验证 API URL
            if not self.security.validate_url(urls["api_url"]):
                self.check_update_complete.emit(
                    False, _("update.error.invalid_api_url")
                )
                return

            try:
                # 获取远程版本信息
                response = requests.get(
                    urls["api_url"],
                    headers={"Accept": "application/json"},
                    timeout=self.config_manager.get("update.source_timeout", 5000)
                    / 1000,
                    verify=True,
                )

                if response.status_code != 200:
                    if response.status_code == 404:
                        self.check_update_complete.emit(
                            False, _("update.error.no_release")
                        )
                    else:
                        self.check_update_complete.emit(
                            False,
                            _("update.error.request_failed").format(
                                status=response.status_code
                            ),
                        )
                    return

                latest = response.json()
                latest_version = latest["tag_name"].lstrip("v")
                current_version = self.config_manager.get("version")

                if self._version_compare(latest_version, current_version) > 0:
                    # 获取当前安装类型和平台
                    install_type = self._get_installation_type()
                    platform = self._get_platform()

                    # 构建下载URL
                    if install_type == "installer":
                        download_url = f"{urls['download_url']}/v{latest_version}/jvman-{latest_version}-{platform}-setup.exe"
                        package_type = "安装版"
                    else:
                        download_url = f"{urls['download_url']}/v{latest_version}/jvman-{latest_version}-{platform}.zip"
                        package_type = "便携版"

                    # 验证下载URL
                    if not self.security.validate_url(download_url):
                        self.check_update_complete.emit(False, "无效的下载 URL")
                        return

                    # 获取发布信息
                    release_info_url = (
                        f"{urls['raw_url']}/v{latest_version}/release.json"
                    )
                    release_info_response = requests.get(release_info_url, verify=True)

                    if release_info_response.status_code == 200:
                        release_info = release_info_response.json()
                        file_name = os.path.basename(download_url)
                        file_info = next(
                            (
                                f
                                for f in release_info["files"]
                                if f["name"] == file_name
                            ),
                            None,
                        )

                        # 获取当前语言的更新日志
                        changelog_content = self._get_changelog_content(
                            urls, latest_version
                        )

                        update_info = {
                            "version": latest_version,
                            "download_url": download_url,
                            "changelog": changelog_content,  # 使用解析后的更新日志内容
                            "release_notes": latest.get("body", ""),
                            "package_type": package_type,
                            "file_size": file_info["size"] if file_info else None,
                            "sha256": file_info["sha256"] if file_info else None,
                        }

                        # 添加其他版本的下载链接
                        alternative_package = {
                            "url": f"{urls['download_url']}/v{latest_version}/jvman-{latest_version}-{platform}-{'setup.exe' if install_type == 'portable' else 'zip'}",
                            "type": "安装版" if install_type == "portable" else "便携版",
                        }
                        update_info["alternative_package"] = alternative_package

                        self.update_available.emit(update_info)
                        self.check_update_complete.emit(
                            True, f"发现新版本 {latest_version}（{package_type}）"
                        )

                        # 更新最后检查时间
                        self.last_check_time = datetime.now()
                        return

                    self.check_update_complete.emit(False, "无法获取发布信息")
                    return

                self.update_not_available.emit()
                self.check_update_complete.emit(True, "当前已是最新版本")

            except requests.exceptions.RequestException as e:
                self.check_update_complete.emit(False, f"网络请求失败: {str(e)}")
            except Exception as e:
                self.check_update_complete.emit(False, f"检查更新失败: {str(e)}")

        except Exception as e:
            self.check_update_complete.emit(False, f"更新检查过程失败: {str(e)}")

    def download_update(self, url, target_path):
        """下载更新"""
        try:
            if self.security.secure_download(url, target_path):
                self.download_complete.emit(target_path)
                return True
            else:
                self.download_error.emit("下载失败")
                return False
        except Exception as e:
            self.download_error.emit(str(e))
            return False

    def _version_compare(self, ver1, ver2):
        """比较版本号"""
        try:
            v1 = [int(x) for x in ver1.split(".")]
            v2 = [int(x) for x in ver2.split(".")]
            return (v1 > v2) - (v1 < v2)
        except Exception:
            return 0

    def _get_platform(self):
        """获取平台标识"""
        if sys.platform == "win32":
            return "windows"
        elif sys.platform == "darwin":
            return "macos"
        else:
            return "linux"

    def get_update_check_interval(self):
        """获取更新检查间隔（小时）"""
        return self.config_manager.get("update.check_interval", 24)

    def should_check_update(self, last_check_time):
        """判断是否应该检查更新"""
        if not last_check_time:
            return True

        interval = timedelta(hours=self.get_update_check_interval())
        return datetime.now() - last_check_time > interval

    def should_check_updates(self):
        """检查是否应该检查更新"""
        try:
            # 检查是否启用了自动更新
            if not self.config_manager.get("update.auto_check", True):
                logger.debug(_("log.debug.auto_update_disabled"))
                return False

            # 获取上次检查时间
            last_check = self.config_manager.get("update.last_check_time")
            if last_check:
                try:
                    last_check = datetime.fromisoformat(last_check)
                    # 获取检查间隔（小时）
                    interval = self.config_manager.get("update.check_interval", 24)
                    # 如果距离上次检查时间不足间隔时间，则不检查
                    if datetime.now() - last_check < timedelta(hours=interval):
                        logger.debug(
                            "Less than {} hours since last check".format(interval)
                        )
                        return False
                except ValueError:
                    logger.warning(_("log.warning.invalid_check_time"))
                    return True

            return True
        except Exception as e:
            logger.error(_("log.error.check_update_failed").format(error=str(e)))
            return False

    def manual_check_update(self):
        """手动检查更新"""
        self.is_manual_check = True
        self.check_update()

    def check_for_updates(self):
        """检查更新"""
        try:
            # 获取更新 URL
            urls, error = self._get_update_urls()
            if error:
                logger.error(error)
                return False

            # 更新上次检查时间
            self.config_manager.set(
                "update.last_check_time", datetime.now().isoformat()
            )
            self.config_manager.save()

            # 执行更新检查
            self.check_update()
            return True
        except Exception as e:
            logger.error(_("log.error.check_update_failed").format(error=str(e)))
            return False

    def _get_error_message(self, error):
        """获取错误信息"""
        if isinstance(error, requests.exceptions.ConnectionError):
            return _("update.error.connection_failed")
        elif isinstance(error, requests.exceptions.Timeout):
            return _("update.error.timeout")
        elif isinstance(error, requests.exceptions.RequestException):
            return _("update.error.request_failed").format(error=str(error))
        elif isinstance(error, json.JSONDecodeError):
            return _("update.error.json_decode_failed")
        else:
            return _("update.error.unknown").format(error=str(error))

    def _compare_versions(self, latest_version, current_version):
        """比较版本号，如果latest_version大于current_version返回True"""

        def version_to_tuple(v):
            # 移除版本号中的'v'前缀
            v = v.lower().lstrip("v")
            # 处理预发布版本
            if "-" in v:
                v, pre = v.split("-", 1)
                # 预发布版本号小于正式版本
                v_parts = list(map(int, v.split(".")))
                return tuple(v_parts + [-1])
            # 将版本号分割为数字列表
            return tuple(map(int, v.split(".")))

        try:
            return version_to_tuple(latest_version) > version_to_tuple(current_version)
        except Exception as e:
            logger.error(_("log.error.compare_version_failed").format(error=str(e)))
            return False

    def get_update_save_path(self):
        """获取更新文件保存路径"""
        try:
            if getattr(sys, "frozen", False):
                # 如果是打包后的环境
                base_path = os.path.dirname(sys.executable)
            else:
                # 如果是开发环境
                base_path = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )

            updates_dir = os.path.join(base_path, "updates")

            # 确保目录存在
            os.makedirs(updates_dir, exist_ok=True)

            # 检查写入权限
            test_file = os.path.join(updates_dir, ".test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                logger.error(_("log.error.update_dir_permission").format(error=str(e)))
                raise PermissionError(_("update.error.no_permission"))

            return updates_dir
        except Exception as e:
            logger.error(_("log.error.get_update_path_failed").format(error=str(e)))
            raise

    def _get_version_changes(self, config, version):
        """从changelog中获取指定版本的更新说明"""
        try:
            changelog = config.get("changelog", [])
            for entry in changelog:
                if entry.get("version") == version:
                    changes = entry.get("changes", [])
                    if isinstance(changes, list):
                        return _("update.changes.list").format(
                            changes="\n".join(f"- {change}" for change in changes)
                        )
                    return str(changes)
            return _("update.changes.no_details")
        except Exception:
            return _("update.changes.no_details")
