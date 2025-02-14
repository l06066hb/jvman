import os
import platform
import re
import subprocess
import shutil
import time
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QComboBox,
    QCheckBox,
    QMessageBox,
    QFrame,
    QGroupBox,
    QScrollArea,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QGridLayout,
    QAbstractItemView,
    QFormLayout,
    QDialogButtonBox,
    QSplitter,
    QApplication,
    QHeaderView,
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QThread, QMetaObject, Q_ARG, Qt
from PyQt6.QtGui import QIcon, QFont, QColor
from loguru import logger
from utils.system_utils import (
    set_environment_variable,
    update_path_variable,
    system_manager,
)
from utils.platform_manager import platform_manager
from utils.i18n_manager import i18n_manager
from utils.theme_manager import ThemeManager
from utils.update_manager import UpdateManager
from utils.backup_manager import BackupManager
import sys

# Windows 特定的导入
if platform.system() == "Windows":
    import winreg
    import win32gui
    import win32con

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
        self.backup_manager = BackupManager()
        self.delayed_save_timer = QTimer()
        self.delayed_save_timer.setSingleShot(True)
        self.delayed_save_timer.timeout.connect(self.save_config)
        self.backup_list = None  # 初始化backup_list属性

        # 获取图标路径
        self.icons_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            ),
            "resources",
            "icons",
        )

        # 获取应用程序根目录
        if getattr(sys, "frozen", False):
            # 如果是打包后的环境，使用程序所在目录作为根目录
            self.root_dir = os.path.dirname(sys.executable)
        else:
            # 如果是开发环境，使用当前工作目录作为根目录
            self.root_dir = os.getcwd()

        logger.debug(f"Settings root path: {self.root_dir}")

        # 设置默认路径（如果配置中没有）
        if not self.config.get("jdk_store_path"):
            self.config.set("jdk_store_path", "jdk")
        if not self.config.get("junction_path"):
            self.config.set("junction_path", "current")

        # 确保必要的目录存在
        self._ensure_directories()

        # 初始化语言设置
        saved_language = self.config.get("language", "zh_CN")
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

        # 初始化手动检查标志位
        self._is_manual_check = False

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
            jdk_store_path = self._to_absolute_path(self.config.get("jdk_store_path"))
            junction_path = self._to_absolute_path(self.config.get("junction_path"))

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
            if hasattr(self, "theme_combo"):
                current_theme = self.theme_combo.currentText()
                theme_names = {
                    "cyan": _("settings.theme_options.cyan"),
                    "light": _("settings.theme_options.light"),
                    "dark": _("settings.theme_options.dark"),
                }
                self.theme_combo.clear()
                self.theme_combo.addItems(
                    [theme_names[theme] for theme in ["cyan", "light", "dark"]]
                )
                # 恢复选择
                reverse_map = {v: k for k, v in theme_names.items()}
                if current_theme in reverse_map:
                    self.theme_combo.setCurrentText(
                        theme_names[reverse_map[current_theme]]
                    )

            # 更新语言选项
            if hasattr(self, "language_combo"):
                current_language = i18n_manager.get_current_language()
                language_names = {
                    "zh_CN": _("settings.language_options.zh_CN"),
                    "en_US": _("settings.language_options.en_US"),
                }
                self.language_combo.clear()
                self.language_combo.addItems(
                    [
                        language_names[lang]
                        for lang in i18n_manager.get_available_languages()
                    ]
                )
                # 设置当前语言
                if current_language in language_names:
                    self.language_combo.setCurrentText(language_names[current_language])

            # 更新环境变量预览
            self.update_env_preview()

            # 更新配置文件优先级显示
            if hasattr(self, "config_labels"):
                for label in self.config_labels:
                    i18n_key = label.property("i18n_key")
                    status_key = label.property("status_key")
                    file_path = label.property("file_path")
                    is_current = label.property("is_current")

                    if all([i18n_key, status_key, file_path]):
                        current_text = (
                            f" <span style='color: #1a73e8;'>({_('settings.env.config_files.current.title')})</span>"
                            if is_current
                            else ""
                        )
                        label.setText(
                            f"{_(status_key)} {file_path} ({_(i18n_key)}){current_text}"
                        )

            # 更新备份管理部分
            if hasattr(self, "backup_group"):
                self.backup_group.setTitle(_("settings.env.backup.title"))

            if hasattr(self, "backup_table"):
                # 更新表格头
                self.backup_table.setHorizontalHeaderLabels(
                    [
                        _("settings.env.backup.table.header.config_file"),
                        _("settings.env.backup.table.header.type"),
                        _("settings.env.backup.table.header.time"),
                    ]
                )

                # 更新表格内容
                for row in range(self.backup_table.rowCount()):
                    # 更新备份类型文本
                    type_item = self.backup_table.item(row, 1)
                    if type_item:
                        backup_type = type_item.data(Qt.ItemDataRole.UserRole)
                        if backup_type:
                            type_text = (
                                _("settings.env.backup.auto")
                                if backup_type == "auto"
                                else _("settings.env.backup.manual")
                            )
                            type_item.setText(type_text)

            # 更新备份管理按钮
            if hasattr(self, "create_button"):
                self.create_button.setText(_("settings.env.backup.create"))
            if hasattr(self, "restore_button"):
                self.restore_button.setText(_("settings.env.backup.restore"))
            if hasattr(self, "view_button"):
                self.view_button.setText(_("settings.env.backup.view"))

            # 刷新备份列表以更新所有文本
            self.refresh_backup_list()

            # 更新备份限制提示
            if hasattr(self, "limit_label"):
                self.limit_label.setText(
                    _("settings.env.backup.limit_hint").format(
                        count=self.backup_manager.max_backups
                    )
                )

            # 更新更新设置组标题
            if hasattr(self, "update_group"):
                self.update_group.setTitle(_("settings.sections.update"))

        except Exception as e:
            logger.error(f"更新界面文本失败: {str(e)}")
        finally:
            self._is_updating = False

    def showEvent(self, event):
        """当标签页显示时获取最新环境变量"""
        super().showEvent(event)
        self.update_env_preview()

    def hideEvent(self, event):
        """当标签页隐藏时停止定时器"""
        super().hideEvent(event)
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.stop()

    def _to_absolute_path(self, relative_path):
        """将相对路径转换为绝对路径"""
        if not relative_path:
            return ""
        try:
            # 如果已经是绝对路径，直接返回规范化后的路径
            if os.path.isabs(relative_path):
                abs_path = os.path.normpath(relative_path)
                logger.debug(f"已是绝对路径，规范化为: {abs_path}")
                return abs_path

            # 使用应用程序根目录作为基准进行转换
            abs_path = os.path.abspath(os.path.join(self.root_dir, relative_path))
            abs_path = os.path.normpath(abs_path)

            # 检查父目录是否存在
            parent_dir = os.path.dirname(abs_path)
            if not os.path.exists(parent_dir):
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                    logger.info(f"创建目录: {parent_dir}")
                except Exception as e:
                    logger.error(f"创建目录失败: {str(e)}")
                    return abs_path

            logger.debug(f"转换相对路径 '{relative_path}' 为绝对路径 '{abs_path}'")
            return abs_path
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

            # 处理 macOS 的 Contents/Home 目录
            if platform.system() == "Darwin" and "/Contents/Home" in abs_path:
                abs_path = os.path.dirname(os.path.dirname(abs_path))
                logger.debug(f"macOS路径还原为: {abs_path}")

            root_dir = os.path.normpath(self.root_dir)

            # 如果在不同驱动器上，保持绝对路径
            if os.path.splitdrive(abs_path)[0] != os.path.splitdrive(root_dir)[0]:
                return abs_path

            # 尝试转换为相对路径
            try:
                rel_path = os.path.relpath(abs_path, root_dir)
                logger.debug(
                    f"Converting absolute path '{abs_path}' to relative path '{rel_path}'"
                )
                # 检查相对路径是否会超出根目录
                if rel_path.startswith(".."):
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
        main_scroll.setStyleSheet(
            """
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
        """
        )

        # 创建主容器
        main_container = QWidget()
        layout = QVBoxLayout(main_container)
        layout.setSpacing(15)

        # 基本设置组
        basic_group = QGroupBox(_("settings.sections.basic"))
        basic_group.setObjectName("basic_group")
        basic_group.setStyleSheet(
            """
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
        """
        )
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
        self.store_path_edit.setText(
            self._to_absolute_path(self.config.get("jdk_store_path"))
        )
        self.store_path_button = QPushButton(_("settings.buttons.browse"))
        self.store_path_button.setProperty("i18n_key", "settings.buttons.browse")
        self.store_path_button.setProperty("browse", True)
        self.store_path_button.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    ),
                    "resources",
                    "icons",
                    "folder.png",
                )
            )
        )
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
        self.junction_path_edit.setText(
            self._to_absolute_path(self.config.get("junction_path"))
        )
        self.junction_path_button = QPushButton(_("settings.buttons.browse"))
        self.junction_path_button.setProperty("i18n_key", "settings.buttons.browse")
        self.junction_path_button.setProperty("browse", True)
        self.junction_path_button.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    ),
                    "resources",
                    "icons",
                    "folder.png",
                )
            )
        )
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
            "cyan": _("settings.theme_options.cyan"),
            "light": _("settings.theme_options.light"),
            "dark": _("settings.theme_options.dark"),
        }
        self.theme_combo.addItems(
            [theme_names[theme] for theme in ["cyan", "light", "dark"]]
        )

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
            "zh_CN": _("settings.language_options.zh_CN"),
            "en_US": _("settings.language_options.en_US"),
        }
        self.language_combo.addItems(
            [language_names[lang] for lang in i18n_manager.get_available_languages()]
        )

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
        self.auto_start_checkbox.setStyleSheet(
            f"""
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
        """
        )
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

        # 添加恢复默认按钮
        reset_button_layout = QHBoxLayout()
        self.reset_button = QPushButton(_("settings.reset"))
        self.reset_button.setProperty("i18n_key", "settings.reset")
        self.reset_button.setIcon(QIcon(os.path.join(self.icons_dir, "reset.png")))
        self.reset_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #dc3545;
                border-radius: 4px;
                background-color: white;
                color: #dc3545;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #FFF0F0;
            }
            QPushButton:pressed {
                background-color: #FFE0E0;
            }
            """
        )
        self.reset_button.clicked.connect(self.reset_basic_settings)
        reset_button_layout.addStretch()
        reset_button_layout.addWidget(self.reset_button)
        basic_layout.addLayout(reset_button_layout)

        # 添加基本设置组到布局
        layout.addWidget(basic_group)

        # 环境变量设置组
        env_group = QGroupBox(_("settings.sections.env"))
        env_group.setObjectName("env_group")
        env_group.setStyleSheet(
            """
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
        """
        )

        env_layout = QVBoxLayout(env_group)
        env_layout.setSpacing(15)
        env_layout.setContentsMargins(15, 5, 15, 15)

        # 方式一容器
        auto_container = QFrame()
        auto_container.setObjectName("desc_container")
        auto_container.setStyleSheet(
            """
            QFrame {
                background-color: #F8F9FA;
                border-radius: 6px;
                padding: 2px;
            }
        """
        )
        auto_layout = QVBoxLayout(auto_container)
        auto_layout.setSpacing(8)
        auto_layout.setContentsMargins(15, 15, 15, 15)

        # 方式一说明
        method_one_desc = QLabel(_("settings.env.auto_method"))
        method_one_desc.setProperty("i18n_key", "settings.env.auto_method")
        method_one_desc.setStyleSheet(
            """
            QLabel {
                color: #1a73e8;
                font-weight: bold;
                font-size: 11pt;
                padding: 8px 0;
                background: transparent;
            }
        """
        )
        auto_layout.addWidget(method_one_desc)

        # 添加配置文件优先级显示区域 (仅用于 Mac/Linux)
        if not platform_manager.is_windows:
            config_priority_frame = QFrame()
            config_priority_frame.setStyleSheet(
                """
                QFrame {
                    background-color: #F0F2F5;
                    border-radius: 4px;
                    padding: 8px;
                    margin: 0 0 8px 0;
                }
                """
            )
            config_priority_layout = QVBoxLayout(config_priority_frame)
            config_priority_layout.setSpacing(2)
            config_priority_layout.setContentsMargins(8, 8, 8, 8)

            # 标题
            priority_title = QLabel(_("settings.env.config_files.priority.title"))
            priority_title.setProperty(
                "i18n_key", "settings.env.config_files.priority.title"
            )
            priority_title.setStyleSheet(
                """
                QLabel {
                    color: #1a73e8;
                    font-weight: 600;
                    font-size: 12px;
                    margin-bottom: 4px;
                    background: transparent;
                }
                """
            )
            config_priority_layout.addWidget(priority_title)

            # 配置文件列表
            self.config_files = [
                ("/etc/profile", "settings.env.config_files.priority.system_profile"),
                ("/etc/paths", "settings.env.config_files.priority.system_paths"),
                (
                    os.path.expanduser("~/.bash_profile"),
                    "settings.env.config_files.priority.user_profile",
                ),
                (
                    os.path.expanduser("~/.profile"),
                    "settings.env.config_files.priority.user_profile_alt",
                ),
            ]

            config_file = platform_manager.get_shell_config_file()
            self.config_labels = []  # 存储配置文件标签的列表

            for file_path, i18n_key in self.config_files:
                if os.path.exists(file_path):
                    if os.access(file_path, os.W_OK):
                        status_key = "settings.env.config_files.status.writable"
                        color = "#28a745"
                    else:
                        status_key = "settings.env.config_files.status.readonly"
                        color = "#dc3545"
                    # 如果是当前使用的配置文件，添加标记
                    current = ""
                    if config_file and os.path.samefile(file_path, config_file):
                        current = f" <span style='color: #1a73e8;'>({_('settings.env.config_files.current.title')})</span>"

                    file_label = QLabel(
                        f"{_(status_key)} {file_path} ({_(i18n_key)}){current}"
                    )
                    file_label.setProperty("i18n_key", i18n_key)
                    file_label.setProperty("status_key", status_key)
                    file_label.setProperty("file_path", file_path)
                    file_label.setProperty("is_current", bool(current))
                    file_label.setStyleSheet(
                        f"""
                        QLabel {{
                            color: {color};
                            font-size: 11px;
                            padding: 2px 4px;
                            background: transparent;
                            line-height: 1.2;
                        }}
                        """
                    )
                    self.config_labels.append(file_label)
                    config_priority_layout.addWidget(file_label)
                else:
                    file_label = QLabel(
                        f"{_('settings.env.config_files.status.not_exist')} {file_path} ({_(i18n_key)})"
                    )
                    file_label.setProperty("i18n_key", i18n_key)
                    file_label.setProperty(
                        "status_key", "settings.env.config_files.status.not_exist"
                    )
                    file_label.setProperty("file_path", file_path)
                    file_label.setProperty("is_current", False)
                    file_label.setStyleSheet(
                        """
                        QLabel {
                            color: #6c757d;
                            font-size: 11px;
                            padding: 2px 4px;
                            background: transparent;
                            line-height: 1.2;
                        }
                        """
                    )
                    self.config_labels.append(file_label)
                    config_priority_layout.addWidget(file_label)

            auto_layout.addWidget(config_priority_frame)

        # 当前环境变量显示区域
        current_env_frame = QFrame()
        current_env_frame.setObjectName("current_env_frame")
        current_env_frame.setStyleSheet(
            """
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

        """
        )

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
        java_home_name.setProperty("type", "env_name")
        self.java_home_layout.addWidget(java_home_name)

        self.current_java_home = QLabel()
        self.current_java_home.setProperty("type", "env_value")
        self.current_java_home.setWordWrap(True)
        self.java_home_layout.addWidget(self.current_java_home, 1)

        self.java_home_new = QLabel()
        self.java_home_new.setProperty("type", "env_value_new")
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
        path_name.setProperty("type", "env_name")
        self.path_layout.addWidget(path_name)

        self.current_path = QLabel()
        self.current_path.setProperty("type", "env_value")
        self.current_path.setWordWrap(True)
        self.path_layout.addWidget(self.current_path, 1)

        self.path_new = QLabel()
        self.path_new.setProperty("type", "env_value_new")
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
        classpath_name.setProperty("type", "env_name")
        self.classpath_layout.addWidget(classpath_name)

        self.current_classpath = QLabel()
        self.current_classpath.setProperty("type", "env_value")
        self.current_classpath.setWordWrap(True)
        self.classpath_layout.addWidget(self.current_classpath, 1)

        self.classpath_new = QLabel()
        self.classpath_new.setProperty("type", "env_value_new")
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
        self.env_warning.setProperty("type", "warning")
        self.env_warning.setWordWrap(True)
        self.env_warning.setVisible(False)
        current_env_layout.addWidget(self.env_warning)

        # 应用环境变量按钮
        self.apply_env_button = QPushButton(_("settings.buttons.apply_env"))
        self.apply_env_button.setProperty("i18n_key", "settings.buttons.apply_env")
        self.apply_env_button.setObjectName("apply_env_button")
        self.apply_env_button.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    ),
                    "resources",
                    "icons",
                    "apply.png",
                )
            )
        )
        self.apply_env_button.setStyleSheet(
            """
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
        """
        )
        current_env_layout.addWidget(
            self.apply_env_button, alignment=Qt.AlignmentFlag.AlignRight
        )

        auto_layout.addWidget(current_env_frame)
        env_layout.addWidget(auto_container)

        # 手动设置区域
        manual_container = QFrame()
        manual_container.setObjectName("desc_container")
        manual_container.setStyleSheet(
            """
            QFrame {
                background-color: #F8F9FA;
                border-radius: 6px;
                padding: 2px;
            }
        """
        )
        manual_layout = QVBoxLayout(manual_container)
        manual_layout.setSpacing(8)
        manual_layout.setContentsMargins(15, 15, 15, 15)

        # 手动设置说明
        manual_desc = QLabel(_("settings.env.manual_method"))
        manual_desc.setProperty("i18n_key", "settings.env.manual_method")
        manual_desc.setStyleSheet(
            """
            QLabel {
                color: #1a73e8;
                font-weight: bold;
                font-size: 11pt;
                padding: 8px 0;
                background: transparent;
            }
        """
        )
        manual_layout.addWidget(manual_desc)

        # 添加说明文本
        manual_tip = QLabel(_("settings.env.manual_tip"))
        manual_tip.setProperty("i18n_key", "settings.env.manual_tip")
        manual_tip.setStyleSheet(
            """
            QLabel {
                color: #666666;
                font-size: 10pt;
                padding: 0 0 8px 0;
            }
        """
        )
        manual_layout.addWidget(manual_tip)

        # 环境变量值容器
        values_frame = QFrame()
        values_frame.setObjectName("values_frame")
        values_frame.setStyleSheet(
            """
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        """
        )
        values_layout = QVBoxLayout(values_frame)
        values_layout.setSpacing(4)
        values_layout.setContentsMargins(10, 10, 10, 10)

        # JAVA_HOME
        java_home_layout = QHBoxLayout()
        java_home_label = QLabel("JAVA_HOME")
        java_home_label.setMinimumWidth(100)
        java_home_label.setStyleSheet("font-weight: bold;")
        self.java_home_value = QLineEdit(self.junction_path_edit.text())
        self.java_home_value.setReadOnly(True)
        self.java_home_value.setMinimumWidth(400)
        self.java_home_value.setStyleSheet(
            """
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: #F8F9FA;
                selection-background-color: #E8F0FE;
            }
        """
        )
        java_home_layout.addWidget(java_home_label)
        java_home_layout.addWidget(self.java_home_value)
        values_layout.addLayout(java_home_layout)

        # PATH
        path_layout = QHBoxLayout()
        path_label = QLabel("PATH")
        path_label.setMinimumWidth(100)
        path_label.setStyleSheet("font-weight: bold;")

        # 根据平台设置不同的格式
        if platform_manager.is_windows:
            path_value = QLineEdit("%JAVA_HOME%\\bin")
        else:
            path_value = QLineEdit("$JAVA_HOME/bin")

        path_value.setReadOnly(True)
        path_value.setMinimumWidth(400)
        path_value.setStyleSheet(self.java_home_value.styleSheet())
        path_layout.addWidget(path_label)
        path_layout.addWidget(path_value)
        values_layout.addLayout(path_layout)

        # CLASSPATH
        classpath_layout = QHBoxLayout()
        classpath_label = QLabel("CLASSPATH")
        classpath_label.setMinimumWidth(100)
        classpath_label.setStyleSheet("font-weight: bold;")

        # 根据平台设置不同的格式
        if platform_manager.is_windows:
            classpath_value = QLineEdit(
                ".;%JAVA_HOME%\\lib\\dt.jar;%JAVA_HOME%\\lib\\tools.jar"
            )
        else:
            classpath_value = QLineEdit(
                ".:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar"
            )

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
        self.update_group = QGroupBox(_("settings.sections.update"))  # 保存为类属性
        self.update_group.setObjectName("update_group")
        self.update_group.setStyleSheet(
            """
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
        """
        )
        update_layout = QVBoxLayout(self.update_group)
        update_layout.setSpacing(10)
        update_layout.setContentsMargins(15, 5, 15, 15)

        # 自动更新设置
        auto_update_layout = QHBoxLayout()
        auto_update_label = QLabel(_("settings.items.auto_update"))
        auto_update_label.setProperty("i18n_key", "settings.items.auto_update")
        auto_update_label.setMinimumWidth(100)

        self.auto_update_checkbox = QCheckBox()
        self.auto_update_checkbox.setStyleSheet(
            f"""
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
        """
        )
        self.auto_update_checkbox.setChecked(self.config.get("update.auto_check", True))

        auto_update_layout.addWidget(auto_update_label)
        auto_update_layout.addWidget(self.auto_update_checkbox)
        auto_update_layout.addStretch()

        # 检查更新按钮
        check_update_layout = QHBoxLayout()
        self.check_update_button = QPushButton(_("settings.buttons.check_update"))
        self.check_update_button.setProperty(
            "i18n_key", "settings.buttons.check_update"
        )
        self.check_update_button.setIcon(
            QIcon(
                os.path.join(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    ),
                    "resources",
                    "icons",
                    "update.png",
                )
            )
        )
        self.check_update_button.setStyleSheet(
            """
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
        """
        )
        check_update_layout.addStretch()
        check_update_layout.addWidget(self.check_update_button)

        update_layout.addLayout(auto_update_layout)
        update_layout.addLayout(check_update_layout)

        # 添加更新设置组到主布局
        layout.addWidget(self.update_group)

        # 添加弹性空间
        layout.addStretch()

        # 设置主滚动区域的widget
        main_scroll.setWidget(main_container)

        # 创建最外层布局
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(main_scroll)

        # 连接信号
        self.store_path_button.clicked.connect(self.select_store_path)
        self.junction_path_button.clicked.connect(self.select_junction_path)
        self.apply_env_button.clicked.connect(self.apply_env_settings)

        # 连接主题切换信号
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)

        # 连接语言切换信号
        self.language_combo.currentTextChanged.connect(self.on_language_changed)

        # 连接自动启动复选框信号
        self.auto_start_checkbox.stateChanged.connect(
            lambda state: self.config.set_auto_start(state == Qt.CheckState.Checked)
        )

        # 连接自动更新复选框信号
        self.auto_update_checkbox.stateChanged.connect(self.on_auto_update_changed)

        # 连接检查更新按钮信号
        self.check_update_button.clicked.connect(self.check_for_updates)

        # 连接 shell 相关信号
        if hasattr(self, "shell_combo"):
            self.shell_combo.currentTextChanged.connect(self.on_shell_changed)
        if hasattr(self, "config_file_button"):
            self.config_file_button.clicked.connect(self.select_config_file)

        # 连接输入框变更信号
        self.store_path_edit.textChanged.connect(self.update_env_preview)
        self.junction_path_edit.textChanged.connect(self.update_env_preview)

        # 在环境变量设置区域添加备份管理组
        backup_group = self.setup_backup_ui()
        env_layout.addWidget(backup_group)

        # 刷新备份列表
        self.refresh_backup_list()

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
                QFileDialog.Option.ShowDirsOnly,
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
                _("settings.messages.path_select_failed"),
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
                QFileDialog.Option.ShowDirsOnly,
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
                _("settings.messages.path_select_failed"),
            )

    def apply_env_settings(self):
        """应用环境变量设置"""
        try:
            # 创建自动备份
            logger.debug("正在创建自动备份...")
            if not self.backup_manager.create_backup("auto"):
                logger.error("创建自动备份失败")
                QMessageBox.warning(
                    self,
                    _("settings.env.backup.error_title"),
                    _("settings.env.backup.create_failed"),
                )
                return

            # 刷新备份列表
            self.refresh_backup_list()

            # 获取当前设置
            junction_path = self._to_absolute_path(self.junction_path_edit.text())
            if not junction_path:
                logger.error("软链接路径为空")
                QMessageBox.warning(
                    self,
                    _("common.warning"),
                    _("settings.messages.select_symlink_path"),
                )
                return

            # 检查路径是否存在
            if not os.path.exists(os.path.dirname(junction_path)):
                logger.error(f"软链接路径不存在: {junction_path}")
                QMessageBox.warning(
                    self,
                    _("common.warning"),
                    _("settings.error.invalid_path").format(path=junction_path),
                )
                return

            if platform_manager.is_windows:
                junction_path = platform_manager.normalize_path(junction_path)

                success = True
                error_messages = []

                # 设置 JAVA_HOME
                if self.env_java_home.isChecked():
                    if not system_manager.set_environment_variable(
                        "JAVA_HOME", junction_path
                    ):
                        success = False
                        error_messages.append(_("settings.messages.java_home_failed"))

                # 设置 PATH
                if self.env_path.isChecked():
                    if platform_manager.is_windows:
                        # Windows 使用 %JAVA_HOME%\bin
                        java_path = "%JAVA_HOME%\\bin"
                    else:
                        # Unix 使用 $JAVA_HOME/bin
                        java_path = "$JAVA_HOME/bin"

                    if not system_manager.update_path_variable(java_path):
                        success = False
                        error_messages.append(_("settings.messages.path_failed"))

                # 设置 CLASSPATH
                if self.env_classpath.isChecked():
                    if platform_manager.is_windows:
                        classpath = (
                            ".;%JAVA_HOME%\\lib\\dt.jar;%JAVA_HOME%\\lib\\tools.jar"
                        )
                    else:
                        classpath = ".:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar"

                    if not system_manager.set_environment_variable(
                        "CLASSPATH", classpath
                    ):
                        success = False
                        error_messages.append(_("settings.messages.classpath_failed"))

                # 保存设置到配置文件（使用相对路径）
                self.config.set(
                    "jdk_store_path",
                    self._to_relative_path(self.store_path_edit.text()),
                )
                self.config.set("junction_path", self._to_relative_path(junction_path))
                self.config.save()
                try:
                    # Windows 特定的环境变量广播
                    win32gui.SendMessageTimeout(
                        win32con.HWND_BROADCAST,
                        win32con.WM_SETTINGCHANGE,
                        0,
                        "Environment",
                        win32con.SMTO_ABORTIFHUNG,
                        5000,
                    )
                    subprocess.run(
                        ["rundll32", "user32.dll,UpdatePerUserSystemParameters"],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                except Exception as e:
                    logger.warning(f"发送环境变量更改通知时出现警告（不影响设置）: {str(e)}")

                QMessageBox.information(
                    self, _("common.success"), _("settings.messages.env_update_windows")
                )
            else:
                # Unix (macOS/Linux) 环境变量处理逻辑
                # 获取配置文件路径
                config_file = platform_manager.get_shell_config_file()
                if not config_file:
                    logger.error("未找到可用的配置文件")
                    QMessageBox.warning(
                        self,
                        _("common.warning"),
                        _("settings.env.config_files.current.not_found"),
                    )
                    return

                # 检查配置文件是否可写
                if not os.access(config_file, os.W_OK):
                    logger.error(f"配置文件无写入权限: {config_file}")
                    QMessageBox.warning(
                        self,
                        _("common.warning"),
                        _("settings.error.permission_denied").format(path=config_file),
                    )
                    return

                # 获取实际的 JDK Home 路径
                jdk_home = self._get_jdk_home_path(junction_path)
                logger.debug(f"JDK Home 路径: {jdk_home}")

                # 备份配置文件
                backup_path = self.backup_config_file(config_file)
                if not backup_path:
                    logger.error("备份配置文件失败")
                    QMessageBox.warning(
                        self, _("common.warning"), _("settings.error.backup_failed")
                    )
                    return

                try:
                    # 读取现有配置文件内容
                    with open(config_file, "r") as f:
                        content = f.read()
                        logger.debug(f"读取配置文件内容: {len(content)} 字节")

                    # 将内容分割成行
                    lines = content.splitlines()

                    # 找到 Java 相关环境变量的行
                    java_env_indices = []
                    java_pattern = re.compile(
                        r"^(export\s+)?(JAVA_HOME|PATH|CLASSPATH)="
                    )

                    # 找到所有 Java 相关环境变量的行号
                    for i, line in enumerate(lines):
                        if java_pattern.match(line.strip()):
                            java_env_indices.append(i)
                            logger.debug(f"找到环境变量行 {i}: {line}")

                    # 如果找到了 Java 相关环境变量，删除它们及其相邻的注释
                    if java_env_indices:
                        # 找到连续的块
                        blocks = []
                        current_block = [java_env_indices[0]]

                        for i in range(1, len(java_env_indices)):
                            if java_env_indices[i] == java_env_indices[i - 1] + 1:
                                current_block.append(java_env_indices[i])
                            else:
                                blocks.append(current_block)
                                current_block = [java_env_indices[i]]
                        blocks.append(current_block)

                        # 扩展块以包含相邻的注释
                        for block in blocks:
                            # 向上查找注释
                            start = block[0]
                            while start > 0 and (
                                lines[start - 1].strip().startswith("#")
                                or not lines[start - 1].strip()
                            ):
                                start -= 1
                            # 向下查找注释
                            end = block[-1]
                            while end < len(lines) - 1 and (
                                lines[end + 1].strip().startswith("#")
                                or not lines[end + 1].strip()
                            ):
                                end += 1
                            block.extend(range(start, block[0]))
                            block.extend(range(block[-1] + 1, end + 1))

                        # 删除所有标记的行
                        all_indices = sorted(set(sum(blocks, [])), reverse=True)
                        for i in all_indices:
                            logger.debug(f"删除行 {i}: {lines[i]}")
                            del lines[i]

                    # 确保文件末尾有空行
                    if lines and lines[-1].strip():
                        lines.append("")

                    # 添加新的 Java 环境变量设置
                    logger.debug("添加新的环境变量设置")
                    lines.append("\n# Java Environment Variables")

                    if self.env_java_home.isChecked():
                        lines.append(f'export JAVA_HOME="{jdk_home}"')
                        logger.debug(f"添加 JAVA_HOME: {jdk_home}")

                    if self.env_path.isChecked():
                        lines.append('export PATH="$JAVA_HOME/bin:$PATH"')
                        logger.debug("添加 PATH")

                    if self.env_classpath.isChecked():
                        lines.append(
                            'export CLASSPATH=".:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar"'
                        )
                        logger.debug("添加 CLASSPATH")

                    lines.append("")  # 添加最后的空行

                    # 写回文件
                    logger.debug(f"写入配置文件: {config_file}")
                    with open(config_file, "w") as f:
                        f.write("\n".join(lines))
                    logger.debug("成功写入配置文件")

                    # 尝试立即生效环境变量
                    reload_cmd = platform_manager.get_shell_reload_command()
                    if reload_cmd:
                        try:
                            shell = os.environ.get("SHELL", "/bin/bash")
                            subprocess.run([shell, "-c", reload_cmd], check=True)
                            logger.debug(f"执行重载命令成功: {reload_cmd}")
                            QMessageBox.information(
                                self,
                                _("common.success"),
                                _("settings.env.source_success"),
                            )
                        except Exception as e:
                            logger.warning(f"自动执行 source 命令失败: {str(e)}")
                            QMessageBox.information(
                                self,
                                _("common.success"),
                                _("settings.messages.env_update_unix").format(
                                    cmd=reload_cmd
                                ),
                            )
                    else:
                        QMessageBox.information(
                            self,
                            _("common.success"),
                            _("settings.messages.env_update_success"),
                        )

                except Exception as e:
                    logger.error(f"写入或更新配置文件失败: {str(e)}")
                    raise

            # 更新环境变量显示
            self.update_env_preview()
            # 再次刷新备份列表
            self.refresh_backup_list()

        except Exception as e:
            logger.error(f"应用环境变量设置失败: {str(e)}")
            QMessageBox.critical(
                self,
                _("common.error"),
                _("settings.messages.env_update_error").format(error=str(e)),
            )

    def backup_config_file(self, file_path):
        """备份配置文件"""
        try:
            if os.path.exists(file_path):
                # 使用时间戳创建备份文件名
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_path = f"{file_path}.{timestamp}.bak"

                # 复制文件,保留所有元数据
                shutil.copy2(file_path, backup_path)
                logger.info(f"已备份配置文件: {backup_path}")
                return backup_path
            return None
        except Exception as e:
            logger.error(f"备份配置文件失败: {str(e)}")
            return None

    def update_env_preview(self):
        """更新环境变量预览"""
        try:
            # 获取当前环境变量值，保持原始格式
            current_java_home = self.get_original_env_value("JAVA_HOME")
            current_path = self.get_original_env_value("PATH")
            current_classpath = self.get_original_env_value("CLASSPATH")

            # 获取新的环境变量值
            new_java_home = self._to_absolute_path(self.junction_path_edit.text())

            # 检查JAVA_HOME和软链接路径是否一致
            paths_match = self.compare_java_home_paths()

            # 根据平台设置不同的格式
            if platform_manager.is_windows:
                new_path_entry = "%JAVA_HOME%\\bin"
                new_classpath = ".;%JAVA_HOME%\\lib\\dt.jar;%JAVA_HOME%\\lib\\tools.jar"
                path_sep = ";"
                var_prefix = "%"
                var_suffix = "%"
            else:
                new_path_entry = "$JAVA_HOME/bin"
                new_classpath = ".:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar"
                path_sep = ":"
                var_prefix = "$"
                var_suffix = ""

            # 更新当前环境变量显示
            self.current_java_home.setText(
                current_java_home
                if current_java_home != _("settings.env.not_set")
                else _("settings.env.not_set")
            )

            # 处理 PATH 显示，保持所有环境变量格式
            if current_path != _("settings.env.not_set"):
                java_paths = []
                for entry in current_path.split(path_sep):
                    # 跳过空路径和 PyQt6 自动添加的路径
                    if not entry or (".conda" in entry and "PyQt6" in entry):
                        continue

                    # 检查是否为 Java 相关路径
                    if any(
                        java_key in entry.lower() for java_key in ["java", "jdk", "jre"]
                    ):
                        # 如果是实际的 JAVA_HOME 路径，转换为变量格式
                        if current_java_home != _(
                            "settings.env.not_set"
                        ) and entry.startswith(current_java_home):
                            entry = entry.replace(
                                current_java_home, f"{var_prefix}JAVA_HOME{var_suffix}"
                            )
                        java_paths.append(entry)
                    elif f"{var_prefix}JAVA_HOME{var_suffix}" in entry:
                        java_paths.append(entry)

                self.current_path.setText(
                    path_sep.join(java_paths)
                    if java_paths
                    else _("settings.env.no_java_path")
                )

                # 设置完整路径作为悬浮提示
                tooltip_html = "<div style='white-space:pre;'>"
                tooltip_html += f"<b>{_('settings.env.all_paths')}:</b><br>"
                for path in current_path.split(path_sep):
                    # 跳过空路径和 PyQt6 自动添加的路径
                    if not path or (".conda" in path and "PyQt6" in path):
                        continue

                    # 保持原始变量格式，只转换实际的 JAVA_HOME 路径
                    if current_java_home != _(
                        "settings.env.not_set"
                    ) and path.startswith(current_java_home):
                        path = path.replace(
                            current_java_home, f"{var_prefix}JAVA_HOME{var_suffix}"
                        )

                    # 高亮显示 Java 相关路径
                    if (
                        any(
                            java_key in path.lower()
                            for java_key in ["java", "jdk", "jre"]
                        )
                        or f"{var_prefix}JAVA_HOME{var_suffix}" in path
                    ):
                        tooltip_html += f"<span style='color:#1a73e8'>{path}</span><br>"
                    else:
                        tooltip_html += f"{path}<br>"
                tooltip_html += "</div>"
                self.current_path.setToolTip(tooltip_html)
            else:
                self.current_path.setText(_("settings.env.not_set"))
                self.current_path.setToolTip("")

            # 处理 CLASSPATH 显示
            self.current_classpath.setText(
                current_classpath
                if current_classpath != _("settings.env.not_set")
                else _("settings.env.not_set")
            )

            # 检查基本设置是否有变更
            basic_settings_changed = self.store_path_edit.text() != self.config.get(
                "jdk_store_path"
            ) or self.junction_path_edit.text() != self.config.get("junction_path")

            # 检查环境变量是否有实际差异
            has_java_home_diff = not paths_match
            has_path_diff = new_path_entry not in current_path
            has_classpath_diff = current_classpath != new_classpath

            # JAVA_HOME 显示
            if self.env_java_home.isChecked():
                if has_java_home_diff:
                    self.java_home_new.setText(new_java_home)
                    self.java_home_new.setProperty("type", "env_value_diff")
                    self.java_home_new.setVisible(True)
                    clear_synced_widgets(self.java_home_layout)
                else:
                    self.java_home_new.setVisible(False)
                    clear_synced_widgets(self.java_home_layout)
                    synced_widget = create_synced_widget(_("settings.env.synced"))
                    self.java_home_layout.insertWidget(
                        self.java_home_layout.count() - 1, synced_widget
                    )
            else:
                self.java_home_new.setVisible(False)
                clear_synced_widgets(self.java_home_layout)

            # PATH 显示
            if self.env_path.isChecked():
                if has_path_diff:
                    self.path_new.setText(new_path_entry)
                    self.path_new.setProperty("type", "env_value_diff")
                    self.path_new.setVisible(True)
                    clear_synced_widgets(self.path_layout)
                else:
                    self.path_new.setVisible(False)
                    clear_synced_widgets(self.path_layout)
                    synced_widget = create_synced_widget(_("settings.env.synced"))
                    self.path_layout.insertWidget(
                        self.path_layout.count() - 1, synced_widget
                    )
            else:
                self.path_new.setVisible(False)
                clear_synced_widgets(self.path_layout)

            # CLASSPATH 显示
            if self.env_classpath.isChecked():
                if has_classpath_diff:
                    self.classpath_new.setText(new_classpath)
                    self.classpath_new.setProperty("type", "env_value_diff")
                    self.classpath_new.setVisible(True)
                    clear_synced_widgets(self.classpath_layout)
                else:
                    self.classpath_new.setVisible(False)
                    clear_synced_widgets(self.classpath_layout)
                    synced_widget = create_synced_widget(_("settings.env.synced"))
                    self.classpath_layout.insertWidget(
                        self.classpath_layout.count() - 1, synced_widget
                    )
            else:
                self.classpath_new.setVisible(False)
                clear_synced_widgets(self.classpath_layout)

            # 更新变更提示和按钮状态
            has_any_diff = (
                (self.env_java_home.isChecked() and has_java_home_diff)
                or (self.env_path.isChecked() and has_path_diff)
                or (self.env_classpath.isChecked() and has_classpath_diff)
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

        except Exception as e:
            logger.error(f"更新环境变量预览失败: {str(e)}")
            self.env_preview.setText(f"更新预览失败: {str(e)}")

    def restore_auto_settings(self):
        """恢复自动设置状态"""
        self.env_java_home.setChecked(self.config.get("auto_set_java_home", True))
        self.env_path.setChecked(self.config.get("auto_set_path", True))
        self.env_classpath.setChecked(self.config.get("auto_set_classpath", True))

        # 连接状态变更信号
        self.env_java_home.stateChanged.connect(
            lambda state: self.save_auto_settings("auto_set_java_home", state)
        )
        self.env_path.stateChanged.connect(
            lambda state: self.save_auto_settings("auto_set_path", state)
        )
        self.env_classpath.stateChanged.connect(
            lambda state: self.save_auto_settings("auto_set_classpath", state)
        )

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
                "zh_CN": _("settings.language_options.zh_CN"),
                "en_US": _("settings.language_options.en_US"),
            }
            # 将显示名称转换回语言代码
            language_map = {v: k for k, v in language_names.items()}
            language = language_map.get(language_text)

            if language and language != i18n_manager.get_current_language():
                # 切换语言
                i18n_manager.switch_language(language)
                # 保存语言设置
                self.config.set("language", language)
                self.config.save()

        except Exception as e:
            logger.error(f"Language switch failed: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to switch language: {str(e)}")

    def on_auto_update_changed(self, state):
        """处理自动更新设置变更"""
        try:
            # 立即更新内存中的配置
            self.config.set("update.auto_check", state == Qt.CheckState.Checked)
            # 启动延迟保存计时器
            self.save_timer.start(300)  # 300ms 后保存
        except Exception as e:
            logger.error(f"更新自动更新设置失败: {str(e)}")
            QMessageBox.warning(
                self, _("settings.error.title"), _("settings.error.save_failed")
            )

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
            QMetaObject.invokeMethod(
                self, "settings_changed", Qt.ConnectionType.QueuedConnection
            )
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            # 使用 Qt.ConnectionType.QueuedConnection 确保在主线程中显示警告
            QMetaObject.invokeMethod(
                self,
                "show_save_error",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, str(e)),
            )

    def show_save_error(self, error_msg):
        """显示保存错误消息（在主线程中调用）"""
        QMessageBox.warning(
            self, _("settings.error.title"), _("settings.error.save_failed")
        )

    def check_for_updates(self):
        """手动检查更新"""
        # 如果已经在检查中，直接返回
        if not self.check_update_button.isEnabled():
            return

        try:
            self.check_update_button.setEnabled(False)
            self.check_update_button.setText(_("settings.buttons.checking"))
            # 设置标志位表示这是手动检查
            self._is_manual_check = True
            self.update_manager.manual_check_update()
        except Exception as e:
            # 只记录日志并重置按钮状态
            logger.error(f"检查更新失败: {str(e)}")
            self._reset_update_button()

    def _reset_update_button(self):
        """重置更新按钮状态"""
        self.check_update_button.setEnabled(True)
        self.check_update_button.setText(_("settings.buttons.check_update"))
        self._is_manual_check = False

    def on_check_update_complete(self, success, message):
        """更新检查完成回调"""
        # 如果不是手动检查，直接重置状态并返回
        if not self._is_manual_check:
            self._reset_update_button()
            return

        # 重置按钮状态
        self._reset_update_button()

    def compare_java_home_paths(self):
        """比较当前 JAVA_HOME 和软链接路径是否一致"""
        try:
            # 获取当前 JAVA_HOME 值
            current_java_home = self.get_original_env_value("JAVA_HOME")
            if current_java_home == _("settings.env.not_set"):
                return False

            # 获取新的 JAVA_HOME 值（软链接路径）
            new_java_home = self._to_absolute_path(self.junction_path_edit.text())

            # 规范化两个路径
            current_java_home = os.path.normpath(current_java_home)
            new_java_home = os.path.normpath(new_java_home)

            # 如果是 Windows，转换为小写进行比较
            if platform_manager.is_windows:
                current_java_home = current_java_home.lower()
                new_java_home = new_java_home.lower()

            # 直接比较路径字符串
            return current_java_home == new_java_home

        except Exception as e:
            logger.error(f"比较 JAVA_HOME 路径失败: {str(e)}")
            return False

    def get_original_env_value(self, name):
        """获取原始环境变量值"""
        try:
            if platform_manager.is_windows:
                # Windows 从注册表获取系统环境变量
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment",
                        0,
                        winreg.KEY_READ,
                    )
                    try:
                        value, _ = winreg.QueryValueEx(key, name)
                        return value
                    except WindowsError:
                        return os.environ.get(name, _("settings.env.not_set"))
                    finally:
                        winreg.CloseKey(key)
                except (ImportError, WindowsError):
                    return os.environ.get(name, _("settings.env.not_set"))
            else:
                # Mac/Linux 系统变量获取逻辑
                home = os.path.expanduser("~")

                # 按优先级顺序定义配置文件
                config_files = [
                    os.path.join(home, ".bash_profile"),  # 最高优先级
                    os.path.join(home, ".bashrc"),
                    os.path.join(home, ".profile"),
                    os.path.join(home, ".zshrc"),
                    "/etc/profile",  # 系统级配置
                    "/etc/paths",  # macOS 特有
                    "/etc/bashrc",
                    "/etc/environment",
                ]

                # 遍历配置文件
                for config_file in config_files:
                    if os.path.exists(config_file):
                        try:
                            with open(config_file, "r") as f:
                                content = f.read()

                            # 使用更精确的正则表达式匹配
                            patterns = [
                                f"^{name}=([^#\n]+)",  # 直接赋值
                                f"^export\s+{name}=([^#\n]+)",  # export 赋值
                            ]

                            for pattern in patterns:
                                match = re.search(pattern, content, re.MULTILINE)
                                if match:
                                    value = match.group(1).strip().strip("\"'")
                                    logger.debug(f"在 {config_file} 中找到 {name}={value}")
                                    return value
                        except Exception as e:
                            logger.debug(f"读取配置文件 {config_file} 失败: {str(e)}")
                            continue

                # 如果配置文件中都没找到，尝试从环境变量获取
                return os.environ.get(name, _("settings.env.not_set"))

        except Exception as e:
            logger.error(f"获取环境变量失败: {str(e)}")
            return _("settings.env.not_set")

    def on_theme_changed(self, theme_text):
        """主题切换处理"""
        try:
            # 定义主题名称映射
            theme_names = {
                "cyan": _("settings.theme_options.cyan"),
                "light": _("settings.theme_options.light"),
                "dark": _("settings.theme_options.dark"),
            }
            # 将显示名称转换回英文主题名
            theme_map = {v: k for k, v in theme_names.items()}
            theme = theme_map.get(theme_text)

            if theme and self.parent:
                self.parent.change_theme(theme)
                # 保存主题设置
                self.config.set("theme", theme)
                self.config.save()
        except Exception as e:
            logger.error(f"Theme switch failed: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to switch theme: {str(e)}")

    def reset_close_action(self):
        """重置关闭行为设置"""
        self.config.set("close_action", None)
        self.config.save()
        QMessageBox.information(
            self,
            _("settings.messages.restart_required"),
            _("settings.messages.reset_close_action"),
        )

    def on_shell_changed(self, shell_type):
        """处理 shell 类型变更"""
        if shell_type == "auto":
            # 自动检测 shell 配置文件
            config_file = platform_manager.get_shell_config_file()
            if config_file:
                self.config_file_path.setText(config_file)
        else:
            # 根据选择的 shell 类型设置默认配置文件
            home = os.path.expanduser("~")
            if shell_type == "zsh":
                config_file = os.path.join(home, ".zshrc")
            elif shell_type == "bash":
                config_file = os.path.join(home, ".bashrc")
            elif shell_type == "fish":
                config_file = os.path.join(home, ".config/fish/config.fish")
            self.config_file_path.setText(config_file)

    def select_config_file(self):
        """选择 shell 配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            _("settings.messages.select_config_file"),
            os.path.expanduser("~"),
            "Shell 配置文件 (*.rc *.profile *.fish);;所有文件 (*.*)",
        )
        if file_path:
            self.config_file_path.setText(file_path)

    def _get_jdk_home_path(self, jdk_path):
        """获取 JDK 的实际 Home 路径"""
        try:
            if platform.system() == "Darwin":
                # 检查是否存在 Contents/Home 目录
                contents_home = os.path.join(jdk_path, "Contents", "Home")
                if os.path.exists(contents_home):
                    logger.debug(f"找到 macOS JDK Home 路径: {contents_home}")
                    return contents_home
            return jdk_path
        except Exception as e:
            logger.error(f"获取 JDK Home 路径失败: {str(e)}")
            return jdk_path

    def create_backup(self):
        """创建备份"""
        try:
            if self.backup_manager.create_backup("manual"):
                self.refresh_backup_list()
                QMessageBox.information(
                    self,
                    _("settings.env.backup.success_title"),
                    _("settings.env.backup.success_message"),
                )
            else:
                QMessageBox.warning(
                    self,
                    _("settings.env.backup.error_title"),
                    _("settings.env.backup.create_failed"),
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                _("settings.env.backup.error_title"),
                _("settings.env.backup.create_error").format(error=str(e)),
            )

    def restore_backup(self):
        """恢复备份"""
        try:
            selected_items = self.backup_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(
                    self,
                    _("settings.env.backup.warning_title"),
                    _("settings.env.backup.select_backup"),
                )
                return

            # 获取选中行的第一个单元格
            selected_item = selected_items[0]
            backup_info = selected_item.data(Qt.ItemDataRole.UserRole)

            # 确认对话框
            reply = QMessageBox.question(
                self,
                _("settings.env.backup.confirm_title"),
                _("settings.env.backup.confirm_message"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                if self.backup_manager.restore_backup(backup_info["name"]):
                    QMessageBox.information(
                        self,
                        _("settings.env.backup.success_title"),
                        _("settings.env.backup.restore_success"),
                    )
                    self.update_env_preview()
                else:
                    QMessageBox.critical(
                        self,
                        _("settings.env.backup.error_title"),
                        _("settings.env.backup.restore_failed"),
                    )

        except Exception as e:
            QMessageBox.critical(
                self,
                _("settings.env.backup.error_title"),
                _("settings.env.backup.restore_error").format(error=str(e)),
            )

    def refresh_backup_list(self):
        """刷新备份列表"""
        try:
            self.backup_table.setRowCount(0)
            backups = self.backup_manager.get_backup_list()

            for backup in backups:
                row = self.backup_table.rowCount()
                self.backup_table.insertRow(row)

                # 配置文件
                config_files = backup.get("config_files", [])
                config_text = (
                    ", ".join(config_files)
                    if config_files
                    else _("settings.env.backup.unknown_config")
                )
                item = QTableWidgetItem(config_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.backup_table.setItem(row, 0, item)

                # 备份类型
                type_text = (
                    _("settings.env.backup.auto")
                    if backup["type"] == "auto"
                    else _("settings.env.backup.manual")
                )
                item = QTableWidgetItem(type_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.backup_table.setItem(row, 1, item)

                # 备份时间
                timestamp = backup["timestamp"]
                try:
                    # 将时间戳转换为datetime对象
                    time_obj = time.strptime(timestamp, "%Y%m%d_%H%M%S")
                    # 格式化为更友好的显示
                    formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time_obj)
                except:
                    formatted_time = timestamp
                item = QTableWidgetItem(formatted_time)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.backup_table.setItem(row, 2, item)

                # 存储完整的备份信息
                self.backup_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, backup)

            # 调整列宽以适应内容
            self.backup_table.resizeColumnsToContents()

            # 确保表格能显示所有内容
            total_width = 0
            for i in range(self.backup_table.columnCount()):
                total_width += self.backup_table.columnWidth(i)

            # 如果总宽度小于表格宽度，则平均分配剩余空间
            if total_width < self.backup_table.width():
                remaining_width = self.backup_table.width() - total_width
                per_column = int(
                    remaining_width / self.backup_table.columnCount()
                )  # 转换为整数
                for i in range(self.backup_table.columnCount()):
                    current_width = self.backup_table.columnWidth(i)
                    self.backup_table.setColumnWidth(i, current_width + per_column)

            # 更新表格
            self.backup_table.update()

        except Exception as e:
            logger.error(f"刷新备份列表失败: {str(e)}")

    def setup_backup_ui(self):
        """设置备份管理UI"""
        # 创建分组框并保存为类属性
        self.backup_group = QGroupBox(_("settings.env.backup.title"))
        backup_layout = QVBoxLayout()

        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()  # 在最左侧添加弹性空间，使按钮右对齐

        # 创建备份按钮
        self.create_button = QPushButton(_("settings.env.backup.create"))
        self.create_button.setIcon(QIcon(os.path.join(self.icons_dir, "backup.png")))
        self.create_button.clicked.connect(self.create_backup)
        self.create_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #1557B0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """
        )
        button_layout.addWidget(self.create_button)

        # 恢复备份按钮
        self.restore_button = QPushButton(_("settings.env.backup.restore"))
        self.restore_button.setIcon(QIcon(os.path.join(self.icons_dir, "restore.png")))
        self.restore_button.clicked.connect(self.restore_backup)
        self.restore_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """
        )
        button_layout.addWidget(self.restore_button)

        # 查看备份按钮
        self.view_button = QPushButton(_("settings.env.backup.view"))
        self.view_button.setIcon(QIcon(os.path.join(self.icons_dir, "view.png")))
        self.view_button.clicked.connect(self.view_backup)
        self.view_button.setStyleSheet(
            """
            QPushButton {
                padding: 8px 16px;
                background-color: white;
                color: #1a73e8;
                border: 1px solid #1a73e8;
                border-radius: 4px;
                font-weight: 500;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #f0f7ff;
                border-color: #1557B0;
                color: #1557B0;
            }
            QPushButton:pressed {
                background-color: #e3f2fd;
                border-color: #0D47A1;
                color: #0D47A1;
            }
        """
        )
        button_layout.addWidget(self.view_button)

        # 设置按钮之间的间距
        button_layout.setSpacing(10)
        button_layout.addStretch()

        backup_layout.addLayout(button_layout)

        # 使用表格显示备份列表
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(3)
        self.backup_table.setHorizontalHeaderLabels(
            [
                _("settings.env.backup.table.header.config_file"),
                _("settings.env.backup.table.header.type"),
                _("settings.env.backup.table.header.time"),
            ]
        )

        # 设置表格列宽平均分配
        header = self.backup_table.horizontalHeader()
        for i in range(3):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            # 设置表头居中对齐
            self.backup_table.horizontalHeaderItem(i).setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

        self.backup_table.setMinimumHeight(120)
        self.backup_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.backup_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.backup_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.backup_table.verticalHeader().setVisible(False)
        self.backup_table.setStyleSheet(
            """
            QTableWidget {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #F8F9FA;
                padding: 8px 4px;
                border: none;
                border-right: 1px solid #E0E0E0;
                border-bottom: 1px solid #E0E0E0;
                font-weight: 500;
                color: #1a73e8;
            }
            QHeaderView::section:last {
                border-right: none;
            }
        """
        )
        backup_layout.addWidget(self.backup_table)

        # 添加备份数量限制提示
        self.limit_label = QLabel(
            _("settings.env.backup.limit_hint").format(
                count=self.backup_manager.max_backups
            )
        )
        self.limit_label.setStyleSheet("color: #666666; font-size: 11px;")
        backup_layout.addWidget(self.limit_label)

        self.backup_group.setLayout(backup_layout)
        return self.backup_group

    def view_backup(self):
        """查看备份内容"""
        try:
            # 获取选中的备份
            selected_items = self.backup_table.selectedItems()
            if not selected_items:
                QMessageBox.warning(
                    self,
                    _("settings.env.backup.error_title"),
                    _("settings.env.backup.select_backup"),
                )
                return

            # 获取备份信息
            backup_info = selected_items[0].data(Qt.ItemDataRole.UserRole)
            if not backup_info:
                QMessageBox.critical(
                    self,
                    _("settings.env.backup.error_title"),
                    _("settings.env.backup.read_failed"),
                )
                return

            # 获取备份内容
            backup_content = self.backup_manager.get_backup_content(backup_info["name"])
            if not backup_content:
                QMessageBox.critical(
                    self,
                    _("settings.env.backup.error_title"),
                    _("settings.env.backup.read_failed"),
                )
                return

            # 创建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(_("settings.env.backup.view_title"))
            dialog.setMinimumSize(1000, 700)

            # 创建布局
            layout = QVBoxLayout(dialog)
            layout.setSpacing(15)
            layout.setContentsMargins(20, 20, 20, 20)

            # 创建内容显示区域
            content_frame = QFrame()
            content_frame.setStyleSheet(
                """
                QFrame {
                    background-color: white;
                    border: 1px solid #e0e4e8;
                    border-radius: 6px;
                }
                QTextEdit {
                    border: none;
                    border-radius: 0;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 12px;
                    line-height: 1.4;
                    padding: 12px;
                    selection-background-color: #e3f2fd;
                }
                QLabel[type="content-title"] {
                    color: #1a73e8;
                    font-weight: 500;
                    font-size: 13px;
                    padding: 0;
                    background: transparent;
                }
                QWidget[type="title-container"] {
                    background: #f8f9fa;
                    border-bottom: 1px solid #e0e4e8;
                }
                QLabel[type="title-icon"] {
                    padding: 0;
                    margin: 0;
                }
            """
            )
            content_layout = QVBoxLayout(content_frame)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(0)

            # 创建分割器
            splitter = QSplitter(Qt.Orientation.Horizontal)
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(1)

            # 左侧备份内容
            left_widget = QWidget()
            left_layout = QVBoxLayout(left_widget)
            left_layout.setContentsMargins(0, 0, 0, 0)
            left_layout.setSpacing(0)

            left_title_container = QWidget()
            left_title_container.setProperty("type", "title-container")
            left_title_layout = QHBoxLayout(left_title_container)
            left_title_layout.setContentsMargins(12, 8, 12, 8)

            # 添加备份内容图标
            left_icon = QLabel()
            left_icon.setProperty("type", "title-icon")
            left_icon.setFixedSize(20, 20)
            left_icon.setPixmap(
                QIcon(os.path.join(self.icons_dir, "backup.png")).pixmap(16, 16)
            )
            left_icon.setContentsMargins(0, 0, 0, 0)
            left_title_layout.addWidget(left_icon)

            left_title = QLabel(_("settings.env.backup.backup_content"))
            left_title.setProperty("type", "content-title")
            left_title_layout.addWidget(left_title)
            left_title_layout.addStretch()

            left_copy = QPushButton()
            left_copy.setIcon(QIcon(os.path.join(self.icons_dir, "copy.png")))
            left_copy.setToolTip(_("common.copy"))
            left_copy.setFixedSize(28, 28)
            left_copy.setStyleSheet(
                """
                QPushButton {
                    border: none;
                    padding: 4px;
                    border-radius: 4px;
                    background: transparent;
                }
                QPushButton:hover {
                    background-color: #f0f7ff;
                }
                QPushButton:pressed {
                    background-color: #e3f2fd;
                }
            """
            )
            left_title_layout.addWidget(left_copy)

            left_layout.addWidget(left_title_container)

            left_edit = QTextEdit()
            left_edit.setReadOnly(True)
            left_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
            left_layout.addWidget(left_edit)

            # 右侧当前内容
            right_widget = QWidget()
            right_layout = QVBoxLayout(right_widget)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_layout.setSpacing(0)

            right_title_container = QWidget()
            right_title_container.setProperty("type", "title-container")
            right_title_layout = QHBoxLayout(right_title_container)
            right_title_layout.setContentsMargins(12, 8, 12, 8)

            # 添加当前内容图标
            right_icon = QLabel()
            right_icon.setProperty("type", "title-icon")
            right_icon.setFixedSize(20, 20)
            right_icon.setPixmap(
                QIcon(os.path.join(self.icons_dir, "current.png")).pixmap(16, 16)
            )
            right_icon.setContentsMargins(0, 0, 0, 0)
            right_title_layout.addWidget(right_icon)

            right_title = QLabel(_("settings.env.backup.current_content"))
            right_title.setProperty("type", "content-title")
            right_title_layout.addWidget(right_title)
            right_title_layout.addStretch()

            right_copy = QPushButton()
            right_copy.setIcon(QIcon(os.path.join(self.icons_dir, "copy.png")))
            right_copy.setToolTip(_("common.copy"))
            right_copy.setFixedSize(28, 28)
            right_copy.setStyleSheet(left_copy.styleSheet())
            right_title_layout.addWidget(right_copy)

            right_layout.addWidget(right_title_container)

            right_edit = QTextEdit()
            right_edit.setReadOnly(True)
            right_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
            right_layout.addWidget(right_edit)

            # 添加到分割器
            splitter.addWidget(left_widget)
            splitter.addWidget(right_widget)
            splitter.setSizes([500, 500])  # 平均分配宽度

            content_layout.addWidget(splitter)
            layout.addWidget(content_frame)

            # 获取当前配置文件内容
            current_content = ""
            if platform_manager.is_windows:
                current_content = self._get_windows_env_content()
            else:
                config_file = platform_manager.get_shell_config_file()
                if config_file and os.path.exists(config_file):
                    with open(config_file, "r", encoding="utf-8") as f:
                        current_content = f.read()

            # 格式化并显示差异
            backup_lines = []
            current_lines = []

            # 获取备份的环境变量内容
            if platform_manager.is_windows:
                backup_lines = []
                # 处理系统环境变量
                backup_lines.append("# System Environment Variables")
                system_vars = {}

                # 从备份内容中提取系统环境变量，保持原始名称和值
                for name, info in backup_content.get("env_vars", {}).items():
                    if not name.startswith("USER_"):
                        system_vars[name] = info["value"]

                # 按固定顺序添加系统变量，保持原始内容
                for var_name in ["JAVA_HOME", "CLASSPATH", "PATH"]:
                    for name, value in system_vars.items():
                        if name.upper() == var_name:
                            if var_name == "PATH":
                                backup_lines.append(f"{name}=")
                                paths = [
                                    p for p in value.split(";") if p
                                ]  # 只过滤空值，保持原始内容
                                for path in paths:
                                    backup_lines.append(f"    {path}")
                            else:
                                backup_lines.append(f"{name}={value}")

                # 处理用户环境变量
                user_vars = {}
                for name, info in backup_content.get("env_vars", {}).items():
                    if name.startswith("USER_"):
                        real_name = name[5:]  # 移除 USER_ 前缀
                        user_vars[real_name] = info["value"]

                if user_vars:
                    backup_lines.append("")  # 空行分隔
                    backup_lines.append("# User Environment Variables")
                    # 按相同顺序添加用户变量，保持原始内容
                    for var_name in ["JAVA_HOME", "CLASSPATH", "PATH"]:
                        for name, value in user_vars.items():
                            if name.upper() == var_name:
                                if var_name == "PATH":
                                    backup_lines.append(f"{name}=")
                                    paths = [
                                        p for p in value.split(";") if p
                                    ]  # 只过滤空值，保持原始内容
                                    for path in paths:
                                        backup_lines.append(f"    {path}")
                                else:
                                    backup_lines.append(f"{name}={value}")
            else:
                # 保持原有的 Unix 系统逻辑不变
                backup_lines = []
                for config_file, info in backup_content.get("env_vars", {}).items():
                    backup_lines.extend(info.get("content", "").splitlines())

            # 计算差异前确保内容格式一致
            backup_text = "\n".join(backup_lines)
            current_text = (
                self._get_windows_env_content()
                if platform_manager.is_windows
                else current_content
            )

            # 计算差异
            import difflib

            differ = difflib.Differ()
            diff = list(
                differ.compare(backup_text.splitlines(), current_text.splitlines())
            )

            # 构建备份内容HTML
            backup_html = ['<pre style="margin: 0; padding: 0;">']
            for line in diff:
                if line.startswith("- "):
                    # 删除的行 - 红色背景
                    backup_html.append(
                        f'<div style="background-color: #fff5f5; color: #c53030; padding: 2px 4px;">-{line[2:]}</div>'
                    )
                elif line.startswith("  "):
                    # 未变更的行 - 保持原样
                    backup_html.append(
                        f'<div style="color: #2d3748; padding: 2px 4px;">{line[2:]}</div>'
                    )
            backup_html.append("</pre>")

            # 构建当前内容HTML
            current_html = ['<pre style="margin: 0; padding: 0;">']
            for line in diff:
                if line.startswith("+ "):
                    # 新增的行 - 绿色背景
                    current_html.append(
                        f'<div style="background-color: #f0fff4; color: #2f855a; padding: 2px 4px;">+{line[2:]}</div>'
                    )
                elif line.startswith("  "):
                    # 未变更的行 - 保持原样
                    current_html.append(
                        f'<div style="color: #2d3748; padding: 2px 4px;">{line[2:]}</div>'
                    )
            current_html.append("</pre>")

            # 设置HTML内容
            left_edit.setHtml("\n".join(backup_html))
            right_edit.setHtml("\n".join(current_html))

            # 复制按钮功能
            def copy_backup_content():
                clipboard = QApplication.clipboard()
                clipboard.setText("\n".join(backup_lines))

            def copy_current_content():
                clipboard = QApplication.clipboard()
                clipboard.setText("\n".join(current_lines))

            # 连接复制按钮信号
            left_copy.clicked.connect(copy_backup_content)
            right_copy.clicked.connect(copy_current_content)

            # 添加按钮区域
            button_box = QDialogButtonBox()
            restore_button = QPushButton(_("settings.env.backup.restore"))
            restore_button.setStyleSheet(
                """
                QPushButton {
                    min-width: 100px;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    background-color: #1a73e8;
                    color: white;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #1557B0;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """
            )

            close_button = QPushButton(_("common.close"))
            close_button.setStyleSheet(
                """
                QPushButton {
                    min-width: 100px;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    background-color: #f8f9fa;
                    color: #666666;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                }
                QPushButton:pressed {
                    background-color: #dee2e6;
                }
            """
            )

            button_box.addButton(restore_button, QDialogButtonBox.ButtonRole.ActionRole)
            button_box.addButton(close_button, QDialogButtonBox.ButtonRole.RejectRole)

            # 连接按钮信号
            restore_button.clicked.connect(
                lambda: self.restore_backup_from_dialog(dialog, backup_info)
            )
            close_button.clicked.connect(dialog.reject)

            layout.addWidget(button_box, alignment=Qt.AlignmentFlag.AlignRight)

            # 显示对话框
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(
                self,
                _("settings.env.backup.error_title"),
                _("settings.env.backup.view_failed").format(error=str(e)),
            )

    def restore_backup_from_dialog(self, dialog, backup_info):
        """从对话框中恢复备份"""
        try:
            # 确认对话框
            reply = QMessageBox.question(
                dialog,
                _("settings.env.backup.confirm_title"),
                _("settings.env.backup.confirm_message"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                if self.backup_manager.restore_backup(backup_info["name"]):
                    QMessageBox.information(
                        dialog,
                        _("settings.env.backup.success_title"),
                        _("settings.env.backup.restore_success"),
                    )
                    self.update_env_preview()
                    dialog.accept()  # 关闭对话框
                else:
                    QMessageBox.critical(
                        dialog,
                        _("settings.env.backup.error_title"),
                        _("settings.env.backup.restore_failed"),
                    )

        except Exception as e:
            QMessageBox.critical(
                dialog,
                _("settings.env.backup.error_title"),
                _("settings.env.backup.restore_error").format(error=str(e)),
            )

    def _get_windows_env_content(self):
        """获取Windows环境变量内容"""
        try:
            content = []

            # 只获取系统环境变量
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"System\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_READ,
            ) as key:
                content.append("# System Environment Variables")
                i = 0
                system_vars = {}
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        upper_name = name.upper()
                        if (
                            upper_name in ["JAVA_HOME", "CLASSPATH"]
                            or upper_name == "PATH"
                        ):
                            system_vars[name] = value  # 保持原始名称
                        i += 1
                    except WindowsError:
                        break

                # 按固定顺序显示变量
                for var_name in ["JAVA_HOME", "CLASSPATH", "PATH"]:
                    for name, value in system_vars.items():
                        if name.upper() == var_name:
                            if var_name == "PATH":
                                content.append(f"{name}=")
                                paths = [p for p in value.split(";") if p]  # 只过滤空值
                                for path in paths:
                                    content.append(f"    {path}")
                            else:
                                content.append(f"{name}={value}")

            return "\n".join(content)
        except Exception as e:
            logger.error(f"获取Windows环境变量内容失败: {str(e)}")
            return ""

    def reset_basic_settings(self):
        """重置基本设置为默认值"""
        try:
            # 确认对话框
            reply = QMessageBox.question(
                self,
                _("common.warning"),
                _("settings.messages.reset_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # 获取应用程序目录
                app_dir = os.path.join(os.path.expanduser("~"), ".jvman")

                # 重置为默认设置
                default_settings = {
                    "jdk_store_path": os.path.join(app_dir, "jdk"),
                    "junction_path": os.path.join(app_dir, "current"),
                    "theme": "cyan",
                    "language": "zh_CN",
                    "auto_start": False,
                }

                # 更新配置
                for key, value in default_settings.items():
                    self.config.set(key, value)

                # 更新界面显示
                self.store_path_edit.setText(default_settings["jdk_store_path"])
                self.junction_path_edit.setText(default_settings["junction_path"])
                self.theme_combo.setCurrentText(
                    _("settings.theme_options." + default_settings["theme"])
                )
                self.language_combo.setCurrentText(
                    _("settings.language_options." + default_settings["language"])
                )
                self.auto_start_checkbox.setChecked(default_settings["auto_start"])

                # 保存配置
                self.config.save()

                # 更新环境变量预览
                self.update_env_preview()

                # 提示成功
                QMessageBox.information(
                    self, _("common.success"), _("settings.messages.reset_success")
                )

        except Exception as e:
            logger.error(f"重置基本设置失败: {str(e)}")
            QMessageBox.critical(
                self,
                _("common.error"),
                _("settings.messages.reset_failed").format(error=str(e)),
            )

    def reset_settings(self):
        """恢复默认设置"""
        try:
            if (
                QMessageBox.question(
                    self,
                    _("common.confirm"),
                    _("settings.messages.reset_confirm"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                == QMessageBox.StandardButton.Yes
            ):
                # 恢复默认设置
                self.config_manager.reset_to_default()
                # 重新加载设置到界面
                self.load_settings()
                # 先更新环境变量预览
                self.update_env_preview()
                # 再更新环境变量同步状态
                self.env_manager.check_env_sync_status()  # 先检查同步状态
                self.update_env_sync_status()  # 然后更新显示
                # 显示成功提示
                QMessageBox.information(
                    self,
                    _("common.success"),
                    _("settings.messages.reset_success"),
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                _("common.error"),
                _("settings.messages.reset_failed").format(error=str(e)),
            )


def create_synced_widget(synced_text):
    """创建同步状态的 QWidget 容器"""
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    # 添加同步图标
    icon_label = QLabel()
    icon_label.setFixedSize(20, 20)
    synced_icon = QIcon(
        os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            ),
            "resources",
            "icons",
            "check.png",
        )
    )
    pixmap = synced_icon.pixmap(16, 16)
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_label.setPixmap(pixmap)
    icon_label.setStyleSheet(
        """
        QLabel {
            padding: 0;
            margin: 0;
            background: transparent;
        }
    """
    )
    layout.addWidget(icon_label)

    # 添加文本
    text_label = QLabel(synced_text)
    text_label.setStyleSheet(
        """
        QLabel {
            color: #28a745;
            font-size: 9pt;
            padding: 0;
            margin: 0;
            background: transparent;
        }
    """
    )
    layout.addWidget(text_label)

    layout.addStretch()
    return widget


def clear_synced_widgets(layout):
    """清理同步状态 widgets"""
    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)
        if isinstance(item.widget(), QWidget) and not isinstance(
            item.widget(), (QLabel, QCheckBox)
        ):
            widget = item.widget()
            layout.removeWidget(widget)
            widget.deleteLater()
