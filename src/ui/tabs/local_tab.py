import os
import shutil
from loguru import logger
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QFileDialog,
    QInputDialog, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon
from utils.system_utils import create_junction, set_environment_variable, update_path_variable

class LocalTab(QWidget):
    """本地管理标签页"""
    
    # 定义信号
    jdk_mapped = pyqtSignal(str, str)  # 版本，路径
    version_switched = pyqtSignal()  # 添加版本切换信号

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # 增加组件间距
        
        # 当前版本信息
        info_container = QWidget()
        info_container.setObjectName('version_container')
        info_container.setStyleSheet("""
            QWidget#version_container {
                background-color: #E3F2FD;
                border: 1px solid #90CAF9;
                border-radius: 8px;
            }
        """)
        info_layout = QHBoxLayout(info_container)
        info_layout.setContentsMargins(15, 10, 15, 10)
        
        # 版本图标和文本容器
        version_content = QHBoxLayout()
        version_content.setSpacing(8)
        
        current_icon = QLabel()
        current_icon.setPixmap(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'java-current.png')).pixmap(QSize(24, 24)))
        version_content.addWidget(current_icon)
        
        self.current_version_label = QLabel('当前版本: 未设置')
        self.current_version_label.setObjectName('current_version_label')
        self.current_version_label.setStyleSheet("""
            QLabel#current_version_label {
                color: #1976D2;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        version_content.addWidget(self.current_version_label)
        version_content.addStretch()
        
        info_layout.addLayout(version_content)
        layout.addWidget(info_container)
        
        # JDK列表区域
        list_layout = QVBoxLayout()
        list_label = QLabel('已安装的JDK:')
        list_label.setStyleSheet("font-weight: bold; font-size: 13px; padding: 5px 0;")
        self.jdk_list = QListWidget()
        # 设置列表样式
        self.jdk_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 5px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 6px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: #F5F5F5;
            }
            QListWidget::item:hover {
                background-color: #F8F8F8;
            }
        """)
        
        list_layout.addWidget(list_label)
        list_layout.addWidget(self.jdk_list)
        
        layout.addLayout(list_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 0, 5, 0)
        
        self.add_button = QPushButton('添加本地JDK')
        self.add_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'add.png')))
        self.remove_button = QPushButton('移除')
        self.remove_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'remove.png')))
        self.switch_button = QPushButton('切换版本')
        self.switch_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'switch.png')))
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()
        button_layout.addWidget(self.switch_button)
        
        layout.addLayout(button_layout)

        # 连接信号
        self.add_button.clicked.connect(self.add_local_jdk)
        self.remove_button.clicked.connect(self.remove_jdk)
        self.switch_button.clicked.connect(self.switch_version)
        
        # 初始化JDK列表
        self.refresh_jdk_list()
        self.update_current_version()

    def get_detailed_version(self, java_path):
        """获取JDK详细版本号"""
        try:
            if not os.path.exists(java_path):
                return None
                
            import subprocess
            # 修复参数冲突，使用capture_output=True时不能同时指定stderr
            result = subprocess.run([java_path, '-version'], 
                                 capture_output=True, 
                                 text=True,
                                 timeout=5)
            
            # 版本信息在stderr中
            if result.stderr:
                # 正则匹配版本号
                import re
                match = re.search(r'version "([^"]+)"', result.stderr)
                if match:
                    return match.group(1)
            return None
        except subprocess.TimeoutExpired:
            logger.error("获取JDK版本超时")
            return None
        except Exception as e:
            logger.error(f"获取JDK版本失败: {str(e)}")
            return None

    def refresh_jdk_list(self):
        """刷新JDK列表"""
        self.jdk_list.clear()
        jdks = self.config.get_all_jdks()
        
        # 获取当前JDK版本
        current_junction = self.config.get('junction_path')
        current_version = None
        if os.path.exists(current_junction):
            for jdk in jdks:
                try:
                    if os.path.samefile(jdk['path'], os.path.realpath(current_junction)):
                        current_version = jdk['version']
                        break
                except Exception:
                    continue
        
        # 更新当前版本显示
        if current_version:
            try:
                detailed_version = self.get_detailed_version(os.path.join(current_junction, 'bin', 'java.exe'))
                version_text = f'当前版本: JDK {current_version}'
                if detailed_version:
                    version_text += f' ({detailed_version})'
                self.current_version_label.setText(version_text)
            except Exception as e:
                logger.error(f"更新版本显示失败: {str(e)}")
                self.current_version_label.setText(f'当前版本: JDK {current_version}')
        else:
            self.current_version_label.setText('当前版本: 未设置')
        
        for jdk in jdks:
            item = QListWidgetItem()
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(16, 12, 16, 12)
            layout.setSpacing(16)
            
            # 版本图标
            icon_label = QLabel()
            icon_label.setFixedSize(32, 32)
            if jdk['version'] == current_version:
                icon_label.setPixmap(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'java-version.png')).pixmap(QSize(32, 32)))
            else:
                icon_label.setPixmap(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'type_java.png')).pixmap(QSize(32, 32)))
            layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
            
            # 版本号和详细版本
            version_container = QWidget()
            version_layout = QVBoxLayout(version_container)
            version_layout.setContentsMargins(0, 0, 0, 0)
            version_layout.setSpacing(2)
            
            # 主版本号
            version_label = QLabel(f"JDK {jdk['version']}")
            version_label.setProperty('version', True)
            version_layout.addWidget(version_label)
            
            # 详细版本号
            detailed_version = self.get_detailed_version(os.path.join(jdk['path'], 'bin', 'java.exe'))
            if detailed_version:
                detail_label = QLabel(detailed_version)
                detail_label.setProperty('detail', True)
                detail_label.setStyleSheet("QLabel[detail='true'] { color: #666666; font-size: 11px; }")
                version_layout.addWidget(detail_label)
            
            layout.addWidget(version_container, 0, Qt.AlignmentFlag.AlignVCenter)
            
            # 添加弹性空间
            layout.addStretch()
            
            # 当前版本标签
            if jdk['version'] == current_version:
                status_container = QWidget()
                status_layout = QHBoxLayout(status_container)
                status_layout.setContentsMargins(0, 0, 0, 0)
                status_layout.setSpacing(4)
                
                # 添加对勾图标
                check_label = QLabel()
                check_label.setPixmap(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'check.png')).pixmap(QSize(16, 16)))
                status_layout.addWidget(check_label)
                
                # 添加星标图标
                star_label = QLabel()
                star_label.setPixmap(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'star.png')).pixmap(QSize(16, 16)))
                status_layout.addWidget(star_label)
                
                # 添加"应用中"文字
                current_label = QLabel("应用中")
                current_label.setProperty('current', True)
                status_layout.addWidget(current_label)
                
                layout.addWidget(status_container, 0, Qt.AlignmentFlag.AlignVCenter)
            
            # 打开目录按钮
            open_button = QPushButton()
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'folder-open.png')
            if os.path.exists(icon_path):
                open_button.setIcon(QIcon(icon_path))
                open_button.setIconSize(QSize(18, 18))
            open_button.setToolTip('打开JDK目录')
            open_button.setProperty('path', jdk['path'])
            open_button.setProperty('transparent', True)
            open_button.setFixedSize(20, 20)
            open_button.clicked.connect(self.open_jdk_directory)
            open_button.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(open_button, 0, Qt.AlignmentFlag.AlignVCenter)
            
            # 存储版本信息
            item.setData(Qt.ItemDataRole.UserRole, jdk)
            
            # 设置项目大小
            item.setSizeHint(QSize(widget.sizeHint().width(), 72))
            self.jdk_list.addItem(item)
            self.jdk_list.setItemWidget(item, widget)

    def add_local_jdk(self):
        """添加本地JDK"""
        # 选择JDK目录
        jdk_dir = QFileDialog.getExistingDirectory(
            self,
            "选择JDK目录",
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not jdk_dir:
            return
            
        # 获取版本号
        version, ok = QInputDialog.getText(
            self,
            "输入版本号",
            "请输入JDK版本号(例如: 8, 11, 17):"
        )
        
        if not ok or not version:
            return
            
        # 验证目录
        if not os.path.exists(os.path.join(jdk_dir, 'bin', 'java.exe')):
            QMessageBox.warning(self, '错误', '所选目录不是有效的JDK目录')
            return
            
        # 添加到配置
        self.jdk_mapped.emit(version, jdk_dir)
        self.refresh_jdk_list()

    def remove_jdk(self):
        """移除JDK"""
        try:
            # 获取当前选中的项
            current_item = self.jdk_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, '警告', '请先选择要移除的JDK')
                return
            
            # 获取选中项的数据
            jdk_data = current_item.data(Qt.ItemDataRole.UserRole)
            if not jdk_data:
                QMessageBox.warning(self, '错误', '无法获取JDK信息')
                return
            
            version = jdk_data['version']
            path = jdk_data['path']
            
            # 确认对话框，提供选项
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle('确认移除')
            msg_box.setText(f'要如何移除 JDK {version}？')
            delete_button = msg_box.addButton('删除文件夹', QMessageBox.ButtonRole.DestructiveRole)
            remove_button = msg_box.addButton('仅从列表移除', QMessageBox.ButtonRole.ActionRole)
            cancel_button = msg_box.addButton('取消', QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(cancel_button)
            
            msg_box.exec()
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == cancel_button:
                return
                
            # 如果选择删除文件夹，才进行文件系统操作
            if clicked_button == delete_button:
                # 如果是当前使用的版本，先取消链接
                junction_path = self.config.get('junction_path')
                if os.path.exists(junction_path):
                    try:
                        current_path = os.path.realpath(junction_path)
                        if os.path.samefile(current_path, path):
                            self.unlink_jdk()
                    except Exception as e:
                        logger.error(f"检查当前版本失败: {str(e)}")
                
                # 删除JDK文件夹
                try:
                    if os.path.exists(path):
                        # 先尝试修改文件属性
                        import win32file
                        import win32con
                        try:
                            win32file.SetFileAttributes(path, win32con.FILE_ATTRIBUTE_NORMAL)
                        except Exception as e:
                            logger.warning(f"修改文件属性失败: {str(e)}")
                        
                        # 使用系统命令强制删除
                        os.system(f'rd /s /q "{path}"')
                        
                        # 检查是否删除成功
                        if os.path.exists(path):
                            shutil.rmtree(path, ignore_errors=True)
                        
                        message = f'JDK {version} 及其文件夹已成功移除'
                    else:
                        message = f'JDK {version} 文件夹不存在，已从列表移除'
                except Exception as e:
                    logger.error(f"删除文件夹失败: {str(e)}")
                    message = f'JDK {version} 已从列表移除，但删除文件夹失败'
            else:  # remove_button
                message = f'JDK {version} 已从列表移除'
            
            # 从列表中移除
            row = self.jdk_list.row(current_item)
            self.jdk_list.takeItem(row)
            
            # 从配置中移除
            jdks = self.config.get_all_jdks()
            jdks = [jdk for jdk in jdks if jdk['path'] != path]
            self.config.set('jdks', jdks)
            
            QMessageBox.information(self, '成功', message)
        
        except Exception as e:
            logger.error(f"移除JDK失败: {str(e)}")
            QMessageBox.warning(self, '错误', f'移除失败: {str(e)}')

    def switch_version(self):
        """切换JDK版本"""
        try:
            current_item = self.jdk_list.currentItem()
            if not current_item:
                QMessageBox.warning(self, '警告', '请先选择要切换的JDK版本')
                return
                
            # 获取JDK信息
            jdk = current_item.data(Qt.ItemDataRole.UserRole)
            if not jdk:
                QMessageBox.warning(self, '错误', '无法获取JDK信息')
                return
                
            # 创建软链接
            junction_path = self.config.get('junction_path')
            
            # 如果已存在链接，先移除
            if os.path.exists(junction_path):
                try:
                    # 先尝试使用rmdir命令
                    os.system(f'rmdir /q /s "{junction_path}"')
                    # 等待文件系统更新
                    import time
                    time.sleep(0.5)
                    # 如果还存在，则强制删除
                    if os.path.exists(junction_path):
                        import win32file
                        import win32con
                        # 修改文件属性
                        win32file.SetFileAttributes(junction_path, win32con.FILE_ATTRIBUTE_NORMAL)
                        os.system(f'rd /s /q "{junction_path}"')
                except Exception as e:
                    logger.error(f"移除旧链接失败: {str(e)}")
                    QMessageBox.warning(self, '错误', '无法移除旧版本，请确保没有程序正在使用JDK')
                    return
            
            # 创建新链接
            try:
                if create_junction(jdk['path'], junction_path):
                    # 更新当前版本
                    self.current_version = jdk['version']
                    # 刷新显示
                    self.refresh_jdk_list()
                    # 发送版本切换信号
                    self.version_switched.emit()
                    # 显示通知
                    QMessageBox.information(self, '成功', f'已切换到 JDK {jdk["version"]}')
                else:
                    QMessageBox.warning(self, '错误', '创建链接失败，请检查权限或重试')
            except Exception as e:
                logger.error(f"创建链接失败: {str(e)}")
                QMessageBox.warning(self, '错误', '创建链接失败: ' + str(e))
        
        except Exception as e:
            logger.error(f"切换JDK版本失败: {str(e)}")
            QMessageBox.warning(self, '错误', f'切换版本失败: {str(e)}')

    def update_current_version(self):
        """更新当前版本显示"""
        self.refresh_jdk_list()  # 重新加载列表以更新显示

    def update_settings(self):
        """更新设置"""
        self.update_current_version() 

    def open_jdk_directory(self):
        """打开JDK目录"""
        button = self.sender()
        if button:
            path = button.property('path')
            if path and os.path.exists(path):
                os.startfile(path) 