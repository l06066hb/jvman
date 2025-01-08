import os
import re
import subprocess
import shutil
from loguru import logger
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QDialog, QDialogButtonBox, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QThread
from PyQt6.QtGui import QIcon, QFont, QPixmap, QColor, QPainter
from src.utils.system_utils import create_symlink, set_environment_variable, update_path_variable
from src.utils.platform_manager import platform_manager
from src.utils.i18n_manager import i18n_manager

# 初始化i18n管理器
_ = i18n_manager.get_text

class JDKLoaderThread(QThread):
    """JDK加载线程"""
    finished = pyqtSignal(dict)  # 发送加载完成的JDK信息
    progress = pyqtSignal(str)   # 发送加载进度信息

    def __init__(self, jdk_path, java_path):
        super().__init__()
        self.jdk_path = jdk_path
        self.java_path = java_path

    def run(self):
        try:
            # 设置进程启动信息
            startupinfo = None
            if platform_manager.is_windows:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            else:
                # 在 Unix 系统上，使用 DEVNULL 重定向输出
                process_args = {
                    'stdout': subprocess.DEVNULL,
                    'stderr': subprocess.PIPE,
                    'stdin': subprocess.DEVNULL
                }

            result = subprocess.run(
                [self.java_path, '-version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=2,
                startupinfo=startupinfo,
                **({} if platform_manager.is_windows else process_args)
            )
            if result.stderr:
                version_info = result.stderr
                version_match = re.search(r'version "([^"]+)"', version_info)
                detailed_version = version_match.group(1) if version_match else None
                
                version_info_lower = version_info.lower()
                if 'openjdk' in version_info_lower:
                    if 'corretto' in version_info_lower:
                        vendor = "Corretto"
                    elif 'temurin' in version_info_lower or 'adoptium' in version_info_lower:
                        vendor = "Temurin"
                    elif 'zulu' in version_info_lower:
                        vendor = "Zulu"
                    elif 'microsoft' in version_info_lower:
                        vendor = "Microsoft"
                    else:
                        vendor = "OpenJDK"
                elif 'java(tm)' in version_info_lower or 'oracle' in version_info_lower:
                    vendor = "Oracle"
                elif 'graalvm' in version_info_lower:
                    vendor = "GraalVM"
                elif 'semeru' in version_info_lower:
                    vendor = "Semeru"
                else:
                    vendor = _("local.vendor.unknown")
                
                self.finished.emit({
                    'path': self.jdk_path,
                    'detailed_version': detailed_version,
                    'vendor': vendor
                })
            else:
                # 如果没有版本信息，发送基本信息
                self.finished.emit({
                    'path': self.jdk_path,
                    'detailed_version': None,
                    'vendor': _("local.vendor.unknown")
                })
        except Exception as e:
            logger.debug(_("log.error.get_jdk_info_failed").format(path=self.jdk_path, error=str(e)))
            # 发送错误状态的信息
            self.finished.emit({
                'path': self.jdk_path,
                'detailed_version': None,
                'vendor': _("local.vendor.unknown"),
                'error': str(e)
            })

class SystemVersionThread(QThread):
    """环境变量版本检查线程"""
    finished = pyqtSignal(str)

    def run(self):
        try:
            # 设置进程启动信息
            startupinfo = None
            if platform_manager.is_windows:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            else:
                # 在 Unix 系统上，使用 DEVNULL 重定向输出
                process_args = {
                    'stdout': subprocess.DEVNULL,
                    'stderr': subprocess.PIPE,
                    'stdin': subprocess.DEVNULL
                }

            result = subprocess.run(
                ['java', '-version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=2,
                startupinfo=startupinfo,
                **({} if platform_manager.is_windows else process_args)
            )
            if result.stderr:
                self.finished.emit(result.stderr.strip())  # 发送完整的版本信息
            else:
                self.finished.emit(None)
        except FileNotFoundError:
            self.finished.emit(_("local.system_version.not_installed"))
        except Exception as e:
            logger.error(f"{_('log.error.get_system_version_failed')}: {str(e)}")
            self.finished.emit(_("local.system_version.unknown"))

    def update_system_version(self, version):
        """更新环境变量版本显示"""
        if version:
            if version == _("local.system_version.not_installed"):
                self.system_version_label.setProperty("status", "not_installed")
                self.system_version_label.setText(_("local.system_version.not_installed"))
            else:
                self.system_version_label.setProperty("status", "installed")
                self.system_version_label.setText(f"{_('local.system_version.title')}: {version}")
            self.system_version_label.style().unpolish(self.system_version_label)
            self.system_version_label.style().polish(self.system_version_label)
        else:
            self.system_version_label.setProperty("status", "not_installed")
            self.system_version_label.setText(_("local.system_version.not_installed"))
            self.system_version_label.style().unpolish(self.system_version_label)
            self.system_version_label.style().polish(self.system_version_label)

class LocalTab(QWidget):
    """本地管理标签页"""
    
    # 定义信号
    jdk_mapped = pyqtSignal(str, str)  # 版本号, 路径
    version_changed = pyqtSignal()  # 版本变更信号
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.jdk_threads = []  # 保存所有JDK加载线程
        self.jdk_details = {}  # 缓存JDK详细信息
        self.init_ui()
        # 连接语言切换信号
        i18n_manager.language_changed.connect(self._update_texts)
        
    def _update_texts(self):
        """更新界面文本"""
        # 更新当前版本标签
        if hasattr(self, 'current_version_label'):
            current_text = self.current_version_label.text()
            # Check if contains "Not Set"
            if _("local.current_version.not_set") in current_text:
                self.current_version_label.setText(_("local.current_version.not_set"))
            # Check if contains "Current Version"
            elif _("local.current_version.prefix") in current_text:
                # Extract version number part (after colon)
                version = current_text.split(": ", 1)[1] if ": " in current_text else ""
                self.current_version_label.setText(f"{_('local.current_version.prefix')}: {version}")

        # 更新环境变量版本标签
        if hasattr(self, 'system_version_label'):
            text = self.system_version_label.text()
            # Check if contains "Not Installed"
            if _("local.system_version.not_installed") in text:
                self.system_version_label.setText(_("local.system_version.not_installed"))
            # Check if contains "Detecting"
            elif _("local.system_version.detecting") in text:
                self.system_version_label.setText(_("local.system_version.detecting"))
            # If system version info, keep version number but update prefix
            elif _("local.system_version.title") in text:
                version = text.split(": ", 1)[1] if ": " in text else ""
                if version:
                    self.system_version_label.setText(f"{_('local.system_version.title')}: {version}")

        # 更新标题和提示文本
        if hasattr(self, 'title_label'):
            self.title_label.setText(_("local.system_version.title"))
        
        if hasattr(self, 'info_label'):
            self.info_label.setText(_("local.system_version.hint"))
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # 当前版本显示
        version_container = QWidget()
        version_container.setObjectName('version_container')
        version_container.setStyleSheet("""
            QWidget#version_container {
                background-color: #EBF3FE;
                border-radius: 8px;
                border: 1px solid #D0E1F9;
            }
        """)
        
        version_layout = QVBoxLayout(version_container)
        version_layout.setContentsMargins(16, 16, 16, 16)
        version_layout.setSpacing(12)
        
        # 当前应用版本
        current_version_widget = QWidget()
        current_version_widget.setObjectName('current_version_widget')
        current_version_widget.setStyleSheet("""
            QWidget#current_version_widget {
                background-color: rgba(26, 115, 232, 0.08);
                border-radius: 6px;
            }
        """)
        current_version_layout = QHBoxLayout(current_version_widget)
        current_version_layout.setContentsMargins(12, 8, 12, 8)
        current_version_layout.setSpacing(8)
        
        # 图标容器
        icon_container = QWidget()
        icon_container.setStyleSheet("background: transparent;")
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(4)
        
        # 添加Java图标
        version_icon = QLabel()
        version_icon.setStyleSheet("background: transparent;")
        java_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                    'resources', 'icons', 'java-current.png')
        java_pixmap = QPixmap(java_icon_path)
        if not java_pixmap.isNull():
            version_icon.setPixmap(QIcon(java_icon_path).pixmap(QSize(18, 18)))
        icon_layout.addWidget(version_icon)
        
        current_version_layout.addWidget(icon_container)
        
        # 当前应用版本标签
        self.current_version_label = QLabel(_("local.current_version.not_set"))
        self.current_version_label.setObjectName('current_version_label')
        self.current_version_label.setStyleSheet("""
            QLabel#current_version_label {
                color: #1a73e8;
                font-weight: 600;
                font-size: 13px;
                background: transparent;
            }
        """)
        current_version_layout.addWidget(self.current_version_label)
        current_version_layout.addStretch()
        
        # 环境变量版本
        system_version_widget = QWidget()
        system_version_widget.setObjectName('system_version_widget')
        system_version_widget.setStyleSheet("""
            QWidget#system_version_widget {
                background-color: rgba(102, 102, 102, 0.06);
                border-radius: 6px;
            }
        """)
        system_version_layout = QVBoxLayout(system_version_widget)
        system_version_layout.setContentsMargins(12, 10, 12, 10)
        system_version_layout.setSpacing(8)

        # 标题行布局
        title_layout = QHBoxLayout()
        title_layout.setSpacing(6)
        
        # 系统Java图标
        system_icon = QLabel()
        system_icon.setStyleSheet("background: transparent;")
        system_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                      'resources', 'icons', 'java-system.png')
        system_pixmap = QPixmap(system_icon_path)
        if not system_pixmap.isNull():
            system_icon.setPixmap(QIcon(system_icon_path).pixmap(QSize(40, 20)))
        title_layout.addWidget(system_icon)
        
        # 标题和说明
        self.title_label = QLabel(_("local.system_version.title"))
        self.title_label.setStyleSheet("""
            color: #444444;
            font-size: 13px;
            font-weight: 600;
            background: transparent;
            letter-spacing: 0.3px;
        """)
        title_layout.addWidget(self.title_label)
        
        # 添加提示信息
        self.info_label = QLabel(_("local.system_version.hint"))
        self.info_label.setStyleSheet("""
            color: #666666;
            font-size: 12px;
            background: transparent;
        """)
        title_layout.addWidget(self.info_label)
        title_layout.addStretch()
        
        system_version_layout.addLayout(title_layout)

        # 版本信息文本框
        self.system_version_label = QLabel(_("local.system_version.detecting"))
        self.system_version_label.setObjectName('system_version_label')
        self.system_version_label.setWordWrap(True)
        self.system_version_label.setStyleSheet("""
            QLabel#system_version_label {
                color: #444444;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                background-color: rgba(0, 0, 0, 0.03);
                border-radius: 4px;
                padding: 10px 12px;
                line-height: 1.5;
                min-height: 40px;
            }
            QLabel#system_version_label[status="installed"] {
                color: #2E7D32;
            }
            QLabel#system_version_label[status="not_installed"] {
                color: #C62828;
            }
        """)
        system_version_layout.addWidget(self.system_version_label)
        
        # 添加到主布局
        version_layout.addWidget(current_version_widget)
        version_layout.addWidget(system_version_widget)
        
        layout.addWidget(version_container)
        
        # JDK列表
        self.jdk_list = QListWidget()
        self.jdk_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget::item {
                border: 1px solid transparent;
                border-radius: 8px;
                margin: 2px 5px;
            }
            QListWidget::item:selected {
                background-color: #F5F9FF;
                border: 1px solid #90CAF9;
            }
            QListWidget::item:hover:!selected {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
            }
        """)
        layout.addWidget(self.jdk_list)
        
        # 按钮容器
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加本地JDK按钮
        add_button = QPushButton()
        add_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons', 'add.png')))
        add_button.clicked.connect(self.add_local_jdk)
        add_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
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
        """)
        
        # 连接语言变化信号
        i18n_manager.language_changed.connect(lambda lang: add_button.setText(_("local.button.add_local_jdk")))
        add_button.setText(_("local.button.add_local_jdk"))
        
        # 将按钮添加到右侧
        button_layout.addStretch()
        button_layout.addWidget(add_button)
        
        layout.addWidget(button_container)
        
        # 刷新JDK列表
        self.refresh_jdk_list()

    def showEvent(self, event):
        """当标签页显示时触发"""
        super().showEvent(event)
        # 重新加载配置并刷新列表
        self.config.load()
        self.refresh_jdk_list()

    def is_current_version(self, path):
        """检查是否是当前使用的版本"""
        try:
            junction_path = self.config.get('junction_path')
            if os.path.exists(junction_path):
                current_path = os.path.realpath(junction_path)
                return os.path.samefile(current_path, path)
        except Exception as e:
            logger.error(f"检查当前版本失败: {str(e)}")
        return False

    def get_vendor_name(self, path):
        """获取JDK发行版名称"""
        try:
            java_path = os.path.join(path, 'bin', 'java.exe')
            if not os.path.exists(java_path):
                return _("local.vendor.unknown")
                
            result = subprocess.run(
                [java_path, '-version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=2  # 减少超时时间
            )
            
            # 版本信息在stderr中
            if result.stderr:
                version_info = result.stderr.lower()
                if 'openjdk' in version_info:
                    if 'corretto' in version_info:
                        return "Corretto"
                    elif 'temurin' in version_info or 'adoptium' in version_info:
                        return "Temurin"
                    elif 'zulu' in version_info:
                        return "Zulu"
                    elif 'microsoft' in version_info:
                        return "Microsoft"
                    else:
                        return "OpenJDK"
                elif 'java(tm)' in version_info or 'oracle' in version_info:
                    return "Oracle"
                elif 'graalvm' in version_info:
                    return "GraalVM"
                elif 'semeru' in version_info:
                    return "Semeru"
                
            return _("local.vendor.unknown")
        except Exception as e:
            logger.error(f"获取JDK发行版失败: {str(e)}")
            return _("local.vendor.unknown")

    def get_detailed_version(self, java_path):
        """获取JDK详细版本信息"""
        try:
            if not os.path.exists(java_path):
                return None
                
            # 修正 Windows 路径分隔符
            java_path = os.path.normpath(java_path)
                
            result = subprocess.run(
                [java_path, '-version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=2  # 减少超时时间
            )
            
            if result.stderr:
                # 正则匹配版本号
                import re
                match = re.search(r'version "([^"]+)"', result.stderr)
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            logger.error(_("version.info.detail.get_failed").format(error=str(e)))
            return None

    def refresh_jdk_list(self):
        """刷新JDK列表"""
        try:
            # 清空现有列表
            self.jdk_list.clear()
            
            # 重新加载配置
            self.config.load()
            
            # 获取所有JDK和当前JDK
            jdks = self.config.get_all_jdks()
            current_jdk = self.config.get_current_jdk()
            current_path = current_jdk['path'] if current_jdk else None
            
            # 启动环境变量版本检查线程
            self.system_version_thread = SystemVersionThread()
            self.system_version_thread.finished.connect(self.update_system_version)
            self.system_version_thread.start()
            
            # 按版本号排序
            jdks.sort(key=lambda x: self.version_sort_key(x.get('version', '')), reverse=True)
            
            # 清理旧线程
            for thread in self.jdk_threads:
                thread.quit()
                thread.wait()
            self.jdk_threads.clear()
            
            # 预处理JDK列表
            valid_jdks = []
            invalid_paths = []
            
            for jdk in jdks:
                jdk_path = jdk.get('path', '')
                if not jdk_path or not os.path.exists(jdk_path):
                    invalid_paths.append(jdk_path)
                    continue
                    
                java_path = os.path.join(jdk_path, 'bin', 'java.exe')
                if not os.path.exists(java_path):
                    invalid_paths.append(jdk_path)
                    continue
                
                valid_jdks.append(jdk)
                
                # 创建并启动加载线程
                thread = JDKLoaderThread(jdk_path, java_path)
                thread.finished.connect(self.on_jdk_loaded)
                self.jdk_threads.append(thread)
                thread.start()
            
            # 批量移除无效的JDK路径
            if invalid_paths:
                for path in invalid_paths:
                    jdk_info = next((jdk for jdk in jdks if jdk.get('path', '') == path), None)
                    if jdk_info:
                        self.config.remove_jdk(path, is_mapped=(jdk_info.get('type') == 'mapped'))
                # 保存配置以确保无效路径被移除
                self.config.save()
            
            # 添加JDK条目（使用基本信息，详细信息将在异步加载后更新）
            for jdk in valid_jdks:
                self.add_jdk_item(jdk, current_path)
            
            # 如果列表为空，显示提示信息
            if not valid_jdks:
                empty_label = QLabel(_("local.list.empty"))
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_label.setStyleSheet("color: #666; padding: 20px;")
                self.jdk_list.addItem(QListWidgetItem())
                self.jdk_list.item(0).setSizeHint(empty_label.sizeHint())
                self.jdk_list.setItemWidget(self.jdk_list.item(0), empty_label)
            
        except Exception as e:
            logger.error(f"刷新JDK列表失败: {str(e)}")
            QMessageBox.warning(self, _("local.dialog.error.title"), f"{_('local.dialog.error.refresh_failed')}: {str(e)}")

    def on_jdk_loaded(self, jdk_info):
        """处理JDK信息加载完成"""
        if not jdk_info:
            return
            
        self.jdk_details[jdk_info['path']] = jdk_info
        
        # 更新对应的列表项
        for i in range(self.jdk_list.count()):
            item = self.jdk_list.item(i)
            widget = self.jdk_list.itemWidget(item)
            if not widget:
                continue
                
            # 查找路径标签来匹配正确的JDK
            path_label = widget.findChild(QLabel, 'path_label')
            if not path_label or path_label.text() != jdk_info['path']:
                continue
                
            # 查找版本标签和供应商标签
            version_label = widget.findChild(QLabel, 'version_label')
            vendor_tag = widget.findChild(QLabel, 'vendor_tag')
            
            if version_label and vendor_tag:
                # 更新版本号和供应商信息
                if jdk_info['detailed_version']:
                    version_label.setText(f"JDK {jdk_info['detailed_version']}")
                if jdk_info['vendor']:
                    self.update_vendor_tag(vendor_tag, jdk_info['vendor'])
                    
        # 如果是当前版本，更新当前版本显示
        current_jdk = self.config.get_current_jdk()
        if current_jdk and current_jdk['path'] == jdk_info['path']:
            self.current_version_label.setText(f"{_('local.current_version.prefix')}: JDK {jdk_info['detailed_version']}")

    def update_system_version(self, version):
        """更新环境变量版本显示"""
        if version:
            if version == _("local.system_version.not_installed"):
                self.system_version_label.setProperty("status", "not_installed")
                self.system_version_label.setText(_("local.system_version.not_installed"))
            else:
                self.system_version_label.setProperty("status", "installed")
                self.system_version_label.setText(f"{_('local.system_version.title')}: {version}")
            self.system_version_label.style().unpolish(self.system_version_label)
            self.system_version_label.style().polish(self.system_version_label)
        else:
            self.system_version_label.setProperty("status", "not_installed")
            self.system_version_label.setText(_("local.system_version.not_installed"))
            self.system_version_label.style().unpolish(self.system_version_label)
            self.system_version_label.style().polish(self.system_version_label)

    def add_jdk_item(self, jdk, current_path):
        """添加JDK列表项"""
        # 创建列表项
        item = QListWidgetItem()
        
        # 创建自定义 widget
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 版本图标
        icon_label = QLabel()
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            'resources',
            'icons',
            'java-apply.png' if jdk['path'] == current_path else 'java.png'
        )
        if os.path.exists(icon_path):
            icon_label.setPixmap(QIcon(icon_path).pixmap(QSize(24, 24)))
        layout.addWidget(icon_label)
        
        # 信息布局
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # 版本信息布局
        version_layout = QHBoxLayout()
        version_layout.setSpacing(8)
        
        # 版本号标签（将在异步加载后更新）
        version_label = QLabel(f"JDK {jdk['version']}")
        version_label.setObjectName('version_label')
        version_label.setStyleSheet("font-size: 10pt; font-weight: bold;")
        version_layout.addWidget(version_label)
        
        # 版本类型标签
        version_type = self._get_version_type(jdk['version'])
        version_type_tag = QLabel(version_type)
        version_type_tag.setStyleSheet(f"""
            background-color: {self._get_version_type_color(version_type)};
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 9pt;
        """)
        version_layout.addWidget(version_type_tag)
        
        # 类型标签
        type_text = _("local.jdk.type.mapped") if jdk['type'] == 'mapped' else _("local.jdk.type.downloaded")
        type_tag = QLabel(type_text)
        type_tag.setStyleSheet("""
            background-color: #6c757d;
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 9pt;
        """)
        version_layout.addWidget(type_tag)
        
        # 发行商标签（将在异步加载后更新）
        vendor_tag = QLabel(_("local.jdk.vendor.unknown"))
        vendor_tag.setObjectName('vendor_tag')
        self.update_vendor_tag(vendor_tag, _("local.jdk.vendor.unknown"))
        version_layout.addWidget(vendor_tag)
        
        # 应用中标签
        if jdk['path'] == current_path:
            current_tag = QWidget()
            current_tag_layout = QHBoxLayout(current_tag)
            current_tag_layout.setContentsMargins(6, 2, 8, 2)
            current_tag_layout.setSpacing(4)
            current_tag.setStyleSheet("""
                background-color: #28a745;
                        border-radius: 4px;
            """)

            # 添加对号图标
            check_icon = QLabel()
            check_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                         'resources', 'icons', 'check-circle.png')
            if os.path.exists(check_icon_path):
                check_icon.setPixmap(QIcon(check_icon_path).pixmap(QSize(14, 14)))
            current_tag_layout.addWidget(check_icon)

            # 添加文字标签
            text_label = QLabel(_("local.jdk.status.in_use"))
            text_label.setStyleSheet("color: white; font-size: 9pt;")
            current_tag_layout.addWidget(text_label)

            version_layout.addWidget(current_tag)
                    
        version_layout.addStretch()
        info_layout.addLayout(version_layout)
        
        # 路径和导入时间
        path_layout = QHBoxLayout()
        path_label = QLabel(jdk['path'])
        path_label.setObjectName('path_label')
        path_label.setStyleSheet("color: #666666; font-size: 9pt;")
        path_layout.addWidget(path_label)
        
        import_time = jdk.get('import_time', _("local.jdk.import_time.unknown"))
        if import_time != _("local.jdk.import_time.unknown"):
            import_time_label = QLabel(f"{_('local.jdk.import_time.prefix')}: {import_time}")
        else:
            import_time_label = QLabel(f"{_('local.jdk.import_time.prefix')}: {_('local.jdk.import_time.unknown')}")
        import_time_label.setStyleSheet("color: #666666; font-size: 9pt;")
        path_layout.addWidget(import_time_label)
        
        path_layout.addStretch()
        info_layout.addLayout(path_layout)
        
        layout.addLayout(info_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)
        
        # 打开目录按钮
        open_dir_button = QPushButton()
        open_dir_button.setToolTip(_("local.button.open_dir"))
        open_dir_button.setFixedSize(32, 32)
        open_dir_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.04);
                border-radius: 4px;
            }
        """)
        folder_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                      'resources', 'icons', 'folder-open.png')
        if os.path.exists(folder_icon_path):
            open_dir_button.setIcon(QIcon(folder_icon_path))
            open_dir_button.setIconSize(QSize(20, 20))
            open_dir_button.setProperty('jdk_path', jdk['path'])
            open_dir_button.clicked.connect(lambda _, path=jdk['path']: self.open_jdk_dir(path))
            button_layout.addWidget(open_dir_button)
            
            if jdk['path'] != current_path:
                # 应用此版本按钮
                set_current_button = QPushButton()
                set_current_button.setToolTip(_("local.button.apply_version"))
                set_current_button.setFixedSize(32, 32)
                set_current_button.setStyleSheet("""
                    QPushButton {
                        border: none;
                        background-color: transparent;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: rgba(26, 115, 232, 0.08);
                        border-radius: 4px;
                    }
                """)
                apply_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                         'resources', 'icons', 'apply.png')
                if os.path.exists(apply_icon_path):
                    set_current_button.setIcon(QIcon(apply_icon_path))
                    set_current_button.setIconSize(QSize(20, 20))
                    set_current_button.setProperty('jdk_path', jdk['path'])
                    set_current_button.clicked.connect(self.on_set_current_clicked)
                    button_layout.addWidget(set_current_button)
                
                # 删除按钮
                delete_button = QPushButton()
                delete_button.setToolTip(_("local.button.delete"))
                delete_button.setFixedSize(32, 32)
                delete_button.setStyleSheet("""
                    QPushButton {
                        border: none;
                        background-color: transparent;
                        padding: 4px;
                    }
                    QPushButton:hover {
                        background-color: rgba(211, 47, 47, 0.08);
                        border-radius: 4px;
                    }
                """)
                delete_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                      'resources', 'icons', 'delete.png')
                if os.path.exists(delete_icon_path):
                    delete_button.setIcon(QIcon(delete_icon_path))
                    delete_button.setIconSize(QSize(20, 20))
                    delete_button.setProperty('jdk_path', jdk['path'])
                    delete_button.clicked.connect(self.on_delete_clicked)
                    button_layout.addWidget(delete_button)
                
        layout.addLayout(button_layout)
        
        item.setSizeHint(widget.sizeHint())
        self.jdk_list.addItem(item)
        self.jdk_list.setItemWidget(item, widget)
        
    def update_vendor_tag(self, vendor_tag, vendor):
        """更新供应商标签样式"""
        vendor_colors = {
            'Oracle': '#F80000',
            'OpenJDK': '#6B94DA',
            'Temurin': '#2C2255',
            'Corretto': '#FF9900',
            'Zulu': '#0095DE',
            'Microsoft': '#00A4EF',
            '未知': '#757575'
        }
        
        vendor_color = next((color for vendor_name, color in vendor_colors.items() 
                        if vendor_name.lower() in vendor.lower()), 
                        vendor_colors['未知'])
        
        vendor_tag.setText(vendor)
        vendor_tag.setStyleSheet(f"""
            background-color: {vendor_color};
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 9pt;
        """)
            
    def version_sort_key(self, version):
        """版本号排序键"""
        try:
            # 将版本号分割为数字部分
            parts = re.findall(r'\d+', version)
            # 转换为整数列表，如果转换失败则使用0
            numbers = [int(part) if part.isdigit() else 0 for part in parts]
            # 补齐位数，确保能够正确比较
            while len(numbers) < 3:
                numbers.append(0)
            return numbers
        except Exception:
            return [0, 0, 0]  # 如果解析失败，返回默认值

    def update_current_version(self):
        """更新当前版本显示"""
        try:
            # 更新环境变量版本显示
            system_version = self.get_system_java_version()
            if system_version:
                if system_version == _("local.system_version.not_installed"):
                    self.system_version_label.setProperty("status", "not_installed")
                    self.system_version_label.setText(_("local.system_version.not_installed"))
                else:
                    self.system_version_label.setProperty("status", "installed")
                    self.system_version_label.setText(f"{_('local.system_version.title')}: {system_version}")
                self.system_version_label.style().unpolish(self.system_version_label)
                self.system_version_label.style().polish(self.system_version_label)
            else:
                self.system_version_label.setProperty("status", "not_installed")
                self.system_version_label.setText(_("local.system_version.not_installed"))
                self.system_version_label.style().unpolish(self.system_version_label)
                self.system_version_label.style().polish(self.system_version_label)

            # 更新当前应用版本显示
            junction_path = self.config.get('junction_path')
            if os.path.exists(junction_path):
                current_path = os.path.realpath(junction_path)
                if os.path.exists(current_path):
                    for jdk in self.config.get_all_jdks():
                        try:
                            if os.path.exists(jdk['path']) and os.path.samefile(jdk['path'], current_path):
                                # 修正 Windows 路径
                                java_path = os.path.normpath(os.path.join(current_path, 'bin', 'java.exe'))
                                detailed_version = self.get_detailed_version(java_path)
                                display_version = detailed_version if detailed_version else jdk['version']
                                self.current_version_label.setText(f"{_('local.current_version.prefix')}: JDK {display_version}")
                                return
                        except Exception as e:
                            logger.error(f"{_('log.error.check_version_failed')}: {str(e)}")
                            continue
            
            # 如果没有找到有效的当前版本
            self.current_version_label.setText(_("local.current_version.not_set"))
            
        except Exception as e:
            logger.error(f"{_('log.error.update_version_failed')}: {str(e)}")
            self.current_version_label.setText(_("local.current_version.not_set"))

    def add_local_jdk(self):
        """添加本地JDK"""
        # 选择JDK目录
        jdk_path = QFileDialog.getExistingDirectory(
            self,
            _("local.dialog.select_jdk_dir"),
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not jdk_path:
            return
            
        # 验证是否是有效的JDK目录
        java_path = os.path.join(jdk_path, 'bin', 'java.exe')
        if not os.path.exists(java_path):
            QMessageBox.warning(self, _("local.dialog.error"), _("local.dialog.invalid_jdk_dir"))
            return
            
        # 检查是否已经添加过
        for jdk in self.config.get_all_jdks():
            try:
                if os.path.samefile(jdk['path'], jdk_path):
                    QMessageBox.warning(self, _("local.dialog.warning"), _("local.dialog.jdk_already_added"))
                    return
            except Exception:
                continue
            
        # 获取版本信息
        try:
            detailed_version = self.get_detailed_version(java_path)
            if not detailed_version:
                QMessageBox.warning(self, _("local.dialog.error"), _("local.dialog.cannot_get_version"))
                return
                
            # 提取主版本号
            import re
            match = re.search(r'(\d+)', detailed_version)
            if not match:
                QMessageBox.warning(self, _("local.dialog.error"), _("local.dialog.cannot_parse_version"))
                return
                
            version = match.group(1)
            
            # 添加到配置
            import datetime
            jdk_info = {
                'version': version,
                'path': jdk_path,
                'type': 'mapped',
                'import_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 添加到配置
            if not self.config.add_mapped_jdk(jdk_info):
                QMessageBox.warning(self, _("local.dialog.warning"), _("local.dialog.jdk_already_added"))
                return
                
            # 确保配置被保存
            self.config.save()
            
            # 发送信号并刷新列表
            self.jdk_mapped.emit(version, jdk_path)
            self.refresh_jdk_list()
            QMessageBox.information(self, _("local.dialog.success"), _("local.dialog.jdk_added").format(version=version))
            
        except Exception as e:
            logger.error(f"{_('log.error.add_jdk_failed')}: {str(e)}")
            QMessageBox.warning(self, _("local.dialog.error"), _("local.dialog.add_jdk_failed").format(error=str(e)))

    def switch_version(self):
        """切换JDK版本"""
        current_item = self.jdk_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, _("local.dialog.warning"), _("local.dialog.select_version_first"))
            return
            
        jdk = current_item.data(Qt.ItemDataRole.UserRole)
        junction_path = self.config.get('junction_path')
        
        # 创建软链接
        if create_symlink(jdk['path'], junction_path):
            self.refresh_jdk_list()
            # 发送版本变更信号
            self.version_changed.emit()
            QMessageBox.information(self, _("local.dialog.success"), _("local.dialog.version_switched").format(version=jdk["version"]))
        else:
            QMessageBox.warning(self, _("local.dialog.error"), _("local.dialog.switch_failed"))

    def remove_jdk(self, jdk_path=None):
        """删除JDK"""
        try:
            if not jdk_path:
                return
            
            # 获取JDK信息
            jdk_info = None
            for jdk in self.config.get_all_jdks():
                if jdk['path'] == jdk_path:
                    jdk_info = jdk
                    break
            
            if not jdk_info:
                QMessageBox.warning(self, _("local.dialog.error"), _("local.dialog.jdk_not_found"))
                return
            
            version_text = jdk_info.get('version', _("local.jdk.version.unknown"))
            vendor_text = jdk_info.get('vendor', _("local.jdk.vendor.unknown"))
            
            # 创建警告对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(_("local.dialog.delete.title"))
            dialog.setFixedWidth(500)  # 增加对话框宽度
            dialog.setStyleSheet("""
                QDialog {
                    background-color: white;
                    border-radius: 8px;
                }
                QLabel {
                    color: #333333;
                    font-size: 13px;
                }
                QLabel#warningTitle {
                    color: #d32f2f;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 0px 0px 16px 0px;
                    background: transparent;
                }
                QLabel#warningMessage {
                    color: #d32f2f;
                    font-size: 13px;
                    line-height: 22px;
                    padding: 20px 24px;
                    background-color: rgba(211, 47, 47, 0.06);
                    border: 1px solid rgba(211, 47, 47, 0.2);
                    border-radius: 6px;
                    margin: 4px 0px 12px 0px;
                    font-weight: 500;
                    letter-spacing: 0.3px;
                }
                QPushButton {
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 13px;
                    min-width: 100px;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            layout.setSpacing(16)
            layout.setContentsMargins(24, 20, 24, 20)
            
            # 标题栏布局
            title_layout = QHBoxLayout()
            title_layout.setSpacing(8)
            title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # 垂直居中对齐
            
            # 添加警告图标
            warning_icon = QLabel()
            warning_icon.setFixedSize(20, 20)
            warning_icon.setStyleSheet("""
                background: transparent;
                margin: 0;  /* 完全移除边距 */
            """)
            warning_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                           'resources', 'icons', 'warn.png')
            if os.path.exists(warning_icon_path):
                pixmap = QPixmap(warning_icon_path)
                if not pixmap.isNull():
                    # 创建一个新的红色图标
                    colored_pixmap = QPixmap(pixmap.size())
                    colored_pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(colored_pixmap)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    
                    # 设置红色
                    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                    painter.setPen(QColor("#d32f2f"))
                    painter.setBrush(QColor("#d32f2f"))
                    
                    # 绘制图标
                    painter.drawPixmap(0, 0, pixmap)
                    painter.end()
                    
                    # 缩放图标
                    scaled_pixmap = colored_pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    warning_icon.setPixmap(scaled_pixmap)
            else:
                logger.error(f"警告图标文件不存在: {warning_icon_path}")
            
            # 创建一个容器来包含图标和标题
            header_container = QWidget()
            header_container.setStyleSheet("background: transparent;")
            header_layout = QHBoxLayout(header_container)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(8)
            header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            
            header_layout.addWidget(warning_icon)
            
            # 警告标题
            warning_title = QLabel(_("local.dialog.delete.warning_title"))
            warning_title.setObjectName("warningTitle")
            warning_title.setStyleSheet("""
                QLabel#warningTitle {
                    color: #d32f2f;
                    font-size: 16px;
                    font-weight: bold;
                    background: transparent;
                    padding: 0;
                    margin: 0;
                }
            """)
            header_layout.addWidget(warning_title)
            
            title_layout.addWidget(header_container)
            title_layout.addStretch()
            
            layout.addLayout(title_layout)
            
            # 警告信息
            warning_message = QLabel(_("local.dialog.delete.warning_message"))
            warning_message.setObjectName("warningMessage")
            warning_message.setWordWrap(True)
            layout.addWidget(warning_message)
            
            # 创建信息容器
            info_container = QWidget()
            info_container.setObjectName("infoContainer")
            info_container.setStyleSheet("""
                QWidget#infoContainer {
                    background-color: #f8f9fa;
                    border-radius: 6px;
                    padding: 20px;
                }
                QLabel {
                    background: transparent;
                }
                QLabel[type="title"] {
                    color: #666666;
                    font-weight: bold;
                    margin-bottom: 6px;
                    font-size: 13px;
                }
                QLabel[type="value"] {
                    color: #1a73e8;
                    font-family: 'Consolas', monospace;
                    padding: 6px 12px;
                    background-color: rgba(26, 115, 232, 0.08);
                    border-radius: 4px;
                    font-size: 13px;
                    letter-spacing: 0.3px;
                }
            """)
            
            info_layout = QVBoxLayout(info_container)
            info_layout.setSpacing(16)
            info_layout.setContentsMargins(20, 20, 20, 20)
            
            # 版本信息行
            version_layout = QVBoxLayout()
            version_layout.setSpacing(6)
            
            version_title = QLabel(_("local.dialog.delete.version_title"))
            version_title.setProperty("type", "title")
            version_layout.addWidget(version_title)
            
            version_value = QLabel(f"{vendor_text} JDK {version_text}")
            version_value.setProperty("type", "value")
            version_layout.addWidget(version_value)
            
            info_layout.addLayout(version_layout)
            
            # 路径信息行
            path_layout = QVBoxLayout()
            path_layout.setSpacing(6)
            
            path_title = QLabel(_("local.dialog.delete.path_title"))
            path_title.setProperty("type", "title")
            path_layout.addWidget(path_title)
            
            path_value = QLabel(jdk_path)
            path_value.setProperty("type", "value")
            path_value.setWordWrap(True)
            path_layout.addWidget(path_value)
            
            info_layout.addLayout(path_layout)
            
            layout.addWidget(info_container)
            
            # 按钮布局
            button_layout = QHBoxLayout()
            button_layout.setSpacing(12)
            
            remove_list_btn = QPushButton(_("local.dialog.button.remove_from_list"))
            remove_list_btn.setFixedWidth(190)  # 增加固定宽度到190px
            remove_list_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #dc3545;
                    background-color: white;
                    color: #dc3545;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #dc3545;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #c82333;
                    color: white;
                }
            """)
            
            remove_all_btn = QPushButton(_("local.dialog.button.delete_folder"))
            remove_all_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background-color: #dc3545;
                    color: white;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
                QPushButton:pressed {
                    background-color: #bd2130;
                }
            """)
            
            cancel_btn = QPushButton(_("local.dialog.button.cancel"))
            cancel_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #ccc;
                    background-color: white;
                    color: #666;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #f8f9fa;
                }
                QPushButton:pressed {
                    background-color: #e9ecef;
                }
            """)
            
            button_layout.addStretch()
            button_layout.addWidget(remove_list_btn)
            button_layout.addWidget(remove_all_btn)
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            
            # 连接按钮信号
            remove_list_btn.clicked.connect(lambda: dialog.done(1))  # 1 表示仅从列表移除
            remove_all_btn.clicked.connect(lambda: dialog.done(2))   # 2 表示删除文件夹
            cancel_btn.clicked.connect(dialog.reject)
            
            result = dialog.exec()
            
            if result > 0:  # 用户选择了某种删除方式
                try:
                    # 如果是当前使用的版本，先取消链接
                    junction_path = self.config.get('junction_path')
                    if os.path.exists(junction_path):
                        try:
                            junction_real_path = os.path.normpath(os.path.realpath(junction_path))
                            if os.path.normcase(junction_real_path) == os.path.normcase(jdk_path):
                                os.unlink(junction_path)
                                # 发送版本变更信号
                                self.version_changed.emit()
                        except Exception as e:
                            logger.error(f"{_('local.error.symlink_failed')}: {str(e)}")
                    
                    # 从配置中移除
                    is_mapped = jdk_info.get('type') == 'mapped'
                    if not self.config.remove_jdk(jdk_path, is_mapped=is_mapped):  # 移除配置中的 JDK 记录
                        raise Exception(_("local.dialog.error.remove_failed"))
                    
                    # 如果选择删除文件夹，才进行文件系统操作
                    if result == 2:  # 删除文件夹
                        import shutil
                        if os.path.exists(jdk_path):
                            shutil.rmtree(jdk_path)
                            message = _("local.dialog.delete.success_message").format(
                                version=version_text,
                                vendor=vendor_text
                            )
                        else:
                            message = _("local.dialog.delete.success_message_not_exist").format(
                                version=version_text,
                                vendor=vendor_text
                            )
                    else:  # 仅从列表移除
                        message = _("local.dialog.delete.success_message_list_only").format(
                            version=version_text,
                            vendor=vendor_text
                        )
                    
                    # 刷新列表
                    self.refresh_jdk_list()
                    self.update_current_version()
                    
                    QMessageBox.information(self, _("local.dialog.delete.success"), message)
                    
                except Exception as e:
                    logger.error(f"{_('local.dialog.error.delete_failed')}: {str(e)}")
                    QMessageBox.warning(
                        self,
                        _("local.dialog.delete.error"),
                        f"{_('local.dialog.error.delete_failed')}: {str(e)}"
                    )
                
        except Exception as e:
            logger.error(f"删除JDK失败: {str(e)}")
            QMessageBox.warning(
                self,
                self._("dialog.error.title"),
                str(e)
            ) 

    def open_jdk_dir(self, jdk_path):
        """打开JDK目录"""
        try:
            if platform_manager.is_windows:
                os.startfile(jdk_path)
            else:
                subprocess.run(['xdg-open', jdk_path])
        except Exception as e:
            logger.error(f"{_('local.error.open_dir_failed')}: {str(e)}")
            QMessageBox.warning(self, _("local.dialog.error"), _("local.error.open_dir_failed").format(error=str(e)))

    def on_set_current_clicked(self):
        """设置当前版本"""
        button = self.sender()
        if not button:
            return
            
        jdk_path = button.property('jdk_path')
        junction_path = self.config.get('junction_path')
            
        # 创建软链接
        if create_symlink(jdk_path, junction_path):
            self.refresh_jdk_list()
            self.update_current_version()
            # 发送版本变更信号
            self.version_changed.emit()
            
            # 创建自定义成功对话框
            success_dialog = QDialog(self)
            success_dialog.setWindowTitle(_("local.dialog.switch.title"))
            success_dialog.setFixedSize(340, 160)  # 减小对话框尺寸
            success_dialog.setStyleSheet("""
                QDialog {
                    background-color: white;
                    border-radius: 8px;
                }
                QLabel {
                    color: #333333;
                    font-size: 13px;
                }
                QLabel#titleLabel {
                    color: #1a73e8;
                    font-size: 14px;
                    font-weight: bold;
                    background: transparent;
                }
                QLabel#messageLabel {
                    color: #5f6368;
                    font-size: 13px;
                    line-height: 1.6;
                    padding: 4px 0;
                    margin: 2px 0;
                }
                QLabel#commandLabel {
                    color: #202124;
                    font-family: 'Consolas', monospace;
                    background-color: #f8f9fa;
                    padding: 6px 10px;
                    border-radius: 4px;
                    border: 1px solid #e8eaed;
                    margin: 4px 0;
                    line-height: 1.4;
                }
                QPushButton {
                    padding: 4px 16px;
                    border: none;
                    border-radius: 4px;
                    background-color: #1a73e8;
                    color: white;
                    font-size: 13px;
                    font-weight: 500;
                    min-width: 70px;
                }
                QPushButton:hover {
                    background-color: #1557b0;
                }
                QPushButton:pressed {
                    background-color: #0d47a1;
                }
                QFrame#line {
                    background-color: #E8EEF7;
                    margin: 0 -12px;
                }
            """)
            
            # 创建布局
            layout = QVBoxLayout(success_dialog)
            layout.setContentsMargins(16, 16, 16, 12)  # 减小边距
            layout.setSpacing(8)  # 减小间距
            
            # 添加图标和标题
            header_layout = QHBoxLayout()
            header_layout.setSpacing(10)  # 减小图标和标题的间距
            
            icon_label = QLabel()
            icon_label.setStyleSheet("background: transparent;")  # 设置背景透明
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                   'resources', 'icons', 'success.png')
            if os.path.exists(icon_path):
                icon_label.setPixmap(QIcon(icon_path).pixmap(QSize(24, 24)))
            header_layout.addWidget(icon_label)
            
            title_label = QLabel(_("local.dialog.switch.success_title"))
            title_label.setObjectName("titleLabel")
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            layout.addLayout(header_layout)
            
            # 添加分隔线
            line = QFrame()
            line.setObjectName("line")
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFixedHeight(1)
            layout.addWidget(line)
            
            # 添加消息内容
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(0, 8, 0, 8)  # 增加内容区域的上下边距
            content_layout.setSpacing(12)  # 增加内容区域的间距
            
            if not platform_manager.is_windows:
                reload_cmd = platform_manager.get_shell_reload_command()
                message = QLabel(_("local.dialog.switch.success_message_unix"))
                message.setObjectName("messageLabel")
                content_layout.addWidget(message)
                
                # 添加命令显示
                cmd_label = QLabel(reload_cmd)
                cmd_label.setObjectName("commandLabel")
                cmd_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                content_layout.addWidget(cmd_label)
            else:
                message = QLabel(_("local.dialog.switch.success_message_windows"))
                message.setObjectName("messageLabel")
                content_layout.addWidget(message)
            
            layout.addWidget(content_widget)
            layout.addStretch()  # 添加弹性空间
            
            # 添加确定按钮
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            ok_button = QPushButton(_("local.dialog.button.ok"))
            ok_button.setFixedWidth(80)  # 减小按钮宽度
            ok_button.clicked.connect(success_dialog.accept)
            button_layout.addWidget(ok_button)
            layout.addLayout(button_layout)
            
            # 显示对话框
            success_dialog.exec()
        else:
            # 创建错误对话框
            error_dialog = QDialog(self)
            error_dialog.setWindowTitle(_("local.dialog.switch.error_title"))
            error_dialog.setFixedSize(340, 140)  # 减小对话框尺寸
            error_dialog.setStyleSheet("""
                QDialog {
                    background-color: white;
                    border-radius: 8px;
                }
                QLabel {
                    color: #333333;
                    font-size: 13px;
                }
                QLabel#titleLabel {
                    color: #d32f2f;
                    font-size: 14px;
                    font-weight: bold;
                    background: transparent;
                }
                QLabel#messageLabel {
                    color: #5f6368;
                    font-size: 13px;
                    line-height: 1.6;
                    padding: 4px 0;
                    margin: 2px 0;
                }
                QPushButton {
                    padding: 4px 16px;
                    border: none;
                    border-radius: 4px;
                    background-color: #d32f2f;
                    color: white;
                    font-size: 13px;
                    font-weight: 500;
                    min-width: 70px;
                }
                QPushButton:hover {
                    background-color: #b71c1c;
                }
                QPushButton:pressed {
                    background-color: #9a0007;
                }
                QFrame#line {
                    background-color: #E8EEF7;
                    margin: 0 -12px;
                }
            """)
            
            # 创建布局
            layout = QVBoxLayout(error_dialog)
            layout.setContentsMargins(16, 16, 16, 12)  # 减小边距
            layout.setSpacing(8)  # 减小间距
            
            # 添加图标和标题
            header_layout = QHBoxLayout()
            header_layout.setSpacing(10)  # 减小图标和标题的间距
            
            icon_label = QLabel()
            icon_label.setStyleSheet("background: transparent;")  # 设置背景透明
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                   'resources', 'icons', 'error.png')
            if os.path.exists(icon_path):
                icon_label.setPixmap(QIcon(icon_path).pixmap(QSize(24, 24)))
            header_layout.addWidget(icon_label)
            
            title_label = QLabel(_("local.dialog.switch.error_title"))
            title_label.setObjectName("titleLabel")
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            layout.addLayout(header_layout)
            
            # 添加分隔线
            line = QFrame()
            line.setObjectName("line")
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFixedHeight(1)
            layout.addWidget(line)
            
            # 添加错误消息
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(0, 8, 0, 8)  # 增加内容区域的上下边距
            content_layout.setSpacing(12)  # 增加内容区域的间距
            
            message = QLabel(_("local.dialog.switch.error_message"))
            message.setObjectName("messageLabel")
            content_layout.addWidget(message)
            
            layout.addWidget(content_widget)
            layout.addStretch()  # 添加弹性空间
            
            # 添加确定按钮
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            ok_button = QPushButton(_("local.dialog.button.ok"))
            ok_button.setFixedWidth(80)  # 减小按钮宽度
            ok_button.clicked.connect(error_dialog.accept)
            button_layout.addWidget(ok_button)
            layout.addLayout(button_layout)
            
            # 显示对话框
            error_dialog.exec()

    def create_styled_dialog(self, title, text, icon=QMessageBox.Icon.Question, buttons=None, default_button=None):
        """创建美化的对话框"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.setIcon(icon)
        
        if buttons:
            dialog.setStandardButtons(buttons)
        if default_button:
            dialog.setDefaultButton(default_button)
        
        # 设置对话框样式
        dialog.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QMessageBox QLabel {
                color: #333333;
                font-size: 13px;
                min-width: 300px;
            }
            QPushButton {
                padding: 6px 16px;
                border-radius: 4px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton[text="确定"], QPushButton[text="Yes"], QPushButton[text="保存"] {
                color: white;
                background-color: #1a73e8;
                border: none;
            }
            QPushButton[text="确定"]:hover, QPushButton[text="Yes"]:hover, QPushButton[text="保存"]:hover {
                background-color: #1557b0;
            }
            QPushButton[text="取消"], QPushButton[text="No"] {
                color: #333333;
                background-color: #f8f9fa;
                border: 1px solid #dadce0;
            }
            QPushButton[text="取消"]:hover, QPushButton[text="No"]:hover {
                background-color: #f1f3f4;
                border-color: #d2d3d7;
            }
            QPushButton[text="仅从列表移除"] {
                color: #333333;
                background-color: #f8f9fa;
                border: 1px solid #dadce0;
            }
            QPushButton[text="仅从列表移除"]:hover {
                background-color: #f1f3f4;
                border-color: #d2d3d7;
            }
            QPushButton[text="删除文件夹"] {
                color: white;
                background-color: #dc3545;
                border: none;
            }
            QPushButton[text="删除文件夹"]:hover {
                background-color: #c82333;
            }
        """)
        
        return dialog

    def on_delete_clicked(self):
        """删除JDK"""
        button = self.sender()
        if not button:
            return
            
        jdk_path = button.property('jdk_path')
        if not jdk_path:
            return
            
        # 获取JDK信息
        jdk_info = None
        for jdk in self.config.get_all_jdks():
            if jdk['path'] == jdk_path:
                jdk_info = jdk
                break
        
        if not jdk_info:
            QMessageBox.warning(self, _("dialog.error.title"), _("local.dialog.jdk_not_found"))
            return
        
        version_text = jdk_info.get('version', _("local.jdk.version.unknown"))
        vendor_text = jdk_info.get('vendor', _("local.jdk.vendor.unknown"))
        
        # 创建警告对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(_("local.dialog.delete.title"))
        dialog.setFixedWidth(500)  # 增加对话框宽度
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 8px;
            }
            QLabel {
                color: #333333;
                font-size: 13px;
            }
            QLabel#warningTitle {
                color: #d32f2f;
                font-size: 16px;
                font-weight: bold;
                padding: 0px 0px 16px 0px;
                background: transparent;
            }
            QLabel#warningMessage {
                color: #d32f2f;
                font-size: 13px;
                line-height: 22px;
                padding: 20px 24px;
                background-color: rgba(211, 47, 47, 0.06);
                border: 1px solid rgba(211, 47, 47, 0.2);
                border-radius: 6px;
                margin: 4px 0px 12px 0px;
                font-weight: 500;
                letter-spacing: 0.3px;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 13px;
                min-width: 100px;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)
        
        # 标题栏布局
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # 垂直居中对齐
        
        # 添加警告图标
        warning_icon = QLabel()
        warning_icon.setFixedSize(20, 20)
        warning_icon.setStyleSheet("""
            background: transparent;
            margin: 0;  /* 完全移除边距 */
        """)
        warning_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                       'resources', 'icons', 'warn.png')
        if os.path.exists(warning_icon_path):
            pixmap = QPixmap(warning_icon_path)
            if not pixmap.isNull():
                # 创建一个新的红色图标
                colored_pixmap = QPixmap(pixmap.size())
                colored_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(colored_pixmap)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # 设置红色
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                painter.setPen(QColor("#d32f2f"))
                painter.setBrush(QColor("#d32f2f"))
                
                # 绘制图标
                painter.drawPixmap(0, 0, pixmap)
                painter.end()
                
                # 缩放图标
                scaled_pixmap = colored_pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                warning_icon.setPixmap(scaled_pixmap)
        else:
            logger.error(f"警告图标文件不存在: {warning_icon_path}")
        
        # 创建一个容器来包含图标和标题
        header_container = QWidget()
        header_container.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addWidget(warning_icon)
        
        # 警告标题
        warning_title = QLabel(_("local.dialog.delete.warning_title"))
        warning_title.setObjectName("warningTitle")
        warning_title.setStyleSheet("""
            QLabel#warningTitle {
                color: #d32f2f;
                font-size: 16px;
                font-weight: bold;
                background: transparent;
                padding: 0;
                margin: 0;
            }
        """)
        header_layout.addWidget(warning_title)
        
        title_layout.addWidget(header_container)
        title_layout.addStretch()
        
        layout.addLayout(title_layout)
        
        # 警告信息
        warning_message = QLabel(_("local.dialog.delete.warning_message"))
        warning_message.setObjectName("warningMessage")
        warning_message.setWordWrap(True)
        layout.addWidget(warning_message)
        
        # 创建信息容器
        info_container = QWidget()
        info_container.setObjectName("infoContainer")
        info_container.setStyleSheet("""
            QWidget#infoContainer {
                background-color: #f8f9fa;
                border-radius: 6px;
                padding: 20px;
            }
            QLabel {
                background: transparent;
            }
            QLabel[type="title"] {
                color: #666666;
                font-weight: bold;
                margin-bottom: 6px;
                font-size: 13px;
            }
            QLabel[type="value"] {
                color: #1a73e8;
                font-family: 'Consolas', monospace;
                padding: 6px 12px;
                background-color: rgba(26, 115, 232, 0.08);
                border-radius: 4px;
                font-size: 13px;
                letter-spacing: 0.3px;
            }
        """)
        
        info_layout = QVBoxLayout(info_container)
        info_layout.setSpacing(16)
        info_layout.setContentsMargins(20, 20, 20, 20)
        
        # 版本信息行
        version_layout = QVBoxLayout()
        version_layout.setSpacing(6)
        
        version_title = QLabel(_("local.dialog.delete.version_title"))
        version_title.setProperty("type", "title")
        version_layout.addWidget(version_title)
        
        version_value = QLabel(f"{vendor_text} JDK {version_text}")
        version_value.setProperty("type", "value")
        version_layout.addWidget(version_value)
        
        info_layout.addLayout(version_layout)
        
        # 路径信息行
        path_layout = QVBoxLayout()
        path_layout.setSpacing(6)
        
        path_title = QLabel(_("local.dialog.delete.path_title"))
        path_title.setProperty("type", "title")
        path_layout.addWidget(path_title)
        
        path_value = QLabel(jdk_path)
        path_value.setProperty("type", "value")
        path_value.setWordWrap(True)
        path_layout.addWidget(path_value)
        
        info_layout.addLayout(path_layout)
        
        layout.addWidget(info_container)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        remove_list_btn = QPushButton(_("local.dialog.button.remove_from_list"))
        remove_list_btn.setFixedWidth(190)  # 增加固定宽度到190px
        remove_list_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #dc3545;
                background-color: white;
                color: #dc3545;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #dc3545;
                color: white;
            }
            QPushButton:pressed {
                background-color: #c82333;
                color: white;
            }
        """)
        
        remove_all_btn = QPushButton(_("local.dialog.button.delete_folder"))
        remove_all_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: #dc3545;
                color: white;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        
        cancel_btn = QPushButton(_("local.dialog.button.cancel"))
        cancel_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                background-color: white;
                color: #666;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
            }
            QPushButton:pressed {
                background-color: #e9ecef;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(remove_list_btn)
        button_layout.addWidget(remove_all_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 连接按钮信号
        remove_list_btn.clicked.connect(lambda: dialog.done(1))  # 1 表示仅从列表移除
        remove_all_btn.clicked.connect(lambda: dialog.done(2))   # 2 表示删除文件夹
        cancel_btn.clicked.connect(dialog.reject)
        
        result = dialog.exec()
        
        if result > 0:  # 用户选择了某种删除方式
            try:
                # 如果是当前使用的版本，先取消链接
                junction_path = self.config.get('junction_path')
                if os.path.exists(junction_path):
                    try:
                        junction_real_path = os.path.normpath(os.path.realpath(junction_path))
                        if os.path.normcase(junction_real_path) == os.path.normcase(jdk_path):
                            os.unlink(junction_path)
                            # 发送版本变更信号
                            self.version_changed.emit()
                    except Exception as e:
                        logger.error(f"{_('local.error.symlink_failed')}: {str(e)}")
                
                # 从配置中移除
                is_mapped = jdk_info.get('type') == 'mapped'
                if not self.config.remove_jdk(jdk_path, is_mapped=is_mapped):  # 移除配置中的 JDK 记录
                    raise Exception(_("local.dialog.error.remove_failed"))
                
                # 如果选择删除文件夹，才进行文件系统操作
                if result == 2:  # 删除文件夹
                    import shutil
                    if os.path.exists(jdk_path):
                        shutil.rmtree(jdk_path)
                        message = _("local.dialog.delete.success_message").format(
                            version=version_text,
                            vendor=vendor_text
                        )
                    else:
                        message = _("local.dialog.delete.success_message_not_exist").format(
                            version=version_text,
                            vendor=vendor_text
                        )
                else:  # 仅从列表移除
                    message = _("local.dialog.delete.success_message_list_only").format(
                        version=version_text,
                        vendor=vendor_text
                    )
                
                # 刷新列表
                self.refresh_jdk_list()
                self.update_current_version()
                
                QMessageBox.information(self, _("local.dialog.delete.success"), message)
                
            except Exception as e:
                logger.error(f"{_('local.dialog.error.delete_failed')}: {str(e)}")
                QMessageBox.warning(
                    self,
                    _("local.dialog.delete.error"),
                    f"{_('local.dialog.error.delete_failed')}: {str(e)}"
                )

    def _get_version_type(self, version):
        """获取版本类型"""
        try:
            major_version = int(version.split('.')[0])
            if major_version in [8, 11, 17, 21]:
                return _("local.version.type.lts")
            elif major_version >= 21:
                return _("local.version.type.latest")
            elif major_version >= 17:
                return _("local.version.type.interim")
            elif major_version >= 11:
                return _("local.version.type.old")
            else:
                return _("local.version.type.legacy")
        except:
            return _("local.version.type.unknown")

    def _get_version_type_color(self, version_type):
        """获取版本类型对应的颜色"""
        colors = {
            _("local.version.type.lts"): "#17a2b8",       # 蓝绿色
            _("local.version.type.old"): "#6c757d",    # 灰色
            _("local.version.type.legacy"): "#dc3545",    # 红色
            _("local.version.type.unknown"): "#6c757d"   # 灰色
        }
        return colors.get(version_type, "#6c757d") 

    def get_system_java_version(self):
        """获取系统Java版本"""
        try:
            result = subprocess.run(
                ['java', '-version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=5
            )
            
            if result.stderr:
                return result.stderr.split('\n')[0]  # 通常版本信息在第一行
            return None
        except FileNotFoundError:
            return _("local.system_version.not_installed")
        except Exception as e:
            logger.error(f"{_('log.error.get_system_version_failed')}: {str(e)}")
            return _("local.system_version.unknown")

    def map_jdk(self, jdk_path):
        """映射JDK"""
        try:
            # 获取版本信息
            version = self._get_jdk_version(jdk_path)
            if not version:
                QMessageBox.warning(self, _("local.dialog.error"), _("local.dialog.cannot_get_version"))
                return
                
            # 添加到配置
            if self.config.add_mapped_jdk({
                'version': version,
                'path': jdk_path,
                'type': 'mapped'
            }):
                # 发送映射信号
                self.jdk_mapped.emit(version, jdk_path)
                # 刷新列表
                self.refresh_jdk_list()
                # 更新当前版本显示
                self.update_current_version()
                # 发送版本变更信号
                self.version_changed.emit()
                QMessageBox.information(self, _("local.dialog.success"), _("local.dialog.jdk_added").format(version=version))
            else:
                QMessageBox.warning(self, _("local.dialog.error"), _("local.dialog.add_jdk_failed"))
        except Exception as e:
            logger.error(f"{_('log.error.map_jdk_failed')}: {str(e)}")
            QMessageBox.warning(self, _("local.dialog.error"), _("local.dialog.add_jdk_failed").format(error=str(e)))

    def _get_jdk_version(self, jdk_path):
        """获取JDK版本信息"""
        try:
            java_path = os.path.join(jdk_path, 'bin', 'java.exe')
            if not os.path.exists(java_path):
                return None
                
            result = subprocess.run(
                [java_path, '-version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=5
            )
            
            if result.stderr:
                version_line = result.stderr.split('\n')[0]
                match = re.search(r'version "([^"]+)"', version_line)
                if match:
                    return match.group(1)
            return None
        except Exception as e:
            logger.error(f"{_('log.error.get_version_failed')}: {str(e)}")
            return None 

    def delete_jdk(self, jdk_info):
        """删除JDK"""
        try:
            # 获取JDK信息
            version = jdk_info.get('version', '')
            vendor = jdk_info.get('vendor', self._("version.vendor.unknown"))
            path = jdk_info.get('path', '')
            
            # 第一层确认：确认是否删除
            confirm_msg = self._("local.delete_confirm").format(
                version=version,
                vendor=vendor
            )
            reply = QMessageBox.question(
                self,
                self._("local.delete_title"),
                confirm_msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 第二层确认：显示具体路径并再次确认
                detail_msg = self._("local.delete_path_confirm").format(
                    version=version,
                    vendor=vendor,
                    path=path
                )
                detail_reply = QMessageBox.warning(
                    self,
                    self._("local.delete_title"),
                    detail_msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if detail_reply == QMessageBox.StandardButton.Yes:
                    # 执行删除操作
                    if os.path.exists(path):
                        import shutil
                        shutil.rmtree(path)
                        message = _("local.dialog.delete.success_message").format(
                            version=version,
                            vendor=vendor
                        )
                    else:
                        message = _("local.dialog.delete.success_message_not_exist").format(
                            version=version,
                            vendor=vendor
                        )
                    
                    # 从配置中移除
                    self.config.remove_jdk(jdk_info)
                    # 刷新列表
                    self.refresh_jdk_list()
                    # 发送版本变更信号
                    self.version_changed.emit()
                    
        except Exception as e:
            logger.error(f"删除JDK失败: {str(e)}")
            QMessageBox.warning(
                self,
                self._("dialog.error.title"),
                str(e)
            ) 