import os
import sys
import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QScrollArea, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from loguru import logger
from src.utils.i18n_manager import i18n_manager

# 初始化翻译函数
_ = i18n_manager.get_text

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

class DocsTab(QWidget):
    """API文档标签页"""
    
    def __init__(self):
        super().__init__()
        
        logger.debug("Initializing DocsTab")
        
        # 初始化界面
        self.init_ui()
        
        # 连接语言切换信号
        i18n_manager.language_changed.connect(self._update_texts)
        logger.debug("Connected language change signal in DocsTab")
        
    def _update_texts(self):
        """更新界面文本"""
        logger.debug("Updating texts in DocsTab")
        
        # 更新搜索框占位符
        if hasattr(self, 'search_input'):
            placeholder = _("docs.search.placeholder")
            logger.debug(f"Setting search placeholder: {placeholder}")
            self.search_input.setPlaceholderText(placeholder)
            
        # 重新加载所有文档区块
        if hasattr(self, 'content_layout'):
            logger.debug("Reloading document sections")
            # 清除现有内容
            while self.content_layout.count():
                item = self.content_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    # 清理布局中的所有部件
                    while item.layout().count():
                        sub_item = item.layout().takeAt(0)
                        if sub_item.widget():
                            sub_item.widget().deleteLater()
                    item.layout().deleteLater()
            
            # 重新添加文档区块
            self.add_doc_sections()
            
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # 搜索区域
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
            }
            QFrame:hover {
                border: 1px solid #1a73e8;
            }
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(12, 8, 12, 8)
        search_layout.setSpacing(6)
        
        # 搜索图标
        search_icon = QLabel()
        if icon_path := get_icon_path('search.png'):
            search_icon.setPixmap(QIcon(icon_path).pixmap(QSize(16, 16)))
        search_icon.setStyleSheet("QLabel { background: transparent; padding: 2px; }")
        search_layout.addWidget(search_icon)
        
        # 搜索输入框
        self.search_input = QLineEdit()
        # 设置初始占位符
        placeholder = _("docs.search.placeholder")
        logger.debug(f"Initial search placeholder: {placeholder}")
        self.search_input.setPlaceholderText(placeholder)
        
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: none;
                padding: 4px;
                font-size: 13px;
                min-width: 300px;
                background: transparent;
                color: #2C3E50;
            }
            QLineEdit:focus {
                outline: none;
            }
            QLineEdit::placeholder {
                color: #666666;
            }
        """)
        self.search_input.textChanged.connect(self.filter_docs)
        search_layout.addWidget(self.search_input)
        
        search_layout.addStretch()
        layout.addWidget(search_frame)
        
        # 文档内容区域
        content_area = QScrollArea()
        content_area.setWidgetResizable(True)
        content_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #F0F0F0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #C0C0C0;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(15)
        content_area.setWidget(content_widget)
        layout.addWidget(content_area)
        
        logger.debug("UI initialized, calling _update_texts")
        # 初始化文本
        self._update_texts()

    def add_doc_sections(self):
        """添加文档分区"""
        # JDK API 文档
        self.add_section_title(_("docs.sections.api"), "api.png")
        self.add_api_docs()
        
        # 添加分隔线
        self.add_separator()
        
        # Java 教程和指南
        self.add_section_title(_("docs.sections.tutorials"), "book.png")
        self.add_tutorial_docs()
        
        # 添加分隔线
        self.add_separator()
        
        # 开发者资源
        self.add_section_title(_("docs.sections.resources"), "dev.png")
        self.add_dev_resources()
        
        # 添加分隔线
        self.add_separator()
        
        # 其他资料
        self.add_section_title(_("docs.sections.others"), "cn.png")
        self.add_chinese_resources()

    def add_section_title(self, title, icon_name):
        """添加分区标题"""
        logger.debug(f"Adding section title: {title}")
        
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 10, 0, 5)
        
        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        if icon_path := get_icon_path(icon_name):
            icon_label.setPixmap(QIcon(icon_path).pixmap(QSize(20, 20)))
        title_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #1a73e8;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        self.content_layout.addLayout(title_layout)
        logger.debug(f"Section title added: {title}")
        
    def add_separator(self):
        """添加分隔线"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #E0E0E0;")
        self.content_layout.addWidget(separator)
        
    def create_doc_button(self, text, url, icon_name=None):
        """创建文档按钮"""
        button = QPushButton(text)
        if icon_name:
            if icon_path := get_icon_path(icon_name):
                button.setIcon(QIcon(icon_path))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: webbrowser.open(url))
        button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 15px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: white;
                color: #2C3E50;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
                border-color: #1a73e8;
            }
        """)
        return button
        
    def add_api_docs(self):
        """添加 API 文档链接"""
        logger.debug("Adding API documentation links")
        api_docs = {
            _("docs.api.jdk23"): 'https://docs.oracle.com/en/java/javase/23/docs/api/',
            _("docs.api.jdk21"): 'https://docs.oracle.com/en/java/javase/21/docs/api/',
            _("docs.api.jdk17"): 'https://docs.oracle.com/en/java/javase/17/docs/api/',
            _("docs.api.jdk11"): 'https://docs.oracle.com/en/java/javase/11/docs/api/',
            _("docs.api.jdk8"): 'https://docs.oracle.com/javase/8/docs/api/'
        }
        
        for version, url in api_docs.items():
            logger.debug(f"Creating API doc button: {version} -> {url}")
            button = self.create_doc_button(version, url, "java.png")
            self.content_layout.addWidget(button)
        logger.debug("API documentation links added")
            
    def add_tutorial_docs(self):
        """添加教程文档链接"""
        tutorials = {
            _("docs.tutorials.spec"): 'https://docs.oracle.com/javase/specs/',
            _("docs.tutorials.tutorial"): 'https://docs.oracle.com/javase/tutorial/',
            _("docs.tutorials.jvm"): 'https://docs.oracle.com/javase/specs/jvms/se21/html/index.html',
            _("docs.tutorials.security"): 'https://www.oracle.com/java/technologies/javase/seccodeguide.html',
            _("docs.tutorials.troubleshoot"): 'https://docs.oracle.com/en/java/javase/21/troubleshoot/index.html'
        }
        
        for title, url in tutorials.items():
            button = self.create_doc_button(title, url, "book.png")
            self.content_layout.addWidget(button)
            
    def add_dev_resources(self):
        """添加开发者资源链接"""
        resources = {
            _("docs.resources.devcenter"): 'https://dev.java/',
            _("docs.resources.openjdk"): 'https://openjdk.org/guide/',
            _("docs.resources.relnotes"): 'https://www.oracle.com/java/technologies/javase/jdk-relnotes-index.html',
            _("docs.resources.adoption"): 'https://wiki.openjdk.org/display/Adoption/Guide',
            _("docs.resources.performance"): 'https://docs.oracle.com/en/java/javase/21/performance/index.html'
        }
        
        # 添加主要资源
        for title, url in resources.items():
            button = self.create_doc_button(title, url, "dev.png")
            self.content_layout.addWidget(button)
            
        # 添加社区资源
        community_resources = {
            _("docs.resources.community.openjdk"): 'https://openjdk.org/groups/gb/',
            _("docs.resources.community.usergroup"): 'https://community.oracle.com/community/groundbreakers/java',
            _("docs.resources.community.spring"): 'https://spring.io/community',
            _("docs.resources.community.jakarta"): 'https://jakarta.ee/community/',
            _("docs.resources.community.reddit"): 'https://www.reddit.com/r/java/',
            _("docs.resources.community.stackoverflow"): 'https://stackoverflow.com/questions/tagged/java'
        }
        
        # 添加社区资源
        for title, url in community_resources.items():
            button = self.create_doc_button(title, url, "community.png")
            self.content_layout.addWidget(button)
            
    def add_chinese_resources(self):
        """添加其他资料链接"""
        resources = {
            _("docs.others.alibaba"): 'https://github.com/alibaba/p3c',
            _("docs.others.jvm"): 'https://github.com/waylau/java-virtual-machine-specification',
            _("docs.others.effective"): 'https://github.com/clxering/Effective-Java-3rd-edition-Chinese-English-bilingual',
            _("docs.others.interview"): 'https://github.com/CyC2018/CS-Notes/blob/master/notes/Java%20%E5%9F%BA%E7%A1%80.md',
            _("docs.others.source"): 'https://github.com/seaswalker/JDK',
            _("docs.others.guide"): 'https://github.com/Snailclimb/JavaGuide',
            _("docs.others.advanced"): 'https://github.com/doocs/advanced-java',
            _("docs.others.growth"): 'https://github.com/hollischuang/toBeTopJavaer',
            _("docs.others.awesome"): 'https://github.com/CodingDocs/awesome-java',
            _("docs.others.tech"): 'https://github.com/crossoverJie/JCSprout',
            _("docs.others.concurrent"): 'https://github.com/RedSpider1/concurrent',
            _("docs.others.jvmcore"): 'https://github.com/doocs/jvm'
        }
        
        # 分批添加资源，每行3个
        items = list(resources.items())
        for i in range(0, len(items), 3):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)
            
            # 添加当前行的资源
            for title, url in items[i:min(i+3, len(items))]:
                button = self.create_doc_button(title, url, "book.png")
                row_layout.addWidget(button)
            
            # 如果当前行不足3个，添加伸缩项
            if len(items[i:min(i+3, len(items))]) < 3:
                row_layout.addStretch()
            
            self.content_layout.addLayout(row_layout)
            
    def filter_docs(self, text):
        """过滤文档链接"""
        text = text.lower()
        
        # 遍历所有按钮
        for i in range(self.content_layout.count()):
            item = self.content_layout.itemAt(i)
            widget = item.widget() if item else None
            
            # 只处理按钮和分隔线
            if isinstance(widget, QPushButton):
                # 如果搜索文本为空或文本匹配，则显示
                if not text or text in widget.text().lower():
                    widget.show()
                else:
                    widget.hide()
            elif isinstance(widget, QFrame) and widget.frameShape() == QFrame.Shape.HLine:
                # 分隔线的显示逻辑：如果下一个按钮可见则显示
                next_visible = False
                for j in range(i + 1, self.content_layout.count()):
                    next_item = self.content_layout.itemAt(j)
                    next_widget = next_item.widget() if next_item else None
                    if isinstance(next_widget, QPushButton) and not next_widget.isHidden():
                        next_visible = True
                        break
                    elif isinstance(next_widget, QFrame) and next_widget.frameShape() == QFrame.Shape.HLine:
                        break
                widget.setVisible(next_visible) 