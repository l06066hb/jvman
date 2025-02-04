import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QHBoxLayout,
    QWidget,
    QScrollArea,
    QTextBrowser,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon, QFont
from loguru import logger
from utils.i18n_manager import i18n_manager

# 初始化翻译函数
_ = i18n_manager.get_text


class UpdateNotificationDialog(QDialog):
    """更新通知对话框"""

    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.parent = parent
        self.download_path = None
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(_("update.dialog.title"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 头部区域
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # 版本信息
        version_widget = QWidget()
        version_layout = QVBoxLayout()
        version_layout.setSpacing(5)

        new_version_label = QLabel(_("update.dialog.new_version"))
        new_version_label.setStyleSheet("color: #666666; font-size: 14px;")
        version_layout.addWidget(new_version_label)

        version_number = QLabel(f"v{self.update_info['version']}")
        version_number.setStyleSheet(
            """
            color: #1a73e8;
            font-size: 24px;
            font-weight: bold;
        """
        )
        version_layout.addWidget(version_number)

        version_widget.setLayout(version_layout)
        header_layout.addWidget(version_widget)

        # 文件信息
        file_info_widget = QWidget()
        file_info_layout = QVBoxLayout()
        file_info_layout.setSpacing(5)

        package_type = QLabel(self.update_info.get("package_type", ""))
        package_type.setStyleSheet("color: #666666; font-size: 12px;")
        file_info_layout.addWidget(package_type)

        if self.update_info.get("file_size"):
            size_mb = self.update_info["file_size"] / 1024 / 1024
            file_size = QLabel(f"{size_mb:.1f} MB")
            file_size.setStyleSheet("color: #666666; font-size: 12px;")
            file_info_layout.addWidget(file_size)

        file_info_widget.setLayout(file_info_layout)
        header_layout.addWidget(file_info_widget, alignment=Qt.AlignmentFlag.AlignRight)

        header.setLayout(header_layout)
        layout.addWidget(header)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #E0E0E0;")
        layout.addWidget(line)

        # 更新内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(10)

        content_title = QLabel(_("update.dialog.whats_new"))
        content_title.setStyleSheet(
            """
            color: #202124;
            font-size: 16px;
            font-weight: bold;
            padding-bottom: 10px;
        """
        )
        content_layout.addWidget(content_title)

        # 使用QTextBrowser显示更新内容，支持富文本
        content_browser = QTextBrowser()
        content_browser.setOpenExternalLinks(True)
        content_browser.setStyleSheet(
            """
            QTextBrowser {
                border: none;
                background-color: transparent;
                color: #202124;
                font-size: 13px;
            }
        """
        )
        content_browser.setHtml(self.update_info.get("release_notes", ""))
        content_browser.setMinimumHeight(150)
        content_layout.addWidget(content_browser)

        content_widget.setLayout(content_layout)
        layout.addWidget(content_widget)

        # 底部按钮区域
        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 更新日志链接
        if self.update_info.get("changelog_url"):
            changelog_link = QPushButton(_("update.dialog.view_changelog"))
            changelog_link.setStyleSheet(
                """
                QPushButton {
                    border: none;
                    color: #1a73e8;
                    font-size: 13px;
                    text-decoration: underline;
                    padding: 5px;
                }
                QPushButton:hover {
                    color: #1557b0;
                }
            """
            )
            changelog_link.setCursor(Qt.CursorShape.PointingHandCursor)
            changelog_link.clicked.connect(
                lambda: QDesktopServices.openUrl(
                    QUrl(self.update_info["changelog_url"])
                )
            )
            button_layout.addWidget(
                changelog_link, alignment=Qt.AlignmentFlag.AlignLeft
            )

        button_layout.addStretch()

        # 备选包下载链接
        if self.update_info.get("alternative_package"):
            alt_package = self.update_info["alternative_package"]
            alt_link = QPushButton(
                _("update.dialog.download_alternative").format(type=alt_package["type"])
            )
            alt_link.setStyleSheet(
                """
                QPushButton {
                    border: 1px solid #1a73e8;
                    border-radius: 4px;
                    color: #1a73e8;
                    font-size: 13px;
                    padding: 8px 16px;
                    background: white;
                }
                QPushButton:hover {
                    background: #F0F7FF;
                }
            """
            )
            alt_link.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(alt_package["url"]))
            )
            button_layout.addWidget(alt_link)

        # 稍后提醒按钮
        remind_later = QPushButton(_("update.dialog.remind_later"))
        remind_later.setStyleSheet(
            """
            QPushButton {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                color: #666666;
                font-size: 13px;
                padding: 8px 16px;
                background: white;
            }
            QPushButton:hover {
                background: #F5F5F5;
            }
        """
        )
        remind_later.clicked.connect(self.reject)
        button_layout.addWidget(remind_later)

        # 立即更新按钮
        self.update_button = QPushButton(_("update.dialog.update_now"))
        self.update_button.setStyleSheet(
            """
            QPushButton {
                border: none;
                border-radius: 4px;
                color: white;
                font-size: 13px;
                padding: 8px 16px;
                background: #1a73e8;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1557b0;
            }
            QPushButton:disabled {
                background: #E0E0E0;
                color: #999999;
            }
        """
        )
        self.update_button.clicked.connect(self.start_update)
        button_layout.addWidget(self.update_button)

        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget)

        # 进度条（初始隐藏）
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(5)

        self.progress_label = QLabel(_("update.dialog.downloading"))
        self.progress_label.setStyleSheet("color: #666666; font-size: 12px;")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(
            """
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
        """
        )
        progress_layout.addWidget(self.progress_bar)

        self.speed_label = QLabel()
        self.speed_label.setStyleSheet("color: #666666; font-size: 12px;")
        progress_layout.addWidget(self.speed_label)

        self.progress_widget.setLayout(progress_layout)
        self.progress_widget.hide()
        layout.addWidget(self.progress_widget)

        self.setLayout(layout)

        # 设置动画定时器
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_progress_gradient)
        self.gradient_offset = 0.0

        # 下载速度计算相关
        self.last_progress = 0
        self.last_time = datetime.now()
        self.speed_timer = QTimer(self)
        self.speed_timer.timeout.connect(self.update_speed)

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

    def update_speed(self):
        """更新下载速度显示"""
        current_progress = self.progress_bar.value()
        current_time = datetime.now()
        time_diff = (current_time - self.last_time).total_seconds()
        if time_diff > 0:
            bytes_per_second = (
                (current_progress - self.last_progress) * 1024 * 1024 / 100 / time_diff
            )
            if bytes_per_second >= 1024 * 1024:
                speed_text = f"{bytes_per_second/1024/1024:.1f} MB/s"
            else:
                speed_text = f"{bytes_per_second/1024:.1f} KB/s"

            # 计算剩余时间
            if bytes_per_second > 0:
                remaining_percentage = 100 - current_progress
                remaining_bytes = (
                    remaining_percentage * self.update_info["file_size"] / 100
                )
                remaining_seconds = remaining_bytes / bytes_per_second
                if remaining_seconds < 60:
                    time_text = f"{int(remaining_seconds)} {_('update.dialog.seconds')}"
                else:
                    time_text = (
                        f"{int(remaining_seconds/60)} {_('update.dialog.minutes')}"
                    )

                self.speed_label.setText(
                    _("update.dialog.download_status").format(
                        speed=speed_text, time=time_text
                    )
                )

            self.last_progress = current_progress
            self.last_time = current_time

    def start_update(self):
        """开始更新"""
        try:
            # 禁用按钮
            self.update_button.setEnabled(False)

            # 显示进度区域
            self.progress_widget.show()

            # 获取下载URL
            download_url = self.update_info.get("download_url")
            if not download_url:
                raise ValueError(_("update.error.no_download_url"))

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

            # 启动进度条动画
            self.animation_timer.start(50)

            # 启动速度计算定时器
            self.speed_timer.start(1000)

            # 开始下载
            self.parent.update_manager.download_update(download_url, self.download_path)

        except Exception as e:
            logger.error(f"开始更新失败: {str(e)}")
            self.download_error(str(e))

    def update_progress(self, progress):
        """更新进度"""
        self.progress_bar.setValue(progress)

    def download_finished(self, file_path):
        """下载完成"""
        # 停止动画和速度计算
        self.animation_timer.stop()
        self.speed_timer.stop()

        # 更新UI状态
        self.progress_label.setText(_("update.dialog.download_complete"))
        self.progress_label.setStyleSheet("color: #34A853; font-size: 12px;")
        self.speed_label.setText(_("update.dialog.preparing_install"))

        # 设置进度条完成状态
        self.progress_bar.setStyleSheet(
            """
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
        """
        )

        logger.info(f"更新文件下载完成: {file_path}")

        # 准备安装
        self.prepare_install(file_path)

    def prepare_install(self, file_path):
        """准备安装"""
        try:
            # 验证文件完整性
            if self.update_info.get("sha256"):
                import hashlib

                with open(file_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                if file_hash != self.update_info["sha256"]:
                    raise ValueError(_("update.error.invalid_checksum"))

            # 根据不同平台准备安装
            import sys

            if sys.platform == "win32":
                # Windows
                if file_path.endswith(".exe"):
                    import subprocess

                    subprocess.Popen([file_path])
                    self.accept()
                elif file_path.endswith(".zip"):
                    # TODO: 实现ZIP文件的安装逻辑
                    pass
            elif sys.platform == "darwin":
                # macOS
                if file_path.endswith(".dmg"):
                    import subprocess

                    subprocess.Popen(["open", file_path])
                    self.accept()
            else:
                # Linux
                if file_path.endswith(".deb"):
                    import subprocess

                    subprocess.Popen(["pkexec", "apt", "install", file_path])
                    self.accept()
                elif file_path.endswith(".rpm"):
                    import subprocess

                    subprocess.Popen(["pkexec", "rpm", "-i", file_path])
                    self.accept()
                elif file_path.endswith(".AppImage"):
                    import os

                    os.chmod(file_path, 0o755)
                    import subprocess

                    subprocess.Popen([file_path])
                    self.accept()

        except Exception as e:
            logger.error(f"准备安装失败: {str(e)}")
            self.download_error(str(e))

    def download_error(self, error_msg):
        """下载错误处理"""
        # 停止动画和速度计算
        self.animation_timer.stop()
        self.speed_timer.stop()

        # 更新UI状态
        self.progress_label.setText(_("update.dialog.download_failed"))
        self.progress_label.setStyleSheet("color: #EA4335; font-size: 12px;")
        self.speed_label.setText(str(error_msg))

        # 设置进度条错误状态
        self.progress_bar.setStyleSheet(
            """
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
        """
        )

        # 添加重试和手动下载选项
        button_layout = self.findChild(QHBoxLayout)
        if button_layout:
            # 清除现有按钮
            for i in reversed(range(button_layout.count())):
                button_layout.itemAt(i).widget().setParent(None)

            # 添加手动下载按钮
            manual_download = QPushButton(_("update.dialog.manual_download"))
            manual_download.setStyleSheet(
                """
                QPushButton {
                    border: 1px solid #1a73e8;
                    border-radius: 4px;
                    color: #1a73e8;
                    font-size: 13px;
                    padding: 8px 16px;
                    background: white;
                }
                QPushButton:hover {
                    background: #F0F7FF;
                }
            """
            )
            manual_download.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(self.update_info["download_url"]))
            )
            button_layout.addWidget(manual_download)

            # 添加重试按钮
            retry_button = QPushButton(_("update.dialog.retry"))
            retry_button.setStyleSheet(
                """
                QPushButton {
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-size: 13px;
                    padding: 8px 16px;
                    background: #1a73e8;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #1557b0;
                }
            """
            )
            retry_button.clicked.connect(self.start_update)
            button_layout.addWidget(retry_button)

    def closeEvent(self, event):
        """关闭事件处理"""
        self.animation_timer.stop()
        self.speed_timer.stop()
        event.accept()
