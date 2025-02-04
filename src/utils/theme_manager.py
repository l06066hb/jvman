from PyQt6.QtWidgets import QApplication


class ThemeManager:
    """主题管理器"""

    # 定义主题颜色常量
    THEME_COLORS = {
        "cyan": {
            "primary": "#48A1B6",  # 主色调
            "primary_light": "#E3F2FD",  # 主色调亮色
            "border": "#B8D4D9",  # 边框色
            "hover": "#E3EEF0",  # 悬停色
            "pressed": "#D1E5E9",  # 按压色
            "background": "#F5F9FA",  # 背景色
            "text": "#2C3E50",  # 文本色
            "secondary_bg": "#FFFFFF",  # 次要背景色
            "container_bg": "#F8F9FA",  # 容器背景色
            "warning": "#f0ad4e",  # 警告色
            "success": "#28a745",  # 成功色
            "error": "#dc3545",  # 错误色
        },
        "light": {
            "primary": "#1976D2",
            "primary_light": "#EBF3FE",
            "border": "#DEE2E6",
            "hover": "#E9ECEF",
            "pressed": "#DEE2E6",
            "background": "#FFFFFF",
            "text": "#2C3E50",
            "secondary_bg": "#FFFFFF",
            "container_bg": "#F8F9FA",
            "warning": "#f0ad4e",
            "success": "#28a745",
            "error": "#dc3545",
        },
        "dark": {
            "primary": "#90CAF9",
            "primary_light": "#1A237E",
            "border": "#404040",
            "hover": "#505050",
            "pressed": "#606060",
            "background": "#2D2D2D",
            "text": "#E0E0E0",
            "secondary_bg": "#353535",
            "container_bg": "#353535",
            "warning": "#f0ad4e",
            "success": "#28a745",
            "error": "#dc3545",
        },
    }

    _instance = None
    _current_theme = "cyan"

    @classmethod
    def initialize(cls, config):
        """初始化主题管理器"""
        if cls._instance is None:
            cls._instance = cls()
            # 从配置中获取主题，如果没有则使用默认的青色主题
            theme = config.get("theme", "cyan")
            cls._current_theme = theme
            cls.apply_theme(theme)
        return cls._instance

    @classmethod
    def get_current_theme(cls):
        """获取当前主题"""
        return cls._current_theme

    @classmethod
    def apply_theme(cls, theme="cyan"):
        """应用主题"""
        try:
            # 如果传入的主题不是有效值，使用青色主题
            if theme not in cls.THEME_COLORS:
                theme = "cyan"

            # 更新当前主题
            cls._current_theme = theme

            # 获取当前主题的颜色
            colors = cls.THEME_COLORS[theme]

            # 基础样式
            base_styles = """
                /* 基础列表样式 */
                QListWidget {
                    border-radius: 16px;
                    padding: 12px;
                }
                QListWidget::item {
                    border: 1px solid transparent;
                    background-color: transparent;
                    border-radius: 12px;
                    min-height: 72px;
                    margin: 6px;
                }
                
                /* 基础按钮样式 */
                QPushButton {
                    padding: 8px 20px;
                    border-radius: 10px;
                    font-weight: bold;
                    font-size: 13px;
                }
                
                /* 透明按钮基础样式 */
                QPushButton[transparent="true"] {
                    background-color: transparent;
                    border: none;
                    padding: 8px;
                    border-radius: 10px;
                    min-width: 40px;
                    min-height: 40px;
                }
                
                /* 标签基础样式 */
                QLabel[version="true"] {
                    font-weight: bold;
                    font-size: 13px;
                }
                QLabel[current="true"] {
                    font-size: 12px;
                }
                
                /* 标题标签样式 */
                QLabel[title="true"] {
                    font-weight: bold;
                    font-size: 14px;
                    padding: 5px 0;
                }
                
                /* 滚动条基础样式 */
                QScrollBar:vertical {
                    border: none;
                    width: 8px;
                    margin: 0px;
                }
                QScrollBar::handle:vertical {
                    border-radius: 4px;
                    min-height: 20px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
                
                /* 组合框基础样式 */
                QComboBox {
                    padding: 5px 10px;
                    border-radius: 6px;
                    min-width: 100px;
                }
                QComboBox::drop-down {
                    border: none;
                    padding-right: 10px;
                }
                
                /* 分组框基础样式 */
                QGroupBox {
                    font-weight: bold;
                    border-radius: 8px;
                    margin-top: 12px;
                    padding-top: 12px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                
                /* 行编辑框基础样式 */
                QLineEdit {
                    padding: 5px 10px;
                    border-radius: 6px;
                    min-height: 20px;
                }
                
                /* 滚动区域基础样式 */
                QScrollArea {
                    border: none;
                }
            """

            # 主题样式
            theme_styles = f"""
                QMainWindow, QWidget {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                }}
                
                /* 当前版本容器样式 */
                QWidget#version_container {{
                    background-color: {colors['primary_light']};
                    border: 1px solid {colors['primary']};
                    border-radius: 16px;
                    padding: 4px;
                }}
                QLabel#current_version_label {{
                    color: {colors['primary']};
                    font-weight: bold;
                    font-size: 13px;
                }}
                
                /* JDK列表样式 */
                QListWidget {{
                    border: 1px solid {colors['border']};
                    background-color: {colors['secondary_bg']};
                }}
                QListWidget::item:selected {{
                    background-color: {colors['primary_light']};
                    border: 1px solid {colors['primary']};
                }}
                QListWidget::item:hover:!selected {{
                    background-color: {colors['hover']};
                    border: 1px solid {colors['border']};
                }}
                
                /* 标签样式 */
                QLabel[version="true"] {{
                    color: {colors['text']};
                }}
                QLabel[current="true"] {{
                    color: {colors['primary']};
                }}
                QLabel[title="true"] {{
                    color: {colors['text']};
                }}
                
                /* 按钮样式 */
                QPushButton {{
                    background-color: {colors['background']};
                    color: {colors['text']};
                    border: 1px solid {colors['border']};
                }}
                QPushButton:hover {{
                    background-color: {colors['hover']};
                }}
                QPushButton:pressed {{
                    background-color: {colors['pressed']};
                }}
                QPushButton#apply_env_button {{
                    background-color: {colors['primary']};
                    color: white;
                    border: none;
                }}
                QPushButton#apply_env_button:hover {{
                    background-color: {colors['primary']};
                    opacity: 0.9;
                }}
                
                /* 透明按钮样式 */
                QPushButton[transparent="true"]:hover {{
                    background-color: {colors['hover']};
                }}
                QPushButton[transparent="true"]:pressed {{
                    background-color: {colors['pressed']};
                }}
                
                /* 滚动条样式 */
                QScrollBar:vertical {{
                    background: {colors['background']};
                }}
                QScrollBar::handle:vertical {{
                    background: {colors['border']};
                }}
                QScrollBar::handle:vertical:hover {{
                    background: {colors['primary']};
                }}
                
                /* 组合框样式 */
                QComboBox {{
                    background-color: {colors['secondary_bg']};
                    border: 1px solid {colors['border']};
                    color: {colors['text']};
                }}
                QComboBox:hover {{
                    border: 1px solid {colors['primary']};
                }}
                QComboBox QAbstractItemView {{
                    background-color: {colors['secondary_bg']};
                    border: 1px solid {colors['border']};
                    selection-background-color: {colors['primary_light']};
                    selection-color: {colors['text']};
                }}
                
                /* 分组框样式 */
                QGroupBox {{
                    border: 1px solid {colors['border']};
                }}
                
                /* 行编辑框样式 */
                QLineEdit {{
                    background-color: {colors['secondary_bg']};
                    border: 1px solid {colors['border']};
                    color: {colors['text']};
                }}
                QLineEdit:hover {{
                    border: 1px solid {colors['primary']};
                }}
                QLineEdit:focus {{
                    border: 1px solid {colors['primary']};
                }}
                
                /* 容器样式 */
                QFrame#desc_container {{
                    background-color: {colors['container_bg']};
                }}
                QFrame#current_env_frame {{
                    background-color: {colors['secondary_bg']};
                    border: 1px solid {colors['border']};
                }}
                QFrame#values_frame {{
                    background-color: {colors['secondary_bg']};
                    border: 1px solid {colors['border']};
                }}
                
                /* 复选框样式 */
                QCheckBox {{
                    color: {colors['text']};
                }}
                QCheckBox::indicator:unchecked {{
                    border: 2px solid {colors['border']};
                    background-color: {colors['secondary_bg']};
                }}
                
                /* 环境变量值样式 */
                QLabel[type="env_value"] {{
                    background-color: {colors['container_bg']};
                    border: 1px solid {colors['border']};
                    color: {colors['text']};
                }}
                
                /* 警告和错误样式 */
                QLabel[type="warning"] {{
                    color: {colors['warning']};
                    background-color: {colors['container_bg']};
                    border: 1px solid {colors['warning']};
                }}
                QLabel[type="error"] {{
                    color: {colors['error']};
                    background-color: {colors['container_bg']};
                    border: 1px solid {colors['error']};
                }}
                QLabel[type="success"] {{
                    color: {colors['success']};
                    background-color: {colors['container_bg']};
                    border: 1px solid {colors['success']};
                }}
            """

            # 获取应用实例
            app = QApplication.instance()
            if app:
                # 应用样式
                app.setStyleSheet(base_styles + theme_styles)

        except Exception as e:
            print(f"应用主题失败: {str(e)}")
