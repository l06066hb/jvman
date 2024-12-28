import os
import zipfile
import hashlib
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QProgressBar, QMessageBox,
    QGroupBox, QFrame, QScrollArea, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QSize, QDateTime, QTimer
from PyQt6.QtGui import QIcon
from utils.jdk_downloader import JDKDownloader
import shutil
import logging
from datetime import datetime
import requests

# 获取logger
logger = logging.getLogger(__name__)

class ConfirmDialog(QDialog):
    """安装确认对话框"""
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("安装确认")
        self.setFixedWidth(450)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("安装确认")
        title_label.setStyleSheet("""
            QLabel {
                color: #1a73e8;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title_label)
        
        # 信息容器
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(10)
        
        # 计算文件大小和MD5
        file_size = os.path.getsize(file_path)
        md5_hash = self.calculate_md5(file_path)
        
        # 文件信息
        file_name_label = QLabel(f"文件名: {os.path.basename(file_path)}")
        file_size_label = QLabel(f"文件大小: {self.format_size(file_size)}")
        md5_label = QLabel(f"MD5: {md5_hash}")
        
        for label in [file_name_label, file_size_label, md5_label]:
            label.setStyleSheet("""
                QLabel {
                    color: #2C3E50;
                    font-family: "Segoe UI", "Microsoft YaHei";
                }
            """)
            info_layout.addWidget(label)
        
        layout.addWidget(info_frame)
        
        # 提示文本
        hint_label = QLabel("确认安装将会解压JDK到指定目录。是否继续？")
        hint_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
            }
        """)
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        
        # 按钮
        button_box = QDialogButtonBox()
        install_button = QPushButton("安装")
        cancel_button = QPushButton("取消")
        
        install_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
        """)
        
        cancel_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                color: #666666;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
        """)
        
        button_box.addButton(install_button, QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(cancel_button, QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)

    def calculate_md5(self, file_path):
        """计算文件MD5值"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            # 分块读取大文件
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

class ProgressDialog(QDialog):
    """进度对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载进度")
        self.setFixedSize(400, 200)  # 增加对话框高度
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 状态标签
        self.status_label = QLabel("准备下载...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #1a73e8;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_label)
        
        # 详细信息标签
        self.detail_label = QLabel()
        self.detail_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
            }
        """)
        self.detail_label.setWordWrap(True)  # 允许文本换行
        layout.addWidget(self.detail_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 6px;
                text-align: center;
                background-color: #F0F0F0;
                height: 12px;
                font-size: 10px;
                margin: 10px 0;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a73e8,
                    stop:0.5 #34A853,
                    stop:1 #1a73e8);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 添加弹性空间
        layout.addStretch()
        
        # 按钮容器
        self.button_container = QWidget()
        button_layout = QHBoxLayout(self.button_container)
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(0, 0, 0, 10)  # 减少底部边距
        
        # 手动下载按钮
        self.manual_download_button = QPushButton("手动下载")
        self.manual_download_button.setFixedSize(100, 32)
        self.manual_download_button.setStyleSheet("""
            QPushButton {
                padding: 6px 20px;
                border: 1px solid #1a73e8;
                border-radius: 4px;
                background-color: white;
                color: #1a73e8;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
            QPushButton:pressed {
                background-color: #E8F0FE;
            }
        """)
        self.manual_download_button.clicked.connect(self.open_manual_download)
        self.manual_download_button.hide()
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFixedSize(100, 32)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                padding: 6px 20px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                color: #666666;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        # 完成按钮
        self.close_button = QPushButton("完成")
        self.close_button.setFixedSize(100, 32)
        self.close_button.setStyleSheet("""
            QPushButton {
                padding: 6px 20px;
                border: none;
                border-radius: 4px;
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #999999;
            }
        """)
        self.close_button.clicked.connect(self.accept)
        self.close_button.hide()
        
        button_layout.addWidget(self.manual_download_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.close_button)
        
        layout.addWidget(self.button_container)
        
        # 存储手动下载链接
        self.manual_download_url = ""
        
        # 设置进度条动画定时器
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_progress_gradient)
        self.gradient_offset = 0.0

    def update_progress_gradient(self):
        """更新进度条渐变动画"""
        self.gradient_offset = (self.gradient_offset + 0.02) % 1.0
        gradient = f"""
            QProgressBar::chunk {{
                background: qlineargradient(x1:{self.gradient_offset}, y1:0, x2:{self.gradient_offset + 1}, y2:0,
                    stop:0 #1a73e8,
                    stop:0.5 #34A853,
                    stop:1 #1a73e8);
                border-radius: 6px;
            }}
        """
        current_style = self.progress_bar.styleSheet()
        base_style = current_style.split("QProgressBar::chunk")[0]
        self.progress_bar.setStyleSheet(base_style + gradient)

    def set_progress(self, current, total, phase="下载"):
        """更新进度"""
        if total > 0:
            percentage = (current / total) * 100
            self.progress_bar.setValue(int(percentage))
            
            # 启动进度条动画
            if not self.animation_timer.isActive():
                self.animation_timer.start(50)  # 50ms 更新一次
            
            if phase == "下载":
                self.status_label.setText("正在下载 JDK...")
                self.detail_label.setText(
                    f"已下载: {current/1024/1024:.1f}MB / {total/1024/1024:.1f}MB ({percentage:.1f}%)"
                )
            else:  # 安装阶段
                self.status_label.setText("正在安装 JDK...")
                self.detail_label.setText(
                    f"正在处理: {current}/{total} 个文件 ({percentage:.1f}%)"
                )

    def set_complete(self, success=True, is_download=True):
        """设置完成状态"""
        # 停止进度条动画
        self.animation_timer.stop()
        
        if success:
            if is_download:
                self.status_label.setText("下载完成！")
                self.detail_label.setText("请在确认对话框中查看详细信息")
            else:
                self.status_label.setText("安装完成！")
                self.detail_label.setText("JDK 已成功安装到指定目录")
            
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #34A853;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            self.progress_bar.setValue(100)
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 6px;
                    text-align: center;
                    background-color: #F0F0F0;
                    height: 12px;
                    font-size: 10px;
                    margin: 10px 0;
                }
                QProgressBar::chunk {
                    background: #34A853;
                    border-radius: 6px;
                }
            """)
            
            self.close_button.setEnabled(True)
            self.close_button.show()
            self.cancel_button.hide()
            self.manual_download_button.hide()
        else:
            self.status_label.setText("操作失败")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #EA4335;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 6px;
                    text-align: center;
                    background-color: #F0F0F0;
                    height: 12px;
                    font-size: 10px;
                    margin: 10px 0;
                }
                QProgressBar::chunk {
                    background: #EA4335;
                    border-radius: 6px;
                }
            """)
            
            self.close_button.setEnabled(True)
            self.close_button.show()
            self.cancel_button.hide()

    def closeEvent(self, event):
        """关闭事件处理"""
        self.animation_timer.stop()  # 停止动画
        if self.close_button.isVisible():
            event.accept()
        else:
            event.ignore()  # 如果还在进行中，阻止关闭

    def show_manual_download_hint(self, vendor, version):
        """显示手动下载提示"""
        self.status_label.setText("无法自动下载")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #F29900;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        
        # 根据不同发行版提供不同的下载链接和提示
        if vendor == "Oracle JDK":
            self.manual_download_url = f"https://www.oracle.com/java/technologies/downloads/#java{version}-windows"
            self.detail_label.setText("需要登录 Oracle 账号才能下载此版本。点击\"手动下载\"前往官网下载页面。")
        elif vendor == "OpenJDK":
            self.manual_download_url = f"https://jdk.java.net/{version}"
            self.detail_label.setText("此版本需要 OpenJDK 官网手动下载。点击\"手动下载\"前往下载页面")
        else:
            self.detail_label.setText("此版本暂不支持自动下载，请前往对应官网下载。")
        
        self.manual_download_button.show()
        self.close_button.show()
        self.cancel_button.hide()
        self.close_button.setEnabled(True)

    def show_error(self, message):
        """显示错误信息"""
        self.status_label.setText("下载失败")
        self.detail_label.setText(f"错误信息：{message}")
        self.close_button.setEnabled(True)
        self.close_button.show()
        self.cancel_button.hide()

    def open_manual_download(self):
        """打开手动下载页面"""
        if self.manual_download_url:
            import webbrowser
            webbrowser.open(self.manual_download_url)

class DownloadTab(QWidget):
    """下载标签页"""
    
    # 定义信号
    jdk_downloaded = pyqtSignal(str, str, str, str)  # 版本，路径，安装时间，导入时间

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.downloader = JDKDownloader()
        self.progress_dialog = None
        self.download_thread = None
        self.install_thread = None
        self.is_downloading = False  # 添加下载状态标志
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # 创建选择区域组
        select_group = QGroupBox("JDK 选择")
        select_group.setFixedHeight(120)  # 减小选择区域高度
        select_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        select_layout = QVBoxLayout(select_group)
        select_layout.setSpacing(15)
        
        # 发行版和版本选择行
        selection_layout = QHBoxLayout()
        
        # 发行版选择
        vendor_container = QWidget()
        vendor_layout = QVBoxLayout(vendor_container)
        vendor_layout.setSpacing(5)
        vendor_label = QLabel('发行版:')
        vendor_label.setStyleSheet("font-weight: bold; color: #666666;")
        self.vendor_combo = QComboBox()
        self.vendor_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #FFFFFF;
                min-width: 200px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: url(icon/down-arrow.png);
            }
            QComboBox QAbstractItemView {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #F5F5F5;
            }
        """)
        self.vendor_combo.addItems([
            'Oracle JDK',
            'OpenJDK',
            'Eclipse Temurin (Adoptium)',
            'Amazon Corretto',
            'Azul Zulu'
        ])
        vendor_layout.addWidget(vendor_label)
        vendor_layout.addWidget(self.vendor_combo)
        
        # 版本选择
        version_container = QWidget()
        version_layout = QVBoxLayout(version_container)
        version_layout.setSpacing(5)
        version_label = QLabel('版本:')
        version_label.setStyleSheet("font-weight: bold; color: #666666;")
        self.version_combo = QComboBox()
        self.version_combo.setStyleSheet(self.vendor_combo.styleSheet())
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_combo)
        
        # 刷新和下载按钮容器
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setSpacing(5)
        button_layout.addWidget(QLabel())  # 占位对齐
        
        button_group = QHBoxLayout()
        
        self.refresh_button = QPushButton('刷新')
        self.refresh_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'refresh.png')))
        self.refresh_button.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
        """)
        
        self.download_button = QPushButton('下载')
        self.download_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'download.png')))
        self.download_button.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                border: none;
                border-radius: 4px;
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1557b0;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #999999;
            }
        """)
        
        button_group.addWidget(self.refresh_button)
        button_group.addWidget(self.download_button)
        button_layout.addLayout(button_group)
        
        # 添加到选择布局
        selection_layout.addWidget(vendor_container)
        selection_layout.addWidget(version_container)
        selection_layout.addWidget(button_container)
        selection_layout.addStretch()
        
        select_layout.addLayout(selection_layout)
        
        # 版本信息区域
        info_group = QGroupBox("版本信息")
        info_group.setStyleSheet(select_group.styleSheet())
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(0)
        info_layout.setContentsMargins(12, 20, 12, 12)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #C0C0C0;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # 创建版本信息容器
        info_container = QFrame()
        info_container.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        info_container_layout = QVBoxLayout(info_container)
        info_container_layout.setContentsMargins(15, 15, 15, 15)
        info_container_layout.setSpacing(0)
        
        self.version_info_label = QLabel()
        self.version_info_label.setWordWrap(True)
        self.version_info_label.setTextFormat(Qt.TextFormat.RichText)
        self.version_info_label.setOpenExternalLinks(True)
        self.version_info_label.setStyleSheet("""
            QLabel {
                font-family: "Segoe UI", "Microsoft YaHei";
                line-height: 1.6;
            }
        """)
        info_container_layout.addWidget(self.version_info_label)
        info_container_layout.addStretch()
        
        scroll.setWidget(info_container)
        info_layout.addWidget(scroll)
        
        layout.addWidget(select_group)
        layout.addWidget(info_group, 1)
        
        # 初始化版本列表
        self.refresh_versions()
        
        # 默认选择最新版本
        if self.version_combo.count() > 0:
            self.version_combo.setCurrentIndex(0)  # 选择第一个版本（最新版本）
            self.on_version_changed(self.version_combo.currentText())  # 触发版本变更事件

    def connect_signals(self):
        """连接信号"""
        self.refresh_button.clicked.connect(self.refresh_versions)
        self.download_button.clicked.connect(self.start_download)
        self.vendor_combo.currentTextChanged.connect(self.on_vendor_changed)
        self.version_combo.currentTextChanged.connect(self.on_version_changed)

    def show_progress_dialog(self, title):
        """显示进度对话框"""
        if not self.progress_dialog:
            self.progress_dialog = ProgressDialog(self)
            # 连接取消按钮信号
            self.progress_dialog.cancel_button.clicked.connect(self.cancel_operation)
            
        self.progress_dialog.setWindowTitle(title)
        self.progress_dialog.progress_bar.setValue(0)
        self.progress_dialog.status_label.setText("准备中...")
        self.progress_dialog.detail_label.setText("")
        self.progress_dialog.close_button.hide()
        self.progress_dialog.cancel_button.show()
        self.progress_dialog.cancel_button.setEnabled(True)
        self.progress_dialog.manual_download_button.hide()
        self.progress_dialog.show()

    def cancel_operation(self):
        """取消当前操作"""
        try:
            if self.download_thread and self.download_thread.isRunning():
                # 防止重复连接信号
                try:
                    self.download_thread.cleanup_complete.disconnect()
                except:
                    pass
                # 连接清理完成信号
                self.download_thread.cleanup_complete.connect(self.on_download_cleanup_complete)
                
                # 更新进度对话框状态
                if self.progress_dialog:
                    self.progress_dialog.status_label.setText("正在取消...")
                    self.progress_dialog.detail_label.setText("正在清理文件...")
                    self.progress_dialog.cancel_button.setEnabled(False)
                
                # 取消下载
                self.download_thread.cancel()
                return
            
            if self.install_thread and self.install_thread.isRunning():
                self.install_thread.cancel()
                self.install_thread.wait()
                self.install_thread.deleteLater()
                self.install_thread = None
            
            # 如果没有活动的线程，直接关闭对话框
            self.is_downloading = False
            if self.progress_dialog:
                self.progress_dialog.reject()
                self.progress_dialog = None
            
        except Exception as e:
            logger.error(f"取消操作失败: {str(e)}")
            if self.progress_dialog:
                self.progress_dialog.show_error(f"取消操作失败: {str(e)}")

    def on_download_cleanup_complete(self):
        """下载清理完成回调"""
        try:
            # 断开所有信号连接
            if self.download_thread:
                try:
                    self.download_thread.cleanup_complete.disconnect()
                    self.download_thread.progress.disconnect()
                    self.download_thread.finished.disconnect()
                except:
                    pass
                
                # 等待线程完成并删除
                if self.download_thread.isRunning():
                    self.download_thread.wait()
                self.download_thread.deleteLater()
                self.download_thread = None

            # 重置状态
            self.is_downloading = False
            
            # 关闭进度对话框
            if self.progress_dialog:
                self.progress_dialog.reject()
                self.progress_dialog = None

        except Exception as e:
            logger.error(f"处理清理完成事件失败: {str(e)}")
            if self.progress_dialog:
                self.progress_dialog.show_error(f"处理清理完成事件失败: {str(e)}")

    def update_download_progress(self, current, total):
        """更新下载进度"""
        if self.progress_dialog and not self.progress_dialog.isHidden():
            self.progress_dialog.set_progress(current, total, "下载")

    def update_install_progress(self, current, total):
        """更新安装进度"""
        if self.progress_dialog and not self.progress_dialog.isHidden():
            self.progress_dialog.set_progress(current, total, "安装")

    def on_download_complete(self, success, message):
        """下载完成回调"""
        try:
            if success:
                # 获取下载的zip文件路径
                zip_file = os.path.join(self.target_dir, f"jdk-{self.version}.zip")
                if os.path.exists(zip_file):
                    # 显示安装确认对话框
                    confirm_dialog = ConfirmDialog(zip_file, self)
                    if confirm_dialog.exec() == QDialog.DialogCode.Accepted:
                        # 用户确认安装，开始安装过程
                        self.progress_dialog.set_complete(True, True)
                        self.start_install(zip_file)
                    else:
                        # 用户取消安装，但保留下载的文件
                        self.progress_dialog.close()
                        QMessageBox.information(self, '下载完成', 
                            f'JDK {self.version} 下载完成！\n可以稍后在下载目录中找到安装包。')
                else:
                    # zip文件不存在，显示错误
                    self.progress_dialog.show_error("下载完成但文件不存在，请重试下载")
            else:
                # 如果消息中包含手动下载的指导，显示手动下载提示
                if "请按以下步骤" in message or "需要登录" in message or "手动下载" in message:
                    self.progress_dialog.show_manual_download_hint(
                        self.vendor_combo.currentText(),
                        self.version_combo.currentData()
                    )
                else:
                    # 显示错误信息，并添加手动下载按钮
                    self.progress_dialog.status_label.setText("下载失败")
                    self.progress_dialog.detail_label.setText(f"错误信息：{message}\n\n您可尝试手动下载此版本。")
                    self.progress_dialog.show_manual_download_hint(
                        self.vendor_combo.currentText(),
                        self.version_combo.currentData()
                    )
        except Exception as e:
            self.progress_dialog.show_error(f"处理下载完成事件失败: {str(e)}")
        finally:
            # 重置下载状态
            self.is_downloading = False

    def start_install(self, zip_file):
        """开始安装程序"""
        try:
            # 验证文件是否存在
            if not os.path.exists(zip_file):
                raise Exception("安装文件不存在")
            
            # 验证是否是有效的 ZIP 文件
            import zipfile
            try:
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    # 验证 ZIP 文件的完整性
                    if zf.testzip() is not None:
                        raise Exception("ZIP 文件已损坏")
            except zipfile.BadZipFile:
                raise Exception("不是有效的 ZIP 文件，下载可能未完成或文件已损坏")
            
            # 保存当前选择的版本信息
            self.current_version = self.version_combo.currentData()
            if not self.current_version:
                self.current_version = self.version  # 使用类成员变量中保存的版本
            
            # 创建安装线程
            self.install_thread = InstallThread(zip_file, self.target_dir)
            self.install_thread.progress.connect(self.update_install_progress)
            self.install_thread.finished.connect(self.on_install_complete)
            
            # 更新进度对话框状态
            self.progress_dialog.status_label.setText("正在安装...")
            self.progress_dialog.detail_label.setText("正在解压文件...")
            self.progress_dialog.progress_bar.setValue(0)
            
            # 启动安装线程
            self.install_thread.start()
        except Exception as e:
            logger.error(f"开始安装失败: {str(e)}")
            self.progress_dialog.status_label.setText("安装失败")
            self.progress_dialog.detail_label.setText(f"错误信息：{str(e)}")
            self.progress_dialog.cancel_button.setText("关闭")
            self.progress_dialog.cancel_button.setEnabled(True)

    def on_install_complete(self, success, message):
        """安装完成的处理"""
        try:
            if success:
                # 获取安装目录
                install_dir = self.config.get('install_path')
                if not install_dir:
                    install_dir = self.target_dir  # 如果没有配置安装路径，使用下载目录
                
                if not install_dir or not os.path.exists(install_dir):
                    raise Exception("安装目录不存在")
                
                logger.debug(f"正在查找JDK目录，安装目录: {install_dir}")
                
                # 获取正确的 JDK 路径（安装目录下的具体版本目录）
                jdk_name = None
                for item in os.listdir(install_dir):
                    item_path = os.path.join(install_dir, item)
                    if os.path.isdir(item_path) and 'jdk' in item.lower():
                        # 检查是否是最新创建的目录
                        if not jdk_name or os.path.getctime(item_path) > os.path.getctime(os.path.join(install_dir, jdk_name)):
                            jdk_name = item
                
                if not jdk_name:
                    raise Exception("无法找到安装的JDK目录")
                
                jdk_path = os.path.join(install_dir, jdk_name)
                logger.debug(f"找到JDK目录: {jdk_path}")
                
                if not os.path.exists(jdk_path):
                    raise Exception(f"JDK目录不存在: {jdk_path}")
                
                # 获取发行商信息
                vendor = self.get_vendor_name(jdk_path)
                logger.debug(f"获取到发行商信息: {vendor}")
                
                # 获取当前时间作为导入时间
                import datetime
                import_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 使用保存的版本信息
                if not hasattr(self, 'current_version') or not self.current_version:
                    self.current_version = self.version  # 使用类成员变量中保存的版本
                
                if not self.current_version:
                    raise Exception("无法获取版本信息")
                
                # 添加到配置
                jdk_info = {
                    'path': jdk_path,
                    'version': self.current_version,
                    'vendor': vendor,
                    'type': 'downloaded',
                    'import_time': import_time
                }
                
                logger.debug(f"准备添加JDK信息到配置: {jdk_info}")
                # 确保添加到配置成功
                if not self.config.add_downloaded_jdk(jdk_info):
                    raise Exception("添加JDK到配置失败")
                
                # 强制保存配置
                self.config.save()
                logger.debug("配置已保存")
                
                # 更新进度对话框
                self.progress_dialog.status_label.setText("安装完成！")
                self.progress_dialog.detail_label.setText("JDK安装已完成，可以点击完成按钮关闭此窗口。")
                self.progress_dialog.cancel_button.setText("完成")
                self.progress_dialog.cancel_button.setEnabled(True)
                
                # 连接完成按钮的点击事件
                try:
                    self.progress_dialog.cancel_button.clicked.disconnect()
                except:
                    pass
                self.progress_dialog.cancel_button.clicked.connect(self.on_install_dialog_complete)
                
                # 立即刷新本地管理标签页
                main_window = self.parent().parent()
                if hasattr(main_window, 'local_tab'):
                    logger.debug("开始刷新本地管理标签页")
                    def do_refresh():
                        try:
                            # 重新加载配置
                            main_window.config.load()  # 使用主窗口的配置实例
                            self.config.load()  # 同时更新当前标签页的配置
                            # 刷新列表
                            main_window.local_tab.refresh_jdk_list()
                            logger.debug("本地管理标签页刷新完成")
                            
                            # 通知主窗口更新JDK菜单
                            main_window.update_jdk_menu()
                        except Exception as e:
                            logger.error(f"刷新本地管理标签页失败: {str(e)}")
                    
                    # 使用定时器确保配置文件已完全保存
                    QTimer.singleShot(1000, do_refresh)
                    # 再次延迟刷新以确保更新
                    QTimer.singleShot(2000, do_refresh)
                    
            else:
                self.progress_dialog.status_label.setText("安装失败")
                self.progress_dialog.detail_label.setText(f"错误信息：{message}")
                self.progress_dialog.cancel_button.setText("关闭")
                self.progress_dialog.cancel_button.setEnabled(True)
                
        except Exception as e:
            logger.error(f"处理安装完成事件失败: {str(e)}")
            self.progress_dialog.status_label.setText("安装失败")
            self.progress_dialog.detail_label.setText(f"错误信息：{str(e)}")
            self.progress_dialog.cancel_button.setText("关闭")
            self.progress_dialog.cancel_button.setEnabled(True)

    def on_install_dialog_complete(self):
        """安装完成对话框关闭时的处理"""
        try:
            # 关闭进度对话框
            self.progress_dialog.accept()
            
            # 再次刷新本地管理标签页
            main_window = self.parent().parent()
            if hasattr(main_window, 'local_tab'):
                logger.debug("安装完成后再次刷新本地管理标签页")
                def do_refresh():
                    try:
                        # 重新加载配置
                        main_window.config.load()  # 使用主窗口的配置实例
                        self.config.load()  # 同时更新当前标签页的配置
                        # 刷新列表
                        main_window.local_tab.refresh_jdk_list()
                        logger.debug("本地管理标签页刷新完成")
                        
                        # 通知主窗口更新JDK菜单
                        main_window.update_jdk_menu()
                    except Exception as e:
                        logger.error(f"刷新本地管理标签页失败: {str(e)}")
                
                # 使用定时器确保配置文件已完全保存
                QTimer.singleShot(1000, do_refresh)
                # 再次延迟刷新以确保更新
                QTimer.singleShot(2000, do_refresh)
        except Exception as e:
            logger.error(f"处理安装完成对话框关闭事件失败: {str(e)}")

    def get_vendor_name(self, jdk_path):
        """获取JDK发行商信息"""
        try:
            # 如果是从 jdk.java.net 下载的版本，直接判定为 OpenJDK
            if hasattr(self, 'vendor') and self.vendor == "OpenJDK":
                return 'OpenJDK'
            
            # 检查 release 文件
            release_file = os.path.join(jdk_path, 'release')
            if os.path.exists(release_file):
                with open(release_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 添加详细的调试日志
                    logger.debug(f"Release文件完整内容:\n{content}")
                    
                    content = content.lower()
                    
                    # 解析所有关键字段
                    fields = {}
                    for line in content.split('\n'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            fields[key.strip()] = value.strip().strip('"').strip("'")
                    logger.debug(f"解析到的字段: {fields}")
                    
                    # 优先检查 IMPLEMENTOR 字段
                    if 'implementor' in fields:
                        implementor = fields['implementor']
                        logger.debug(f"IMPLEMENTOR字段值: {implementor}")
                        
                        if 'temurin' in implementor or 'eclipse' in implementor:
                            return 'Temurin'
                        elif 'corretto' in implementor or 'amazon' in implementor:
                            return 'Corretto'
                        elif 'zulu' in implementor or 'azul' in implementor:
                            return 'Zulu'
                        elif 'microsoft' in implementor:
                            return 'Microsoft'
                        elif 'openjdk' in implementor:
                            return 'OpenJDK'
                        # 如果是 Oracle Corporation，需要进一步判断
                        elif 'oracle' in implementor:
                            # 检查是否存在商业版特有的字段
                            if any(key for key in fields.keys() if 'oracle' in key and key != 'implementor'):
                                return 'Oracle'
                            # 否则认为是 OpenJDK 的官方构建版本
                            return 'OpenJDK'
                    
                    # 如果没有找到 IMPLEMENTOR 或无法确定，检查整个文件内容
                    if 'temurin' in content or 'eclipse' in content:
                        return 'Temurin'
                    elif 'corretto' in content or 'amazon' in content:
                        return 'Corretto'
                    elif 'zulu' in content or 'azul' in content:
                        return 'Zulu'
                    elif 'microsoft' in content:
                        return 'Microsoft'
            
            # 如果无法从 release 文件确定，检查路径名
            path_lower = jdk_path.lower()
            if 'temurin' in path_lower or 'eclipse' in path_lower:
                return 'Temurin'
            elif 'corretto' in path_lower or 'amazon' in path_lower:
                return 'Corretto'
            elif 'zulu' in path_lower or 'azul' in path_lower:
                return 'Zulu'
            elif 'microsoft' in path_lower:
                return 'Microsoft'
            elif 'openjdk' in path_lower:
                return 'OpenJDK'
            
            # 如果是从 jdk.java.net 下载的，默认为 OpenJDK
            if hasattr(self, 'vendor') and self.vendor == "OpenJDK":
                return 'OpenJDK'
            
            return '未知'
        except Exception as e:
            logger.error(f"获取JDK发行商信息失败: {str(e)}")
            return '未知'

    def start_download(self):
        """开始下载"""
        if self.is_downloading:
            return
            
        if self.version_combo.currentIndex() < 0:
            QMessageBox.warning(self, "警告", "请先选择要下载的JDK版本")
            return
        
        # 如果存在旧的下载线程，确保它已经停止并清理
        if hasattr(self, 'download_thread') and self.download_thread:
            try:
                # 断开所有信号连接
                self.download_thread.cleanup_complete.disconnect()
                self.download_thread.progress.disconnect()
                self.download_thread.finished.disconnect()
            except:
                pass
            
            # 等待线程完成并删除
            if self.download_thread.isRunning():
                self.download_thread.cancel()
                self.download_thread.wait()
            self.download_thread.deleteLater()
            self.download_thread = None
        
        # 重置进度对话框
        if self.progress_dialog:
            self.progress_dialog.deleteLater()
            self.progress_dialog = None
        
        self.vendor = self.vendor_combo.currentText()
        self.version = self.version_combo.currentData()
        self.target_dir = self.config.get('jdk_store_path')
        
        # 确保目标目录存在
        os.makedirs(self.target_dir, exist_ok=True)
        
        # 显示进度对话框
        self.show_progress_dialog("正在下载")
        
        # 设置下载状态
        self.is_downloading = True
        
        # 创建并启动下载线程
        self.download_thread = DownloadThread(self.downloader, self.vendor, self.version, self.target_dir)
        self.download_thread.progress.connect(self.update_download_progress)
        self.download_thread.finished.connect(self.on_download_complete)
        self.download_thread.start()

    def on_vendor_changed(self, vendor):
        """处理发行版变更"""
        self.refresh_versions()

    def on_version_changed(self, version):
        """处理版本变更"""
        if version:
            version_number = version.replace('JDK ', '')
            info = self.downloader.get_version_info(self.vendor_combo.currentText(), version_number)
            if info:
                # 更新版本信息
                self.version_info_label.setText(f"""
                    <style>
                        .content-section {{
                            color: #3c4043;
                            line-height: 1.6;
                            text-align: justify;
                            margin: 15px 0;
                        }}
                        .link-section {{
                            margin-top: 25px;
                            padding-top: 15px;
                            border-top: 1px solid #E0E0E0;
                        }}
                        .link-item {{
                            margin: 12px 0;
                            display: flex;
                            align-items: center;
                            transition: transform 0.2s;
                        }}
                        .link-item:hover {{
                            transform: translateX(5px);
                        }}
                        .link-icon {{
                            margin-right: 12px;
                            color: #1a73e8;
                            font-size: 18px;
                        }}
                        .link-text {{
                            flex: 1;
                            color: #1a73e8;
                        }}
                        a {{
                            color: #1a73e8;
                            text-decoration: none;
                            display: block;
                            width: 100%;
                        }}
                        a:hover {{
                            text-decoration: none;
                        }}
                        .section-title {{
                            color: #1a73e8;
                            font-size: 14px;
                            font-weight: bold;
                            margin: 20px 0 10px 0;
                            display: flex;
                            align-items: center;
                        }}
                        .section-title::before {{
                            content: "✦";
                            margin-right: 8px;
                            color: #1a73e8;
                        }}
                    </style>
                    <div class='content-section'>
                        {info}
                    </div>
                    <div class='link-section'>
                        <div class='section-title'>相关资源</div>
                        <div class='link-item'>
                            <span class='link-icon'>📚</span>
                            <a href='https://docs.oracle.com/en/java/javase/{version_number}/docs/api/' target='_blank'>
                                <span class='link-text'>Java {version_number} API 文档</span>
                            </a>
                        </div>
                        <div class='link-item'>
                            <span class='link-icon'>📖</span>
                            <a href='https://docs.oracle.com/en/java/javase/{version_number}/specs/' target='_blank'>
                                <span class='link-text'>Java {version_number} 语言规范</span>
                            </a>
                        </div>
                    </div>
                """)
            else:
                self.version_info_label.setText("""
                    <div style='color: #666666; font-style: italic; padding: 20px 0;'>
                        暂无版本信息
                    </div>
                """)
        else:
            self.version_info_label.setText("")

    def refresh_versions(self):
        """刷新版本列表"""
        self.version_combo.clear()
        vendor = self.vendor_combo.currentText()
        versions = self.downloader.get_available_versions(vendor)
        for version in versions:
            self.version_combo.addItem(f"JDK {version}", version)

    def update_settings(self):
        """更新设置"""
        pass 

class DownloadThread(QThread):
    """下载线程"""
    progress = pyqtSignal(int, int)  # 当前大小，总大小
    finished = pyqtSignal(bool, str)  # 成功标志，消息
    cleanup_complete = pyqtSignal()  # 清理完成信号
    
    def __init__(self, downloader, vendor, version, target_dir):
        super().__init__()
        self.downloader = downloader
        self.vendor = vendor
        self.version = version
        self.target_dir = target_dir
        self.is_cancelled = False
        self.current_file = None  # 当前正在下载的文件路径
        self.file_handle = None  # 文件句柄
        self.response = None  # 响应对象
        self.download_success = False  # 下载是否成功
        self.is_cleaning = False  # 是否正在清理
        
    def run(self):
        """执行下载任务"""
        try:
            # 获取下载链接
            download_url = self.downloader._get_download_url(self.vendor, self.version)
            if not download_url:
                self.finished.emit(False, "无法获取下载链接，请尝试手动下载")
                return

            # 设置下载文件路径
            self.current_file = os.path.join(self.target_dir, f"jdk-{self.version}.zip")
            
            # 创建下载请求
            self.response = requests.get(download_url, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }, 
                stream=True,
                timeout=30
            )
            if not self.response or self.response.status_code != 200:
                self.finished.emit(False, "创建下载请求失败，请检查网络连接")
                return
                
            # 获取文件大小
            total_size = int(self.response.headers.get('content-length', 0))
            block_size = 1024 * 1024  # 1MB
            current_size = 0
            
            # 开始下载
            self.file_handle = open(self.current_file, 'wb')
            for data in self.response.iter_content(block_size):
                if self.is_cancelled:
                    return
                    
                if data:
                    current_size += len(data)
                    self.file_handle.write(data)
                    self.progress.emit(current_size, total_size)
            
            # 关闭文件
            self.file_handle.close()
            self.file_handle = None
            
            # 检查文件是否下载完整
            if os.path.exists(self.current_file) and os.path.getsize(self.current_file) == total_size:
                self.download_success = True
                self.finished.emit(True, "下载完成")
            else:
                self.finished.emit(False, "下载文件不完整，请重试")
                
        except Exception as e:
            logger.error(f"下载失败: {str(e)}")
            self.finished.emit(False, f"下载失败: {str(e)}")
            
        finally:
            self.close_handles()
            if not self.download_success and self.current_file and os.path.exists(self.current_file):
                try:
                    os.remove(self.current_file)
                except Exception as e:
                    logger.error(f"清理未完成的下载文件失败: {str(e)}")

    def cancel(self):
        """取消下载"""
        if self.is_cancelled:  # 如果已经取消，直接返回
            return
        self.is_cancelled = True
        self.start_cleanup()  # 开始清理
        
    def start_cleanup(self):
        """开始清理过程"""
        if self.is_cleaning:  # 如果已经在清理中，直接返回
            return
            
        self.is_cleaning = True
        try:
            # 先关闭句柄
            self.close_handles()
            # 删除文件
            if self.current_file and os.path.exists(self.current_file):
                try:
                    os.remove(self.current_file)
                    logger.info(f"成功删除文件: {self.current_file}")
                except Exception as e:
                    logger.error(f"删除文件失败: {str(e)}")
            # 发送清理完成信号
            self.cleanup_complete.emit()
        except Exception as e:
            logger.error(f"清理资源失败: {str(e)}")
            self.cleanup_complete.emit()
        finally:
            # 确保线程能够正常退出
            self.quit()
            self.wait()
            
    def close_handles(self):
        """关闭文件句柄和响应对象"""
        try:
            # 关闭文件句柄
            if self.file_handle:
                try:
                    self.file_handle.close()
                except Exception as e:
                    logger.error(f"关闭文件句柄失败: {str(e)}")
                self.file_handle = None
            
            # 关闭响应对象
            if self.response:
                try:
                    self.response.close()
                except Exception as e:
                    logger.error(f"关闭响应对象失败: {str(e)}")
                self.response = None
                
        except Exception as e:
            logger.error(f"关闭句柄失败: {str(e)}")
            
    def cancel(self):
        """取消下载"""
        if self.is_cancelled:  # 如果已经取消，直接返回
            return
        self.is_cancelled = True
        self.start_cleanup()  # 开始清理

class InstallThread(QThread):
    """安装线程"""
    progress = pyqtSignal(int, int)  # 当前文件数，总文件数
    finished = pyqtSignal(bool, str, str, str)  # 成功标志，消息，安装时间，导入时间
    
    def __init__(self, zip_path, target_dir):
        super().__init__()
        self.zip_path = zip_path
        self.target_dir = target_dir
        self.is_cancelled = False
        
    def run(self):
        try:
            start_time = QDateTime.currentDateTime()
            
            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                # 获取所有文件列表
                file_list = zip_ref.namelist()
                total_files = len(file_list)
                
                # 获取根目录名称
                root_dir = file_list[0].split('/')[0]
                
                # 解压所有文件
                for index, member in enumerate(file_list, 1):
                    if self.is_cancelled:
                        self.finished.emit(False, "安装已取消", "", "")
                        return
                    
                    zip_ref.extract(member, self.target_dir)
                    self.progress.emit(index, total_files)
            
            # 计算安装时间
            install_time = start_time.msecsTo(QDateTime.currentDateTime()) / 1000.0
            import_time = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            
            # 删除zip文件
            os.remove(self.zip_path)
            
            # 重命名文件夹为标准格式
            version = os.path.basename(self.zip_path).replace("jdk-", "").replace(".zip", "")
            old_path = os.path.join(self.target_dir, root_dir)
            new_path = os.path.join(self.target_dir, f"jdk-{version}")
            
            # 如果目标目录已存在，先删除
            if os.path.exists(new_path):
                shutil.rmtree(new_path, ignore_errors=True)
            
            # 重命名目录
            try:
                os.rename(old_path, new_path)
            except Exception as e:
                logger.error(f"重命名目录失败: {str(e)}")
                # 如果重命名失败，尝试使用复制的方式
                shutil.copytree(old_path, new_path)
                shutil.rmtree(old_path, ignore_errors=True)
            
            self.finished.emit(True, "安装完成", f"{install_time:.1f}秒", import_time)
        except Exception as e:
            self.finished.emit(False, str(e), "", "")
            
    def cancel(self):
        self.is_cancelled = True 