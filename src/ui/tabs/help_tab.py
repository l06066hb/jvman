from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel
from PyQt6.QtCore import Qt

class HelpTab(QWidget):
    """使用说明标签页"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
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
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # 创建内容标签
        content = QLabel()
        content.setWordWrap(True)
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setStyleSheet("""
            QLabel {
                font-family: "Segoe UI", "Microsoft YaHei";
                line-height: 1.6;
                padding: 20px;
            }
        """)
        
        # 使用说明内容
        help_text = """
        <style>
            .title { color: #1a73e8; font-size: 18px; font-weight: bold; margin: 20px 0 10px 0; }
            .subtitle { color: #202124; font-size: 16px; font-weight: bold; margin: 15px 0 8px 0; }
            .text { color: #3c4043; margin: 5px 0; }
            .note { color: #5f6368; font-style: italic; margin: 5px 0; }
            .step { margin: 5px 0 5px 20px; }
        </style>
        
        <div class='title'>JDK管理工具使用说明</div>
        
        <div class='subtitle'>1. 在线下载JDK</div>
        <div class='text'>在"在线下载"标签页中：</div>
        <div class='step'>• 选择JDK发行版（Oracle/OpenJDK/Adoptium等）</div>
        <div class='step'>• 选择具体的JDK版本</div>
        <div class='step'>• 查看版本���细信息和特性说明</div>
        <div class='step'>• 点击"下载"按钮开始下载</div>
        <div class='step'>• 等待下载和安装完成</div>
        <div class='note'>注：Oracle JDK可能需要登录Oracle官网手动下载</div>
        
        <div class='subtitle'>2. 本地JDK管理</div>
        <div class='text'>在"本地管理"标签页中：</div>
        <div class='step'>• 点击"添加本地JDK"选择已安装的JDK目录</div>
        <div class='step'>• 查看JDK详细信息和版本特性</div>
        <div class='step'>• 点击"切换版本"应用选中的JDK</div>
        <div class='step'>• 点击文件夹图标可快速打开JDK目录</div>
        <div class='step'>• 可以移除不需要的JDK版本</div>
        
        <div class='subtitle'>3. 环境变量配置</div>
        <div class='text'>在"设置"标签页中：</div>
        <div class='step'>• 配置JDK存储路径和软链接路径</div>
        <div class='step'>• 选择需要设置的环境变量</div>
        <div class='step'>• 点击"应用环境变量设置"生效</div>
        <div class='note'>注：建议在修改环境变量前先备份</div>
        
        <div class='subtitle'>4. 主题切换</div>
        <div class='text'>在"设置"标签页中：</div>
        <div class='step'>• 选择喜欢的主题（浅色/深色/青色）</div>
        <div class='step'>• 主题会立即生效</div>
        
        <div class='subtitle'>5. 系统托盘</div>
        <div class='text'>最小化到系统托盘后：</div>
        <div class='step'>• 可以查看当前使用的JDK版本</div>
        <div class='step'>• 快速切换到其他JDK版本</div>
        <div class='step'>• 双击图标可以打开主界面</div>
        
        <div class='subtitle'>6. 常见问题</div>
        <div class='step'>• 需要管理员权限才能修改环境变量</div>
        <div class='step'>• 软链接路径不要使用中文</div>
        <div class='step'>• 如遇问题请查看logs目录下的日志文件</div>
        <div class='step'>• 部分JDK版本可能需要手动下载安装</div>
        """
        
        content.setText(help_text)
        scroll.setWidget(content)
        layout.addWidget(scroll) 