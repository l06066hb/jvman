import os
from datetime import datetime
import markdown  # 添加 markdown 库导入
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
    QMessageBox,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon, QFont
from loguru import logger
from utils.i18n_manager import i18n_manager

# 初始化翻译函数
_ = i18n_manager.get_text


def convert_markdown_to_html(markdown_text):
    """将 Markdown 文本转换为 HTML"""
    try:
        # 配置 markdown 转换器
        md = markdown.Markdown(
            extensions=[
                'markdown.extensions.extra',  # 包含表格、代码块等扩展功能
                'markdown.extensions.nl2br',  # 将换行符转换为 <br>
                'markdown.extensions.sane_lists',  # 更好的列表处理
                'markdown.extensions.codehilite'  # 代码高亮
            ]
        )
        
        # 转换 Markdown 为 HTML
        html = md.convert(markdown_text or '')
        
        # 添加基本样式
        styled_html = f"""
        <html>
        <head>
        <style>
            body {{ font-family: system-ui, -apple-system, sans-serif; }}
            h1, h2, h3, h4, h5, h6 {{ color: #333; margin-top: 1em; margin-bottom: 0.5em; }}
            h1 {{ font-size: 1.5em; }}
            h2 {{ font-size: 1.3em; }}
            h3 {{ font-size: 1.1em; }}
            p {{ margin: 0.5em 0; line-height: 1.5; }}
            ul, ol {{ margin: 0.5em 0; padding-left: 2em; }}
            li {{ margin: 0.3em 0; }}
            code {{ background-color: #f5f5f5; padding: 0.2em 0.4em; border-radius: 3px; font-family: monospace; }}
            pre {{ background-color: #f5f5f5; padding: 1em; border-radius: 5px; overflow-x: auto; }}
            pre code {{ background-color: transparent; padding: 0; }}
            blockquote {{ margin: 1em 0; padding-left: 1em; border-left: 4px solid #ddd; color: #666; }}
            table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
            th, td {{ border: 1px solid #ddd; padding: 0.5em; text-align: left; }}
            th {{ background-color: #f5f5f5; }}
            a {{ color: #1a73e8; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            hr {{ border: none; border-top: 1px solid #ddd; margin: 1em 0; }}
        </style>
        </head>
        <body>
        {html}
        </body>
        </html>
        """
        
        return styled_html
    except Exception as e:
        logger.error(f"Markdown 转换失败: {str(e)}")
        return markdown_text  # 如果转换失败，返回原始文本


class UpdateNotificationDialog(QDialog):
    """更新通知对话框"""

    def __init__(self, update_info, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.parent = parent  # 保存父窗口引用
        self.download_path = None
        self.is_downloading = False  # 添加下载状态标志
        self.download_url = update_info.get("download_url")
        self.init_ui()
        
        # 连接信号
        if self.parent and hasattr(self.parent, "update_manager"):
            self.parent.update_manager.download_progress.connect(self.update_progress)
            self.parent.update_manager.download_complete.connect(self.on_download_complete)
            self.parent.update_manager.download_error.connect(self.on_download_error)

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

        # 进度条区域（初始隐藏）
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(10)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: none;
                border-radius: 4px;
                background-color: #E8F0FE;
                height: 8px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1a73e8;
                border-radius: 4px;
            }
            """
        )
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel(_("update.new_version.download.preparing"))
        self.progress_label.setStyleSheet("color: #666666; font-size: 12px;")
        progress_layout.addWidget(self.progress_label)

        self.progress_widget.setLayout(progress_layout)
        self.progress_widget.hide()  # 初始隐藏
        layout.addWidget(self.progress_widget)

        # 内容区域
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(15)

        # 更新说明
        notes_label = QLabel(_("update.dialog.release_notes"))
        notes_label.setStyleSheet("color: #666666; font-size: 14px;")
        content_layout.addWidget(notes_label)

        content_browser = QTextBrowser()
        content_browser.setStyleSheet(
            """
            QTextBrowser {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 10px;
                background-color: white;
                font-size: 13px;
            }
        """
        )
        # 转换并设置 HTML 内容
        release_notes = self.update_info.get("release_notes", "")
        if release_notes:
            html_content = convert_markdown_to_html(release_notes)
            content_browser.setHtml(html_content)
        content_browser.setMinimumHeight(150)
        content_browser.setOpenExternalLinks(True)  # 允许打开外部链接
        content_layout.addWidget(content_browser)

        content_widget.setLayout(content_layout)
        layout.addWidget(content_widget)

        # 底部按钮区域
        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 更新日志链接
        if self.update_info.get("changelog_url"):
            changelog_link = QPushButton(_("update.dialog.buttons.view_changelog"))
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
                    color: #174ea6;
                }
            """
            )
            changelog_link.clicked.connect(self.open_changelog)
            button_layout.addWidget(changelog_link)

        button_layout.addStretch()

        # 取消按钮
        cancel_button = QPushButton(_("update.dialog.buttons.cancel"))
        cancel_button.setStyleSheet(
            """
            QPushButton {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px 16px;
                color: #666666;
                font-size: 13px;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
                border-color: #D0D0D0;
            }
        """
        )
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        # 下载按钮
        self.download_button = QPushButton(_("update.dialog.buttons.download"))
        self.download_button.setStyleSheet(
            """
            QPushButton {
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                color: white;
                font-size: 13px;
                background-color: #1a73e8;
            }
            QPushButton:hover {
                background-color: #174ea6;
            }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #999999;
            }
        """
        )
        self.download_button.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_button)

        button_widget.setLayout(button_layout)
        layout.addWidget(button_widget)

        self.setLayout(layout)

    def update_progress(self, progress):
        """更新下载进度"""
        if not self.progress_widget.isVisible():
            self.progress_widget.show()
            self.download_button.setEnabled(False)

        self.progress_bar.setValue(progress)
        self.progress_label.setText(_("update.new_version.download.progress").format(percent=progress))
        
        # 确保UI更新
        QApplication.processEvents()

    def start_download(self):
        """开始下载"""
        if self.is_downloading:  # 防止重复点击
            return

        try:
            self.is_downloading = True
            self.progress_widget.show()
            self.download_button.setEnabled(False)
            self.progress_bar.setValue(0)
            self.progress_label.setText(_("update.new_version.download.preparing"))

            # 开始下载
            if self.parent and hasattr(self.parent, "update_manager"):
                save_dir = self.parent.update_manager.get_update_save_path()
                save_path = os.path.join(save_dir, f"update_v{self.update_info['version']}.zip")

                # 直接调用下载方法
                QTimer.singleShot(0, lambda: self.parent.update_manager.download_update(self.download_url, save_path))
        except Exception as e:
            self.is_downloading = False
            self.on_download_error(str(e))

    def on_download_complete(self, file_path):
        """下载完成处理"""
        try:
            self.is_downloading = False
            self.progress_label.setText(_("update.dialog.download.complete"))
            self.download_path = file_path

            # 显示下载完成和安装选项对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(_("update.dialog.download.title"))
            msg_box.setText(_("update.dialog.download.complete"))
            msg_box.setInformativeText(_("update.dialog.download.complete_info").format(path=file_path))
            
            # 添加按钮
            install_btn = msg_box.addButton(_("update.dialog.download.install_now"), QMessageBox.ButtonRole.AcceptRole)
            open_folder_btn = msg_box.addButton(_("update.dialog.download.open_folder"), QMessageBox.ButtonRole.ActionRole)
            later_btn = msg_box.addButton(_("update.dialog.buttons.later"), QMessageBox.ButtonRole.RejectRole)
            
            msg_box.setDefaultButton(install_btn)
            msg_box.exec()

            clicked_button = msg_box.clickedButton()
            
            if clicked_button == install_btn:
                self.start_install(file_path)
            elif clicked_button == open_folder_btn:
                try:
                    os.startfile(os.path.dirname(file_path))
                except:
                    pass
                self._disconnect_signals()
                self.accept()
            else:  # later_btn
                self._disconnect_signals()
                self.accept()

        except Exception as e:
            logger.error(f"处理下载完成事件失败: {str(e)}")
            self.on_download_error(str(e))

    def start_install(self, file_path):
        """开始安装更新"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(_("update.dialog.install.error.file_not_found").format(path=file_path))

            import sys
            import subprocess

            # 根据不同平台执行安装
            if sys.platform == "win32":
                if file_path.endswith(".exe"):
                    # 如果是安装包，直接执行
                    try:
                        subprocess.Popen([file_path])
                        self._disconnect_signals()
                        self.accept()
                                # 通知用户程序将退出
                        QTimer.singleShot(500, lambda: QApplication.quit())
                    except PermissionError:
                        raise PermissionError(_("update.dialog.install.error.no_permission"))
                    except Exception as e:
                        raise Exception(_("update.error.install_failed").format(error=str(e)))
                        
                elif file_path.endswith(".zip"):
                    # 如果是便携版ZIP，提示解压路径
                    install_dir = os.path.dirname(os.path.dirname(file_path))
                    reply = QMessageBox.information(
                        self,
                        _("update.dialog.install.title"),
                        _("update.dialog.install.portable_info").format(path=install_dir),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        # 打开文件所在目录
                        os.startfile(os.path.dirname(file_path))
                        self._disconnect_signals()
                        self.accept()
                        # 通知用户程序将退出
                        QTimer.singleShot(500, lambda: QApplication.quit())

            elif sys.platform == "darwin":  # macOS
                if file_path.endswith(".dmg"):
                    subprocess.Popen(["open", file_path])
                    self._disconnect_signals()
                    self.accept()
                    QTimer.singleShot(500, lambda: QApplication.quit())

            else:  # Linux
                if file_path.endswith(".deb"):
                    subprocess.Popen(["pkexec", "apt", "install", file_path])
                    self._disconnect_signals()
                    self.accept()
                    QTimer.singleShot(500, lambda: QApplication.quit())
                elif file_path.endswith(".rpm"):
                    subprocess.Popen(["pkexec", "rpm", "-i", file_path])
                    self._disconnect_signals()
                    self.accept()
                    QTimer.singleShot(500, lambda: QApplication.quit())
                elif file_path.endswith(".AppImage"):
                    # 设置可执行权限
                    os.chmod(file_path, 0o755)
                    subprocess.Popen([file_path])
                    self._disconnect_signals()
                    self.accept()
                    QTimer.singleShot(500, lambda: QApplication.quit())

        except FileNotFoundError as e:
            logger.error(f"安装文件不存在: {str(e)}")
            QMessageBox.warning(
                self,
                _("update.dialog.install.error.title"),
                str(e)
            )
        except PermissionError as e:
            logger.error(f"安装权限不足: {str(e)}")
            QMessageBox.warning(
                self,
                _("update.dialog.install.error.title"),
                str(e)
            )
        except Exception as e:
            logger.error(f"启动安装失败: {str(e)}")
            QMessageBox.warning(
                self,
                _("update.dialog.install.error.title"),
                _("update.dialog.install.error.message").format(error=str(e))
            )
            # 打开下载目录
            try:
                os.startfile(os.path.dirname(file_path))
            except:
                pass

    def on_download_error(self, error):
        """下载错误处理"""
        self.is_downloading = False
        self.progress_label.setText(_("update.new_version.download.failed").format(error=error))
        self.download_button.setEnabled(True)
        
        # 断开信号连接
        self._disconnect_signals()

        QMessageBox.warning(
            self,
            _("dialog.error.title"),
            _("update.new_version.download.failed").format(error=error)
        )

    def _disconnect_signals(self):
        """断开所有信号连接并重置状态"""
        if self.parent and hasattr(self.parent, "update_manager"):
            try:
                self.parent.update_manager.download_progress.disconnect(self.update_progress)
                self.parent.update_manager.download_complete.disconnect(self.on_download_complete)
                self.parent.update_manager.download_error.disconnect(self.on_download_error)
                
                # 取消下载
                if self.is_downloading:
                    self.parent.update_manager.cancel_download()
                
                # 重置更新管理器状态
                self.parent.update_manager.reset_check_state()
            except:
                pass
            
            # 重置设置页面的更新按钮状态
            if hasattr(self.parent, "settings_tab"):
                self.parent.settings_tab._reset_update_button()
            
            # 重置下载状态
            self.is_downloading = False
            self.download_button.setEnabled(True)
            self.progress_widget.hide()
            self.progress_bar.setValue(0)
            self.progress_label.setText(_("update.new_version.download.preparing"))

    def open_changelog(self):
        """打开更新日志链接"""
        if self.update_info.get("changelog_url"):
            QDesktopServices.openUrl(QUrl(self.update_info["changelog_url"]))

    def closeEvent(self, event):
        """关闭事件处理"""
        if self.is_downloading:
            # 如果正在下载，询问用户是否确定要取消下载
            reply = QMessageBox.question(
                self,
                _("update.dialog.cancel.title"),
                _("update.dialog.cancel.download_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._disconnect_signals()
                event.accept()
            else:
                event.ignore()
        else:
            self._disconnect_signals()
            event.accept()

    def reject(self):
        """处理取消操作"""
        if self.is_downloading:
            # 如果正在下载，显示确认对话框
            reply = QMessageBox.question(
                self,
                _("update.dialog.cancel.title"),
                _("update.dialog.cancel.download_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._disconnect_signals()
                super().reject()
        else:
            self._disconnect_signals()
            super().reject()
