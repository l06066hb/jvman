import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QComboBox,
    QCheckBox, QMessageBox, QFrame, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QFont
from utils.system_utils import set_environment_variable, update_path_variable

class SettingsTab(QWidget):
    """设置标签页"""
    
    # 定义信号
    settings_changed = pyqtSignal()

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # 增加组件间距

        # 基本设置组
        basic_group = QGroupBox("基本设置")
        basic_group.setStyleSheet("""
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
        basic_layout = QVBoxLayout(basic_group)
        basic_layout.setSpacing(10)
        
        # JDK存储路径设置
        store_layout = QHBoxLayout()
        store_label = QLabel('JDK存储路径:')
        store_label.setMinimumWidth(100)
        self.store_path_edit = QLineEdit()
        self.store_path_edit.setStyleSheet("padding: 5px; border: 1px solid #E0E0E0; border-radius: 4px;")
        self.store_path_edit.setText(self.config.get('jdk_store_path'))
        self.store_path_button = QPushButton('浏览')
        self.store_path_button.setProperty('browse', True)
        self.store_path_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'folder.png')))
        self.store_path_button.setStyleSheet("""
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
        
        store_layout.addWidget(store_label)
        store_layout.addWidget(self.store_path_edit)
        store_layout.addWidget(self.store_path_button)
        
        # 软链接路径设置
        junction_layout = QHBoxLayout()
        junction_label = QLabel('软链接路径:')
        junction_label.setMinimumWidth(100)
        self.junction_path_edit = QLineEdit()
        self.junction_path_edit.setStyleSheet("padding: 5px; border: 1px solid #E0E0E0; border-radius: 4px;")
        self.junction_path_edit.setText(self.config.get('junction_path'))
        self.junction_path_button = QPushButton('浏览')
        self.junction_path_button.setProperty('browse', True)
        self.junction_path_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'folder.png')))
        self.junction_path_button.setStyleSheet(self.store_path_button.styleSheet())
        
        junction_layout.addWidget(junction_label)
        junction_layout.addWidget(self.junction_path_edit)
        junction_layout.addWidget(self.junction_path_button)
        
        # 主题设置
        theme_layout = QHBoxLayout()
        theme_label = QLabel('界面主题:')
        theme_label.setMinimumWidth(100)
        self.theme_combo = QComboBox()
        self.theme_combo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #FFFFFF;
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
        self.theme_combo.addItems(['浅色', '深色', '青色'])
        current_theme = self.config.get('theme', 'light')
        if current_theme == 'light':
            self.theme_combo.setCurrentText('浅色')
        elif current_theme == 'dark':
            self.theme_combo.setCurrentText('深色')
        else:
            self.theme_combo.setCurrentText('青色')
        
        # 连接主题变更信号
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        # 自启动设置
        auto_start_layout = QHBoxLayout()
        auto_start_label = QLabel('开机自启动:')
        auto_start_label.setMinimumWidth(100)
        
        self.auto_start_checkbox = QCheckBox()
        self.auto_start_checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 8px;
                padding: 4px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                border: none;
                border-radius: 3px;
                background-color: #1a73e8;
                image: url(icon/check.png);
            }
        """)
        self.auto_start_checkbox.setChecked(self.config.get_auto_start_status())
        
        auto_start_layout.addWidget(auto_start_label)
        auto_start_layout.addWidget(self.auto_start_checkbox)
        auto_start_layout.addStretch()
        
        # 添加到基本设置布局
        basic_layout.addLayout(store_layout)
        basic_layout.addLayout(junction_layout)
        basic_layout.addLayout(theme_layout)
        basic_layout.addLayout(auto_start_layout)
        
        # 保存按钮
        self.save_button = QPushButton('保存设置')
        self.save_button.setObjectName('save_button')
        self.save_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'save.png')))
        self.save_button.setStyleSheet("""
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
        basic_layout.addWidget(self.save_button, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addWidget(basic_group)

        # 环境变量设置组
        env_group = QGroupBox("环境变量设置")
        env_group.setStyleSheet(basic_group.styleSheet())
        env_layout = QVBoxLayout(env_group)
        env_layout.setSpacing(10)
        
        # 自动设置区域
        auto_container = QFrame()
        auto_container.setObjectName('desc_container')
        auto_container.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border-radius: 6px;
                padding: 2px;
            }
        """)
        auto_layout = QVBoxLayout(auto_container)
        auto_layout.setSpacing(8)
        auto_layout.setContentsMargins(15, 15, 15, 15)

        # 自动设置说明
        auto_desc = QLabel('方式一：自动设置：通过下方选项自动设置系统环境变量')
        auto_desc.setProperty('description', True)
        auto_desc.setStyleSheet("""
            QLabel {
                color: #333333;
                padding: 5px;
                font-weight: bold;
                background: transparent;
            }
        """)
        auto_desc.setFont(QFont("Microsoft YaHei", 10))
        auto_desc.setText("⚙️ 方式一：自动设置：通过下方选项自动设置系统环境变量")
        auto_layout.addWidget(auto_desc)

        # 环境变量选项
        self.env_java_home = QCheckBox('设置 JAVA_HOME')
        self.env_path = QCheckBox('添加到 PATH')
        self.env_classpath = QCheckBox('设置 CLASSPATH')
        
        checkbox_style = """
            QCheckBox {
                spacing: 8px;
                padding: 4px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                border: none;
                border-radius: 3px;
                background-color: #1a73e8;
                image: url(icon/check.png);
            }
        """
        self.env_java_home.setStyleSheet(checkbox_style)
        self.env_path.setStyleSheet(checkbox_style)
        self.env_classpath.setStyleSheet(checkbox_style)
        
        auto_layout.addWidget(self.env_java_home)
        auto_layout.addWidget(self.env_path)
        auto_layout.addWidget(self.env_classpath)
        
        # 应用环境变量按钮
        self.apply_env_button = QPushButton('应用环境变量设置')
        self.apply_env_button.setObjectName('apply_env_button')
        self.apply_env_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'icon', 'apply.png')))
        self.apply_env_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #1a73e8;
                border-radius: 4px;
                background-color: white;
                color: #1a73e8;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
            }
            QPushButton:pressed {
                background-color: #E8F0FE;
            }
        """)
        auto_layout.addWidget(self.apply_env_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        env_layout.addWidget(auto_container)
        
        # 手动设置区域
        manual_container = QFrame()
        manual_container.setObjectName('desc_container')
        manual_container.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border-radius: 6px;
                padding: 2px;
            }
        """)
        manual_layout = QVBoxLayout(manual_container)
        manual_layout.setSpacing(8)
        manual_layout.setContentsMargins(15, 15, 15, 15)

        # 手动设置说明
        manual_desc = QLabel('方式二：手动设置：复制以下内容到系统环境变量中')
        manual_desc.setProperty('description', True)
        manual_desc.setStyleSheet("""
            QLabel {
                color: #333333;
                padding: 5px;
                font-weight: bold;
                background: transparent;
            }
        """)
        manual_desc.setFont(QFont("Microsoft YaHei", 10))
        manual_desc.setText("📋 方式二：手动设置：复制以下内容到系统环境变量中")
        manual_layout.addWidget(manual_desc)

        # 环境变量值容器
        values_frame = QFrame()
        values_frame.setObjectName('values_frame')
        values_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        """)
        values_layout = QVBoxLayout(values_frame)
        values_layout.setSpacing(4)
        values_layout.setContentsMargins(10, 10, 10, 10)

        # JAVA_HOME
        java_home_layout = QHBoxLayout()
        java_home_label = QLabel('JAVA_HOME')
        java_home_label.setMinimumWidth(100)
        java_home_label.setStyleSheet("font-weight: bold;")
        self.java_home_value = QLineEdit(self.junction_path_edit.text())
        self.java_home_value.setReadOnly(True)
        self.java_home_value.setMinimumWidth(400)
        self.java_home_value.setStyleSheet("""
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: #F8F9FA;
                selection-background-color: #E8F0FE;
            }
        """)
        java_home_layout.addWidget(java_home_label)
        java_home_layout.addWidget(self.java_home_value)
        values_layout.addLayout(java_home_layout)

        # PATH
        path_layout = QHBoxLayout()
        path_label = QLabel('PATH')
        path_label.setMinimumWidth(100)
        path_label.setStyleSheet("font-weight: bold;")
        path_value = QLineEdit('%JAVA_HOME%\\bin')
        path_value.setReadOnly(True)
        path_value.setMinimumWidth(400)
        path_value.setStyleSheet(self.java_home_value.styleSheet())
        path_layout.addWidget(path_label)
        path_layout.addWidget(path_value)
        values_layout.addLayout(path_layout)

        # CLASSPATH
        classpath_layout = QHBoxLayout()
        classpath_label = QLabel('CLASSPATH')
        classpath_label.setMinimumWidth(100)
        classpath_label.setStyleSheet("font-weight: bold;")
        classpath_value = QLineEdit('.;%JAVA_HOME%\\lib\\dt.jar;%JAVA_HOME%\\lib\\tools.jar')
        classpath_value.setReadOnly(True)
        classpath_value.setMinimumWidth(400)
        classpath_value.setStyleSheet(self.java_home_value.styleSheet())
        classpath_layout.addWidget(classpath_label)
        classpath_layout.addWidget(classpath_value)
        values_layout.addLayout(classpath_layout)

        manual_layout.addWidget(values_frame)
        env_layout.addWidget(manual_container)
        
        # 添加环境变量组到主布局
        layout.addWidget(env_group)
        
        # 添加弹性空间
        layout.addStretch()
        
        # 连接信号
        self.store_path_button.clicked.connect(self.select_store_path)
        self.junction_path_button.clicked.connect(self.select_junction_path)
        self.save_button.clicked.connect(self.save_settings)
        self.apply_env_button.clicked.connect(self.apply_env_settings)
        
        # 连接路径编辑框变更信号以更新说明文本
        self.junction_path_edit.textChanged.connect(self.update_env_description)

    def select_store_path(self):
        """选择JDK存储路径"""
        path = QFileDialog.getExistingDirectory(
            self,
            "选择JDK存储路径",
            self.store_path_edit.text(),
            QFileDialog.Option.ShowDirsOnly
        )
        if path:
            self.store_path_edit.setText(path)

    def select_junction_path(self):
        """选择软链接路径"""
        path = QFileDialog.getExistingDirectory(
            self,
            "选择软链接路径",
            self.junction_path_edit.text(),
            QFileDialog.Option.ShowDirsOnly
        )
        if path:
            self.junction_path_edit.setText(path)

    def save_settings(self):
        """保存设置"""
        # 保存JDK存储路径
        self.config.set('jdk_store_path', self.store_path_edit.text())
        
        # 保存软链接路径
        self.config.set('junction_path', self.junction_path_edit.text())
        
        # 保存自启动设置
        self.config.set_auto_start(self.auto_start_checkbox.isChecked())
        
        # 发送设置变更信号
        self.settings_changed.emit()
        
        # 显示保存成功提示
        QMessageBox.information(self, '成功', '设置已保存')

    def apply_env_settings(self):
        """应用环境变量设置"""
        junction_path = self.junction_path_edit.text()
        
        try:
            if self.env_java_home.isChecked():
                set_environment_variable('JAVA_HOME', junction_path)
            
            if self.env_path.isChecked():
                update_path_variable(os.path.join(junction_path, 'bin'))
            
            if self.env_classpath.isChecked():
                classpath = f".;%JAVA_HOME%\\lib\\dt.jar;%JAVA_HOME%\\lib\\tools.jar"
                set_environment_variable('CLASSPATH', classpath)
            
            QMessageBox.information(self, '成功', '环境变量设置已更新')
        except Exception as e:
            QMessageBox.warning(self, '错误', f'设置环境变量失败: {str(e)}') 

    def update_env_description(self):
        """更新环境变量说明文本"""
        if hasattr(self, 'java_home_value_label'):
            self.java_home_value_label.setText('= ' + self.junction_path_edit.text()) 

    def on_theme_changed(self, text):
        """处理主题变更"""
        if text == '浅色':
            theme = 'light'
        elif text == '深色':
            theme = 'dark'
        else:
            theme = 'cyan'
        
        # 保存主题设置
        self.config.set('theme', theme)
        # 发送设置变更信号
        self.settings_changed.emit()
        # 保存配置
        self.config.save()

    def reset_close_action(self):
        """重置关闭行为设置"""
        self.config.set('close_action', None)
        self.config.save()
        QMessageBox.information(self, '提示', '关闭行为已重置，下次关闭窗口时将重新询问。') 