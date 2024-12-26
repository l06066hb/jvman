from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QColor

class HelpTab(QWidget):
    """帮助说明标签页"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
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
        
        # 添加帮助内容
        self.add_help_section(content_layout, "下载安装说明", "icon/download.png", [
            ("安装方式选择", [
                "• 推荐使用 ZIP 免安装版本，避免与系统已有环境变量冲突",
                "• ZIP 版本可直接解压使用，支持多版本共存",
                "• 安装版可能会修改系统环境变量，不利于多版本管理",
                "• 如已安装其他 JDK，建议先备份环境变量"
            ]),
            ("下载说明", [
                "• 选择所需的 JDK 发行版（Oracle/OpenJDK/Adoptium等）",
                "• 选择具体的 JDK 版本号",
                "• 查看版本详细信息和新特性说明",
                "• Oracle JDK 可能需要登录官网手动下载",
                "• 下载完成后会自动解压到指定目录"
            ]),
            ("安装位置", [
                "• 默认安装在程序配置的 JDK 目录下",
                "• 可以在设置中修改默认安装路径",
                "• 建议安装路径不要包含中文和特殊字符",
                "• 确保安装位置有足够的磁盘空间"
            ])
        ])
        
        self.add_help_section(content_layout, "功能使用说明", "icon/feature.png", [
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
        
        self.add_help_section(content_layout, "环境变量管理", "icon/env.png", [
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
            ])
        ])
        
        self.add_help_section(content_layout, "使用技巧", "icon/tips.png", [
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
        
        self.add_help_section(content_layout, "常见问题", "icon/warning.png", [
            ("下载问题", [
                "• 检查网络连接是否正常",
                "• 尝试切换到其他下载源",
                "• 部分版本可能需要手动下载",
                "• 确保磁盘空间充足",
                "• 下载失败可以重试或更换版本"
            ]),
            ("环境变量问题", [
                "• 需要管理员权限才能修改",
                "• 修改后新开终端才能生效",
                "• 避免与其他工具冲突",
                "• 如有异常可以使用还原功能",
                "• 建议定期备份环境变量"
            ]),
            ("使用问题", [
                "• 软链接路径不要使用中文",
                "• 安装路径避免特殊字符",
                "• 查看日志可以定位问题",
                "• 版本切换后请重启终端",
                "• 使用有问题可以查看日志"
            ])
        ])
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
    def add_help_section(self, parent_layout, title, icon_path, items):
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