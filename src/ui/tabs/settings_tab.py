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
        
        basic_layout.addLayout(store_layout)
        basic_layout.addLayout(junction_layout)
        basic_layout.addLayout(theme_layout)
        
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
        
        # 环境变量说明
        desc_container = QFrame()
        desc_container.setObjectName('desc_container')
        desc_container.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border-radius: 6px;
                padding: 2px;
            }
        """)
        desc_layout = QVBoxLayout(desc_container)
        desc_layout.setSpacing(8)
        desc_layout.setContentsMargins(15, 15, 15, 15)

        # 标题
        title_label = QLabel('环境变量配置说明')
        title_label.setProperty('title', True)
        title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 13px;
                padding-bottom: 5px;
            }
        """)
        desc_layout.addWidget(title_label)

        # 自动设置说明
        auto_desc = QLabel('1. 可以通过下方选项自动设置系统环境变量')
        auto_desc.setProperty('description', True)
        desc_layout.addWidget(auto_desc)

        # 手动设置说明
        manual_desc = QLabel('2. 也可以手动设置，将以下值复制到系统环境变量中：')
        manual_desc.setProperty('description', True)
        desc_layout.addWidget(manual_desc)

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
        java_home_label.setProperty('key', True)
        java_home_value = QLabel('= ' + self.junction_path_edit.text())
        java_home_value.setProperty('value', True)
        java_home_layout.addWidget(java_home_label)
        java_home_layout.addWidget(java_home_value)
        values_layout.addLayout(java_home_layout)

        # PATH
        path_layout = QHBoxLayout()
        path_label = QLabel('PATH')
        path_label.setProperty('key', True)
        path_value = QLabel('= %JAVA_HOME%\\bin')
        path_value.setProperty('value', True)
        path_layout.addWidget(path_label)
        path_layout.addWidget(path_value)
        values_layout.addLayout(path_layout)

        # CLASSPATH
        classpath_layout = QHBoxLayout()
        classpath_label = QLabel('CLASSPATH')
        classpath_label.setProperty('key', True)
        classpath_value = QLabel('= .;%JAVA_HOME%\\lib\\dt.jar;%JAVA_HOME%\\lib\\tools.jar')
        classpath_value.setProperty('value', True)
        classpath_layout.addWidget(classpath_label)
        classpath_layout.addWidget(classpath_value)
        values_layout.addLayout(classpath_layout)

        desc_layout.addWidget(values_frame)
        env_layout.addWidget(desc_container)

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
        
        env_layout.addWidget(self.env_java_home)
        env_layout.addWidget(self.env_path)
        env_layout.addWidget(self.env_classpath)
        
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
        env_layout.addWidget(self.apply_env_button, alignment=Qt.AlignmentFlag.AlignRight)
        
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
        
        # 主题设置已经在on_theme_changed中保存
        
        # 发送设置变更信号
        self.settings_changed.emit()

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
        self.config.save_config() 