import os
import subprocess
from loguru import logger
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QListWidget, QListWidgetItem,
    QMessageBox, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap

class LocalTab(QWidget):
    """本地管理标签页"""
    
    # 定义信号
    jdk_mapped = pyqtSignal(str, str)  # 版本号，路径
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # 当前版本显示
        version_container = QWidget()
        version_container.setObjectName('version_container')
        version_container.setFixedHeight(50)
        version_container.setStyleSheet("""
            QWidget#version_container {
                background-color: #EBF3FE;
                border-radius: 8px;
            }
        """)
        
        version_layout = QHBoxLayout(version_container)
        version_layout.setContentsMargins(16, 0, 16, 0)
        version_layout.setSpacing(8)
        
        # 添加check-circle图标
        check_icon = QLabel()
        check_icon.setStyleSheet("background: transparent;")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'check-circle.png')
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            pixmap.setDevicePixelRatio(1)  # 确保清晰度
            check_icon.setPixmap(pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        version_layout.addWidget(check_icon)
        
        # 添加Java图标
        version_icon = QLabel()
        version_icon.setStyleSheet("background: transparent;")
        java_icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'java-current.png')
        java_pixmap = QPixmap(java_icon_path)
        if not java_pixmap.isNull():
            java_pixmap.setDevicePixelRatio(1)  # 确保清晰度
            version_icon.setPixmap(java_pixmap.scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        version_layout.addWidget(version_icon)
        
        # 版本号标签
        self.current_version_label = QLabel('当前版本: 未设置')
        self.current_version_label.setObjectName('current_version_label')
        self.current_version_label.setStyleSheet("""
            QLabel#current_version_label {
                color: #1a73e8;
                font-weight: bold;
                font-size: 13px;
                background: transparent;
            }
        """)
        version_layout.addWidget(self.current_version_label)
        version_layout.addStretch()
        
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
        add_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'add.png')))
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
        
        # 切换版本按钮
        switch_button = QPushButton('切换版本')
        switch_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'switch.png')))
        switch_button.clicked.connect(self.switch_version)
        switch_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #1a73e8;
                border-radius: 4px;
                background-color: white;
                color: #1a73e8;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F5F9FF;
            }
            QPushButton:pressed {
                background-color: #E8F0FE;
            }
        """)
        
        # 移除JDK按钮
        remove_button = QPushButton('移除JDK')
        remove_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'remove.png')))
        remove_button.clicked.connect(self.remove_jdk)
        remove_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                color: #666666;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
                border-color: #D0D0D0;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
            }
        """)
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(switch_button)
        button_layout.addWidget(remove_button)
        button_layout.addStretch()
        
        layout.addWidget(button_container)
        
        # 刷新JDK列表
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
                timeout=5
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
                
            result = subprocess.run(
                [java_path, '-version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=5
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
        self.jdk_list.clear()
        jdks = self.config.get_all_jdks()
        
        for jdk in jdks:
            # 创建列表项容器
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(10, 5, 10, 5)
            
            # 左侧信息容器
            info_container = QWidget()
            info_layout = QVBoxLayout(info_container)
            info_layout.setSpacing(4)
            
            # 第一行：版本和发行版
            version_layout = QHBoxLayout()
            version_label = QLabel(f"JDK {jdk['version']}")
            version_label.setProperty('version', True)
            
            # 获取详细版本
            java_path = os.path.join(jdk['path'], 'bin', 'java.exe')
            detailed_version = self.get_detailed_version(java_path)
            if detailed_version:
                version_label.setText(f"JDK {jdk['version']} ({detailed_version})")
            
            # 发行版标签
            vendor_name = self.get_vendor_name(jdk['path'])
            vendor_label = QLabel(vendor_name)
            vendor_label.setStyleSheet("""
                QLabel {
                    background-color: #E3F2FD;
                    color: #1976D2;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 11px;
                }
            """)
            
            version_layout.addWidget(version_label)
            version_layout.addWidget(vendor_label)
            version_layout.addStretch()
            
            # 第二行：路径
            path_label = QLabel(jdk['path'])
            path_label.setStyleSheet("color: #666666; font-size: 12px;")
            
            # 第三行：导入时间
            time_label = QLabel(f"导入时间: {jdk.get('import_time', '未知')}")
            time_label.setStyleSheet("color: #666666; font-size: 11px;")
            
            info_layout.addLayout(version_layout)
            info_layout.addWidget(path_label)
            info_layout.addWidget(time_label)
            
            # 右侧按钮容器
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setSpacing(8)
            
            # 当前版本标签
            if self.is_current_version(jdk['path']):
                current_label = QLabel("应用中")
                current_label.setStyleSheet("""
                    QLabel {
                        color: #34A853;
                        font-weight: bold;
                        padding-right: 8px;
                    }
                """)
                button_layout.addWidget(current_label)
            
            # 打开目录图标
            open_icon = QLabel()
            open_icon.setPixmap(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'folder.png')).pixmap(QSize(20, 20)))
            open_icon.setCursor(Qt.CursorShape.PointingHandCursor)
            open_icon.mousePressEvent = lambda e, path=jdk['path']: self.open_jdk_dir(path)
            button_layout.addWidget(open_icon)
            
            # 添加到主布局
            item_layout.addWidget(info_container, stretch=1)
            item_layout.addWidget(button_container)
            
            # 创建列表项
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            list_item.setData(Qt.ItemDataRole.UserRole, jdk)
            
            self.jdk_list.addItem(list_item)
            self.jdk_list.setItemWidget(list_item, item_widget)
            
        # 更新当前版本显示
        self.update_current_version()

    def update_current_version(self):
        """更新当前版本显示"""
        junction_path = self.config.get('junction_path')
        if os.path.exists(junction_path):
            try:
                current_path = os.path.realpath(junction_path)
                for jdk in self.config.get_all_jdks():
                    if os.path.samefile(jdk['path'], current_path):
                        java_path = os.path.join(current_path, 'bin', 'java.exe')
                        detailed_version = self.get_detailed_version(java_path)
                        version_text = f"当前版本: JDK {jdk['version']}"
                        if detailed_version:
                            version_text += f" ({detailed_version})"
                        self.current_version_label.setText(version_text)
                        return
            except Exception as e:
                logger.error(f"更新当前版本显示失败: {str(e)}")
        
        self.current_version_label.setText("当前版本: 未设置")

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
            self.config.add_mapped_jdk({
                'version': version,
                'path': jdk_path,
                'type': 'mapped',
                'import_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # 发送信号
            self.jdk_mapped.emit(version, jdk_path)
            
            # 刷新列表
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
        from utils.system_utils import create_junction
        if create_junction(jdk['path'], junction_path):
            self.refresh_jdk_list()
            QMessageBox.information(self, '成功', f'已切换到 JDK {jdk["version"]}')
        else:
            QMessageBox.warning(self, '错误', '切换JDK版本失败')

    def remove_jdk(self):
        """移除JDK"""
        current_item = self.jdk_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, '警告', '请先选择要移除的JDK')
            return
            
        jdk = current_item.data(Qt.ItemDataRole.UserRole)
        
        # 创建确认对话框
        dialog = QDialog(self)
        dialog.setWindowTitle('移除JDK')
        dialog.setFixedWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # 提示文本
        label = QLabel(f'确定要移除 JDK {jdk["version"]} 吗？')
        layout.addWidget(label)
        
        # 按钮
        button_box = QDialogButtonBox()
        delete_button = QPushButton('删除文件夹')
        delete_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                background-color: #dc3545;
                color: white;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        
        remove_button = QPushButton('仅从列表移除')
        remove_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #6c757d;
                border-radius: 4px;
                background-color: white;
                color: #6c757d;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
            }
        """)
        
        cancel_button = QPushButton('取消')
        cancel_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                color: #666666;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
            }
        """)
        
        button_box.addButton(delete_button, QDialogButtonBox.ButtonRole.DestructiveRole)
        button_box.addButton(remove_button, QDialogButtonBox.ButtonRole.ActionRole)
        button_box.addButton(cancel_button, QDialogButtonBox.ButtonRole.RejectRole)
        
        layout.addWidget(button_box)
        
        # 连接��号
        delete_button.clicked.connect(dialog.accept)
        remove_button.clicked.connect(lambda: dialog.done(2))
        cancel_button.clicked.connect(dialog.reject)
        
        # 显示对话框
        result = dialog.exec()
        
        if result != QDialog.DialogCode.Rejected:
            try:
                version = jdk['version']
                path = jdk['path']
                
                # 如果是当前使用的版本，先取消链接
                junction_path = self.config.get('junction_path')
                if os.path.exists(junction_path):
                    try:
                        if os.path.samefile(path, os.path.realpath(junction_path)):
                            os.unlink(junction_path)
                    except Exception as e:
                        logger.error(f"取消软链接失败: {str(e)}")
                
                # 从配置中移除
                self.config.remove_jdk(path, jdk.get('type') == 'mapped')
                
                # 如果选择删除文件夹，才进行文件系统操作
                if result == QDialog.DialogCode.Accepted:
                    import shutil
                    if os.path.exists(path):
                        shutil.rmtree(path)
                        message = f'JDK {version} 及其文件夹已成功��除'
                    else:
                        message = f'JDK {version} 文件夹不存在，已从列表移除'
                else:
                    message = f'JDK {version} 已从列表移除'
                
                # 刷新列表
                self.refresh_jdk_list()
                
                QMessageBox.information(self, '成功', message)
                
            except Exception as e:
                logger.error(f"移除JDK失败: {str(e)}")
                QMessageBox.warning(self, '错误', f'移除JDK失败: {str(e)}')

    def open_jdk_dir(self, path):
        """打开JDK目录"""
        try:
            os.startfile(path)
        except Exception as e:
            logger.error(f"打开目录失败: {str(e)}")
            QMessageBox.warning(self, '错误', f'打开目录失败: {str(e)}') 