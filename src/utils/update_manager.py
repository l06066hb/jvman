import os
import sys
import json
import requests
from datetime import datetime, timedelta
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal
import time
import re
from PyQt6.QtWidgets import QMessageBox

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
    show_error = pyqtSignal(str, str)  # 显示错误消息信号（标题，消息）

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
            self.is_downloading = False  # 添加下载状态标志
            self.update_notification_shown = False  # 添加标志位，表示是否已显示更新通知
            self.initialized = True

    def _get_installation_type(self):
        """获取当前安装类型（便携版/安装版）"""
        try:
            # 首先检查安装标记文件
            install_marker = os.path.join(os.path.dirname(sys.executable), ".installer")
            if os.path.exists(install_marker):
                return "installer"

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
            locale = i18n_manager.get_current_locale()

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
            if not changelog_path:
                logger.warning("未找到更新日志路径配置")
                return None

            # 构建更新日志URL
            changelog_url = f"{urls['raw_url']}/{changelog_path}"
            if not changelog_url:
                logger.warning("无法构建更新日志URL")
                return None

            # 验证URL
            if not self.security.validate_url(changelog_url):
                logger.warning(f"无效的更新日志 URL: {changelog_url}")
                return None

            try:
                # 获取更新日志内容
                response = requests.get(
                    changelog_url,
                    timeout=self.config_manager.get("update.source_timeout", 5000) / 1000,
                    verify=True,
                    headers=self._get_request_headers()
                )

                if response.status_code != 200:
                    logger.warning(f"获取更新日志失败: HTTP {response.status_code}")
                    return None

                # 使用配置的编码读取内容
                encoding = self.config_manager.get("update.changelog.encoding", "utf-8")
                content = response.content.decode(encoding)

                # 解析指定版本的更新内容
                changelog_content = self._parse_changelog(content, version)
                if not changelog_content:
                    logger.warning(f"未找到版本 {version} 的更新说明")
                    return None

                return changelog_content

            except requests.exceptions.RequestException as e:
                logger.warning(f"请求更新日志失败: {str(e)}")
                return None
            except Exception as e:
                logger.warning(f"处理更新日志失败: {str(e)}")
                return None

        except Exception as e:
            logger.error(f"获取更新日志内容失败: {str(e)}")
            return None

    def check_update(self):
        """检查更新"""
        try:
            # 获取更新相关的URL
            urls, error = self._get_update_urls()
            if error:
                if self.is_manual_check:
                    self.show_error.emit(_("update.dialog.title"), error)
                self.check_update_complete.emit(False, error)
                return

            # 验证URL
            if not self.security.validate_url(urls["api_url"]):
                error_msg = _("update.error.invalid_api_url")
                if self.is_manual_check:
                    self.show_error.emit(_("update.dialog.title"), error_msg)
                self.check_update_complete.emit(False, error_msg)
                return

            try:
                # 获取远程版本信息
                response = requests.get(
                    urls["api_url"],
                    headers=self._get_request_headers(),
                    timeout=self.config_manager.get("update.source_timeout", 5000) / 1000,
                    verify=True,
                )

                if response.status_code != 200:
                    error_msg = (_("update.error.no_release") if response.status_code == 404 
                               else _("update.error.request_failed").format(status=response.status_code))
                    if self.is_manual_check:
                        self.show_error.emit(_("update.dialog.title"), error_msg)
                    self.check_update_complete.emit(False, error_msg)
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
                        package_type = _("update.package_type.installer")
                    else:
                        download_url = f"{urls['download_url']}/v{latest_version}/jvman-{latest_version}-{platform}.zip"
                        package_type = _("update.package_type.portable")

                    # 验证下载URL
                    if not self.security.validate_url(download_url):
                        self.check_update_complete.emit(False, _("update.error.invalid_api_url"))
                        return

                    # 获取发布信息
                    release_info_url = f"{urls['raw_url']}/v{latest_version}/release.json"
                    try:
                        release_info_response = requests.get(
                            release_info_url,
                            verify=True,
                            timeout=self.config_manager.get("update.source_timeout", 5000) / 1000
                        )

                        if release_info_response.status_code == 200:
                            try:
                                release_info = release_info_response.json()
                                file_name = os.path.basename(download_url)
                                file_info = next(
                                    (
                                        f
                                        for f in release_info.get("files", [])
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
                                    "changelog": changelog_content,
                                    "release_notes": latest.get("body", ""),
                                    "package_type": package_type,
                                    "file_size": file_info["size"] if file_info else None,
                                    "sha256": file_info["sha256"] if file_info else None,
                                }

                                # 添加其他版本的下载链接
                                alternative_package = {
                                    "url": f"{urls['download_url']}/v{latest_version}/jvman-{latest_version}-{platform}-{'setup.exe' if install_type == 'portable' else 'zip'}",
                                    "type": _("update.package_type.installer") if install_type == "portable" else _("update.package_type.portable"),
                                }
                                update_info["alternative_package"] = alternative_package

                                # 发送更新可用信号
                                self.update_available.emit(update_info)
                                self.update_notification_shown = True
                                
                                # 更新最后检查时间
                                self.last_check_time = datetime.now()
                                return

                            except json.JSONDecodeError as e:
                                logger.error(f"解析发布信息JSON失败: {str(e)}")
                                self.check_update_complete.emit(False, _("update.error.invalid_release_json"))
                                return
                            except Exception as e:
                                logger.error(f"处理发布信息失败: {str(e)}")
                                self.check_update_complete.emit(False, _("update.error.process_release_failed").format(error=str(e)))
                                return
                        else:
                            # 如果无法获取release.json，仍然继续，只是没有文件大小和校验信息
                            logger.warning(_("update.error.no_release_json").format(status=release_info_response.status_code))
                            update_info = {
                                "version": latest_version,
                                "download_url": download_url,
                                "changelog": self._get_changelog_content(urls, latest_version),
                                "release_notes": latest.get("body", ""),
                                "package_type": package_type,
                            }

                            # 添加其他版本的下载链接
                            alternative_package = {
                                "url": f"{urls['download_url']}/v{latest_version}/jvman-{latest_version}-{platform}-{'setup.exe' if install_type == 'portable' else 'zip'}",
                                "type": _("update.package_type.installer") if install_type == "portable" else _("update.package_type.portable"),
                            }
                            update_info["alternative_package"] = alternative_package

                            # 发送更新可用信号
                            self.update_available.emit(update_info)
                            self.update_notification_shown = True
                            
                            # 更新最后检查时间
                            self.last_check_time = datetime.now()
                            return

                    except requests.exceptions.RequestException as e:
                        logger.warning(_("update.error.get_release_json_failed").format(error=str(e)))
                        # 如果无法获取release.json，仍然继续，只是没有文件大小和校验信息
                        update_info = {
                            "version": latest_version,
                            "download_url": download_url,
                            "changelog": self._get_changelog_content(urls, latest_version),
                            "release_notes": latest.get("body", ""),
                            "package_type": package_type,
                        }

                        # 添加其他版本的下载链接
                        alternative_package = {
                            "url": f"{urls['download_url']}/v{latest_version}/jvman-{latest_version}-{platform}-{'setup.exe' if install_type == 'portable' else 'zip'}",
                            "type": _("update.package_type.installer") if install_type == "portable" else _("update.package_type.portable"),
                        }
                        update_info["alternative_package"] = alternative_package

                        # 发送更新可用信号
                        self.update_available.emit(update_info)
                        self.update_notification_shown = True
                        
                        # 更新最后检查时间
                        self.last_check_time = datetime.now()
                        return

                # 如果没有新版本，只在手动检查时发送信号
                if self.is_manual_check:
                    self.check_update_complete.emit(True, _("update.status.latest_version"))
                    # 更新最后检查时间
                    self.last_check_time = datetime.now()

            except requests.exceptions.RequestException as e:
                error_msg = _("update.status.check_failed").format(error=str(e))
                if self.is_manual_check:
                    self.show_error.emit(_("update.dialog.title"), error_msg)
                self.check_update_complete.emit(False, error_msg)
            except Exception as e:
                error_msg = _("update.status.check_failed").format(error=str(e))
                if self.is_manual_check:
                    self.show_error.emit(_("update.dialog.title"), error_msg)
                self.check_update_complete.emit(False, error_msg)

        except Exception as e:
            error_msg = _("update.status.process_failed").format(error=str(e))
            if self.is_manual_check:
                self.show_error.emit(_("update.dialog.title"), error_msg)
            self.check_update_complete.emit(False, error_msg)

    def download_update(self, url, target_path):
        """下载更新"""
        try:
            # 如果已经在下载中，直接返回
            if self.is_downloading:
                return False

            self.is_downloading = True

            # 创建目标目录（如果不存在）
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # 发送准备下载信号
            self.download_progress.emit(0)

            # 使用流式下载
            response = requests.get(
                url,
                stream=True,
                verify=True,
                timeout=self.config_manager.get("update.source_timeout", 5000) / 1000,
            )

            if response.status_code != 200:
                self.is_downloading = False
                self.download_error.emit(_("update.error.download_failed").format(status=response.status_code))
                return False

            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            if total_size == 0:
                self.is_downloading = False
                self.download_error.emit(_("update.error.no_size").format(url=url))
                return False

            block_size = 8192  # 8KB
            downloaded = 0
            last_progress_update = 0
            last_progress_time = time.time()
            update_interval = 0.1  # 最小进度更新间隔（秒）

            with open(target_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    if not self.is_downloading:  # 检查是否取消下载
                        response.close()
                        try:
                            os.remove(target_path)  # 删除未完成的文件
                        except:
                            pass
                        return False

                    if data:
                        downloaded += len(data)
                        f.write(data)
                        
                        # 计算进度
                        current_progress = int((downloaded / total_size) * 100)
                        current_time = time.time()
                        
                        # 只在进度变化超过1%且时间间隔超过0.1秒时更新进度条
                        if (current_progress > last_progress_update and 
                            current_time - last_progress_time >= update_interval):
                            self.download_progress.emit(current_progress)
                            last_progress_update = current_progress
                            last_progress_time = current_time

            # 验证下载是否完整
            if downloaded != total_size:
                logger.error(f"下载不完整: 已下载 {downloaded} 字节，总大小 {total_size} 字节")
                self.is_downloading = False
                self.download_error.emit(_("update.error.incomplete"))
                try:
                    os.remove(target_path)  # 删除不完整的文件
                except Exception as e:
                    logger.error(f"删除不完整文件失败: {str(e)}")
                return False

            # 发送100%进度
            self.download_progress.emit(100)
            self.is_downloading = False
            self.download_complete.emit(target_path)
            return True

        except requests.exceptions.Timeout:
            self.is_downloading = False
            self.download_error.emit(_("update.error.timeout"))
            return False
        except requests.exceptions.ConnectionError:
            self.is_downloading = False
            self.download_error.emit(_("update.error.connection"))
            return False
        except Exception as e:
            self.is_downloading = False
            self.download_error.emit(_("update.error.general").format(error=str(e)))
            return False
        finally:
            # 清理资源
            try:
                if 'response' in locals():
                    response.close()
            except Exception as e:
                logger.error(f"清理下载资源失败: {str(e)}")
            
            # 如果下载失败，尝试删除不完整的文件
            if 'downloaded' in locals() and 'total_size' in locals():
                if downloaded != total_size and os.path.exists(target_path):
                    try:
                        os.remove(target_path)
                    except:
                        pass

    def cancel_download(self):
        """取消下载"""
        if self.is_downloading:
            self.is_downloading = False
            self.download_error.emit(_("update.error.cancelled"))

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

    def _get_random_user_agent(self):
        """生成随机的 User-Agent"""
        chrome_versions = ['120.0.0.0', '119.0.0.0', '118.0.0.0', '117.0.0.0']
        platforms = {
            'windows': {
                'os': 'Windows NT 10.0; Win64; x64',
                'platform': '"Windows"'
            },
            'darwin': {
                'os': 'Macintosh; Intel Mac OS X 10_15_7',
                'platform': '"macOS"'
            },
            'linux': {
                'os': 'X11; Linux x86_64',
                'platform': '"Linux"'
            }
        }

        platform_key = self._get_platform()
        platform_info = platforms.get(platform_key, platforms['windows'])
        chrome_version = chrome_versions[int(time.time()) % len(chrome_versions)]

        return {
            'user_agent': f'Mozilla/5.0 ({platform_info["os"]}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36',
            'platform': platform_info['platform']
        }

    def _get_request_headers(self):
        """获取请求头"""
        browser_info = self._get_random_user_agent()
        return {
            "Accept": "application/json,application/vnd.github.v3+json",
            "User-Agent": browser_info['user_agent'],
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": browser_info['platform'],
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }

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

    def reset_check_state(self):
        """重置检查状态"""
        self.is_manual_check = False
        self.update_notification_shown = False
        self.is_downloading = False

    def manual_check_update(self):
        """手动检查更新"""
        self.reset_check_state()  # 先重置状态
        self.is_manual_check = True  # 设置为手动检查
        self.check_update()  # 开始检查更新

    def auto_check_update(self):
        """自动检查更新"""
        self.reset_check_state()  # 先重置状态
        self.check_update()

    # def check_for_updates(self):
    #     """检查更新"""
    #     try:
    #         # 获取更新 URL
    #         urls, error = self._get_update_urls()
    #         if error:
    #             logger.error(error)
    #             return False

    #         # 更新上次检查时间
    #         self.config_manager.set(
    #             "update.last_check_time", datetime.now().isoformat()
    #         )
    #         self.config_manager.save()

    #         # 执行更新检查
    #         self.check_update()
    #         return True
    #     except Exception as e:
    #         logger.error(_("log.error.check_update_failed").format(error=str(e)))
    #         return False

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
