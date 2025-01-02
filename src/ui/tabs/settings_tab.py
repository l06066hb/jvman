import os
import winreg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QComboBox,
    QCheckBox, QMessageBox, QFrame, QGroupBox, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QIcon, QFont
from src.utils.system_utils import set_environment_variable, update_path_variable
from src.utils.platform_manager import platform_manager
from src.utils.theme_manager import ThemeManager

class SettingsTab(QWidget):
    """设置标签页"""
    
    # 定义信号
    settings_changed = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.parent = parent
        self.setup_ui()
        # 恢复自动设置状态
        self.restore_auto_settings()

    def showEvent(self, event):
        """当标签页显示时获取最新环境变量"""
        super().showEvent(event)
        self.update_env_preview()

    def hideEvent(self, event):
        """当标签页隐藏时停止定时器"""
        super().hideEvent(event)
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()

    def setup_ui(self):
        """初始化界面"""
        # 创建主滚动区域
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 设置滚动条样式
        main_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            
            /* 基础滚动条结构 */
            QScrollBar:vertical {
                width: 4px;
                background: transparent;
                margin: 0px;
                border-radius: 2px;
            }
            QScrollBar:horizontal {
                height: 4px;
                background: transparent;
                margin: 0px;
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                height: 0px;
                background: transparent;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                width: 0px;
                background: transparent;
            }
            
            /* 主题相关样式 */
            /* 浅色主题 */
            .light QScrollBar::handle:vertical, .light QScrollBar::handle:horizontal {
                background-color: rgba(26, 115, 232, 0.3);
                min-height: 20px;
                min-width: 20px;
                border-radius: 2px;
            }
            .light QScrollBar::handle:vertical:hover {
                background-color: rgba(26, 115, 232, 0.8);
                width: 8px;
            }
            .light QScrollBar::handle:horizontal:hover {
                background-color: rgba(26, 115, 232, 0.8);
                height: 8px;
            }
            
            /* 深色主题 */
            .dark QScrollBar::handle:vertical, .dark QScrollBar::handle:horizontal {
                background-color: rgba(255, 255, 255, 0.3);
                min-height: 20px;
                min-width: 20px;
                border-radius: 2px;
            }
            .dark QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.8);
                width: 8px;
            }
            .dark QScrollBar::handle:horizontal:hover {
                background-color: rgba(255, 255, 255, 0.8);
                height: 8px;
            }
            
            /* 青色主题 */
            .cyan QScrollBar::handle:vertical, .cyan QScrollBar::handle:horizontal {
                background-color: rgba(0, 188, 212, 0.3);
                min-height: 20px;
                min-width: 20px;
                border-radius: 2px;
            }
            .cyan QScrollBar::handle:vertical:hover {
                background-color: rgba(0, 188, 212, 0.8);
                width: 8px;
            }
            .cyan QScrollBar::handle:horizontal:hover {
                background-color: rgba(0, 188, 212, 0.8);
                height: 8px;
            }
        """)
        
        # 创建主容器
        main_container = QWidget()
        layout = QVBoxLayout(main_container)
        layout.setSpacing(15)

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
        self.store_path_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons', 'folder.png')))
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
        self.junction_path_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons', 'folder.png')))
        self.junction_path_button.setStyleSheet(self.store_path_button.styleSheet())
        
        junction_layout.addWidget(junction_label)
        junction_layout.addWidget(self.junction_path_edit)
        junction_layout.addWidget(self.junction_path_button)
        
        # 主题设置
        theme_layout = QHBoxLayout()
        theme_label = QLabel('界面主题:')
        theme_label.setMinimumWidth(100)
        self.theme_combo = QComboBox()
        
        # 添加主题选项（使用中文显示）
        theme_names = {
            'cyan': '青色',
            'light': '浅色',
            'dark': '深色'
        }
        self.theme_combo.addItems([theme_names[theme] for theme in ['cyan', 'light', 'dark']])
        
        # 设置当前主题
        current_theme = ThemeManager.get_current_theme()
        self.theme_combo.setCurrentText(theme_names[current_theme])
        
        # 连接信号时转换回英文主题名
        def on_theme_changed(theme_text):
            # 将中文主题名转换回英文
            theme_map = {v: k for k, v in theme_names.items()}
            theme = theme_map[theme_text]
            if self.parent:
                self.parent.change_theme(theme)
        
        self.theme_combo.currentTextChanged.connect(on_theme_changed)
        
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
                image: url(resources/icons/check.png);
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
        
        # 添加基本设置组到布局
        layout.addWidget(basic_group)
        
        # 环境变量设置组
        env_group = QGroupBox("环境变量设置")
        env_group.setStyleSheet("""
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
        
        env_layout = QVBoxLayout(env_group)
        env_layout.setSpacing(15)
        env_layout.setContentsMargins(15, 5, 15, 15)
        
        # 方式一容器
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

        # 方式一说明
        method_one_desc = QLabel("📌 方式一：自动设置环境变量")
        method_one_desc.setProperty('description', True)
        method_one_desc.setStyleSheet("""
            QLabel {
                color: #1a73e8;
                font-weight: bold;
                font-size: 11pt;
                padding: 8px 0;
                background: transparent;
            }
        """)
        auto_layout.addWidget(method_one_desc)
        
        # 当前环境变量显示区域
        current_env_frame = QFrame()
        current_env_frame.setObjectName('current_env_frame')
        current_env_frame.setStyleSheet("""
            QFrame#current_env_frame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 15px;
            }
            QLabel[type="env_name"] {
                color: #333333;
                font-weight: bold;
                font-size: 10pt;
                min-width: 100px;
            }
            QLabel[type="env_value"] {
                color: #666666;
                padding: 8px 12px;
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-family: Consolas, Monaco, monospace;
                margin: 2px 0;
            }
            QLabel[type="env_value_new"] {
                color: #28a745;
                padding: 8px 12px;
                background-color: #E7F5EA;
                border: 1px solid #28a745;
                border-radius: 4px;
                font-family: Consolas, Monaco, monospace;
                margin: 2px 0;
            }
            QLabel[type="env_value_diff"] {
                color: #dc3545;
                padding: 8px 12px;
                background-color: #FFF0F0;
                border: 1px solid #dc3545;
                border-radius: 4px;
                font-family: Consolas, Monaco, monospace;
                margin: 2px 0;
            }
            QLabel[type="env_value_synced"] {
                color: #28a745;
                padding: 8px 12px;
                background-color: #F8F9FA;
                border: 1px solid #28a745;
                border-radius: 4px;
                font-family: Consolas, Monaco, monospace;
                margin: 2px 0;
                padding-right: 32px;
            }
            QLabel[type="warning"] {
                color: #f0ad4e;
                font-weight: bold;
                padding: 8px 12px;
                background-color: #fcf8e3;
                border: 1px solid #faebcc;
                border-radius: 4px;
                margin: 8px 0;
            }
            QToolTip {
                background-color: #2C3E50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-family: Consolas, Monaco, monospace;
                opacity: 230;
            }
        """)
        
        current_env_layout = QVBoxLayout(current_env_frame)
        current_env_layout.setSpacing(12)
        current_env_layout.setContentsMargins(15, 15, 15, 15)
        
        # 定义复选框样式
        checkbox_style = """
            QCheckBox {
                spacing: 8px;
                padding: 8px;
                border-radius: 4px;
                font-size: 10pt;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                border: none;
                border-radius: 4px;
                background-color: #1a73e8;
                image: url(resources/icons/auto-setup.png);
            }
            QCheckBox:hover {
                background-color: #F0F7FF;
            }
        """
        
        # JAVA_HOME 显示和设置
        java_home_container = QFrame()
        self.java_home_layout = QHBoxLayout(java_home_container)
        self.java_home_layout.setContentsMargins(0, 0, 0, 0)
        self.java_home_layout.setSpacing(10)
        
        java_home_name = QLabel("JAVA_HOME")
        java_home_name.setProperty('type', 'env_name')
        self.java_home_layout.addWidget(java_home_name)
        
        self.current_java_home = QLabel()
        self.current_java_home.setProperty('type', 'env_value')
        self.current_java_home.setWordWrap(True)
        self.java_home_layout.addWidget(self.current_java_home, 1)
        
        self.java_home_new = QLabel()
        self.java_home_new.setProperty('type', 'env_value_new')
        self.java_home_new.setWordWrap(True)
        self.java_home_new.setVisible(False)
        self.java_home_layout.addWidget(self.java_home_new, 1)
        
        self.env_java_home = QCheckBox('自动设置')
        self.env_java_home.setStyleSheet(checkbox_style)
        self.java_home_layout.addWidget(self.env_java_home)
        
        current_env_layout.addWidget(java_home_container)
        
        # PATH 显示和设置
        path_container = QFrame()
        self.path_layout = QHBoxLayout(path_container)
        self.path_layout.setContentsMargins(0, 0, 0, 0)
        self.path_layout.setSpacing(10)
        
        path_name = QLabel("PATH")
        path_name.setProperty('type', 'env_name')
        self.path_layout.addWidget(path_name)
        
        self.current_path = QLabel()
        self.current_path.setProperty('type', 'env_value')
        self.current_path.setWordWrap(True)
        self.path_layout.addWidget(self.current_path, 1)
        
        self.path_new = QLabel()
        self.path_new.setProperty('type', 'env_value_new')
        self.path_new.setWordWrap(True)
        self.path_new.setVisible(False)
        self.path_layout.addWidget(self.path_new, 1)
        
        self.env_path = QCheckBox('自动设置')
        self.env_path.setStyleSheet(checkbox_style)
        self.path_layout.addWidget(self.env_path)
        
        current_env_layout.addWidget(path_container)
        
        # CLASSPATH 显示和设置
        classpath_container = QFrame()
        self.classpath_layout = QHBoxLayout(classpath_container)
        self.classpath_layout.setContentsMargins(0, 0, 0, 0)
        self.classpath_layout.setSpacing(10)
        
        classpath_name = QLabel("CLASSPATH")
        classpath_name.setProperty('type', 'env_name')
        self.classpath_layout.addWidget(classpath_name)
        
        self.current_classpath = QLabel()
        self.current_classpath.setProperty('type', 'env_value')
        self.current_classpath.setWordWrap(True)
        self.classpath_layout.addWidget(self.current_classpath, 1)
        
        self.classpath_new = QLabel()
        self.classpath_new.setProperty('type', 'env_value_new')
        self.classpath_new.setWordWrap(True)
        self.classpath_new.setVisible(False)
        self.classpath_layout.addWidget(self.classpath_new, 1)
        
        self.env_classpath = QCheckBox('自动设置')
        self.env_classpath.setStyleSheet(checkbox_style)
        self.classpath_layout.addWidget(self.env_classpath)
        
        current_env_layout.addWidget(classpath_container)
        
        # 变更提示标签
        self.env_warning = QLabel()
        self.env_warning.setProperty('type', 'warning')
        self.env_warning.setWordWrap(True)
        self.env_warning.setVisible(False)
        current_env_layout.addWidget(self.env_warning)
        
        # 应用环境变量按钮
        self.apply_env_button = QPushButton('应用环境变量设置')
        self.apply_env_button.setObjectName('apply_env_button')
        self.apply_env_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons', 'apply.png')))
        self.apply_env_button.setStyleSheet("""
            QPushButton#apply_env_button {
                padding: 10px 24px;
                border: none;
                border-radius: 6px;
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
                font-size: 10pt;
                min-width: 180px;
            }
            QPushButton#apply_env_button:hover {
                background-color: #1557B0;
            }
            QPushButton#apply_env_button:pressed {
                background-color: #0D47A1;
            }
            QPushButton#apply_env_button:disabled {
                background-color: #E0E0E0;
                color: #999999;
            }
        """)
        current_env_layout.addWidget(self.apply_env_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        auto_layout.addWidget(current_env_frame)
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
        manual_desc = QLabel('📋 方式二：手动设置环境变量')
        manual_desc.setProperty('description', True)
        manual_desc.setStyleSheet("""
            QLabel {
                color: #1a73e8;
                font-weight: bold;
                font-size: 11pt;
                padding: 8px 0;
                background: transparent;
            }
        """)
        manual_layout.addWidget(manual_desc)

        # 添加说明文本
        manual_tip = QLabel('复制以下内容到系统环境变量中：')
        manual_tip.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 10pt;
                padding: 0 0 8px 0;
            }
        """)
        manual_layout.addWidget(manual_tip)

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

        # 根据平台设置不同的格式
        if platform_manager.is_windows:
            path_value = QLineEdit('%JAVA_HOME%\\bin')
        else:
            path_value = QLineEdit('$JAVA_HOME/bin')

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

        # 根据平台设置不同的格式
        if platform_manager.is_windows:
            classpath_value = QLineEdit('.;%JAVA_HOME%\\lib\\dt.jar;%JAVA_HOME%\\lib\\tools.jar')
        else:
            classpath_value = QLineEdit('.:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar')

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
        self.apply_env_button.clicked.connect(self.apply_env_settings)
        
        # 连接路径编辑框变更信号以更新说明文本
        self.junction_path_edit.textChanged.connect(self.update_env_description)
        self.junction_path_edit.textChanged.connect(self.update_env_preview)
        
        # 连接环境变量复选框变更信号
        self.env_java_home.stateChanged.connect(self.update_env_preview)
        self.env_path.stateChanged.connect(self.update_env_preview)
        self.env_classpath.stateChanged.connect(self.update_env_preview)
        
        # 初始化环境变量预览
        self.update_env_preview()

        # Shell 设置组 (仅在非 Windows 平台显示)
        if not platform_manager.is_windows:
            shell_group = QGroupBox("Shell 设置")
            shell_layout = QVBoxLayout()
            
            # Shell 类型选择
            shell_type_layout = QHBoxLayout()
            shell_type_label = QLabel("Shell 类型:")
            self.shell_combo = QComboBox()
            self.shell_combo.addItems(['auto', 'bash', 'zsh', 'fish'])
            current_shell = self.config.get('shell_type', 'auto')
            self.shell_combo.setCurrentText(current_shell)
            self.shell_combo.currentTextChanged.connect(self.on_shell_changed)
            shell_type_layout.addWidget(shell_type_label)
            shell_type_layout.addWidget(self.shell_combo)
            shell_layout.addLayout(shell_type_layout)
            
            # 配置文件路径
            config_file_layout = QHBoxLayout()
            config_file_label = QLabel("配置文件:")
            self.config_file_path = QLineEdit(self.config.get('shell_config_path', ''))
            config_file_button = QPushButton("浏览")
            config_file_button.clicked.connect(self.select_config_file)
            config_file_layout.addWidget(config_file_label)
            config_file_layout.addWidget(self.config_file_path)
            config_file_layout.addWidget(config_file_button)
            shell_layout.addLayout(config_file_layout)
            
            shell_group.setLayout(shell_layout)
            layout.addWidget(shell_group)

        # 设置主滚动区域的widget
        main_scroll.setWidget(main_container)
        
        # 创建最外层布局
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(main_scroll)

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

    def apply_env_settings(self):
        """应用环境变量设置"""
        junction_path = self.junction_path_edit.text()
        
        try:
            # 获取当前最新的环境变量值
            current_path = self.get_original_env_value('PATH')
            current_classpath = self.get_original_env_value('CLASSPATH')
            
            if self.env_java_home.isChecked():
                set_environment_variable('JAVA_HOME', junction_path)
            
            if self.env_path.isChecked():
                # 检查是否已存在 JAVA_HOME 路径
                if platform_manager.is_windows:
                    java_home_path = '%JAVA_HOME%\\bin'
                    if java_home_path not in current_path:
                        update_path_variable(java_home_path)
                else:
                    java_home_path = '$JAVA_HOME/bin'
                    if java_home_path not in current_path:
                        system_manager.update_path_variable(os.path.join(junction_path, 'bin'))
            
            if self.env_classpath.isChecked():
                # 检查是否已存在相同的 CLASSPATH 设置
                if platform_manager.is_windows:
                    new_classpath = ".;%JAVA_HOME%\\lib\\dt.jar;%JAVA_HOME%\\lib\\tools.jar"
                else:
                    new_classpath = ".:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar"
                if current_classpath != new_classpath:
                    set_environment_variable('CLASSPATH', new_classpath)
            
            # 保存当前设置到配置
            self.config.set('jdk_store_path', self.store_path_edit.text())
            self.config.set('junction_path', self.junction_path_edit.text())
            self.config.save()
            
            # 更新预览显示
            self.update_env_preview()
            
            # 如果是 Unix 系统，提供重新加载命令
            if not platform_manager.is_windows:
                reload_cmd = platform_manager.get_shell_reload_command()
                if reload_cmd:
                    QMessageBox.information(
                        self, 
                        '成功', 
                        f'环境变量设置已更新\n请运行以下命令使环境变量生效：\n{reload_cmd}'
                    )
                # else:
                #     QMessageBox.information(self, '成功', '环境变量设置已更新')
            # else:
            #     QMessageBox.information(self, '成功', '环境变量设置已更新')
            
        except Exception as e:
            QMessageBox.warning(self, '错误', f'设置环境变量失败: {str(e)}')

    def update_env_description(self):
        """更新环境变量说明文本"""
        if hasattr(self, 'java_home_value_label'):
            self.java_home_value_label.setText('= ' + self.junction_path_edit.text()) 

    def on_theme_changed(self, theme):
        """主题切换处理"""
        if self.parent:
            self.parent.change_theme(theme)

    def reset_close_action(self):
        """重置关闭行为设置"""
        self.config.set('close_action', None)
        self.config.save()
        QMessageBox.information(self, '提示', '关闭行为已重置，下次关闭窗口时将重新询问。') 

    def on_shell_changed(self, shell_type):
        """处理 shell 类型变更"""
        if shell_type == 'auto':
            # 自动检测 shell 配置文件
            config_file = platform_manager.get_shell_config_file()
            if config_file:
                self.config_file_path.setText(config_file)
        else:
            # 根据选择的 shell 类型设置默认配置文件
            home = os.path.expanduser('~')
            if shell_type == 'zsh':
                config_file = os.path.join(home, '.zshrc')
            elif shell_type == 'bash':
                config_file = os.path.join(home, '.bashrc')
            elif shell_type == 'fish':
                config_file = os.path.join(home, '.config/fish/config.fish')
            self.config_file_path.setText(config_file)
    
    def select_config_file(self):
        """选择 shell 配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Shell 配置文件",
            os.path.expanduser("~"),
            "Shell 配置文件 (*.rc *.profile *.fish);;所有文件 (*.*)"
        )
        if file_path:
            self.config_file_path.setText(file_path) 

    def get_original_env_value(self, name):
        """获取原始环境变量值（保持变量引用格式）"""
        try:
            if platform_manager.is_windows:
                # Windows 从注册表获取系统环境变量
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment', 0, winreg.KEY_READ)
                try:
                    value, _ = winreg.QueryValueEx(key, name)
                    return value
                except WindowsError:
                    return os.environ.get(name, '未设置')
                finally:
                    winreg.CloseKey(key)
            else:
                # Unix 系统从 shell 配置文件获取
                config_file = platform_manager.get_shell_config_file()
                if not config_file or not os.path.exists(config_file):
                    return os.environ.get(name, '未设置')
                    
                with open(config_file, 'r') as f:
                    content = f.read()
                    
                # 根据不同 shell 查找环境变量设置
                if platform_manager.shell == 'fish':
                    import re
                    # 查找 set -x NAME "value" 格式
                    pattern = f'set -x {name} "(.*?)"'
                    match = re.search(pattern, content)
                    if match:
                        return match.group(1)
                else:
                    # 查找 export NAME="value" 或 export NAME=value 格式
                    import re
                    pattern = f'export {name}=["\']?(.*?)["\']?(?:\n|$)'
                    match = re.search(pattern, content)
                    if match:
                        return match.group(1)
                    
                # 如果配置文件中没找到，从环境变量获取
                return os.environ.get(name, '未设置')
        except Exception as e:
            logger.error(f"获取环境变量 {name} 失败: {str(e)}")
            return os.environ.get(name, '未设置')

    def update_env_preview(self):
        """更新环境变量预览"""
        # 获取当前环境变量值，保持原始格式
        current_java_home = self.get_original_env_value('JAVA_HOME')
        current_path = self.get_original_env_value('PATH')
        current_classpath = self.get_original_env_value('CLASSPATH')
        
        # 获取新的环境变量值
        new_java_home = self.junction_path_edit.text()
        
        # 根据平台设置不同的格式
        if platform_manager.is_windows:
            new_path_entry = '%JAVA_HOME%\\bin'
            new_classpath = ".;%JAVA_HOME%\\lib\\dt.jar;%JAVA_HOME%\\lib\\tools.jar"
            path_sep = ';'
            var_prefix = '%'
            var_suffix = '%'
        else:
            new_path_entry = '$JAVA_HOME/bin'
            new_classpath = ".:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar"
            path_sep = ':'
            var_prefix = '$'
            var_suffix = ''
        
        # 更新当前环境变量显示
        self.current_java_home.setText(current_java_home)
        
        # 处理 PATH 显示，保持所有环境变量格式
        if current_path != '未设置':
            java_paths = []
            for entry in current_path.split(path_sep):
                # 跳过空路径和 PyQt6 自动添加的路径
                if not entry or ('.conda' in entry and 'PyQt6' in entry):
                    continue
                    
                # 检查是否为 Java 相关路径
                if any(java_key in entry.lower() for java_key in ['java', 'jdk', 'jre']):
                    # 如果是实际的 JAVA_HOME 路径，转换为变量格式
                    if current_java_home != '未设置' and entry.startswith(current_java_home):
                        entry = entry.replace(current_java_home, f'{var_prefix}JAVA_HOME{var_suffix}')
                    java_paths.append(entry)
                elif f'{var_prefix}JAVA_HOME{var_suffix}' in entry:
                    java_paths.append(entry)
            
            self.current_path.setText(path_sep.join(java_paths) if java_paths else '未找到 Java 相关路径')
            
            # 设置完整路径作为悬浮提示
            tooltip_html = "<div style='white-space:pre;'>"
            tooltip_html += "<b>所有路径:</b><br>"
            for path in current_path.split(path_sep):
                # 跳过空路径和 PyQt6 自动添加的路径
                if not path or ('.conda' in path and 'PyQt6' in path):
                    continue
            
                # 保持原始变量格式，只转换实际的 JAVA_HOME 路径
                if current_java_home != '未设置' and path.startswith(current_java_home):
                    path = path.replace(current_java_home, f'{var_prefix}JAVA_HOME{var_suffix}')
            
                # 高亮显示 Java 相关路径
                if any(java_key in path.lower() for java_key in ['java', 'jdk', 'jre']) or f'{var_prefix}JAVA_HOME{var_suffix}' in path:
                    tooltip_html += f"<span style='color:#1a73e8'>{path}</span><br>"
                else:
                    tooltip_html += f"{path}<br>"
            tooltip_html += "</div>"
            self.current_path.setToolTip(tooltip_html)
        else:
            self.current_path.setText('未设置')
            self.current_path.setToolTip('')
        
        # 处理 CLASSPATH 显示
        self.current_classpath.setText(current_classpath)
        
        # 检查基本设置是否有变更
        basic_settings_changed = (
            self.store_path_edit.text() != self.config.get('jdk_store_path') or
            self.junction_path_edit.text() != self.config.get('junction_path')
        )
        
        # 检查环境变量是否有实际差异
        has_java_home_diff = current_java_home != new_java_home
        has_path_diff = new_path_entry not in current_path
        has_classpath_diff = current_classpath != new_classpath
        
        # JAVA_HOME 显示
        if self.env_java_home.isChecked():
            if basic_settings_changed and has_java_home_diff:
                self.java_home_new.setText(new_java_home)
                self.java_home_new.setProperty('type', 'env_value_diff')
                self.java_home_new.setVisible(True)
                clear_synced_widgets(self.java_home_layout)
            else:
                self.java_home_new.setVisible(False)
                clear_synced_widgets(self.java_home_layout)
                synced_widget = create_synced_widget()
                self.java_home_layout.insertWidget(self.java_home_layout.count() - 1, synced_widget)
        else:
            self.java_home_new.setVisible(False)
            clear_synced_widgets(self.java_home_layout)
        
        # PATH 显示
        if self.env_path.isChecked():
            if basic_settings_changed and has_path_diff:
                self.path_new.setText(new_path_entry)
                self.path_new.setProperty('type', 'env_value_diff')
                self.path_new.setVisible(True)
                clear_synced_widgets(self.path_layout)
            else:
                self.path_new.setVisible(False)
                clear_synced_widgets(self.path_layout)
                synced_widget = create_synced_widget()
                self.path_layout.insertWidget(self.path_layout.count() - 1, synced_widget)
        else:
            self.path_new.setVisible(False)
            clear_synced_widgets(self.path_layout)
        
        # CLASSPATH 显示
        if self.env_classpath.isChecked():
            if basic_settings_changed and has_classpath_diff:
                self.classpath_new.setText(new_classpath)
                self.classpath_new.setProperty('type', 'env_value_diff')
                self.classpath_new.setVisible(True)
                clear_synced_widgets(self.classpath_layout)
            else:
                self.classpath_new.setVisible(False)
                clear_synced_widgets(self.classpath_layout)
                synced_widget = create_synced_widget()
                self.classpath_layout.insertWidget(self.classpath_layout.count() - 1, synced_widget)
        else:
            self.classpath_new.setVisible(False)
            clear_synced_widgets(self.classpath_layout)
        
        # 更新变更提示和按钮状态
        has_any_diff = (
            (self.env_java_home.isChecked() and has_java_home_diff) or
            (self.env_path.isChecked() and has_path_diff) or
            (self.env_classpath.isChecked() and has_classpath_diff)
        )
        
        if basic_settings_changed and has_any_diff:
            self.env_warning.setText('⚠️ 检测到基本设置有变更，请点击"应用环境变量设置"使变更生效')
            self.env_warning.setVisible(True)
            self.apply_env_button.setEnabled(True)
        else:
            self.env_warning.setVisible(False)
            self.apply_env_button.setEnabled(False)
        
        # 更新手动设置区域的值
        self.java_home_value.setText(new_java_home)
        
        # 强制更新样式
        for widget in [self.java_home_new, self.path_new, self.classpath_new]:
            widget.style().unpolish(widget)
            widget.style().polish(widget) 

    def restore_auto_settings(self):
        """恢复自动设置状态"""
        self.env_java_home.setChecked(self.config.get('auto_set_java_home', True))
        self.env_path.setChecked(self.config.get('auto_set_path', True))
        self.env_classpath.setChecked(self.config.get('auto_set_classpath', True))
        
        # 连接状态变更信号
        self.env_java_home.stateChanged.connect(lambda state: self.save_auto_settings('auto_set_java_home', state))
        self.env_path.stateChanged.connect(lambda state: self.save_auto_settings('auto_set_path', state))
        self.env_classpath.stateChanged.connect(lambda state: self.save_auto_settings('auto_set_classpath', state))

    def save_auto_settings(self, key, state):
        """保存自动设置状态"""
        self.config.set(key, bool(state))
        self.config.save()
        self.update_env_preview() 

def create_synced_widget():
    """创建同步状态的 QWidget 容器"""
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    
    # 添加同步图标
    icon_label = QLabel()
    icon_label.setFixedSize(20, 20)
    synced_icon = QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons', 'check.png'))
    pixmap = synced_icon.pixmap(16, 16)
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_label.setPixmap(pixmap)
    icon_label.setStyleSheet("""
        QLabel {
            padding: 0;
            margin: 0;
            background: transparent;
        }
    """)
    layout.addWidget(icon_label)
    
    # 添加文本
    text_label = QLabel("环境变量已同步")
    text_label.setStyleSheet("""
        QLabel {
            color: #28a745;
            font-size: 9pt;
            padding: 0;
            margin: 0;
            background: transparent;
        }
    """)
    layout.addWidget(text_label)
    
    layout.addStretch()
    return widget

def clear_synced_widgets(layout):
    """清理同步状态 widgets"""
    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)
        if isinstance(item.widget(), QWidget) and not isinstance(item.widget(), (QLabel, QCheckBox)):
            widget = item.widget()
            layout.removeWidget(widget)
            widget.deleteLater() 