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
        title_label = QLabel("JDK 安装确认")
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
            self.detail_label.setText("此版本需要从 OpenJDK 官网手动下载。点击\"手动下载\"前往下载页面。")
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
        self.progress_dialog.manual_download_button.hide()
        self.progress_dialog.show()

    def cancel_operation(self):
        """取消当前操作"""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.cancel()
        
        if self.progress_dialog:
            self.progress_dialog.reject()

    def update_download_progress(self, current, total):
        """更新下载进度"""
        if self.progress_dialog and not self.progress_dialog.isHidden():
            self.progress_dialog.set_progress(current, total, "下载")

    def update_install_progress(self, current, total):
        """更新安装进度"""
        if self.progress_dialog and not self.progress_dialog.isHidden():
            self.progress_dialog.set_progress(current, total, "安装")

    def on_download_complete(self, success, message):
        """下载完成处理"""
        # 重置下载状态
        self.is_downloading = False
        
        if success:
            version = self.version_combo.currentData()
            target_dir = self.config.get('jdk_store_path')
            zip_path = os.path.join(target_dir, f"jdk-{version}.zip")
            jdk_path = os.path.join(target_dir, f"jdk-{version}")
            
            # 设置下载完成状态
            if self.progress_dialog:
                self.progress_dialog.set_complete(True, is_download=True)
                self.progress_dialog.accept()
            
            # 显示确认对话框
            confirm_dialog = ConfirmDialog(zip_path, self)
            if confirm_dialog.exec() == QDialog.DialogCode.Accepted:
                # 显示安装进度对话框
                self.show_progress_dialog("正在安装")
                
                # 创建并启动安装线程
                self.install_thread = InstallThread(zip_path, target_dir)
                self.install_thread.progress.connect(self.update_install_progress)
                self.install_thread.finished.connect(self.on_install_complete)
                self.install_thread.start()
            else:
                # 用户取消安装，删除下载的文件
                try:
                    os.remove(zip_path)
                except Exception as e:
                    logger.error(f"删除文件失败: {str(e)}")
        else:
            if self.progress_dialog:
                # 根据错误类型提供不同的提示
                if "需要登录" in message or "手动下载" in message:
                    self.progress_dialog.show_manual_download_hint(
                        self.vendor_combo.currentText(),
                        self.version_combo.currentData()
                    )
                else:
                    self.progress_dialog.show_error(message)
                    self.progress_dialog.set_complete(False)

    def on_install_complete(self, success, message, install_time, import_time):
        """安装完成处理"""
        if success:
            version = self.version_combo.currentData()
            jdk_path = os.path.join(self.config.get('jdk_store_path'), f"jdk-{version}")
            
            if self.progress_dialog:
                self.progress_dialog.set_complete(True, is_download=False)
            
            # 发送下载完成信号，包含安装时间和导入时间
            self.jdk_downloaded.emit(str(version), jdk_path, install_time, import_time)
        else:
            if self.progress_dialog:
                self.progress_dialog.set_complete(False)
            QMessageBox.warning(self, '错误', f'安装失败: {message}')

    def start_download(self):
        """开始下载"""
        if self.is_downloading:
            return
            
        if self.version_combo.currentIndex() < 0:
            QMessageBox.warning(self, "警告", "请先选择要下载的JDK版本")
            return
        
        vendor = self.vendor_combo.currentText()
        version = self.version_combo.currentData()
        target_dir = self.config.get('jdk_store_path')
        
        # 确保目标目录存在
        os.makedirs(target_dir, exist_ok=True)
        
        # 显示进度对话框
        self.show_progress_dialog("正在下载")
        
        # 设置下载状态
        self.is_downloading = True
        
        # 创建并启动下载线程
        self.download_thread = DownloadThread(self.downloader, vendor, version, target_dir)
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
    
    def __init__(self, downloader, vendor, version, target_dir):
        super().__init__()
        self.downloader = downloader
        self.vendor = vendor
        self.version = version
        self.target_dir = target_dir
        self.is_cancelled = False
        
    def run(self):
        try:
            success, message = self.downloader.download_jdk(
                self.vendor, 
                self.version, 
                self.target_dir,
                progress_callback=self.progress.emit
            )
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, str(e))
            
    def cancel(self):
        self.is_cancelled = True

class InstallThread(QThread):
    """安装线程"""
    progress = pyqtSignal(int, int)  # 当前文件数，总文件数
    finished = pyqtSignal(bool, str, str, str)  # 成功标���，消息，安装时间，导入时间
    
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