import os
import re
import subprocess
from loguru import logger
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QDialog, QDialogButtonBox, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QThread
from PyQt6.QtGui import QIcon, QFont, QPixmap
from src.utils.system_utils import create_symlink, set_environment_variable, update_path_variable
from src.utils.platform_manager import platform_manager

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
                    vendor = "未知"
                
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
                    'vendor': "未知"
                })
        except Exception as e:
            logger.debug(f"获取JDK信息失败: {self.jdk_path}, {str(e)}")
            # 发送错误状态的信息
            self.finished.emit({
                'path': self.jdk_path,
                'detailed_version': None,
                'vendor': "未知",
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
            self.finished.emit("未安装")
        except Exception as e:
            logger.error(f"获取系统Java版本失败: {str(e)}")
            self.finished.emit("未知")

    def update_system_version(self, version):
        """更新环境变量版本显示"""
        if version:
            if version == "未安装":
                self.system_version_label.setProperty("status", "not_installed")
                self.system_version_label.setText("未安装 Java 运行环境")
            else:
                self.system_version_label.setProperty("status", "installed")
                self.system_version_label.setText(version)  # 显示完整的版本信息
            self.system_version_label.style().unpolish(self.system_version_label)
            self.system_version_label.style().polish(self.system_version_label)
        else:
            self.system_version_label.setProperty("status", "not_installed")
            self.system_version_label.setText("未安装 Java 运行环境")
            self.system_version_label.style().unpolish(self.system_version_label)
            self.system_version_label.style().polish(self.system_version_label)

class LocalTab(QWidget):
    """本地管理标签页"""
    
    # 定义信号
    jdk_mapped = pyqtSignal(str, str)  # version, path
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.jdk_threads = []  # 保存所有JDK加载线程
        self.jdk_details = {}  # 缓存JDK详细信息
        self.init_ui()
        
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
        
        version_layout = QVBoxLayout(version_container)  # 改为垂直布局
        version_layout.setContentsMargins(16, 16, 16, 16)
        version_layout.setSpacing(12)  # 增加垂直间距
        
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
        self.current_version_label = QLabel('当前应用版本: 未设置')
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
        title_label = QLabel('环境变量版本')
        title_label.setStyleSheet("""
            color: #444444;
            font-size: 13px;
            font-weight: 600;
            background: transparent;
            letter-spacing: 0.3px;
        """)
        title_layout.addWidget(title_label)
        
        # 添加提示信息
        info_label = QLabel('(通过系统 java -version 命令获取)')
        info_label.setStyleSheet("""
            color: #666666;
            font-size: 12px;
            background: transparent;
        """)
        title_layout.addWidget(info_label)
        title_layout.addStretch()
        
        system_version_layout.addLayout(title_layout)

        # 版本信息文本框
        self.system_version_label = QLabel('检测中...')
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
        add_button = QPushButton('添加本地JDK')
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
        
        # 将按钮添加到右侧
        button_layout.addStretch()  # 添加弹性空间，将按钮推到右侧
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
                return "未知"
                
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
                
            return "未知"
        except Exception as e:
            logger.error(f"获取JDK发行版失败: {str(e)}")
            return "未知"

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
            logger.error(f"获取详细版本失败: {str(e)}")
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
                jdk_path = jdk['path']
                if not os.path.exists(jdk_path):
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
                    jdk_info = next((jdk for jdk in jdks if jdk['path'] == path), None)
                    if jdk_info:
                        self.config.remove_jdk(path, is_mapped=(jdk_info.get('type') == 'mapped'))
            
            # 添加JDK条目（使用基本信息，详细信息将在异步加载后更新）
            for jdk in valid_jdks:
                self.add_jdk_item(jdk, current_path)
            
        except Exception as e:
            logger.error(f"刷新JDK列表失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"刷新JDK列表失败: {str(e)}")

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
            self.current_version_label.setText(f"当前应用版本: JDK {jdk_info['detailed_version']}")

    def update_system_version(self, version):
        """更新环境变量版本显示"""
        if version:
            if version == "未安装":
                self.system_version_label.setProperty("status", "not_installed")
                self.system_version_label.setText("未安装 Java 运行环境")
            else:
                self.system_version_label.setProperty("status", "installed")
                self.system_version_label.setText(version)  # 显示完整的版本信息
            self.system_version_label.style().unpolish(self.system_version_label)
            self.system_version_label.style().polish(self.system_version_label)
        else:
            self.system_version_label.setProperty("status", "not_installed")
            self.system_version_label.setText("未安装 Java 运行环境")
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
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons', 
                               'java-apply.png' if jdk['path'] == current_path else 'java.png')
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
        type_text = "已映射" if jdk['type'] == 'mapped' else "已下载"
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
        vendor_tag = QLabel("未知")
        vendor_tag.setObjectName('vendor_tag')
        self.update_vendor_tag(vendor_tag, "未知")
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
            text_label = QLabel("应用中")
            text_label.setStyleSheet("color: white; font-size: 9pt;")
            current_tag_layout.addWidget(text_label)

            version_layout.addWidget(current_tag)
        
        version_layout.addStretch()
        info_layout.addLayout(version_layout)
        
        # 路径和导入时间
        path_layout = QHBoxLayout()
        path_label = QLabel(jdk['path'])
        path_label.setObjectName('path_label')  # 添加ObjectName以便后续查找
        path_label.setStyleSheet("color: #666666; font-size: 9pt;")
        path_layout.addWidget(path_label)
        
        import_time = jdk.get('import_time', '未知')
        if import_time != '未知':
            import_time_label = QLabel(f"导入时间: {import_time}")
        else:
            import_time_label = QLabel("导入时间: 未知")
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
        open_dir_button.setToolTip("打开目录")
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
            set_current_button.setToolTip("应用此版本")
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
        delete_button.setToolTip("删除")
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
                if system_version == "未安装":
                    self.system_version_label.setProperty("status", "not_installed")
                    self.system_version_label.setText("环境变量版本: 未安装")
                else:
                    self.system_version_label.setProperty("status", "installed")
                    self.system_version_label.setText(f"环境变量版本: {system_version}")
                self.system_version_label.style().unpolish(self.system_version_label)
                self.system_version_label.style().polish(self.system_version_label)
            else:
                self.system_version_label.setProperty("status", "not_installed")
                self.system_version_label.setText("环境变量版本: 未安装")
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
                                self.current_version_label.setText(f"当前应用版本: JDK {display_version}")
                                return
                        except Exception as e:
                            logger.error(f"检查JDK版本失败: {str(e)}")
                            continue
            
            # 如果没有找到有效的当前版本
            self.current_version_label.setText("当前应用版本: 未设置")
            
        except Exception as e:
            logger.error(f"更新当前版本显示失败: {str(e)}")
            self.current_version_label.setText("当前应用版本: 未设置")

    def add_local_jdk(self):
        """添加本地JDK"""
        # 选择JDK目录
        jdk_path = QFileDialog.getExistingDirectory(
            self,
            "选择JDK安装目录",
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not jdk_path:
            return
            
        # 验证是否是有效的JDK目录
        java_path = os.path.join(jdk_path, 'bin', 'java.exe')
        if not os.path.exists(java_path):
            QMessageBox.warning(self, '错误', '所选目录不是有效的JDK目录')
            return
            
        # 检查是否已经添加过
        for jdk in self.config.get_all_jdks():
            try:
                if os.path.samefile(jdk['path'], jdk_path):
                    QMessageBox.warning(self, '警告', '该JDK已经添加过了')
                    return
            except Exception:
                continue
            
        # 获取版本信息
        try:
            detailed_version = self.get_detailed_version(java_path)
            if not detailed_version:
                QMessageBox.warning(self, '错误', '无法获取JDK版本信息')
                return
                
            # 提取主版本号
            import re
            match = re.search(r'(\d+)', detailed_version)
            if not match:
                QMessageBox.warning(self, '错误', '无法解析JDK版本号')
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
                QMessageBox.warning(self, '警告', '该JDK已经添加过了')
                return
                
            # 发送信号并刷新列表
            self.jdk_mapped.emit(version, jdk_path)
            self.refresh_jdk_list()
            QMessageBox.information(self, '成功', f'已添加 JDK {version}')
            
        except Exception as e:
            logger.error(f"添加JDK失败: {str(e)}")
            QMessageBox.warning(self, '错误', f'添加JDK失败: {str(e)}')

    def switch_version(self):
        """切换JDK版本"""
        current_item = self.jdk_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, '警告', '请先选择要切换的JDK版本')
            return
            
        jdk = current_item.data(Qt.ItemDataRole.UserRole)
        junction_path = self.config.get('junction_path')
        
        # 创建软链接
        if create_symlink(jdk['path'], junction_path):
            self.refresh_jdk_list()
            QMessageBox.information(self, '成功', f'已切换到 JDK {jdk["version"]}')
        else:
            QMessageBox.warning(self, '错误', '切换JDK版本失败')

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
                QMessageBox.warning(self, '错误', '未找到指定的JDK信息')
                return
            
            version_text = jdk_info.get('version', '未知')
            vendor_text = jdk_info.get('vendor', '未知')
            
            # 弹出确认对话框
            dialog = QDialog(self)
            dialog.setWindowTitle('删除JDK')
            layout = QVBoxLayout(dialog)
            
            message = QLabel(f'确定要删除 JDK {version_text} ({vendor_text}) 吗？')
            layout.addWidget(message)
            
            button_box = QDialogButtonBox()
            remove_list_btn = button_box.addButton('仅从列表移除', QDialogButtonBox.ButtonRole.ActionRole)
            remove_all_btn = button_box.addButton('删除文件夹', QDialogButtonBox.ButtonRole.ActionRole)
            cancel_btn = button_box.addButton('取消', QDialogButtonBox.ButtonRole.RejectRole)
            layout.addWidget(button_box)
            
            # 设置按钮样式
            remove_list_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    border: 1px solid #dc3545;
                    border-radius: 4px;
                    background-color: white;
                    color: #dc3545;
                }
                QPushButton:hover {
                    background-color: #dc3545;
                    color: white;
                }
            """)
            
            remove_all_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    border: none;
                    border-radius: 4px;
                    background-color: #dc3545;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            
            cancel_btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background-color: white;
                    color: #666;
                }
                QPushButton:hover {
                    background-color: #f8f9fa;
                }
            """)
            
            # 连接按钮信号
            remove_list_btn.clicked.connect(lambda: dialog.done(1))  # 1 表示仅从列表移除
            remove_all_btn.clicked.connect(lambda: dialog.done(2))   # 2 表示删除文件夹
            cancel_btn.clicked.connect(dialog.reject)
            
            result = dialog.exec()
            
            if result > 0:  # 用户选择了某种删除方式
                # 如果是当前使用的版本，先取消链接
                junction_path = self.config.get('junction_path')
                if os.path.exists(junction_path):
                    try:
                        junction_real_path = os.path.normpath(os.path.realpath(junction_path))
                        if os.path.normcase(junction_real_path) == os.path.normcase(jdk_path):
                            os.unlink(junction_path)
                    except Exception as e:
                        logger.error(f"取消软链接失败: {str(e)}")
                
                # 从配置中移除
                is_mapped = jdk_info.get('type') == 'mapped'
                self.config.remove_jdk(jdk_path, is_mapped)  # 移除配置中的 JDK 记录
                
                # 如果选择删除文件夹，才进行文件系统操作
                if result == 2:  # 删除文件夹
                    import shutil
                    if os.path.exists(jdk_path):
                        shutil.rmtree(jdk_path)
                        message = f'JDK {version_text} ({vendor_text}) 及其文件夹已成功删除'
                    else:
                        message = f'JDK {version_text} ({vendor_text}) 文件夹不存在，已从列表移除'
                else:  # 仅从列表移除
                    message = f'JDK {version_text} ({vendor_text}) 已从列表移除'
                
                # 刷新列表
                self.refresh_jdk_list()
                self.update_current_version()
                
                QMessageBox.information(self, '成功', message)
                
        except Exception as e:
            logger.error(f"删除JDK失败: {str(e)}")
            QMessageBox.warning(self, '错误', f'删除JDK失败: {str(e)}')

    def open_jdk_dir(self, path):
        """打开JDK目录"""
        try:
            os.startfile(path)
        except Exception as e:
            logger.error(f"打开目录失败: {str(e)}")
            QMessageBox.warning(self, '错误', f'打开目录失败: {str(e)}') 

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
            
            # 创建自定义成功对话框
            success_dialog = QDialog(self)
            success_dialog.setWindowTitle("切换成功")
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
            
            title_label = QLabel("JDK 切换成功")
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
                message = QLabel("已成功切换到新的 JDK 版本\n请运行以下命令使环境变量生效：")
                message.setObjectName("messageLabel")
                content_layout.addWidget(message)
                
                # 添加命令显示
                cmd_label = QLabel(reload_cmd)
                cmd_label.setObjectName("commandLabel")
                cmd_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                content_layout.addWidget(cmd_label)
            else:
                message = QLabel("已成功切换到新的 JDK 版本\n环境变量已自动更新，可以直接使用")
                message.setObjectName("messageLabel")
                content_layout.addWidget(message)
            
            layout.addWidget(content_widget)
            layout.addStretch()  # 添加弹性空间
            
            # 添加确定按钮
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            ok_button = QPushButton("确定")
            ok_button.setFixedWidth(80)  # 减小按钮宽度
            ok_button.clicked.connect(success_dialog.accept)
            button_layout.addWidget(ok_button)
            layout.addLayout(button_layout)
            
            # 显示对话框
            success_dialog.exec()
        else:
            # 创建错误对话框
            error_dialog = QDialog(self)
            error_dialog.setWindowTitle("切换失败")
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
            
            title_label = QLabel("JDK 切换失败")
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
            
            message = QLabel("切换 JDK 版本失败\n请检查目录权限和路径是否正确")
            message.setObjectName("messageLabel")
            content_layout.addWidget(message)
            
            layout.addWidget(content_widget)
            layout.addStretch()  # 添加弹性空间
            
            # 添加确定按钮
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            ok_button = QPushButton("确定")
            ok_button.setFixedWidth(80)  # 减小按钮宽度
            ok_button.clicked.connect(error_dialog.accept)
            button_layout.addWidget(ok_button)
            layout.addLayout(button_layout)
            
            # 显示对话框
            error_dialog.exec()

    def on_delete_clicked(self):
        """处理删除按钮点击"""
        try:
            # 获取按钮关联的JDK路径
            button = self.sender()
            if not button:
                logger.error("无法获取触发事件的按钮")
                return
                
            jdk_path = button.property('jdk_path')
            if not jdk_path:
                logger.error("按钮未关联JDK路径")
                return
            
            # 调用移除方法
            self.remove_jdk(jdk_path)
                
        except Exception as e:
            logger.error(f"删除JDK失败: {str(e)}")
            QMessageBox.warning(self, '错误', f'删除JDK失败: {str(e)}') 

    def _get_version_type(self, version):
        """获取版本类型"""
        try:
            major_version = int(version.split('.')[0])
            if major_version in [8, 11, 17, 21]:
                return "LTS"
            elif major_version >= 21:
                return "最新版"
            elif major_version >= 17:
                return "过渡版"
            elif major_version >= 11:
                return "旧版本"
            else:
                return "传统版"
        except:
            return "未知版本"

    def _get_version_type_color(self, version_type):
        """获取版本类型对应的颜色"""
        colors = {
            "LTS": "#17a2b8",       # 蓝绿色
            "旧版本": "#6c757d",    # 灰色
            "传统版": "#dc3545",    # 红色
            "未知版本": "#6c757d"   # 灰色
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
            return "未安装"
        except Exception as e:
            logger.error(f"获取系统Java版本失败: {str(e)}")
            return "未知" 