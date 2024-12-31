import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QGraphicsDropShadowEffect, QPushButton
)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QPoint, QEasingCurve, QRect
from PyQt6.QtGui import QIcon, QColor, QPainter, QPainterPath
from loguru import logger

def get_icon_path(icon_name):
    """获取图标路径，支持多个场景
    
    Args:
        icon_name: 图标文件名
        
    Returns:
        str: 图标的完整路径，如果找不到则返回 None
    """
    # 可能的基础路径列表
    base_paths = []
    
    # 1. 打包后环境路径
    if getattr(sys, 'frozen', False):
        base_paths.append(os.path.join(sys._MEIPASS, 'resources', 'icons'))
    
    # 2. 开发环境路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    base_paths.extend([
        os.path.join(project_root, 'resources', 'icons'),  # 主项目resources目录
        os.path.join(current_dir, '..', '..', '..', 'resources', 'icons'),  # 相对路径
        os.path.join(os.path.dirname(sys.executable), 'resources', 'icons'),  # 可执行文件目录
    ])
    
    # 3. 作为模块安装的环境路径
    if '__file__' in globals():
        module_dir = os.path.dirname(os.path.abspath(__file__))
        base_paths.append(os.path.join(module_dir, 'resources', 'icons'))
    
    # 遍历所有可能的路径
    for base_path in base_paths:
        icon_path = os.path.join(base_path, icon_name)
        if os.path.exists(icon_path):
            return icon_path
            
    # 如果找不到图标，记录警告并返回 None
    logger.warning(f"Icon not found: {icon_name}")
    logger.debug(f"Searched paths: {base_paths}")
    return None

class FloatingNavButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(38, 38)
        self.setStyleSheet("""
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
        """)
        self.setText("☰")
        self.setMouseTracking(True)
        self.raise_()

class FloatingNavPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setFixedHeight(320)
        self.setup_ui()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.is_expanded = False
        self.slide_animation = QPropertyAnimation(self, b"geometry")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutExpo)
        
    def paintEvent(self, event):
        """重写绘制事件以实现完美的圆角阴影"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 创建圆角路径
        rect = self.content.rect()
        path = QPainterPath()
        path.addRoundedRect(
            float(rect.x()),
            float(rect.y()),
            float(rect.width()),
            float(rect.height()),
            16.0,
            16.0
        )
        
        # 设置裁剪区域
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
        
        # 创建标题区域
        title_widget = QWidget()
        title_widget.setObjectName("titleWidget")
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(16, 10, 16, 10)
        
        # 添加标题图标
        title_icon = QLabel()
        title_icon.setFixedSize(16, 16)
        if icon_path := get_icon_path('menu.png'):
            title_icon.setPixmap(QIcon(icon_path).pixmap(12, 12))
        title_icon.setStyleSheet("background: transparent; padding: 2px;")
        title_layout.addWidget(title_icon)
        
        title_label = QLabel("目录导航")
        title_label.setObjectName("titleLabel")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        content_layout.addWidget(title_widget)
        
        # 创建导航按钮容器
        nav_container = QWidget()
        nav_container.setObjectName("navContainer")
        self.nav_layout = QVBoxLayout(nav_container)
        self.nav_layout.setContentsMargins(10, 6, 10, 10)
        self.nav_layout.setSpacing(3)
        
        content_layout.addWidget(nav_container)
        layout.addWidget(self.content)
        
        # 为内容添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(-4, 0)
        self.content.setGraphicsEffect(shadow)
        
        # 设置样式
        self.setStyleSheet("""
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
        """)

    def layout(self):
        """返回导航按钮容器的布局"""
        return self.nav_layout

class QuickNavTrigger(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 160)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 创建主布局，设置为0边距以确保内容容器居中
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建内容容器，设置固定宽度
        content = QFrame(self)
        content.setObjectName("content")
        content.setFixedWidth(32)  # 设置固定宽度
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 10, 0, 10)
        content_layout.setSpacing(6)
        
        # 添加导航图标
        icon_container = QWidget()
        icon_container.setFixedSize(24, 24)  # 稍微减小容器尺寸
        icon_layout = QHBoxLayout(icon_container)  # 使用水平布局确保左右居中
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)
        
        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        icon_label.setStyleSheet("""
            QLabel {
                background-color: rgba(59, 130, 246, 0.12);
                border-radius: 6px;
                padding: 3px;
            }
        """)
        if icon_path := get_icon_path('nav.png'):
            icon_label.setPixmap(QIcon(icon_path).pixmap(14, 14))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(icon_container, 0, Qt.AlignmentFlag.AlignHCenter)
        
        # 创建垂直文字
        text_label = QLabel("快\n捷\n导\n航")
        text_label.setStyleSheet("""
            QLabel {
                color: #3B82F6;
                font-size: 14px;
                font-weight: 600;
                line-height: 2.2;
                letter-spacing: 3px;
            }
        """)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(text_label, 0, Qt.AlignmentFlag.AlignHCenter)
        content_layout.addStretch()
        
        # 将内容容器添加到主布局并居中
        layout.addWidget(content, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(-2, 2)
        content.setGraphicsEffect(shadow)
        
        # 设置内容容器样式
        content.setStyleSheet("""
            QFrame#content {
                background-color: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.8);
                border-radius: 12px;
            }
            QFrame#content:hover {
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.9);
            }
        """)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent().toggle_navigation()

class HelpTab(QWidget):
    def __init__(self):
        super().__init__()
        self.sections = []  # Store section references
        self.nav_visible = False
        self.init_ui()
        self.setup_navigation()
        # 监听主窗口移动
        self.window().installEventFilter(self)

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
            ("JDK 发行版说明", "java.png"),
            ("版本标识说明", "java-version.png"),
            ("平台支持说明", "platform.png"),
            ("功能使用说明", "feature.png"),
            ("环境变量管理", "env.png"),
            ("使用技巧", "tips.png"),
            ("常见问题", "warning.png")
        ]
        
        for title, icon_name in sections_data:
            nav_btn = QPushButton(title)
            if icon_path := get_icon_path(icon_name):
                nav_btn.setIcon(QIcon(icon_path))
                nav_btn.setIconSize(QSize(18, 18))
            nav_btn.clicked.connect(lambda checked, t=title: self.scroll_to_section(t))
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
            self.nav_panel.setGeometry(self.width(), panel_y, 
                                     self.nav_panel.width(), self.nav_panel.height())

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
                QRect(self.width(), panel_y, self.nav_panel.width(), self.nav_panel.height()))
            self.nav_panel.slide_animation.setEndValue(
                QRect(self.width() - self.nav_panel.width(), panel_y, 
                     self.nav_panel.width(), self.nav_panel.height()))
            self.nav_panel.show()
        else:
            # 收起动画
            self.nav_panel.slide_animation.setStartValue(
                QRect(self.width() - self.nav_panel.width(), panel_y, 
                     self.nav_panel.width(), self.nav_panel.height()))
            self.nav_panel.slide_animation.setEndValue(
                QRect(self.width(), panel_y, self.nav_panel.width(), self.nav_panel.height()))
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

    def scroll_to_section(self, title):
        """滚动到指定标题的章节"""
        for section in self.sections:
            # 查找标题标签
            title_layout = section.findChild(QHBoxLayout)
            if title_layout:
                for i in range(title_layout.count()):
                    widget = title_layout.itemAt(i).widget()
                    if isinstance(widget, QLabel) and widget.text() == title:
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
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
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
        """)
        
        # 创建内容容器
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #F5F7FA;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(25, 25, 25, 25)
        
        # 按新顺序添加帮助内容
        
        # 添加 JDK 发行版说明
        self.add_help_section(content_layout, "JDK 发行版说明", "java.png", [
            ("Oracle JDK", [
                "• Oracle 官方发行版，提供商业支持",
                "• 包含商业特性和专有功能",
                "• 需要 Oracle 账号下载",
                "• 商业用途需要付费许可",
                "• 更新最及时，性能优化好"
            ]),
            ("OpenJDK", [
                "• 开源参考实现，完全免费",
                "• 由 Oracle 主导开发维护",
                "• 不包含商业特性",
                "• 仅提供最新的三个 LTS 版本",
                "• 适合开发和学习使用"
            ]),
            ("Eclipse Temurin", [
                "• 由 Eclipse 基金会维护的 OpenJDK 发行版",
                "• 前身是 AdoptOpenJDK",
                "• 提供长期稳定支持",
                "• 免费商用，质量可靠",
                "• 社区活跃，更新及时"
            ]),
            ("Amazon Corretto", [
                "• 亚马逊发布的 OpenJDK 发行版",
                "• 针对云环境优化",
                "• 提供长期支持和安全更新",
                "• 免费商用，AWS 官方支持",
                "• 适合云原生应用"
            ]),
            ("Azul Zulu", [
                "• Azul Systems 发布的 OpenJDK 发行版",
                "• 提供全面的版本支持",
                "• 有免费版和商业版",
                "• 性能优化，稳定可靠",
                "• 适合企业级应用"
            ])
        ])
        
        # 添加版本标识说明
        self.add_help_section(content_layout, "版本标识说明", "java-version.png", [
            ("版本生命周期", [
                "• LTS (Long Term Support): 长期支持版本，如 8、11、17、21",
                "• GA (General Availability): 正式发布版本，稳定可用",
                "• EA (Early Access): 早期访问版本，预览版",
                "• CPU (Critical Patch Update): 关键补丁更新",
                "• PSU (Patch Set Update): 完整补丁集更新"
            ]),
            ("版本号说明", [
                "• 主版本号: 重大更新，如 Java 8、Java 11",
                "• 次版本号: 新特性更新，如 11.0.12",
                "• 补丁版本: Bug修复和安全更新，如 11.0.12.7",
                "• Build号: 构建版本，如 11.0.12+7",
                "• 发行标识: 如 -LTS、-GA、-EA"
            ]),
            ("更新频率", [
                "• LTS版本: 每两年发布一次",
                "• 非LTS版本: 每六个月发布一次",
                "• 安全更新: 每季度发布一次",
                "• 关键补丁: 根据需要随时发布",
                "• 预览版本: 新版本发布前几个月"
            ]),
            ("选择建议", [
                "• 企业项目建议使用 LTS 版本",
                "• 开发测试可以使用最新 GA 版本",
                "• 尝鲜体验可以使用 EA 版本",
                "• 生产环境避免使用 EA 版本",
                "• 重视安全应及时更新 CPU 版本"
            ])
        ])
        
        # 添加平台支持说明
        self.add_help_section(content_layout, "平台支持说明", "platform.png", [
            ("Windows", [
                "• 使用符号链接进行版本切换",
                "• 需要管理员权限修改系统环境变量",
                "• 支持 Windows 10/11 的原生符号链接",
                "• 自动配置系统环境变量",
                "• 切换版本后立即生效"
            ]),
            ("macOS", [
                "• 支持 Homebrew 安装的 JDK",
                "• 使用符号链接进行版本切换",
                "• 自动更新 shell 配置文件（bash/zsh）",
                "• 需要管理员权限创建符号链接",
                "• 切换后需重新加载配置文件"
            ]),
            ("Linux", [
                "• 支持 apt/yum 包管理器安装的 JDK",
                "• 使用符号链接进行版本切换",
                "• 自动更新 shell 配置文件（bash/zsh/fish）",
                "• 需要 sudo 权限创建符号链接",
                "• 切换后需重新加载配置文件"
            ])
        ])
        
        # 添加功能使用说明
        self.add_help_section(content_layout, "功能使用说明", "feature.png", [
            ("在线下载", [
                "• 支持多个主流 JDK 发行版下载",
                "• 自动检测并显示最新版本信息",
                "• 显示版本特性和发布说明",
                "• 支持断点续传和下载进度显示",
                "• 下载完成后自动解压安装"
            ]),
            ("本地管理", [
                "• 支持添加本地已安装的 JDK",
                "• 自动识别 JDK 版本信息",
                "• 可以移除不需要的版本",
                "• 支持查看安装路径和版本详情",
                "• 点击路径可以打开安装目录"
            ]),
            ("版本切换", [
                "• 点击切换按钮即可更改使用版本",
                "• 自动更新环境变量配置",
                "• 支持通过托盘菜单快速切换",
                "• 切换后新开终端才会生效",
                "• 可以使用 java -version 验证"
            ])
        ])
        
        # 添加环境变量管理说明
        self.add_help_section(content_layout, "环境变量管理", "env.png", [
            ("自动管理", [
                "• 自动配置 JAVA_HOME 环境变量",
                "• 自动更新系统 Path 环境变量",
                "• 使用软链接实现无缝切换",
                "• 避免手动修改系统环境变量",
                "• 支持环境变量备份和还原"
            ]),
            ("手动设置", [
                "• 可以查看当前环境变量值",
                "• 支持复制环境变量内容",
                "• 提供手动配置的参考值",
                "• 修改后可以立即生效",
                "• 配置出错可以使用还原功能"
            ]),
            ("平台差异", [
                "• Windows：直接修改系统环境变量",
                "• macOS：更新 shell 配置文件",
                "• Linux：更新 shell 配置文件",
                "• Unix 系统需重新加载配置",
                "• 支持多种 shell（bash/zsh/fish）"
            ])
        ])
        
        # 添加使用技巧
        self.add_help_section(content_layout, "使用技巧", "tips.png", [
            ("托盘功能", [
                "• 双击托盘图标打开主界面",
                "• 右键菜单快速切换版本",
                "• 托盘图标显示当前版本",
                "• 支持开机自启动设置",
                "• 最小化时自动隐藏到托盘"
            ]),
            ("界面操作", [
                "• 支持浅色/深色主题切换",
                "• 可以调整界面布局大小",
                "• 版本列表支持搜索筛选",
                "• 支持键盘快捷操作",
                "• 界面所有按钮都有提示"
            ])
        ])
        
        # 添加常见问题
        self.add_help_section(content_layout, "常见问题", "warning.png", [
            ("下载问题", [
                "• 检查网络连接是否正常",
                "• 尝试切换到其他下载源",
                "• 部分版本可能需要手动下载",
                "• 确保磁盘空间充足",
                "• 下载失败可以重试或更换版本"
            ]),
            ("环境变量问题", [
                "• Windows 需要管理员权限",
                "• Unix 需要 sudo 权限",
                "• 修改后新开终端才能生效",
                "• 避免与其他工具冲突",
                "• 建议定期备份环境变量"
            ]),
            ("使用问题", [
                "• 软链接路径不要使用中文",
                "• 安装路径避免特殊字符",
                "• 查看日志可以定位问题",
                "• 版本切换后请重启终端",
                "• Unix 系统需重新加载配置"
            ])
        ])
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
    def add_help_section(self, parent_layout, title, icon_name, items):
        """添加帮助内容区块"""
        # 创建区块容器
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E5E9F2;
                margin: 0;
            }
        """)
        
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
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font-size: 16px;
                font-weight: bold;
                padding: 2px 0;
            }
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        section_layout.addLayout(title_layout)
        
        # 添加分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("""
            background-color: #E8EEF7;
            margin: 0 -10px;
        """)
        section_layout.addWidget(separator)
        
        # 添加内容项
        for item_title, item_list in items:
            item_frame = QFrame()
            item_frame.setStyleSheet("""
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
            """)
            item_layout = QVBoxLayout(item_frame)
            item_layout.setSpacing(6)
            item_layout.setContentsMargins(16, 12, 16, 12)
            
            # 添加子标题
            title_layout = QHBoxLayout()
            title_layout.setSpacing(8)
            
            bullet = QLabel("•")
            bullet.setStyleSheet("""
                QLabel {
                    color: #1a73e8;
                    font-size: 16px;
                    font-weight: bold;
                }
            """)
            title_layout.addWidget(bullet)
            
            item_title_label = QLabel(item_title)
            item_title_label.setStyleSheet("""
                QLabel {
                    color: #1a73e8;
                    font-weight: bold;
                    font-size: 14px;
                }
            """)
            title_layout.addWidget(item_title_label)
            title_layout.addStretch()
            item_layout.addLayout(title_layout)
            
            # 添加描述列表
            desc_frame = QFrame()
            desc_frame.setStyleSheet("""
                QFrame {
                    background: transparent;
                    margin-left: 4px;
                }
            """)
            desc_layout = QVBoxLayout(desc_frame)
            desc_layout.setSpacing(4)
            desc_layout.setContentsMargins(0, 0, 0, 0)
            
            for desc in item_list:
                desc_label = QLabel(desc)
                desc_label.setStyleSheet("""
                    QLabel {
                        color: #4A5568;
                        font-size: 13px;
                        line-height: 1.5;
                    }
                """)
                desc_label.setWordWrap(True)
                desc_layout.addWidget(desc_label)
            
            item_layout.addWidget(desc_frame)
            section_layout.addWidget(item_frame)
        
        parent_layout.addWidget(section) 
        # 将 section 添加到列表中以供导航使用
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