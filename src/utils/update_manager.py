import os
import sys
import json
import requests
from datetime import datetime, timedelta
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal

from .config_manager import ConfigManager

class UpdateManager(QObject):
    """更新管理器"""
    
    # 定义信号
    update_available = pyqtSignal(dict)  # 有更新可用时发出
    update_not_available = pyqtSignal()  # 没有更新时发出
    download_progress = pyqtSignal(int)  # 下载进度
    download_complete = pyqtSignal(str)  # 下载完成，参数为下载文件路径
    download_error = pyqtSignal(str)  # 下载错误，参数为错误信息
    
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.last_check_time = None
        
    def should_check_updates(self):
        """检查是否应该检查更新"""
        if not self.config.get('update.auto_check', True):
            return False
            
        # 获取上次检查时间
        last_check = self.config.get('update.last_check_time')
        if last_check:
            last_check = datetime.fromisoformat(last_check)
            # 获取检查间隔（小时）
            interval = self.config.get('update.check_interval', 24)
            # 如果距离上次检查时间不足间隔时间，则不检查
            if datetime.now() - last_check < timedelta(hours=interval):
                return False
                
        return True
        
    def check_for_updates(self):
        """检查更新"""
        try:
            # 获取检查更新URL
            check_url = self.config.get('update.check_url')
            if not check_url:
                logger.error("更新检查URL未配置")
                self.download_error.emit("更新检查URL未配置")
                return
                
            # 发送请求获取版本信息
            response = requests.get(check_url)
            if response.status_code == 200:
                remote_config = response.json()
                current_version = self.config.get('version', '0.0.0')
                remote_version = remote_config.get('version', '0.0.0')
                
                # 更新最后检查时间
                self.config.set('update.last_check_time', datetime.now().isoformat())
                self.config.save()
                
                # 比较版本号
                if self._compare_versions(remote_version, current_version):
                    # 构建下载URL
                    download_url = self.config.get('update.download_url').format(
                        version=remote_version
                    )
                    
                    # 从changelog中获取更新说明
                    description = self._get_version_changes(remote_config, remote_version)
                    
                    # 有新版本
                    update_info = {
                        'version': remote_version,
                        'description': description,
                        'download_url': download_url
                    }
                    self.update_available.emit(update_info)
                else:
                    # 没有新版本
                    self.update_not_available.emit()
            else:
                error_msg = f"检查更新失败: HTTP {response.status_code}"
                logger.error(error_msg)
                self.download_error.emit(error_msg)
        except Exception as e:
            logger.error(f"检查更新时发生错误: {str(e)}")
            self.download_error.emit(f"检查更新时发生错误: {str(e)}")
            
    def _compare_versions(self, latest_version, current_version):
        """比较版本号，如果latest_version大于current_version返回True"""
        def version_to_tuple(v):
            # 移除版本号中的'v'前缀
            v = v.lower().lstrip('v')
            # 将版本号分割为数字列表
            return tuple(map(int, v.split('.')))
            
        try:
            return version_to_tuple(latest_version) > version_to_tuple(current_version)
        except Exception:
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
                self.download_error.emit(f"下载失败: HTTP {response.status_code}")
        except Exception as e:
            self.download_error.emit(f"下载时发生错误: {str(e)}")
            
    def get_update_save_path(self):
        """获取更新文件保存路径"""
        if getattr(sys, 'frozen', False):
            # 如果是打包后的环境
            base_path = os.path.dirname(sys.executable)
        else:
            # 如果是开发环境
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        return os.path.join(base_path, 'updates') 
            
    def _get_version_changes(self, config, version):
        """从changelog中获取指定版本的更新说明"""
        try:
            changelog = config.get('changelog', [])
            for entry in changelog:
                if entry.get('version') == version:
                    changes = entry.get('changes', [])
                    if isinstance(changes, list):
                        return "更新内容：\n" + "\n".join(f"- {change}" for change in changes)
                    return str(changes)
            return "暂无更新说明"
        except Exception:
            return "暂无更新说明" 