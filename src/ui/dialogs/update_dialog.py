import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar,
    QPushButton, QHBoxLayout, QWidget
)
from PyQt6.QtCore import Qt

from loguru import logger

class UpdateDialog(QDialog):
    """更新对话框"""
    
    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.parent = parent
        self.download_path = None
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("发现新版本")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # 版本信息
        version_label = QLabel(f"新版本: {self.update_info['version']}")
        version_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(version_label)
        
        # 更新说明
        if self.update_info.get('description'):
            desc_label = QLabel(self.update_info['description'])
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
            
        # 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 更新按钮
        self.update_button = QPushButton("立即更新")
        self.update_button.clicked.connect(self.start_update)
        button_layout.addWidget(self.update_button)
        
        # 稍后提醒按钮
        remind_later_button = QPushButton("稍后提醒")
        remind_later_button.clicked.connect(self.reject)
        button_layout.addWidget(remind_later_button)
        
        # 添加按钮布局
        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget)
        
        self.setLayout(layout)
        
    def start_update(self):
        """开始更新"""
        try:
            # 禁用按钮
            self.update_button.setEnabled(False)
            
            # 显示进度条
            self.progress_bar.setVisible(True)
            
            # 获取下载URL
            download_url = self.update_info.get('download_url')
            if not download_url:
                raise ValueError("下载URL不可用")
                
            # 创建下载目录
            save_path = self.parent.update_manager.get_update_save_path()
            os.makedirs(save_path, exist_ok=True)
            
            # 获取文件名
            filename = os.path.basename(download_url)
            self.download_path = os.path.join(save_path, filename)
            
            # 连接信号
            self.parent.update_manager.download_progress.connect(self.update_progress)
            self.parent.update_manager.download_complete.connect(self.download_finished)
            self.parent.update_manager.download_error.connect(self.download_error)
            
            # 开始下载
            self.parent.update_manager.download_update(download_url, self.download_path)
            
        except Exception as e:
            logger.error(f"开始更新失败: {str(e)}")
            self.download_error(str(e))
            
    def update_progress(self, progress):
        """更新进度条"""
        self.progress_bar.setValue(progress)
        
    def download_finished(self, file_path):
        """下载完成"""
        logger.info(f"更新文件下载完成: {file_path}")
        self.accept()
        
        # TODO: 根据不同平台实现不同的安装逻辑
        # Windows: 启动安装程序
        # macOS: 打开DMG文件
        # Linux: 设置可执行权限或使用包管理器安装
        
    def download_error(self, error_msg):
        """下载错误"""
        from PyQt6.QtWidgets import QMessageBox
        logger.error(f"下载更新失败: {error_msg}")
        
        # 显示错误消息
        QMessageBox.critical(
            self,
            "更新失败",
            f"下载更新失败: {error_msg}",
            QMessageBox.StandardButton.Ok
        )
        
        # 重置UI状态
        self.progress_bar.setVisible(False)
        self.update_button.setEnabled(True) 