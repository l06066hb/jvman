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
        self.init_ui()
        
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
        search_layout.setSpacing(6)  # 调整图标和输入框的间距
        
        # 搜索图标
        search_icon = QLabel()
        if icon_path := get_icon_path('search.png'):
            search_icon.setPixmap(QIcon(icon_path).pixmap(QSize(16, 16)))
        search_icon.setStyleSheet("""
            QLabel {
                background: transparent;
                padding: 2px;
            }
        """)
        search_layout.addWidget(search_icon)
        
        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索文档资料...")
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
        
        # 添加伸缩项，确保搜索框靠左
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
        
        # 添加文档链接
        self.add_doc_sections()
        
    def add_doc_sections(self):
        """添加文档分区"""
        # JDK API 文档
        self.add_section_title("JDK API 文档", "api.png")
        self.add_api_docs()
        
        # 添加分隔线
        self.add_separator()
        
        # Java 教程和指南
        self.add_section_title("Java 教程和指南", "book.png")
        self.add_tutorial_docs()
        
        # 添加分隔线
        self.add_separator()
        
        # 开发者资源
        self.add_section_title("开发者资源", "dev.png")
        self.add_dev_resourcess()
        
        # 添加分隔线
        self.add_separator()
        
        # 中文资料
        self.add_section_title("中文资料", "cn.png")
        self.add_chinese_resourcess()
        
    def add_section_title(self, title, icon_name):
        """添加分区标题"""
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
        api_docs = {
            'JDK 23': 'https://docs.oracle.com/en/java/javase/23/docs/api/',
            'JDK 21 (LTS)': 'https://docs.oracle.com/en/java/javase/21/docs/api/',
            'JDK 17 (LTS)': 'https://docs.oracle.com/en/java/javase/17/docs/api/',
            'JDK 11 (LTS)': 'https://docs.oracle.com/en/java/javase/11/docs/api/',
            'JDK 8 (LTS)': 'https://docs.oracle.com/javase/8/docs/api/'
        }
        
        for version, url in api_docs.items():
            button = self.create_doc_button(version, url, "java.png")
            self.content_layout.addWidget(button)
            
    def add_tutorial_docs(self):
        """添加教程文档链接"""
        tutorials = {
            'Java 语言规范': 'https://docs.oracle.com/javase/specs/',
            'Java 教程 (Oracle)': 'https://docs.oracle.com/javase/tutorial/',
            'JVM 规范': 'https://docs.oracle.com/javase/specs/jvms/se21/html/index.html',
            'Java 安全编程指南': 'https://www.oracle.com/java/technologies/javase/seccodeguide.html',
            'Java 故障排除指南': 'https://docs.oracle.com/en/java/javase/21/troubleshoot/index.html'
        }
        
        for title, url in tutorials.items():
            button = self.create_doc_button(title, url, "book.png")
            self.content_layout.addWidget(button)
            
    def add_dev_resourcess(self):
        """添加开发者资源链接"""
        resourcess = {
            'Java 开发者中心': 'https://dev.java/',
            'OpenJDK 文档': 'https://openjdk.org/guide/',
            'Java 发行说明': 'https://www.oracle.com/java/technologies/javase/jdk-relnotes-index.html',
            'Java 兼容性指南': 'https://wiki.openjdk.org/display/Adoption/Guide',
            'Java 性能优化指南': 'https://docs.oracle.com/en/java/javase/21/performance/index.html'
        }
        
        for title, url in resourcess.items():
            button = self.create_doc_button(title, url, "dev.png")
            self.content_layout.addWidget(button)
            
    def add_chinese_resourcess(self):
        """添加中文资料链接"""
        resourcess = {
            'Java 开发手册(阿里巴巴)': 'https://github.com/alibaba/p3c',
            'Java 虚拟机规范(中文版)': 'https://github.com/waylau/java-virtual-machine-specification',
            'Effective Java 中文版': 'https://github.com/clxering/Effective-Java-3rd-edition-Chinese-English-bilingual',
            'Java 核心技术面试精讲': 'https://github.com/CyC2018/CS-Notes/blob/master/notes/Java%20%E5%9F%BA%E7%A1%80.md',
            'Java 源码分析': 'https://github.com/seaswalker/JDK',
            'JavaGuide(Java面试+学习指南)': 'https://github.com/Snailclimb/JavaGuide',
            'advanced-java(互联网 Java 工程师进阶知识完全扫盲)': 'https://github.com/doocs/advanced-java',
            'Java 工程师成神之路': 'https://github.com/hollischuang/toBeTopJavaer',
            'Java 优质开源项目集合': 'https://github.com/CodingDocs/awesome-java',
            'Java 技术栈系列文章': 'https://github.com/crossoverJie/JCSprout',
            'Java 并发知识点总结': 'https://github.com/RedSpider1/concurrent',
            'JVM 底层原理解析': 'https://github.com/doocs/jvm'
        }
        
        for title, url in resourcess.items():
            button = self.create_doc_button(title, url, "cn.png")
            self.content_layout.addWidget(button)
            
    def filter_docs(self, text):
        """过滤文档"""
        search_text = text.lower()
        for i in range(self.content_layout.count()):
            item = self.content_layout.itemAt(i)
            if item:
                widget = item.widget()
                if isinstance(widget, QPushButton):
                    if search_text in widget.text().lower():
                        widget.show()
                    else:
                        widget.hide()
                elif isinstance(widget, QFrame):  # 分隔线
                    visible_count = 0
                    # 检查分隔线前后的按钮是否可见
                    for j in range(max(0, i-5), min(self.content_layout.count(), i+5)):
                        prev_item = self.content_layout.itemAt(j)
                        if prev_item and isinstance(prev_item.widget(), QPushButton):
                            if prev_item.widget().isVisible():
                                visible_count += 1
                    widget.setVisible(visible_count > 0) 