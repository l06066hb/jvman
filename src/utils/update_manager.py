import os
import sys
import json
import requests
from datetime import datetime, timedelta
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal

from .config_manager import ConfigManager
from .i18n_manager import i18n_manager

# 使用正确的国际化方法
_ = i18n_manager.get_text

class UpdateManager(QObject):
    """更新管理器"""
    
    # 定义信号
    update_available = pyqtSignal(dict)  # 有更新可用时发出
    update_not_available = pyqtSignal()  # 没有更新时发出
    download_progress = pyqtSignal(int)  # 下载进度
    download_complete = pyqtSignal(str)  # 下载完成，参数为下载文件路径
    download_error = pyqtSignal(str)  # 下载错误，参数为错误信息
    check_update_complete = pyqtSignal(bool, str)  # 检查更新完成信号（是否成功，消息）
    
    # 默认更新检查URL
    # TODO  完善自动更新逻辑
    DEFAULT_CHECK_URL = "https://api.github.com/repos/yourusername/jvman/releases/latest"
    
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.last_check_time = None
        self.is_manual_check = False  # 是否是手动检查
        
    def should_check_updates(self):
        """检查是否应该检查更新"""
        try:
            # 检查是否启用了自动更新
            if not self.config.get('update.auto_check', True):
                logger.debug(_("log.debug.auto_update_disabled"))
                return False
                
            # 获取上次检查时间
            last_check = self.config.get('update.last_check_time')
            if last_check:
                try:
                    last_check = datetime.fromisoformat(last_check)
                    # 获取检查间隔（小时）
                    interval = self.config.get('update.check_interval', 24)
                    # 如果距离上次检查时间不足间隔时间，则不检查
                    if datetime.now() - last_check < timedelta(hours=interval):
                        logger.debug(_("log.debug.check_interval_not_reached").format(hours=interval))
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
        self.check_for_updates()
        
    def check_for_updates(self):
        """检查更新"""
        try:
            # 获取检查更新URL
            check_url = self.config.get('update.check_url', self.DEFAULT_CHECK_URL)
            
            # 设置请求超时和重试
            session = requests.Session()
            session.mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
            session.mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
            
            # 发送请求获取版本信息
            response = session.get(check_url, timeout=10)
            response.raise_for_status()
            
            remote_config = response.json()
            current_version = self.config.get('version', '0.0.0')
            remote_version = remote_config.get('version', '0.0.0')
            
            # 更新最后检查时间
            self.config.set('update.last_check_time', datetime.now().isoformat())
            self.config.save()
            
            # 比较版本号
            has_update = self._compare_versions(remote_version, current_version)
            if has_update:
                # 构建下载URL
                download_url = remote_config.get('download_url') or self.config.get('update.download_url', '').format(
                    version=remote_version
                )
                
                if not download_url:
                    raise ValueError(_("update.error.no_download_url"))
                
                # 从changelog中获取更新说明
                description = self._get_version_changes(remote_config, remote_version)
                
                # 有新版本
                update_info = {
                    'version': remote_version,
                    'description': description,
                    'download_url': download_url,
                    'is_manual_check': self.is_manual_check
                }
                self.update_available.emit(update_info)
                self.check_update_complete.emit(True, _("update.new_version.found").format(version=remote_version))
            else:
                # 没有新版本
                self.update_not_available.emit()
                if self.is_manual_check:
                    self.check_update_complete.emit(True, _("update.no_update"))
                
        except Exception as e:
            error_msg = self._get_error_message(e)
            logger.error(error_msg)
            self.download_error.emit(error_msg)
            if self.is_manual_check:
                self.check_update_complete.emit(False, error_msg)
        finally:
            self.is_manual_check = False
            
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
            v = v.lower().lstrip('v')
            # 处理预发布版本
            if '-' in v:
                v, pre = v.split('-', 1)
                # 预发布版本号小于正式版本
                v_parts = list(map(int, v.split('.')))
                return tuple(v_parts + [-1])
            # 将版本号分割为数字列表
            return tuple(map(int, v.split('.')))
            
        try:
            return version_to_tuple(latest_version) > version_to_tuple(current_version)
        except Exception as e:
            logger.error(_("log.error.compare_version_failed").format(error=str(e)))
            return False
            
    def download_update(self, url, save_path):
        """下载更新"""
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024  # 1 KB
                downloaded = 0
                
                with open(save_path, 'wb') as f:
                    for data in response.iter_content(block_size):
                        downloaded += len(data)
                        f.write(data)
                        if total_size:
                            progress = int((downloaded / total_size) * 100)
                            self.download_progress.emit(progress)
                            
                self.download_complete.emit(save_path)
            else:
                self.download_error.emit(_("update.error.download_failed").format(status=response.status_code))
        except Exception as e:
            self.download_error.emit(_("update.error.download_error").format(error=str(e)))
            
    def get_update_save_path(self):
        """获取更新文件保存路径"""
        try:
            if getattr(sys, 'frozen', False):
                # 如果是打包后的环境
                base_path = os.path.dirname(sys.executable)
            else:
                # 如果是开发环境
                base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                
            updates_dir = os.path.join(base_path, 'updates')
            
            # 确保目录存在
            os.makedirs(updates_dir, exist_ok=True)
            
            # 检查写入权限
            test_file = os.path.join(updates_dir, '.test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
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
            changelog = config.get('changelog', [])
            for entry in changelog:
                if entry.get('version') == version:
                    changes = entry.get('changes', [])
                    if isinstance(changes, list):
                        return _("update.changes.list").format(changes="\n".join(f"- {change}" for change in changes))
                    return str(changes)
            return _("update.changes.no_details")
        except Exception:
            return _("update.changes.no_details") 