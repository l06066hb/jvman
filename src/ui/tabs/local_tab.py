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
import re

class LocalTab(QWidget):
    """本地管理标签页"""
    
    # 定义信号
    jdk_mapped = pyqtSignal(str, str)  # 版本号，路径
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
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
        try:
            # 清空现有列表
            self.jdk_list.clear()
            
            # 重新加载配置
            self.config.load()
            
            # 获取所有JDK
            jdks = self.config.get_all_jdks()
            
            # 获取当前JDK
            current_jdk = self.config.get_current_jdk()
            current_path = current_jdk['path'] if current_jdk else None
            
            # 按版本号排序
            jdks.sort(key=lambda x: self.version_sort_key(x.get('version', '')), reverse=True)
            
            # 添加JDK条目
            for jdk in jdks:
                if os.path.exists(jdk['path']):
                    # 创建列表项
                    item = QListWidgetItem()
                    
                    # 创建自定义 widget
                    widget = QWidget()
                    layout = QHBoxLayout(widget)
                    layout.setContentsMargins(5, 5, 5, 5)
                    
                    # 版本图标
                    icon_label = QLabel()
                    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'java.png')
                    if os.path.exists(icon_path):
                        icon_label.setPixmap(QIcon(icon_path).pixmap(QSize(24, 24)))
                    layout.addWidget(icon_label)
                    
                    # 信息布局
                    info_layout = QVBoxLayout()
                    info_layout.setSpacing(2)
                    
                    # 版本信息布局（包含版本号和标签）
                    version_layout = QHBoxLayout()
                    version_layout.setSpacing(8)
                    
                    # 版本号
                    version_label = QLabel(f"JDK {jdk['version']}")
                    version_label.setStyleSheet("font-size: 10pt; font-weight: bold;")
                    version_layout.addWidget(version_label)
                    
                    # 当前版本标签
                    if jdk['path'] == current_path:
                        current_tag = QLabel("✓ 已应用")
                        current_tag.setStyleSheet("""
                            background-color: #28a745;
                            color: white;
                            padding: 2px 6px;
                            border-radius: 4px;
                            font-size: 9pt;
                            font-weight: bold;
                        """)
                        version_layout.addWidget(current_tag)
                    
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
                    
                    # 发行商标签
                    vendor = jdk.get('vendor', '未知')
                    vendor_tag = QLabel(vendor)
                    
                    # 为不同发行商设置不同的颜色
                    vendor_colors = {
                        'Oracle': '#F80000',      # Oracle红色
                        'OpenJDK': '#6B94DA',     # OpenJDK蓝色
                        'Temurin': '#2C2255',     # Eclipse深蓝色
                        'Corretto': '#FF9900',    # Amazon橙色
                        'Zulu': '#0095DE',        # Azul蓝色
                        'Microsoft': '#00A4EF',   # Microsoft蓝色
                        '未知': '#757575'         # 灰色
                    }
                    
                    # 获取发行商颜色，如果没有匹配的发行商则使用默认颜色
                    vendor_color = next((color for vendor_name, color in vendor_colors.items() 
                                    if vendor_name.lower() in vendor.lower()), 
                                    vendor_colors['未知'])
                    
                    vendor_tag.setStyleSheet(f"""
                        background-color: {vendor_color};
                        color: white;
                        padding: 2px 6px;
                        border-radius: 4px;
                        font-size: 9pt;
                    """)
                    version_layout.addWidget(vendor_tag)
                    
                    version_layout.addStretch()
                    info_layout.addLayout(version_layout)
                    
                    # 路径和导入时间
                    path_layout = QHBoxLayout()
                    path_label = QLabel(jdk['path'])
                    path_label.setStyleSheet("color: #666666; font-size: 9pt;")
                    path_layout.addWidget(path_label)
                    
                    # 添加导入时间
                    import_time = jdk.get('import_time', '未知')
                    if import_time != '未知':
                        import_time_label = QLabel(f"导入时间: {import_time}")
                    else:
                        import_time_label = QLabel("导入时间: 未知")
                    import_time_label.setStyleSheet("color: #666666; font-size: 9pt;")
                    path_layout.addWidget(import_time_label)
                    
                    path_layout.addStretch()
                    info_layout.addLayout(path_layout)
                    
                    # 将info_layout添加到主布局
                    layout.addLayout(info_layout)
                    
                    # 添加按钮到右侧
                    button_layout = QHBoxLayout()
                    button_layout.setSpacing(8)  # 设置按钮之间的间距
                    
                    # 打开目录按钮
                    open_dir_button = QPushButton("打开目录")
                    open_dir_button.setStyleSheet("""
                        QPushButton {
                            padding: 4px 12px;
                            border: 1px solid #E0E0E0;
                            border-radius: 4px;
                            background-color: white;
                            color: #666666;
                        }
                        QPushButton:hover {
                            background-color: #f8f9fa;
                        }
                    """)
                    open_dir_button.setProperty('jdk_path', jdk['path'])
                    open_dir_button.clicked.connect(lambda _, path=jdk['path']: self.open_jdk_dir(path))
                    button_layout.addWidget(open_dir_button)
                    
                    # 设为当前版本按钮
                    if jdk['path'] != current_path:
                        set_current_button = QPushButton("设为当前版本")
                        set_current_button.setStyleSheet("""
                            QPushButton {
                                padding: 4px 12px;
                                border: none;
                                border-radius: 4px;
                                background-color: #1a73e8;
                                color: white;
                            }
                            QPushButton:hover {
                                background-color: #1557b0;
                            }
                        """)
                        set_current_button.setProperty('jdk_path', jdk['path'])
                        set_current_button.clicked.connect(self.on_set_current_clicked)
                        button_layout.addWidget(set_current_button)
                    
                    # 删除按钮
                    delete_button = QPushButton("删除")
                    delete_button.setStyleSheet("""
                        QPushButton {
                            padding: 4px 12px;
                            border: none;
                            border-radius: 4px;
                            background-color: #dc3545;
                            color: white;
                        }
                        QPushButton:hover {
                            background-color: #c82333;
                        }
                    """)
                    delete_button.setProperty('jdk_path', jdk['path'])
                    delete_button.clicked.connect(self.on_delete_clicked)
                    button_layout.addWidget(delete_button)
                    
                    # 将按钮布局添加到主布局的右侧
                    layout.addLayout(button_layout)
                    
                    # 设置自定义widget
                    item.setSizeHint(widget.sizeHint())
                    self.jdk_list.addItem(item)
                    self.jdk_list.setItemWidget(item, widget)
                    
                else:
                    # 如果路径不存在，从配置中移除
                    logger.debug(f"移除不存在的JDK路径: {jdk['path']}")
                    self.config.remove_jdk(jdk['path'], is_mapped=(jdk.get('type') == 'mapped'))
            
            # 更新当前版本显示
            self.update_current_version()
            
        except Exception as e:
            logger.error(f"刷新JDK列表失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"刷新JDK列表失败: {str(e)}")
            
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
            junction_path = self.config.get('junction_path')
            if os.path.exists(junction_path):
                current_path = os.path.realpath(junction_path)
                if os.path.exists(current_path):
                    for jdk in self.config.get_all_jdks():
                        try:
                            if os.path.exists(jdk['path']) and os.path.samefile(jdk['path'], current_path):
                                java_path = os.path.join(current_path, 'bin', 'java.exe')
                                detailed_version = self.get_detailed_version(java_path)
                                version_text = f"当前版本: JDK {jdk['version']}"
                                if detailed_version:
                                    version_text += f" ({detailed_version})"
                                self.current_version_label.setText(version_text)
                                return
                        except Exception as e:
                            logger.error(f"检查JDK版本失败: {str(e)}")
                            continue
            
            # 如果没有找到有效的当前版本
            self.current_version_label.setText("当前版本: 未设置")
            
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
        from utils.system_utils import create_junction
        if create_junction(jdk['path'], junction_path):
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
        """处理设为当前版本按钮点击"""
        try:
            # 获取按钮关联的JDK路径
            button = self.sender()
            jdk_path = button.property('jdk_path')
            if not jdk_path:
                return
            
            # 创建软链接
            junction_path = self.config.get('junction_path')
            from utils.system_utils import create_junction
            
            # 如果已存在软链接，先删除
            if os.path.exists(junction_path):
                try:
                    os.unlink(junction_path)
                except Exception as e:
                    logger.error(f"删除已存在的软链接失败: {str(e)}")
                    QMessageBox.warning(self, '错误', '切换JDK版本失败：无法删除已存在的软链接')
                    return
            
            # 创建新的软链接
            if create_junction(jdk_path, junction_path):
                # 获取JDK信息用于显示消息
                jdk_info = None
                for jdk in self.config.get_all_jdks():
                    if jdk['path'] == jdk_path:
                        jdk_info = jdk
                        break
                
                version_text = jdk_info['version'] if jdk_info else '未知版本'
                vendor_text = jdk_info.get('vendor', '未知')
                
                # 刷新列表和当前版本显示
                self.refresh_jdk_list()
                self.update_current_version()
                QMessageBox.information(self, '成功', f'已切换到 JDK {version_text} ({vendor_text})')
            else:
                QMessageBox.warning(self, '错误', '切换JDK版本失败：创建软链接失败')
                
        except Exception as e:
            logger.error(f"设置当前版本失败: {str(e)}")
            QMessageBox.warning(self, '错误', f'设置当前版本失败: {str(e)}')

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
            "最新版": "#28a745",    # 绿色
            "过渡版": "#fd7e14",    # 橙色
            "旧版本": "#6c757d",    # 灰色
            "传统版": "#dc3545",    # 红色
            "未知版本": "#6c757d"   # 灰色
        }
        return colors.get(version_type, "#6c757d") 