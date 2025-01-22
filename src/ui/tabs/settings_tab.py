import os
import winreg
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QComboBox,
    QCheckBox, QMessageBox, QFrame, QGroupBox, QScrollArea
)
from PyQt6.QtCore import (
    pyqtSignal, Qt, QTimer, QThread,
    QMetaObject, Q_ARG
)
from PyQt6.QtGui import QIcon, QFont
from loguru import logger
from utils.system_utils import set_environment_variable, update_path_variable, system_manager
from utils.platform_manager import platform_manager
from utils.i18n_manager import i18n_manager
from utils.theme_manager import ThemeManager
from utils.update_manager import UpdateManager
import win32gui
import win32con
import sys

# 初始化翻译函数
_ = i18n_manager.get_text

class SettingsTab(QWidget):
    """设置标签页"""
    
    # 定义信号
    settings_changed = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.parent = parent
        
        # 获取图标路径
        self.icons_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons')
        
        # 获取应用程序根目录
        if getattr(sys, 'frozen', False):
            # 如果是打包后的环境，使用程序所在目录作为根目录
            self.root_dir = os.path.dirname(sys.executable)
        else:
            # 如果是开发环境，使用当前工作目录作为根目录
            self.root_dir = os.getcwd()
            
        logger.debug(f"Settings root path: {self.root_dir}")
        
        # 设置默认路径（如果配置中没有）
        if not self.config.get('jdk_store_path'):
            self.config.set('jdk_store_path', 'jdk')
        if not self.config.get('junction_path'):
            self.config.set('junction_path', 'current')
            
        # 确保必要的目录存在
        self._ensure_directories()
        
        # 初始化语言设置
        saved_language = self.config.get('language', 'zh_CN')
        i18n_manager.switch_language(saved_language)
        
        # 添加标志位防止循环调用
        self._is_updating = False
        
        # 获取更新管理器实例
        self.update_manager = UpdateManager()
        self.update_manager.check_update_complete.connect(self.on_check_update_complete)
        
        # 添加保存延迟计时器
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.delayed_save)
        
        # 添加后台保存线程
        self.save_thread = QThread()
        self.save_thread.start()
        
        self.setup_ui()
        # 恢复自动设置状态
        self.restore_auto_settings()
        
        # 连接语言切换信号
        i18n_manager.language_changed.connect(self._update_texts)
        
        # 连接更新设置信号
        self.auto_update_checkbox.stateChanged.connect(self.on_auto_update_changed)
        self.check_update_button.clicked.connect(self.check_for_updates)

    def _ensure_directories(self):
        """确保必要的目录结构存在"""
        try:
            # 获取绝对路径
            jdk_store_path = self._to_absolute_path(self.config.get('jdk_store_path'))
            junction_path = self._to_absolute_path(self.config.get('junction_path'))
            
            # 创建 JDK 存储目录
            if not os.path.exists(jdk_store_path):
                os.makedirs(jdk_store_path, exist_ok=True)
                logger.info(f"创建 JDK 存储目录: {jdk_store_path}")
            
            # 创建软链接目标目录
            junction_dir = os.path.dirname(junction_path)
            if not os.path.exists(junction_dir):
                os.makedirs(junction_dir, exist_ok=True)
                logger.info(f"创建软链接目标目录: {junction_dir}")
                    
        except Exception as e:
            logger.error(f"创建目录结构失败: {str(e)}")

    def _update_texts(self):
        """更新所有界面文本"""
        if self._is_updating:
            return
            
        self._is_updating = True
        try:
            # 更新基本设置组
            basic_group = self.findChild(QGroupBox, "basic_group")
            if basic_group:
                basic_group.setTitle(_("settings.sections.basic"))
                
            # 更新环境变量设置组
            env_group = self.findChild(QGroupBox, "env_group")
            if env_group:
                env_group.setTitle(_("settings.sections.env"))
                
            # 更新 Shell 设置组
            shell_group = self.findChild(QGroupBox, "shell_group")
            if shell_group:
                shell_group.setTitle(_("settings.sections.shell"))
                
            # 更新标签文本
            for label in self.findChildren(QLabel):
                if label.property("i18n_key"):
                    label.setText(_(label.property("i18n_key")))
                    
            # 更新按钮文本
            for button in self.findChildren(QPushButton):
                if button.property("i18n_key"):
                    button.setText(_(button.property("i18n_key")))
                    
            # 更新复选框文本
            for checkbox in self.findChildren(QCheckBox):
                if checkbox.property("i18n_key"):
                    checkbox.setText(_(checkbox.property("i18n_key")))
                    
            # 更新主题选项
            if hasattr(self, 'theme_combo'):
                current_theme = self.theme_combo.currentText()
                theme_names = {
                    'cyan': _("settings.theme_options.cyan"),
                    'light': _("settings.theme_options.light"),
                    'dark': _("settings.theme_options.dark")
                }
                self.theme_combo.clear()
                self.theme_combo.addItems([theme_names[theme] for theme in ['cyan', 'light', 'dark']])
                # 恢复选择
                reverse_map = {v: k for k, v in theme_names.items()}
                if current_theme in reverse_map:
                    self.theme_combo.setCurrentText(theme_names[reverse_map[current_theme]])
                    
            # 更新语言选项
            if hasattr(self, 'language_combo'):
                current_language = i18n_manager.get_current_language()
                language_names = {
                    'zh_CN': _("settings.language_options.zh_CN"),
                    'en_US': _("settings.language_options.en_US")
                }
                self.language_combo.clear()
                self.language_combo.addItems([language_names[lang] for lang in i18n_manager.get_available_languages()])
                # 设置当前语言
                if current_language in language_names:
                    self.language_combo.setCurrentText(language_names[current_language])
            
            # 更新环境变量预览
            self.update_env_preview()
        finally:
            self._is_updating = False

    def showEvent(self, event):
        """当标签页显示时获取最新环境变量"""
        super().showEvent(event)
        self.update_env_preview()

    def hideEvent(self, event):
        """当标签页隐藏时停止定时器"""
        super().hideEvent(event)
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()

    def _to_absolute_path(self, relative_path):
        """将相对路径转换为绝对路径"""
        if not relative_path:
            return ""
        try:
            # 如果已经是绝对路径，直接返回规范化后的路径
            if os.path.isabs(relative_path):
                return os.path.normpath(relative_path)
                
            # 使用应用程序根目录作为基准进行转换
            abs_path = os.path.abspath(os.path.join(self.root_dir, relative_path))
            logger.debug(f"Converting relative path '{relative_path}' to absolute path '{abs_path}'")
            return os.path.normpath(abs_path)
        except Exception as e:
            logger.error(f"转换绝对路径失败: {str(e)}")
            return relative_path

    def _to_relative_path(self, absolute_path):
        """将绝对路径转换为相对路径"""
        if not absolute_path:
            return ""
        try:
            # 规范化路径
            abs_path = os.path.normpath(absolute_path)
            root_dir = os.path.normpath(self.root_dir)
            
            # 如果在不同驱动器上，保持绝对路径
            if os.path.splitdrive(abs_path)[0] != os.path.splitdrive(root_dir)[0]:
                return abs_path
                
            # 尝试转换为相对路径
            try:
                rel_path = os.path.relpath(abs_path, root_dir)
                logger.debug(f"Converting absolute path '{abs_path}' to relative path '{rel_path}'")
                # 检查相对路径是否会超出根目录
                if rel_path.startswith('..'):
                    return abs_path
                return rel_path
            except ValueError:
                # 如果转换失败（例如不同驱动器），返回绝对路径
                return abs_path
        except Exception as e:
            logger.error(f"转换相对路径失败: {str(e)}")
            return absolute_path

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
        basic_group = QGroupBox(_("settings.sections.basic"))
        basic_group.setObjectName("basic_group")
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
        
        # 输入框和按钮的通用样式
        input_style = """
            QLineEdit {
                padding: 5px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #E3F2FD;
            }
            QLineEdit:hover {
                border: 1px solid #BBDEFB;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
                background-color: #FFFFFF;
            }
        """
        
        button_style = """
            QPushButton {
                padding: 5px 15px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #FFFFFF;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
                border: 1px solid #BBDEFB;
            }
            QPushButton:pressed {
                background-color: #E0E0E0;
                border: 1px solid #2196F3;
            }
        """
        
        combo_style = """
            QComboBox {
                padding: 5px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                min-width: 120px;
            }
            QComboBox:hover {
                border: 1px solid #BBDEFB;
            }
            QComboBox:focus {
                border: 1px solid #2196F3;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(resources/icons/dropdown.png);
                width: 12px;
                height: 12px;
            }
            QComboBox::down-arrow:hover {
                image: url(resources/icons/dropdown_hover.png);
            }
        """
        
        # JDK存储路径设置
        store_layout = QHBoxLayout()
        store_label = QLabel(_("settings.items.jdk_path"))
        store_label.setProperty("i18n_key", "settings.items.jdk_path")
        store_label.setMinimumWidth(100)
        self.store_path_edit = QLineEdit()
        self.store_path_edit.setStyleSheet(input_style)
        self.store_path_edit.setText(self._to_absolute_path(self.config.get('jdk_store_path')))
        self.store_path_button = QPushButton(_("settings.buttons.browse"))
        self.store_path_button.setProperty("i18n_key", "settings.buttons.browse")
        self.store_path_button.setProperty('browse', True)
        self.store_path_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons', 'folder.png')))
        self.store_path_button.setStyleSheet(button_style)
        
        store_layout.addWidget(store_label)
        store_layout.addWidget(self.store_path_edit)
        store_layout.addWidget(self.store_path_button)
        
        # 软链接路径设置
        junction_layout = QHBoxLayout()
        junction_label = QLabel(_("settings.items.symlink_path"))
        junction_label.setProperty("i18n_key", "settings.items.symlink_path")
        junction_label.setMinimumWidth(100)
        self.junction_path_edit = QLineEdit()
        self.junction_path_edit.setStyleSheet(input_style)
        self.junction_path_edit.setText(self._to_absolute_path(self.config.get('junction_path')))
        self.junction_path_button = QPushButton(_("settings.buttons.browse"))
        self.junction_path_button.setProperty("i18n_key", "settings.buttons.browse")
        self.junction_path_button.setProperty('browse', True)
        self.junction_path_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons', 'folder.png')))
        self.junction_path_button.setStyleSheet(button_style)
        
        junction_layout.addWidget(junction_label)
        junction_layout.addWidget(self.junction_path_edit)
        junction_layout.addWidget(self.junction_path_button)
        
        # 主题设置
        theme_layout = QHBoxLayout()
        theme_label = QLabel(_("settings.items.theme"))
        theme_label.setProperty("i18n_key", "settings.items.theme")
        theme_label.setMinimumWidth(100)
        self.theme_combo = QComboBox()
        self.theme_combo.setStyleSheet(combo_style)
        
        # 添加主题选项
        theme_names = {
            'cyan': _("settings.theme_options.cyan"),
            'light': _("settings.theme_options.light"),
            'dark': _("settings.theme_options.dark")
        }
        self.theme_combo.addItems([theme_names[theme] for theme in ['cyan', 'light', 'dark']])
        
        # 设置当前主题
        current_theme = ThemeManager.get_current_theme()
        if current_theme in theme_names:
            self.theme_combo.setCurrentText(theme_names[current_theme])
        
        # 连接信号
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        # 语言设置
        language_layout = QHBoxLayout()
        language_label = QLabel(_("settings.items.language"))
        language_label.setProperty("i18n_key", "settings.items.language")
        language_label.setMinimumWidth(100)
        self.language_combo = QComboBox()
        self.language_combo.setStyleSheet(combo_style)
        
        # 添加语言选项
        language_names = {
            'zh_CN': _("settings.language_options.zh_CN"),
            'en_US': _("settings.language_options.en_US")
        }
        self.language_combo.addItems([language_names[lang] for lang in i18n_manager.get_available_languages()])
        
        # 设置当前语言
        current_language = i18n_manager.get_current_language()
        if current_language in language_names:
            self.language_combo.setCurrentText(language_names[current_language])
        
        # 连接信号
        self.language_combo.currentTextChanged.connect(self.on_language_changed)
        
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch()
        
        # 自启动设置
        auto_start_layout = QHBoxLayout()
        auto_start_label = QLabel(_("settings.items.auto_start"))
        auto_start_label.setProperty("i18n_key", "settings.items.auto_start")
        auto_start_label.setMinimumWidth(100)
        
        self.auto_start_checkbox = QCheckBox()
        self.auto_start_checkbox.setStyleSheet(f"""
            QCheckBox {{
                spacing: 8px;
                padding: 4px;
                border-radius: 4px;
            }}
            QCheckBox:hover {{
                background-color: #F0F7FF;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid #C0C4CC;
                border-radius: 4px;
                background: white;
            }}
            QCheckBox::indicator:hover {{
                border-color: #1a73e8;
            }}
            QCheckBox::indicator:checked {{
                border: 1px solid #E8F0FE;
                background-color: #E8F0FE;
                image: url({os.path.join(self.icons_dir, 'check_square.png').replace(os.sep, '/')});
                border-radius: 4px;
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:checked:hover {{
                border: 1px solid #D2E3FC;
                background-color: #D2E3FC;
            }}
        """)
        self.auto_start_checkbox.setChecked(self.config.get_auto_start_status())
        
        auto_start_layout.addWidget(auto_start_label)
        auto_start_layout.addWidget(self.auto_start_checkbox)
        auto_start_layout.addStretch()
        
        # 添加到基本设置布局
        basic_layout.addLayout(store_layout)
        basic_layout.addLayout(junction_layout)
        basic_layout.addLayout(theme_layout)
        basic_layout.addLayout(language_layout)
        basic_layout.addLayout(auto_start_layout)
        
        # 添加基本设置组到布局
        layout.addWidget(basic_group)
        
        # 环境变量设置组
        env_group = QGroupBox(_("settings.sections.env"))
        env_group.setObjectName("env_group")
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
            QFrame#desc_container {
                background-color: #F8F9FA;
                border-radius: 6px;
                padding: 2px;
            }
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
            QLabel[type="env_value"]:hover {
                border: 1px solid #BBDEFB;
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
        method_one_desc = QLabel(_("settings.env.auto_method"))
        method_one_desc.setProperty("i18n_key", "settings.env.auto_method")
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
        checkbox_style = f"""
            QCheckBox {{
                spacing: 8px;
                padding: 8px;
                border-radius: 4px;
                font-size: 10pt;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 2px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                border: none;
                border-radius: 4px;
                background-color: transparent;
                image: url({os.path.join(self.icons_dir, 'auto-setup.png').replace(os.sep, '/')});
            }}
            QCheckBox:hover {{
                background-color: #F0F7FF;
            }}
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
        
        self.env_java_home = QCheckBox(_("settings.env.auto_setup"))
        self.env_java_home.setProperty("i18n_key", "settings.env.auto_setup")
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
        
        self.env_path = QCheckBox(_("settings.env.auto_setup"))
        self.env_path.setProperty("i18n_key", "settings.env.auto_setup")
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
        
        self.env_classpath = QCheckBox(_("settings.env.auto_setup"))
        self.env_classpath.setProperty("i18n_key", "settings.env.auto_setup")
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
        self.apply_env_button = QPushButton(_("settings.buttons.apply_env"))
        self.apply_env_button.setProperty("i18n_key", "settings.buttons.apply_env")
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
                border: 1px solid rgba(0, 0, 0, 0.1);
            }
            QPushButton#apply_env_button:pressed {
                background-color: #0D47A1;
                border: 1px solid rgba(0, 0, 0, 0.2);
            }
            QPushButton#apply_env_button:disabled {
                background-color: #E0E0E0;
                color: #999999;
                border: none;
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
        manual_desc = QLabel(_("settings.env.manual_method"))
        manual_desc.setProperty("i18n_key", "settings.env.manual_method")
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
        manual_tip = QLabel(_("settings.env.manual_tip"))
        manual_tip.setProperty("i18n_key", "settings.env.manual_tip")
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
        
        # 更新设置组
        update_group = QGroupBox(_("settings.sections.update"))
        update_group.setObjectName("update_group")
        update_group.setStyleSheet("""
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
        update_layout = QVBoxLayout(update_group)
        update_layout.setSpacing(10)
        update_layout.setContentsMargins(15, 5, 15, 15)
        
        # 自动更新设置
        auto_update_layout = QHBoxLayout()
        auto_update_label = QLabel(_("settings.items.auto_update"))
        auto_update_label.setProperty("i18n_key", "settings.items.auto_update")
        auto_update_label.setMinimumWidth(100)
        
        self.auto_update_checkbox = QCheckBox()
        self.auto_update_checkbox.setStyleSheet(f"""
            QCheckBox {{
                spacing: 8px;
                padding: 4px;
                border-radius: 4px;
            }}
            QCheckBox:hover {{
                background-color: #F0F7FF;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid #C0C4CC;
                border-radius: 4px;
                background: white;
            }}
            QCheckBox::indicator:hover {{
                border-color: #1a73e8;
            }}
            QCheckBox::indicator:checked {{
                border: 1px solid #E8F0FE;
                background-color: #E8F0FE;
                image: url({os.path.join(self.icons_dir, 'check_square.png').replace(os.sep, '/')});
                border-radius: 4px;
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:checked:hover {{
                border: 1px solid #D2E3FC;
                background-color: #D2E3FC;
            }}
        """)
        self.auto_update_checkbox.setChecked(self.config.get('update.auto_check', True))
        
        auto_update_layout.addWidget(auto_update_label)
        auto_update_layout.addWidget(self.auto_update_checkbox)
        auto_update_layout.addStretch()
        
        # 检查更新按钮
        check_update_layout = QHBoxLayout()
        self.check_update_button = QPushButton(_("settings.buttons.check_update"))
        self.check_update_button.setProperty("i18n_key", "settings.buttons.check_update")
        self.check_update_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'resources', 'icons', 'update.png')))
        self.check_update_button.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #1a73e8;
                border-radius: 4px;
                background-color: white;
                color: #1a73e8;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #F0F7FF;
            }
            QPushButton:pressed {
                background-color: #E3F2FD;
            }
        """)
        check_update_layout.addStretch()
        check_update_layout.addWidget(self.check_update_button)
        
        update_layout.addLayout(auto_update_layout)
        update_layout.addLayout(check_update_layout)
        
        # 添加更新设置组到主布局
        layout.addWidget(update_group)
        
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
            shell_group = QGroupBox(_("settings.sections.shell"))
            shell_layout = QVBoxLayout()
            
            # Shell 类型选择
            shell_type_layout = QHBoxLayout()
            shell_type_label = QLabel(_("settings.items.shell_type"))
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
            config_file_label = QLabel(_("settings.items.config_file"))
            self.config_file_path = QLineEdit(self.config.get('shell_config_path', ''))
            config_file_button = QPushButton(_("settings.buttons.browse"))
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
        try:
            current_path = self._to_absolute_path(self.store_path_edit.text())
            # 确保路径存在，如果不存在则使用工作目录
            if not os.path.exists(current_path):
                current_path = self.root_dir
                
            path = QFileDialog.getExistingDirectory(
                self,
                _("settings.messages.select_jdk_path"),
                current_path,
                QFileDialog.Option.ShowDirsOnly
            )
            if path:
                # 规范化路径
                path = os.path.normpath(path)
                self.store_path_edit.setText(path)
        except Exception as e:
            logger.error(f"选择存储路径失败: {str(e)}")
            QMessageBox.warning(
                self,
                _("settings.error.title"),
                _("settings.messages.path_select_failed")
            )

    def select_junction_path(self):
        """选择软链接路径"""
        try:
            current_path = self._to_absolute_path(self.junction_path_edit.text())
            # 确保路径存在，如果不存在则使用工作目录
            if not os.path.exists(current_path):
                current_path = self.root_dir
                
            path = QFileDialog.getExistingDirectory(
                self,
                _("settings.messages.select_symlink_path"),
                current_path,
                QFileDialog.Option.ShowDirsOnly
            )
            if path:
                # 规范化路径
                path = os.path.normpath(path)
                self.junction_path_edit.setText(path)
        except Exception as e:
            logger.error(f"选择软链接路径失败: {str(e)}")
            QMessageBox.warning(
                self,
                _("settings.error.title"),
                _("settings.messages.path_select_failed")
            )

    def apply_env_settings(self):
        """应用环境变量设置"""
        try:
            # 检查管理员权限
            if not platform_manager.check_admin_rights():
                QMessageBox.warning(
                    self,
                    _("settings.error.title"),
                    platform_manager.get_error_message('admin_rights')
                )
                return

            # 获取当前路径和新路径（使用绝对路径）
            junction_path = self._to_absolute_path(self.junction_path_edit.text())
            junction_path = platform_manager.normalize_path(junction_path)

            success = True
            error_messages = []

            # 设置 JAVA_HOME
            if self.env_java_home.isChecked():
                if not system_manager.set_environment_variable('JAVA_HOME', junction_path):
                    success = False
                    error_messages.append(_("settings.messages.java_home_failed"))

            # 设置 PATH
            if self.env_path.isChecked():
                if platform_manager.is_windows:
                    # Windows 使用 %JAVA_HOME%\bin
                    java_path = '%JAVA_HOME%\\bin'
                else:
                    # Unix 使用 $JAVA_HOME/bin
                    java_path = '$JAVA_HOME/bin'

                if not system_manager.update_path_variable(java_path):
                    success = False
                    error_messages.append(_("settings.messages.path_failed"))

            # 设置 CLASSPATH
            if self.env_classpath.isChecked():
                if platform_manager.is_windows:
                    classpath = ".;%JAVA_HOME%\\lib\\dt.jar;%JAVA_HOME%\\lib\\tools.jar"
                else:
                    classpath = ".:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar"

                if not system_manager.set_environment_variable('CLASSPATH', classpath):
                    success = False
                    error_messages.append(_("settings.messages.classpath_failed"))

            # 保存设置到配置文件（使用相对路径）
            self.config.set('jdk_store_path', self._to_relative_path(self.store_path_edit.text()))
            self.config.set('junction_path', self._to_relative_path(junction_path))
            self.config.save()

            # 更新环境变量预览
            self.update_env_preview()

            # 显示结果消息
            if success:
                if platform_manager.is_windows:
                    # Windows 下发送系统广播通知环境变量更改
                    win32gui.SendMessageTimeout(
                        win32con.HWND_BROADCAST,
                        win32con.WM_SETTINGCHANGE,
                        0,
                        'Environment',
                        win32con.SMTO_ABORTIFHUNG,
                        5000
                    )
                    QMessageBox.information(
                        self,
                        _("settings.messages.env_update_success"),
                        _("settings.messages.env_update_windows")
                    )
                else:
                    # Unix 系统提供重新加载命令
                    reload_cmd = platform_manager.get_shell_reload_command()
                    if reload_cmd:
                        QMessageBox.information(
                            self,
                            _("settings.messages.env_update_success"),
                            _("settings.messages.env_update_unix").format(cmd=reload_cmd)
                        )
            else:
                error_message = "\n".join(error_messages)
                QMessageBox.warning(
                    self,
                    _("settings.error.title"),
                    _("settings.messages.env_update_partial_failed").format(errors=error_message)
                )

        except Exception as e:
            logger.error(f"应用环境变量设置失败: {str(e)}")
            QMessageBox.critical(
                self,
                _("settings.error.title"),
                _("settings.messages.env_update_error").format(error=str(e))
            )

    def update_env_description(self):
        """更新环境变量说明文本"""
        if hasattr(self, 'java_home_value_label'):
            self.java_home_value_label.setText('= ' + self.junction_path_edit.text()) 

    def on_theme_changed(self, theme_text):
        """主题切换处理"""
        try:
            # 定义主题名称映射
            theme_names = {
                'cyan': _("settings.theme_options.cyan"),
                'light': _("settings.theme_options.light"),
                'dark': _("settings.theme_options.dark")
            }
            # 将显示名称转换回英文主题名
            theme_map = {v: k for k, v in theme_names.items()}
            theme = theme_map.get(theme_text)
            
            if theme and self.parent:
                self.parent.change_theme(theme)
                # 保存主题设置
                self.config.set('theme', theme)
                self.config.save()
        except Exception as e:
            logger.error(f"Theme switch failed: {str(e)}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to switch theme: {str(e)}"
            )

    def reset_close_action(self):
        """重置关闭行为设置"""
        self.config.set('close_action', None)
        self.config.save()
        QMessageBox.information(
            self, 
            _("settings.messages.restart_required"),
            _("settings.messages.reset_close_action")
        )

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
            _("settings.messages.select_config_file"),
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
                    return os.environ.get(name, _("settings.env.not_set"))
                finally:
                    winreg.CloseKey(key)
            else:
                # Unix 系统从 shell 配置文件获取
                config_file = platform_manager.get_shell_config_file()
                if not config_file or not os.path.exists(config_file):
                    return os.environ.get(name, _("settings.env.not_set"))
                    
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
                return os.environ.get(name, _("settings.env.not_set"))
        except Exception as e:
            logger.error(f"获取环境变量 {name} 失败: {str(e)}")
            return os.environ.get(name, _("settings.env.not_set"))

    def compare_java_home_paths(self):
        """比较JAVA_HOME和软链接路径"""
        try:
            current_java_home = self.get_original_env_value('JAVA_HOME')
            junction_path = self._to_absolute_path(self.junction_path_edit.text())
            
            # 如果JAVA_HOME未设置，直接返回False
            if current_java_home == _("settings.env.not_set"):
                return False
                
            # 规范化路径
            current_java_home = os.path.normpath(current_java_home)
            junction_path = os.path.normpath(junction_path)
            
            try:
                # 获取实际路径（解析软链接）
                real_java_home = os.path.realpath(current_java_home)
                real_junction = os.path.realpath(junction_path)
                
                # 规范化实际路径
                real_java_home = os.path.normpath(real_java_home)
                real_junction = os.path.normpath(real_junction)
                
                # 尝试使用samefile比较（处理大小写和路径格式差异）
                if os.path.exists(real_java_home) and os.path.exists(real_junction):
                    return os.path.samefile(real_java_home, real_junction)
                    
                # 如果路径不存在，进行字符串比较
                return real_java_home.lower() == real_junction.lower()
                
            except Exception as e:
                logger.debug(f"路径比较时出现异常: {str(e)}")
                # 如果无法解析实际路径，回退到基本的字符串比较
                return current_java_home.lower() == junction_path.lower()
                
        except Exception as e:
            logger.error(f"比较JAVA_HOME路径失败: {str(e)}")
            return False

    def update_env_preview(self):
        """更新环境变量预览"""
        # 获取当前环境变量值，保持原始格式
        current_java_home = self.get_original_env_value('JAVA_HOME')
        current_path = self.get_original_env_value('PATH')
        current_classpath = self.get_original_env_value('CLASSPATH')
        
        # 获取新的环境变量值
        new_java_home = self._to_absolute_path(self.junction_path_edit.text())
        
        # 检查JAVA_HOME和软链接路径是否一致
        paths_match = self.compare_java_home_paths()
        
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
        self.current_java_home.setText(current_java_home if current_java_home != _("settings.env.not_set") else _("settings.env.not_set"))
        
        # 处理 PATH 显示，保持所有环境变量格式
        if current_path != _("settings.env.not_set"):
            java_paths = []
            for entry in current_path.split(path_sep):
                # 跳过空路径和 PyQt6 自动添加的路径
                if not entry or ('.conda' in entry and 'PyQt6' in entry):
                    continue
                    
                # 检查是否为 Java 相关路径
                if any(java_key in entry.lower() for java_key in ['java', 'jdk', 'jre']):
                    # 如果是实际的 JAVA_HOME 路径，转换为变量格式
                    if current_java_home != _("settings.env.not_set") and entry.startswith(current_java_home):
                        entry = entry.replace(current_java_home, f'{var_prefix}JAVA_HOME{var_suffix}')
                    java_paths.append(entry)
                elif f'{var_prefix}JAVA_HOME{var_suffix}' in entry:
                    java_paths.append(entry)
            
            self.current_path.setText(path_sep.join(java_paths) if java_paths else _("settings.env.no_java_path"))
            
            # 设置完整路径作为悬浮提示
            tooltip_html = "<div style='white-space:pre;'>"
            tooltip_html += f"<b>{_('settings.env.all_paths')}:</b><br>"
            for path in current_path.split(path_sep):
                # 跳过空路径和 PyQt6 自动添加的路径
                if not path or ('.conda' in path and 'PyQt6' in path):
                    continue
            
                # 保持原始变量格式，只转换实际的 JAVA_HOME 路径
                if current_java_home != _("settings.env.not_set") and path.startswith(current_java_home):
                    path = path.replace(current_java_home, f'{var_prefix}JAVA_HOME{var_suffix}')
            
                # 高亮显示 Java 相关路径
                if any(java_key in path.lower() for java_key in ['java', 'jdk', 'jre']) or f'{var_prefix}JAVA_HOME{var_suffix}' in path:
                    tooltip_html += f"<span style='color:#1a73e8'>{path}</span><br>"
                else:
                    tooltip_html += f"{path}<br>"
            tooltip_html += "</div>"
            self.current_path.setToolTip(tooltip_html)
        else:
            self.current_path.setText(_("settings.env.not_set"))
            self.current_path.setToolTip('')
        
        # 处理 CLASSPATH 显示
        self.current_classpath.setText(current_classpath if current_classpath != _("settings.env.not_set") else _("settings.env.not_set"))
        
        # 检查基本设置是否有变更
        basic_settings_changed = (
            self.store_path_edit.text() != self.config.get('jdk_store_path') or
            self.junction_path_edit.text() != self.config.get('junction_path')
        )
        
        # 检查环境变量是否有实际差异
        has_java_home_diff = not paths_match
        has_path_diff = new_path_entry not in current_path
        has_classpath_diff = current_classpath != new_classpath
        
        # JAVA_HOME 显示
        if self.env_java_home.isChecked():
            if has_java_home_diff:
                self.java_home_new.setText(new_java_home)
                self.java_home_new.setProperty('type', 'env_value_diff')
                self.java_home_new.setVisible(True)
                clear_synced_widgets(self.java_home_layout)
            else:
                self.java_home_new.setVisible(False)
                clear_synced_widgets(self.java_home_layout)
                synced_widget = create_synced_widget(_("settings.env.synced"))
                self.java_home_layout.insertWidget(self.java_home_layout.count() - 1, synced_widget)
        else:
            self.java_home_new.setVisible(False)
            clear_synced_widgets(self.java_home_layout)
        
        # PATH 显示
        if self.env_path.isChecked():
            if has_path_diff:
                self.path_new.setText(new_path_entry)
                self.path_new.setProperty('type', 'env_value_diff')
                self.path_new.setVisible(True)
                clear_synced_widgets(self.path_layout)
            else:
                self.path_new.setVisible(False)
                clear_synced_widgets(self.path_layout)
                synced_widget = create_synced_widget(_("settings.env.synced"))
                self.path_layout.insertWidget(self.path_layout.count() - 1, synced_widget)
        else:
            self.path_new.setVisible(False)
            clear_synced_widgets(self.path_layout)
        
        # CLASSPATH 显示
        if self.env_classpath.isChecked():
            if has_classpath_diff:
                self.classpath_new.setText(new_classpath)
                self.classpath_new.setProperty('type', 'env_value_diff')
                self.classpath_new.setVisible(True)
                clear_synced_widgets(self.classpath_layout)
            else:
                self.classpath_new.setVisible(False)
                clear_synced_widgets(self.classpath_layout)
                synced_widget = create_synced_widget(_("settings.env.synced"))
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
        
        if has_any_diff:
            self.env_warning.setText(_("settings.env.change_warning"))
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

    def on_language_changed(self, language_text):
        """处理语言切换"""
        if self._is_updating:
            return
            
        try:
            # 定义语言名称映射
            language_names = {
                'zh_CN': _("settings.language_options.zh_CN"),
                'en_US': _("settings.language_options.en_US")
            }
            # 将显示名称转换回语言代码
            language_map = {v: k for k, v in language_names.items()}
            language = language_map.get(language_text)
            
            if language and language != i18n_manager.get_current_language():
                # 切换语言
                i18n_manager.switch_language(language)
                # 保存语言设置
                self.config.set('language', language)
                self.config.save()
                
        except Exception as e:
            logger.error(f"Language switch failed: {str(e)}")
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to switch language: {str(e)}"
            )

    def on_auto_update_changed(self, state):
        """处理自动更新设置变更"""
        try:
            # 立即更新内存中的配置
            self.config.set('update.auto_check', state == Qt.CheckState.Checked)
            # 启动延迟保存计时器
            self.save_timer.start(300)  # 300ms 后保存
        except Exception as e:
            logger.error(f"更新自动更新设置失败: {str(e)}")
            QMessageBox.warning(self, _("settings.error.title"), _("settings.error.save_failed"))
    
    def delayed_save(self):
        """延迟保存配置"""
        try:
            # 将保存操作移动到后台线程
            QTimer.singleShot(0, self.save_thread, lambda: self.save_config())
        except Exception as e:
            logger.error(f"延迟保存失败: {str(e)}")
    
    def save_config(self):
        """在后台线程中保存配置"""
        try:
            self.config.save()
            # 使用 Qt.ConnectionType.QueuedConnection 确保信号在主线程中处理
            QMetaObject.invokeMethod(self, "settings_changed", Qt.ConnectionType.QueuedConnection)
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            # 使用 Qt.ConnectionType.QueuedConnection 确保在主线程中显示警告
            QMetaObject.invokeMethod(
                self,
                "show_save_error",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, str(e))
            )
    
    def show_save_error(self, error_msg):
        """显示保存错误消息（在主线程中调用）"""
        QMessageBox.warning(self, _("settings.error.title"), _("settings.error.save_failed"))

    def check_for_updates(self):
        """手动检查更新"""
        try:
            self.check_update_button.setEnabled(False)
            self.check_update_button.setText(_("settings.buttons.checking"))
            self.update_manager.manual_check_update()
        except Exception as e:
            logger.error(f"检查更新失败: {str(e)}")
            QMessageBox.warning(self, _("settings.error.title"), _("settings.error.update_check_failed"))
            self.check_update_button.setEnabled(True)
            self.check_update_button.setText(_("settings.buttons.check_update"))

    def on_check_update_complete(self, success, message):
        """更新检查完成回调"""
        self.check_update_button.setEnabled(True)
        self.check_update_button.setText(_("settings.buttons.check_update"))
        if not success:
            QMessageBox.warning(self, _("settings.error.title"), message)

def create_synced_widget(synced_text):
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
    text_label = QLabel(synced_text)
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