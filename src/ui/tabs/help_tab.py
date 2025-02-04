import os
import sys
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QGraphicsDropShadowEffect,
    QPushButton,
    QApplication,
)
from PyQt6.QtCore import (
    Qt,
    QSize,
    QPropertyAnimation,
    QPoint,
    QEasingCurve,
    QRect,
    QTimer,
)
from PyQt6.QtGui import QIcon, QColor, QPainter, QPainterPath
from loguru import logger
from utils.i18n_manager import i18n_manager

# 初始化翻译函数
_ = i18n_manager.get_text


def get_icon_path(icon_name):
    """Get icon path, supporting multiple scenarios

    Args:
        icon_name: Icon filename

    Returns:
        str: Complete path to the icon, or None if not found
    """
    # List of possible base paths
    base_paths = []

    # 1. Packaged environment path
    if getattr(sys, "frozen", False):
        base_paths.append(os.path.join(sys._MEIPASS, "resources", "icons"))

    # 2. Development environment path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    base_paths.extend(
        [
            os.path.join(
                project_root, "resources", "icons"
            ),  # Main project resources directory
            os.path.join(
                current_dir, "..", "..", "..", "resources", "icons"
            ),  # Relative path
            os.path.join(
                os.path.dirname(sys.executable), "resources", "icons"
            ),  # Executable directory
        ]
    )

    # 3. Module installation environment path
    if "__file__" in globals():
        module_dir = os.path.dirname(os.path.abspath(__file__))
        base_paths.append(os.path.join(module_dir, "resources", "icons"))

    # Traverse all possible paths
    for base_path in base_paths:
        icon_path = os.path.join(base_path, icon_name)
        if os.path.exists(icon_path):
            return icon_path

    # If icon not found, log warning and return None
    logger.warning(f"Icon not found: {icon_name}")
    logger.debug(f"Searched paths: {base_paths}")
    return None


class FloatingNavButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 38)
        self.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.6);
                border: none;
                border-radius: 19px;
                color: rgba(148, 163, 184, 0.8);
                font-size: 16px;
                font-family: Arial;
            }
            QPushButton:hover {
                background-color: rgba(74, 158, 255, 0.9);
                color: white;
            }
            QPushButton:pressed {
                background-color: rgba(59, 130, 246, 0.95);
                color: white;
            }
        """
        )
        self.setText("☰")
        self.setMouseTracking(True)
        self.raise_()


class FloatingNavPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Initialize the translation function
        self._ = i18n_manager.get_text

        self.setFixedWidth(260)
        self.setFixedHeight(320)
        self.setup_ui()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.is_expanded = False
        self.slide_animation = QPropertyAnimation(self, b"geometry")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutExpo)

        # 连接语言切换信号
        i18n_manager.language_changed.connect(self._update_texts)

    def _update_texts(self):
        """更新界面文本"""
        try:
            if hasattr(self, "title_label"):
                self.title_label.setText(_("help.navigation.title"))

            # 更新导航按钮文本
            layout = self.layout()
            if layout:
                for i in range(layout.count()):
                    widget = layout.itemAt(i).widget()
                    if isinstance(widget, QPushButton):
                        section_key = widget.property("section_key")
                        if section_key:
                            widget.setText(_(section_key))
        except Exception as e:
            print(f"Error updating nav panel texts: {e}")

    def paintEvent(self, event):
        """Override paint event to achieve perfect rounded shadow"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Create rounded path
        rect = self.content.rect()
        path = QPainterPath()
        path.addRoundedRect(
            float(rect.x()),
            float(rect.y()),
            float(rect.width()),
            float(rect.height()),
            16.0,
            16.0,
        )

        # Set clipping area
        painter.setClipPath(path)

        super().paintEvent(event)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.content = QWidget(self)
        self.content.setObjectName("content")
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Create title area
        title_widget = QWidget()
        title_widget.setObjectName("titleWidget")
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(16, 10, 16, 10)

        # Add title icon
        title_icon = QLabel()
        title_icon.setFixedSize(16, 16)
        if icon_path := get_icon_path("menu.png"):
            title_icon.setPixmap(QIcon(icon_path).pixmap(12, 12))
        title_icon.setStyleSheet("background: transparent; padding: 2px;")
        title_layout.addWidget(title_icon)

        self.title_label = QLabel(_("help.navigation.title"))
        self.title_label.setObjectName("titleLabel")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        content_layout.addWidget(title_widget)

        # Create navigation button container
        nav_container = QWidget()
        nav_container.setObjectName("navContainer")
        self.nav_layout = QVBoxLayout(nav_container)
        self.nav_layout.setContentsMargins(10, 6, 10, 10)
        self.nav_layout.setSpacing(3)

        content_layout.addWidget(nav_container)
        layout.addWidget(self.content)

        # Add shadow effect to content
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(-4, 0)
        self.content.setGraphicsEffect(shadow)

        # Set styles
        self.setStyleSheet(
            """
            QWidget {
                background: transparent;
            }
            #content {
                background-color: rgba(255, 255, 255, 0.98);
                border-top-left-radius: 16px;
                border-bottom-left-radius: 16px;
                border-left: 1px solid rgba(226, 232, 240, 0.95);
                border-top: 1px solid rgba(226, 232, 240, 0.95);
                border-bottom: 1px solid rgba(226, 232, 240, 0.95);
            }
            #titleWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(248, 250, 252, 0.98),
                    stop:1 rgba(248, 250, 252, 0.95));
                border-top-left-radius: 16px;
                border-bottom: 1px solid rgba(241, 245, 249, 0.9);
                padding: 2px 0;
            }
            #titleLabel {
                color: #3B82F6;
                font-size: 13px;
                font-weight: 600;
                margin-left: 4px;
            }
            #navContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.98),
                    stop:1 rgba(255, 255, 255, 0.95));
                border-bottom-left-radius: 16px;
            }
            QPushButton {
                text-align: left;
                padding: 7px 14px;
                border: none;
                border-radius: 6px;
                color: #64748b;
                font-size: 12px;
                margin: 1px 3px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(243, 244, 246, 0.95);
                color: #3b82f6;
            }
        """
        )

    def layout(self):
        """Return the layout of the navigation button container"""
        return self.nav_layout


class QuickNavTrigger(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(36)  # 只设置宽度，高度根据语言自适应
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Create main layout with 0 margins to ensure content container is centered
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create content container with fixed width
        self.content = QFrame(self)
        self.content.setObjectName("content")
        self.content.setFixedWidth(32)  # Set fixed width
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 10, 0, 10)
        content_layout.setSpacing(6)

        # Add navigation icon
        icon_container = QWidget()
        icon_container.setFixedSize(24, 24)  # Slightly reduce container size
        icon_layout = QHBoxLayout(
            icon_container
        )  # Use horizontal layout to ensure left-right centering
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)

        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        icon_label.setStyleSheet(
            """
            QLabel {
                background-color: rgba(59, 130, 246, 0.12);
                border-radius: 6px;
                padding: 3px;
            }
        """
        )
        if icon_path := get_icon_path("nav.png"):
            icon_label.setPixmap(QIcon(icon_path).pixmap(14, 14))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(icon_container, 0, Qt.AlignmentFlag.AlignHCenter)

        # Create vertical text
        self.text_label = QLabel(_("help.navigation.quick_nav"))
        self.text_label.setStyleSheet(
            """
            QLabel {
                color: #3B82F6;
                font-size: 13px;
                font-weight: 600;
                line-height: 1.6;
                letter-spacing: 1px;
            }
        """
        )
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setFixedWidth(20)  # 限制宽度以确保文本垂直排列
        content_layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignHCenter)
        content_layout.addStretch()

        # Add content container to main layout and center it
        layout.addWidget(self.content, 0, Qt.AlignmentFlag.AlignCenter)

        # Add shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(-2, 2)
        self.content.setGraphicsEffect(shadow)

        # Set content container styles
        self.content.setStyleSheet(
            """
            QFrame#content {
                background-color: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.8);
                border-radius: 12px;
            }
            QFrame#content:hover {
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.9);
            }
        """
        )

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 连接语言切换信号
        i18n_manager.language_changed.connect(self._update_texts)

        # 初始化高度
        self._adjust_height()

    def _update_texts(self):
        """更新界面文本"""
        self.text_label.setText(_("help.navigation.quick_nav"))
        self._adjust_height()

    def _adjust_height(self):
        """根据当前语言调整高度"""
        # 获取当前语言
        current_lang = i18n_manager.get_current_language()
        # 根据语言设置不同的高度
        if current_lang == "en_US":
            self.setFixedHeight(280)  # 英文需要更多空间
        else:
            self.setFixedHeight(240)  # 中文使用原来的高度

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent().toggle_navigation()


class HelpTab(QWidget):
    def __init__(self):
        super().__init__()
        self.sections = []  # Store section references
        self.nav_visible = False

        # 连接语言切换信号
        i18n_manager.language_changed.connect(self._update_texts)

        self.init_ui()
        self.setup_navigation()
        # 监听主窗口移动
        self.window().installEventFilter(self)

        # 初始化文本
        self._update_texts()

    def eventFilter(self, obj, event):
        """事件过滤器，用于监听主窗口移动"""
        if obj == self.window() and event.type() == event.Type.Move:
            # 当窗口移动时，自动隐藏导航面板
            if self.nav_visible:
                self.nav_panel.hide()
                self.nav_visible = False
        return super().eventFilter(obj, event)

    def setup_navigation(self):
        """设置导航面板"""
        # 创建导航面板
        self.nav_panel = FloatingNavPanel(self)

        # 创建快捷导航触发器
        self.nav_trigger = QuickNavTrigger(self)

        # 按新顺序添加导航项目
        sections_data = [
            ("help.sections.jdk_vendors", "java.png"),
            ("help.sections.version_types", "java-version.png"),
            ("help.sections.platform_support", "platform.png"),
            ("help.sections.feature_usage", "feature.png"),
            ("help.sections.env_management", "env.png"),
            ("help.sections.usage_tips", "tips.png"),
            ("help.sections.ide.title", "ide.png"),
            ("help.sections.faq", "warning.png"),
        ]

        for key, icon_name in sections_data:
            nav_btn = QPushButton(_(key))
            if icon_path := get_icon_path(icon_name):
                nav_btn.setIcon(QIcon(icon_path))
                nav_btn.setIconSize(QSize(18, 18))
            # Store the key directly in the button's property
            nav_btn.setProperty("section_key", key)
            nav_btn.clicked.connect(
                lambda checked, btn=nav_btn: self.scroll_to_section(
                    btn.property("section_key")
                )
            )
            self.nav_panel.layout().addWidget(nav_btn)

        # 设置初始位置
        self.update_nav_position()

    def update_nav_position(self):
        """更新导航位置"""
        # 更新触发器位置
        trigger_y = (self.height() - self.nav_trigger.height()) // 2
        self.nav_trigger.move(self.width() - self.nav_trigger.width(), trigger_y)

        # 更新导航面板位置
        panel_y = (self.height() - self.nav_panel.height()) // 2
        if not self.nav_panel.is_expanded:
            self.nav_panel.setGeometry(
                self.width(), panel_y, self.nav_panel.width(), self.nav_panel.height()
            )

    def toggle_navigation(self):
        """切换导航面板显示状态"""
        if self.nav_panel.slide_animation.state() == QPropertyAnimation.State.Running:
            return

        # 安全地断开之前的所有连接
        try:
            self.nav_panel.slide_animation.finished.disconnect()
        except TypeError:
            # 如果没有连接，忽略错误
            pass

        panel_y = (self.height() - self.nav_panel.height()) // 2
        if not self.nav_panel.is_expanded:
            # 展开动画
            self.nav_panel.slide_animation.setStartValue(
                QRect(
                    self.width(),
                    panel_y,
                    self.nav_panel.width(),
                    self.nav_panel.height(),
                )
            )
            self.nav_panel.slide_animation.setEndValue(
                QRect(
                    self.width() - self.nav_panel.width(),
                    panel_y,
                    self.nav_panel.width(),
                    self.nav_panel.height(),
                )
            )
            self.nav_panel.show()
        else:
            # 收起动画
            self.nav_panel.slide_animation.setStartValue(
                QRect(
                    self.width() - self.nav_panel.width(),
                    panel_y,
                    self.nav_panel.width(),
                    self.nav_panel.height(),
                )
            )
            self.nav_panel.slide_animation.setEndValue(
                QRect(
                    self.width(),
                    panel_y,
                    self.nav_panel.width(),
                    self.nav_panel.height(),
                )
            )
            # 动画结束后隐藏面板
            self.nav_panel.slide_animation.finished.connect(self._hide_panel)

        self.nav_panel.slide_animation.start()
        self.nav_panel.is_expanded = not self.nav_panel.is_expanded

    def _hide_panel(self):
        """隐藏面板的辅助方法"""
        self.nav_panel.hide()
        # 安全地断开连接
        try:
            self.nav_panel.slide_animation.finished.disconnect(self._hide_panel)
        except TypeError:
            pass

    def scroll_to_section(self, section_key):
        """滚动到指定标题的章节"""
        if not section_key:
            return

        # 使用 key 查找对应的章节
        for section in self.sections:
            title_layout = section.findChild(QHBoxLayout)
            if title_layout:
                for i in range(title_layout.count()):
                    widget = title_layout.itemAt(i).widget()
                    if isinstance(widget, QLabel) and widget.text() == _(section_key):
                        scroll_area = self.findChild(QScrollArea)
                        if scroll_area:
                            # 使用 ensureWidgetVisible 滚动到目标位置
                            scroll_area.ensureWidgetVisible(section, 0, 5)
                            # 隐藏导航面板并重置状态
                            self.nav_panel.hide()
                            self.nav_panel.is_expanded = False
                            return

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;
                background-color: #F5F7FA;
            }
            QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 10px;
                border-radius: 5px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #D0D0D0;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #B0B0B0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """
        )

        # 创建内容容器
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: #F5F7FA;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(20)
        self.content_layout.setContentsMargins(25, 25, 25, 25)

        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)

        # 添加帮助内容
        self._update_help_content()

    def _update_help_content(self):
        """更新帮助内容"""
        # 清除现有内容
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 重置sections列表
        self.sections.clear()

        # 根据当前语言选择内容
        if i18n_manager.get_current_language() == "zh_CN":
            sections_data = [
                (
                    _("help.sections.jdk_vendors"),
                    "java.png",
                    [
                        (
                            "Oracle JDK",
                            [
                                "• Oracle 官方发行版，提供商业支持",
                                "• 包含商业特性和专有功能",
                                "• 下载需要 Oracle 账号",
                                "• 商业使用需要付费许可",
                                "• 更新最及时，性能优化",
                            ],
                        ),
                        (
                            "OpenJDK",
                            [
                                "• 开源参考实现，完全免费",
                                "• 由 Oracle 维护",
                                "• 不包含商业特性",
                                "• 仅提供最新三个 LTS 版本",
                                "• 适合开发和学习",
                            ],
                        ),
                        (
                            "Adoptium",
                            [
                                "• Eclipse 基金会维护的 OpenJDK 构建版本",
                                "• 前身是 AdoptOpenJDK",
                                "• 提供全平台支持",
                                "• 完全免费，可商用",
                                "• 社区活跃，更新及时",
                            ],
                        ),
                        (
                            "Amazon Corretto",
                            [
                                "• 亚马逊维护的 OpenJDK 发行版",
                                "• 针对云环境优化",
                                "• 完全免费，可商用",
                                "• 提供长期支持",
                                "• AWS 服务推荐使用",
                            ],
                        ),
                        (
                            "Zulu",
                            [
                                "• Azul Systems 维护的 OpenJDK 构建版本",
                                "• 提供社区版和企业版",
                                "• 社区版免费使用",
                                "• 更新周期稳定",
                                "• 提供专业技术支持",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.version_types"),
                    "java-version.png",
                    [
                        (
                            _("help.subtitles.lifecycle"),
                            [
                                "• LTS (长期支持)：长期支持版本，如 8、11、17、21",
                                "• GA (正式发布)：正式发布版本，稳定可用",
                                "• EA (早期访问)：早期访问版本，预览版",
                                "• CPU (关键补丁)：关键补丁更新",
                                "• PSU (补丁集)：完整补丁集更新",
                            ],
                        ),
                        (
                            _("help.subtitles.version_number"),
                            [
                                "• 主版本号：重大更新，如 Java 8、Java 11",
                                "• 次版本号：新特性，如 11.0.12",
                                "• 补丁版本：Bug 修复和安全更新，如 11.0.12.7",
                                "• 构建号：构建版本，如 11.0.12+7",
                                "• 发布标识：如 -LTS、-GA、-EA",
                            ],
                        ),
                        (
                            _("help.subtitles.update_frequency"),
                            [
                                "• LTS 版本：每两年发布一次",
                                "• 非 LTS 版本：每六个月发布一次",
                                "• 安全更新：每季度发布",
                                "• 关键补丁：根据需要发布",
                                "• 预览版本：新版本发布前数月",
                            ],
                        ),
                        (
                            _("help.subtitles.selection_guide"),
                            [
                                "• 企业项目应使用 LTS 版本",
                                "• 开发测试可使用最新 GA 版本",
                                "• 提前体验可使用 EA 版本",
                                "• 生产环境应避免使用 EA 版本",
                                "• 应优先考虑安全性并定期更新",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.platform_support"),
                    "platform.png",
                    [
                        (
                            "Windows",
                            [
                                "• 使用符号链接进行版本切换",
                                "• 需要管理员权限修改系统环境变量",
                                "• 支持 Windows 10/11 原生符号链接",
                                "• 自动配置系统环境变量",
                                "• 版本切换立即生效",
                            ],
                        ),
                        (
                            "macOS",
                            [
                                "• 支持通过 Homebrew 安装 JDK",
                                "• 使用符号链接进行版本切换",
                                "• 自动更新 shell 配置文件（bash/zsh）",
                                "• 需要管理员权限创建符号链接",
                                "• 切换后需要重新加载配置文件",
                            ],
                        ),
                        (
                            "Linux",
                            [
                                "• 支持通过 apt/yum 包管理器安装 JDK",
                                "• 使用符号链接进行版本切换",
                                "• 自动更新 shell 配置文件（bash/zsh/fish）",
                                "• 需要 sudo 权限创建符号链接",
                                "• 切换后需要重新加载配置文件",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.feature_usage"),
                    "feature.png",
                    [
                        (
                            _("help.subtitles.online_download"),
                            [
                                "• 支持多个主流 JDK 发行版",
                                "• 自动检测并显示最新版本信息",
                                "• 显示版本特性和发布说明",
                                "• 支持下载进度显示",
                                "• 下载完成后自动解压安装",
                            ],
                        ),
                        (
                            _("help.subtitles.local_management"),
                            [
                                "• 支持添加本地已安装的 JDK",
                                "• 自动识别 JDK 版本信息",
                                "• 可移除不需要的版本",
                                "• 支持查看安装路径和版本详情",
                                "• 点击路径可打开安装目录",
                            ],
                        ),
                        (
                            _("help.subtitles.version_switch"),
                            [
                                "• 点击切换按钮即可更换版本",
                                "• 自动更新环境变量配置",
                                "• 支持通过托盘菜单快速切换",
                                "• 切换后新开终端生效",
                                "• 可通过 java -version 验证",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.env_management"),
                    "env.png",
                    [
                        (
                            _("help.subtitles.auto_management"),
                            [
                                "• 自动配置 JAVA_HOME 环境变量",
                                "• 自动更新系统 Path 环境变量",
                                "• 使用软链接实现无缝切换",
                                "• 避免手动修改系统环境变量",
                                "• 支持环境变量备份和还原",
                            ],
                        ),
                        (
                            _("help.subtitles.manual_setting"),
                            [
                                "• 可查看当前环境变量值",
                                "• 支持复制环境变量内容",
                                "• 提供手动配置参考值",
                                "• 修改后立即生效",
                                "• 配置错误可恢复",
                            ],
                        ),
                        (
                            _("help.subtitles.platform_diff"),
                            [
                                "• Windows：直接修改系统环境变量",
                                "• macOS：更新 shell 配置文件",
                                "• Linux：更新 shell 配置文件",
                                "• Unix 系统需要重新加载配置",
                                "• 支持多种 shell（bash/zsh/fish）",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.usage_tips"),
                    "tips.png",
                    [
                        (
                            _("help.subtitles.tray_feature"),
                            [
                                "• 双击托盘图标打开主界面",
                                "• 右键菜单快速切换版本",
                                "• 托盘图标显示当前版本",
                                "• 支持开机启动设置",
                                "• 自动最小化到托盘",
                            ],
                        ),
                        (
                            _("help.subtitles.interface_operation"),
                            [
                                "• 支持浅色/深色主题切换",
                                "• 可调整界面布局大小",
                                "• 版本列表支持搜索筛选",
                                "• 支持键盘快捷键",
                                "• 界面所有按钮都有提示",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.ide.title"),
                    "ide.png",
                    [
                        (
                            _("ide.overview.title"),
                            [
                                "• 支持主流 IDE：IntelliJ IDEA、Eclipse、VS Code 等",
                                "• 自动识别并配置 IDE 的 JDK 路径",
                                "• 支持多个项目使用不同的 JDK 版本",
                                "• IDE 可以直接使用我们管理的 JDK",
                                "• 版本切换后 IDE 自动识别新版本",
                            ],
                        ),
                        (
                            _("ide.config.title"),
                            [
                                f"• {_('ide.config.intellij.title')}:",
                                f"  {_('ide.config.intellij.steps')[0]}",
                                "  - 打开 Settings (Ctrl+Alt+S)",
                                "  - 转到 Build, Execution, Deployment > Build Tools",
                                "  - 配置 Gradle JVM 或 Maven JVM 为软链接路径",
                                "",
                                f"• {_('ide.config.vscode.title')}:",
                                f"  {_('ide.config.vscode.intro')}",
                                (
                                    "code",
                                    '{\n    "java.jdt.ls.java.home": "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\jvman\\current",\n    "java.configuration.runtimes": [\n        {\n            "name": "JavaSE-Current",\n            "path": "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\jvman\\current",\n            "default": true\n        }\n    ]\n}',
                                ),
                                "",
                                f"• {_('ide.config.eclipse.title')}:",
                                f"  {_('ide.config.eclipse.steps')[0]}",
                                "  - Window > Preferences",
                                "  - Java > Installed JREs",
                                "  - 添加 JRE，选择软链接路径",
                            ],
                        ),
                        (
                            _("ide.benefits.title"),
                            [
                                f"• {_('ide.benefits.env_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.benefits.env_points")
                                ],
                                f"• {_('ide.benefits.project_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.benefits.project_points")
                                ],
                                f"• {_('ide.benefits.version_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.benefits.version_points")
                                ],
                            ],
                        ),
                        (
                            _("ide.practices.title"),
                            [
                                f"• {_('ide.practices.path_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.practices.path_points")
                                ],
                                f"• {_('ide.practices.version_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.practices.version_points")
                                ],
                                f"• {_('ide.practices.performance_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.practices.performance_points")
                                ],
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.faq"),
                    "warning.png",
                    [
                        (
                            _("help.subtitles.download_issues"),
                            [
                                "• 检查网络连接",
                                "• 尝试切换其他下载源",
                                "• 部分版本可能需要手动下载",
                                "• 确保磁盘空间充足",
                                "• 下载失败可重试或切换版本",
                            ],
                        ),
                        (
                            _("help.subtitles.env_issues"),
                            [
                                "• Windows 需要管理员权限",
                                "• Unix 需要 sudo 权限",
                                "• 新开终端后修改生效",
                                "• 避免与其他工具冲突",
                                "• 建议定期备份环境变量",
                            ],
                        ),
                        (
                            _("help.subtitles.usage_issues"),
                            [
                                "• 软链接路径不要使用中文",
                                "• 安装路径避免特殊字符",
                                "• 查看日志可帮助诊断问题",
                                "• 切换版本后重启终端",
                                "• Unix 系统需要重新加载配置",
                            ],
                        ),
                        (
                            _("help.subtitles.ide_issues"),
                            [
                                "• IDE 无法识别 JDK：",
                                "  - 检查软链接路径是否正确",
                                "  - 确认 JDK 版本已正确安装",
                                "  - 尝试重启 IDE 或清除缓存",
                                "• 项目编译失败：",
                                "  - 验证项目 JDK 版本设置",
                                "  - 检查构建工具配置",
                                "  - 更新项目依赖",
                                "• IDE 配置问题：",
                                "  - 确保 IDE 使用了正确的软链接路径",
                                "  - 检查项目的 JDK 配置是否正确",
                                "  - 重新导入项目或刷新 Gradle/Maven 配置",
                            ],
                        ),
                    ],
                ),
            ]
        else:
            sections_data = [
                (
                    _("help.sections.jdk_vendors"),
                    "java.png",
                    [
                        (
                            "Oracle JDK",
                            [
                                "• Oracle official release, providing commercial support",
                                "• Includes commercial features and proprietary functionality",
                                "• Requires Oracle account for download",
                                "• Commercial use requires paid license",
                                "• Updated most timely, performance optimization",
                            ],
                        ),
                        (
                            "OpenJDK",
                            [
                                "• Open source reference implementation, completely free",
                                "• Maintained by Oracle",
                                "• Does not include commercial features",
                                "• Only provides the latest three LTS versions",
                                "• Suitable for development and learning",
                            ],
                        ),
                        (
                            "Eclipse Temurin",
                            [
                                "• OpenJDK release maintained by the Eclipse Foundation",
                                "• Formerly known as AdoptOpenJDK",
                                "• Provides long-term support",
                                "• Free for commercial use, high quality",
                                "• Active community, updated timely",
                            ],
                        ),
                        (
                            "Amazon Corretto",
                            [
                                "• Amazon-released OpenJDK release",
                                "• Optimized for cloud environments",
                                "• Provides long-term support and security updates",
                                "• Free for commercial use, AWS official support",
                                "• Suitable for cloud-native applications",
                            ],
                        ),
                        (
                            "Azul Zulu",
                            [
                                "• OpenJDK release from Azul Systems",
                                "• Provides comprehensive version support",
                                "• Has free and commercial versions",
                                "• Performance optimization, stable reliability",
                                "• Suitable for enterprise applications",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.version_types"),
                    "java-version.png",
                    [
                        (
                            _("help.subtitles.lifecycle"),
                            [
                                "• LTS (Long Term Support): Long-term support versions, such as 8, 11, 17, 21",
                                "• GA (General Availability): Official release versions, stable and usable",
                                "• EA (Early Access): Early access versions, previews",
                                "• CPU (Critical Patch Update): Critical patch updates",
                                "• PSU (Patch Set Update): Full patch set updates",
                            ],
                        ),
                        (
                            _("help.subtitles.version_number"),
                            [
                                "• Major version number: Major updates, such as Java 8, Java 11",
                                "• Minor version number: New features, such as 11.0.12",
                                "• Patch version: Bug fixes and security updates, such as 11.0.12.7",
                                "• Build number: Build version, such as 11.0.12+7",
                                "• Release identifier: Such as -LTS, -GA, -EA",
                            ],
                        ),
                        (
                            _("help.subtitles.update_frequency"),
                            [
                                "• LTS versions: Released every two years",
                                "• Non-LTS versions: Released every six months",
                                "• Security updates: Released quarterly",
                                "• Critical patches: Released as needed",
                                "• Preview versions: Months before new versions are released",
                            ],
                        ),
                        (
                            _("help.subtitles.selection_guide"),
                            [
                                "• Enterprise projects should use LTS versions",
                                "• Development and testing can use the latest GA version",
                                "• Early access can use EA versions",
                                "• Production environments should avoid EA versions",
                                "• Security should be prioritized and updated regularly",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.platform_support"),
                    "platform.png",
                    [
                        (
                            "Windows",
                            [
                                "• Use symbolic links for version switching",
                                "• Requires administrator privileges to modify system environment variables",
                                "• Supports Windows 10/11 native symbolic links",
                                "• Automatically configures system environment variables",
                                "• Version switch takes effect immediately",
                            ],
                        ),
                        (
                            "macOS",
                            [
                                "• Supports JDK installation via Homebrew",
                                "• Use symbolic links for version switching",
                                "• Automatically updates shell configuration files (bash/zsh)",
                                "• Requires administrator privileges to create symbolic links",
                                "• Configuration files need to be reloaded after switching",
                            ],
                        ),
                        (
                            "Linux",
                            [
                                "• Supports JDK installation via apt/yum package managers",
                                "• Use symbolic links for version switching",
                                "• Automatically updates shell configuration files (bash/zsh/fish)",
                                "• Requires sudo privileges to create symbolic links",
                                "• Configuration files need to be reloaded after switching",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.feature_usage"),
                    "feature.png",
                    [
                        (
                            _("help.subtitles.online_download"),
                            [
                                "• Supports multiple mainstream JDK releases",
                                "• Automatically detects and displays the latest version information",
                                "• Displays version features and release notes",
                                "• Supports download progress display",
                                "• Automatically extracts and installs after download",
                            ],
                        ),
                        (
                            _("help.subtitles.local_management"),
                            [
                                "• Supports adding locally installed JDKs",
                                "• Automatically recognizes JDK version information",
                                "• Can remove unnecessary versions",
                                "• Supports viewing installation paths and version details",
                                "• Clicking the path opens the installation directory",
                            ],
                        ),
                        (
                            _("help.subtitles.version_switch"),
                            [
                                "• Click the switch button to change the version",
                                "• Automatically updates environment variable configurations",
                                "• Supports quick switching via tray menu",
                                "• Switching takes effect after opening a new terminal",
                                "• Can be verified using java -version",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.env_management"),
                    "env.png",
                    [
                        (
                            _("help.subtitles.auto_management"),
                            [
                                "• Automatically configures JAVA_HOME environment variable",
                                "• Automatically updates system Path environment variable",
                                "• Uses soft links for seamless switching",
                                "• Avoids manually modifying system environment variables",
                                "• Supports environment variable backup and restoration",
                            ],
                        ),
                        (
                            _("help.subtitles.manual_setting"),
                            [
                                "• Can view current environment variable values",
                                "• Supports copying environment variable content",
                                "• Provides reference values for manual configuration",
                                "• Changes take effect immediately",
                                "• Incorrect configuration can be restored",
                            ],
                        ),
                        (
                            _("help.subtitles.platform_diff"),
                            [
                                "• Windows: Directly modify system environment variables",
                                "• macOS: Update shell configuration files",
                                "• Linux: Update shell configuration files",
                                "• Unix systems require configuration reloading",
                                "• Supports multiple shells (bash/zsh/fish)",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.usage_tips"),
                    "tips.png",
                    [
                        (
                            _("help.subtitles.tray_feature"),
                            [
                                "• Double-click the tray icon to open the main interface",
                                "• Right-click the menu to quickly switch versions",
                                "• Tray icon displays the current version",
                                "• Supports startup settings",
                                "• Minimizes to the tray automatically",
                            ],
                        ),
                        (
                            _("help.subtitles.interface_operation"),
                            [
                                "• Supports light/dark theme switching",
                                "• Can adjust the interface layout size",
                                "• Version list supports search filtering",
                                "• Supports keyboard shortcuts",
                                "• All buttons in the interface have tooltips",
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.ide.title"),
                    "ide.png",
                    [
                        (
                            _("ide.overview.title"),
                            [
                                "• Supports mainstream IDEs: IntelliJ IDEA, Eclipse, VS Code, etc.",
                                "• Automatically recognizes and configures JDK paths for IDEs",
                                "• Supports multiple projects using different JDK versions",
                                "• IDEs can directly use the JDK managed by us",
                                "• The IDE automatically recognizes new versions after switching",
                            ],
                        ),
                        (
                            _("ide.config.title"),
                            [
                                f"• {_('ide.config.intellij.title')}:",
                                f"  {_('ide.config.intellij.steps')[0]}",
                                "  - Open Settings (Ctrl+Alt+S)",
                                "  - Go to Build, Execution, Deployment > Build Tools",
                                "  - Configure Gradle JVM or Maven JVM to use the symlink path",
                                "",
                                f"• {_('ide.config.vscode.title')}:",
                                f"  {_('ide.config.vscode.intro')}",
                                (
                                    "code",
                                    '{\n    "java.jdt.ls.java.home": "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\jvman\\current",\n    "java.configuration.runtimes": [\n        {\n            "name": "JavaSE-Current",\n            "path": "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\jvman\\current",\n            "default": true\n        }\n    ]\n}',
                                ),
                                "",
                                f"• {_('ide.config.eclipse.title')}:",
                                f"  {_('ide.config.eclipse.steps')[0]}",
                                "  - Window > Preferences",
                                "  - Java > Installed JREs",
                                "  - Add JRE, select the symlink path",
                            ],
                        ),
                        (
                            _("ide.benefits.title"),
                            [
                                f"• {_('ide.benefits.env_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.benefits.env_points")
                                ],
                                f"• {_('ide.benefits.project_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.benefits.project_points")
                                ],
                                f"• {_('ide.benefits.version_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.benefits.version_points")
                                ],
                            ],
                        ),
                        (
                            _("ide.practices.title"),
                            [
                                f"• {_('ide.practices.path_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.practices.path_points")
                                ],
                                f"• {_('ide.practices.version_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.practices.version_points")
                                ],
                                f"• {_('ide.practices.performance_title')}:",
                                *[
                                    f"  - {point}"
                                    for point in _("ide.practices.performance_points")
                                ],
                            ],
                        ),
                    ],
                ),
                (
                    _("help.sections.faq"),
                    "warning.png",
                    [
                        (
                            _("help.subtitles.download_issues"),
                            [
                                "• Check network connection",
                                "• Try switching to other download sources",
                                "• Some versions may require manual download",
                                "• Ensure sufficient disk space",
                                "• Retry or switch versions if download fails",
                            ],
                        ),
                        (
                            _("help.subtitles.env_issues"),
                            [
                                "• Windows requires administrator privileges",
                                "• Unix requires sudo privileges",
                                "• Changes take effect after restarting terminal",
                                "• Avoid conflicts with other tools",
                                "• It is recommended to periodically backup environment variables",
                            ],
                        ),
                        (
                            _("help.subtitles.usage_issues"),
                            [
                                "• Do not use Chinese characters in soft link paths",
                                "• Avoid special characters in installation paths",
                                "• Check logs for help diagnosing issues",
                                "• Restart terminal after switching versions",
                                "• Unix systems require configuration reloading",
                            ],
                        ),
                        (
                            _("help.subtitles.ide_issues"),
                            [
                                "• IDE cannot recognize JDK:",
                                "  - Check if the soft link path is correct",
                                "  - Confirm that the JDK version is correctly installed",
                                "  - Try restarting IDE or clearing cache",
                                "• Project compilation fails:",
                                "  - Verify project JDK version settings",
                                "  - Check build tool configurations",
                                "  - Update project dependencies",
                                "• IDE configuration issues:",
                                "  - Ensure that the IDE is using the correct soft link path",
                                "  - Check the project's JDK configuration",
                                "  - Re-import the project or refresh Gradle/Maven configurations",
                            ],
                        ),
                    ],
                ),
            ]

        # 添加帮助内容
        for title, icon_name, items in sections_data:
            self.add_help_section(self.content_layout, title, icon_name, items)

    def create_code_block(self, code_content):
        """创建代码块"""
        # 创建外层容器
        container = QFrame()
        container.setStyleSheet(
            """
            QFrame {
                margin: 8px 0;
                padding: 0;
                background: transparent;
            }
        """
        )
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 创建代码块框架
        code_frame = QFrame()
        code_frame.setObjectName("codeBlock")
        code_frame.setStyleSheet(
            """
            QFrame#codeBlock {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                margin: 0;
                padding: 0;
            }
        """
        )

        code_layout = QVBoxLayout(code_frame)
        code_layout.setContentsMargins(16, 16, 16, 16)
        code_layout.setSpacing(0)

        # 创建顶部工具栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 8)

        # 添加复制按钮
        copy_button = QPushButton("复制代码")
        copy_button.setStyleSheet(
            """
            QPushButton {
                background-color: #2D3748;
                color: #E2E8F0;
                border: 1px solid #4A5568;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4A5568;
            }
            QPushButton:pressed {
                background-color: #1A202C;
            }
            QPushButton:disabled {
                background-color: #4A5568;
                color: #9CA3AF;
            }
        """
        )
        copy_button.setFixedSize(70, 24)
        copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        toolbar.addStretch()
        toolbar.addWidget(copy_button)
        code_layout.addLayout(toolbar)

        # 处理代码内容
        # 使用 \n 分割，保持原始格式
        code_lines = code_content.split("\n")

        # 创建代码标签
        code_label = QLabel()
        code_label.setObjectName("codeText")
        code_label.setStyleSheet(
            """
            QLabel#codeText {
                color: #E2E8F0;
                font-family: 'JetBrains Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.6;
                white-space: pre;
                background: transparent;
                padding: 0;
                border: none;
            }
        """
        )

        # 设置代码内容
        code_label.setText(code_content)
        code_layout.addWidget(code_label)

        # 添加代码框架到容器
        container_layout.addWidget(code_frame)

        # 复制功能
        def copy_code():
            clipboard = QApplication.instance().clipboard()
            clipboard.setText(code_content)
            copy_button.setText("已复制")
            copy_button.setEnabled(False)
            QTimer.singleShot(
                1500,
                lambda: [copy_button.setText("复制代码"), copy_button.setEnabled(True)],
            )

        copy_button.clicked.connect(copy_code)

        return container

    def _apply_syntax_highlighting(self, line):
        """应用简单的语法高亮"""
        # 替换HTML特殊字符
        line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # 关键字高亮
        keywords = [
            "import",
            "from",
            "class",
            "def",
            "return",
            "if",
            "else",
            "for",
            "while",
            "try",
            "except",
            "finally",
            "with",
            "as",
            "in",
            "is",
            "not",
            "and",
            "or",
            "true",
            "false",
            "null",
            "None",
            "True",
            "False",
        ]

        # 特殊标记
        special_chars = ["{", "}", "[", "]", "(", ")", ",", ":"]

        # 应用高亮
        words = line.split(" ")
        highlighted_words = []

        for word in words:
            # 检查是否是空字符串
            if not word:
                highlighted_words.append("")
                continue

            # 处理特殊字符
            for char in special_chars:
                if char in word:
                    parts = word.split(char)
                    new_parts = []
                    for i, part in enumerate(parts):
                        if part:
                            new_parts.append(self._highlight_word(part))
                        if i < len(parts) - 1:
                            new_parts.append(
                                f'<span style="color: #94A3B8;">{char}</span>'
                            )
                    word = "".join(new_parts)
                    break
            else:
                word = self._highlight_word(word)

            highlighted_words.append(word)

        return " ".join(highlighted_words)

    def _highlight_word(self, word):
        """对单个词应用高亮规则"""
        # 关键字
        keywords = [
            "import",
            "from",
            "class",
            "def",
            "return",
            "if",
            "else",
            "for",
            "while",
            "try",
            "except",
            "finally",
            "with",
            "as",
            "in",
            "is",
            "not",
            "and",
            "or",
            "true",
            "false",
            "null",
            "None",
            "True",
            "False",
        ]

        # 数字
        if word.replace(".", "").isdigit():
            return f'<span style="color: #F59E0B;">{word}</span>'

        # 字符串（以引号开始和结束）
        if (word.startswith('"') and word.endswith('"')) or (
            word.startswith("'") and word.endswith("'")
        ):
            return f'<span style="color: #10B981;">{word}</span>'

        # 关键字
        if word in keywords:
            return f'<span style="color: #3B82F6;">{word}</span>'

        # 函数调用（以括号结尾）
        if word.endswith("("):
            return f'<span style="color: #60A5FA;">{word[:-1]}</span><span style="color: #94A3B8;">(</span>'

        # 属性访问（点号后面的部分）
        if "." in word:
            parts = word.split(".")
            highlighted_parts = []
            for i, part in enumerate(parts):
                if i == 0:
                    highlighted_parts.append(part)
                else:
                    highlighted_parts.append(
                        f'<span style="color: #60A5FA;">{part}</span>'
                    )
            return '<span style="color: #94A3B8;">.</span>'.join(highlighted_parts)

        return word

    def process_description(self, desc, desc_layout):
        """处理描述文本，包括代码块"""
        # 如果输入是字符串，直接作为普通文本处理
        if isinstance(desc, str):
            text_label = QLabel(desc)
            text_label.setStyleSheet(
                """
                QLabel {
                    color: #4A5568;
                    font-size: 13px;
                    line-height: 1.5;
                    padding: 0;
                    margin: 0;
                }
            """
            )
            text_label.setWordWrap(True)
            desc_layout.addWidget(text_label)
        # 如果是元组，且第一个元素是 "code"，则作为代码块处理
        elif isinstance(desc, tuple) and len(desc) == 2 and desc[0] == "code":
            code_block = self.create_code_block(desc[1])
            desc_layout.addWidget(code_block)

    def add_help_section(self, parent_layout, title, icon_name, items):
        """添加帮助内容区块"""
        # 创建区块容器
        section = QFrame()
        section.setStyleSheet(
            """
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E5E9F2;
                margin: 0;
            }
        """
        )

        # 创建阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(0, 2)
        section.setGraphicsEffect(shadow)

        section_layout = QVBoxLayout(section)
        section_layout.setSpacing(12)
        section_layout.setContentsMargins(20, 16, 20, 16)

        # 添加标题
        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)

        icon_label = QLabel()
        if icon_path := get_icon_path(icon_name):
            icon_label.setPixmap(QIcon(icon_path).pixmap(QSize(22, 22)))
            title_layout.addWidget(icon_label)

        # 确保标题被翻译
        title_label = QLabel(_(title) if isinstance(title, str) else title)
        title_label.setStyleSheet(
            """
            QLabel {
                color: #2C3E50;
                font-size: 16px;
                font-weight: bold;
                padding: 2px 0;
            }
        """
        )
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        section_layout.addLayout(title_layout)

        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(
            """
            background-color: #E8EEF7;
            margin: 0 -10px;
        """
        )
        section_layout.addWidget(separator)

        # 添加内容项
        for item_title, item_list in items:
            item_frame = QFrame()
            item_frame.setStyleSheet(
                """
                QFrame {
                    background-color: #F8FAFD;
                    border-radius: 8px;
                    margin: 2px 0;
                    border: 1px solid transparent;
                }
                QFrame:hover {
                    background-color: #EDF2FC;
                    border: 1px solid #E5E9F2;
                }
            """
            )
            item_layout = QVBoxLayout(item_frame)
            item_layout.setSpacing(6)
            item_layout.setContentsMargins(16, 12, 16, 12)

            # 添加子标题
            title_layout = QHBoxLayout()
            title_layout.setSpacing(8)

            bullet = QLabel("•")
            bullet.setStyleSheet(
                """
                QLabel {
                    color: #1a73e8;
                    font-size: 16px;
                    font-weight: bold;
                }
            """
            )
            title_layout.addWidget(bullet)

            # 确保子标题被翻译
            item_title_label = QLabel(
                _(item_title) if isinstance(item_title, str) else item_title
            )
            item_title_label.setStyleSheet(
                """
                QLabel {
                    color: #1a73e8;
                    font-weight: bold;
                    font-size: 14px;
                }
            """
            )
            title_layout.addWidget(item_title_label)
            title_layout.addStretch()
            item_layout.addLayout(title_layout)

            # 添加描述列表
            desc_frame = QFrame()
            desc_frame.setStyleSheet(
                """
                QFrame {
                    background: transparent;
                    margin-left: 4px;
                }
            """
            )
            desc_layout = QVBoxLayout(desc_frame)
            desc_layout.setSpacing(4)
            desc_layout.setContentsMargins(0, 0, 0, 0)

            for desc in item_list:
                self.process_description(desc, desc_layout)

            item_layout.addWidget(desc_frame)
            section_layout.addWidget(item_frame)

        parent_layout.addWidget(section)
        self.sections.append(section)

    def hideEvent(self, event):
        """当标签页隐藏时，同时隐藏导航面板"""
        super().hideEvent(event)
        if self.nav_visible:
            self.nav_panel.hide()
            self.nav_visible = False

    def showEvent(self, event):
        """当标签页显示时，更新导航按钮位置"""
        super().showEvent(event)
        self.update_nav_position()

    def focusOutEvent(self, event):
        """当失去焦点时，隐藏导航面板"""
        super().focusOutEvent(event)
        if self.nav_visible:
            self.nav_panel.hide()
            self.nav_visible = False

    def resizeEvent(self, event):
        """窗口大小改变时更新导航位置"""
        super().resizeEvent(event)
        self.update_nav_position()

    def _update_texts(self):
        """更新界面文本"""
        # 更新帮助内容
        self._update_help_content()

        # 更新导航面板
        if hasattr(self, "nav_panel"):
            # 清除导航按钮
            nav_layout = self.nav_panel.nav_layout
            if nav_layout:
                while nav_layout.count():
                    item = nav_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()

            # 重新添加导航按钮
            sections_data = [
                ("help.sections.jdk_vendors", "java.png"),
                ("help.sections.version_types", "java-version.png"),
                ("help.sections.platform_support", "platform.png"),
                ("help.sections.feature_usage", "feature.png"),
                ("help.sections.env_management", "env.png"),
                ("help.sections.usage_tips", "tips.png"),
                ("help.sections.ide.title", "ide.png"),
                ("help.sections.faq", "warning.png"),
            ]

            for key, icon_name in sections_data:
                nav_btn = QPushButton(_(key))
                if icon_path := get_icon_path(icon_name):
                    nav_btn.setIcon(QIcon(icon_path))
                    nav_btn.setIconSize(QSize(18, 18))
                nav_btn.setProperty("section_key", key)
                nav_btn.clicked.connect(
                    lambda checked, btn=nav_btn: self.scroll_to_section(
                        btn.property("section_key")
                    )
                )
                nav_layout.addWidget(nav_btn)

        # 更新快捷导航文本
        if hasattr(self, "nav_trigger"):
            # 查找并更新文本标签
            for child in self.nav_trigger.findChildren(QLabel):
                if not child.pixmap():  # 不是图标的标签
                    child.setText(_("help.navigation.quick_nav"))
                    child.setWordWrap(True)  # 允许文本换行
                    break
