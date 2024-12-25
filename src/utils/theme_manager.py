from PyQt6.QtWidgets import QApplication

class ThemeManager:
    """主题管理器"""
    
    @staticmethod
    def apply_theme(theme):
        """应用主题"""
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
        """
        
        if theme == 'light':
            QApplication.instance().setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #FFFFFF;
                    color: #2C3E50;
                }
                
                /* 当前版本容器样式 */
                QWidget#version_container {
                    background-color: #EBF3FE;
                    border: 1px solid #90CAF9;
                    border-radius: 16px;
                    padding: 4px;
                }
                QLabel#current_version_label {
                    color: #1976D2;
                    font-weight: bold;
                    font-size: 13px;
                }
                
                /* JDK列表样式 */
                QListWidget {
                    border: 1px solid #E0E0E0;
                    background-color: #FFFFFF;
                }
                QListWidget::item:selected {
                    background-color: #F5F9FF;
                    border: 1px solid #90CAF9;
                }
                QListWidget::item:hover:!selected {
                    background-color: #F8F9FA;
                    border: 1px solid #E0E0E0;
                }
                
                /* 标签样式 */
                QLabel[version="true"] {
                    color: #2C3E50;
                }
                QLabel[current="true"] {
                    color: #1976D2;
                }
                QLabel[title="true"] {
                    color: #2C3E50;
                }
                
                /* 按钮样式 */
                QPushButton {
                    background-color: #F8F9FA;
                    color: #2C3E50;
                    border: 1px solid #DEE2E6;
                }
                QPushButton:hover {
                    background-color: #E9ECEF;
                }
                QPushButton:pressed {
                    background-color: #DEE2E6;
                }
                
                /* 透明按钮样式 */
                QPushButton[transparent="true"]:hover {
                    background-color: rgba(0, 0, 0, 0.05);
                }
                QPushButton[transparent="true"]:pressed {
                    background-color: rgba(0, 0, 0, 0.1);
                }
            """)
        elif theme == 'dark':
            QApplication.instance().setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #2D2D2D;
                    color: #E0E0E0;
                }
                
                /* 当前版本容器样式 */
                QWidget#version_container {
                    background-color: #1A237E;
                    border: 1px solid #283593;
                    border-radius: 16px;
                    padding: 4px;
                }
                QLabel#current_version_label {
                    color: #90CAF9;
                    font-weight: bold;
                    font-size: 13px;
                }
                
                /* JDK列表样式 */
                QListWidget {
                    border: 1px solid #404040;
                    background-color: #2D2D2D;
                }
                QListWidget::item:selected {
                    background-color: #3D3D3D;
                    border: 1px solid #505050;
                }
                QListWidget::item:hover:!selected {
                    background-color: #353535;
                    border: 1px solid #404040;
                }
                
                /* 标签样式 */
                QLabel[version="true"] {
                    color: #E0E0E0;
                }
                QLabel[current="true"] {
                    color: #90CAF9;
                }
                QLabel[title="true"] {
                    color: #E0E0E0;
                }
                
                /* 按钮样式 */
                QPushButton {
                    background-color: #404040;
                    color: #E0E0E0;
                    border: 1px solid #505050;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
                QPushButton:pressed {
                    background-color: #606060;
                }
                
                /* 透明按钮样式 */
                QPushButton[transparent="true"]:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
                QPushButton[transparent="true"]:pressed {
                    background-color: rgba(255, 255, 255, 0.2);
                }
            """)
        else:  # cyan theme
            QApplication.instance().setStyleSheet(base_styles + """
                QMainWindow, QWidget {
                    background-color: #F5F9FA;
                    color: #2C3E50;
                }
                
                /* 当前版本容器样式 */
                QWidget#version_container {
                    background-color: #E3F2FD;
                    border: 1px solid #48A1B6;
                    border-radius: 16px;
                    padding: 4px;
                }
                QLabel#current_version_label {
                    color: #48A1B6;
                    font-weight: bold;
                    font-size: 13px;
                }
                
                /* JDK列表样式 */
                QListWidget {
                    border: 1px solid #B8D4D9;
                    background-color: #FFFFFF;
                }
                QListWidget::item:selected {
                    background-color: #E3F2FD;
                    border: 1px solid #48A1B6;
                }
                QListWidget::item:hover:!selected {
                    background-color: #F0F7F8;
                    border: 1px solid #B8D4D9;
                }
                
                /* 标签样式 */
                QLabel[version="true"] {
                    color: #2C3E50;
                }
                QLabel[current="true"] {
                    color: #48A1B6;
                }
                QLabel[title="true"] {
                    color: #2C3E50;
                }
                
                /* 按钮样式 */
                QPushButton {
                    background-color: #F5F9FA;
                    color: #2C3E50;
                    border: 1px solid #B8D4D9;
                }
                QPushButton:hover {
                    background-color: #E3EEF0;
                }
                QPushButton:pressed {
                    background-color: #D1E5E9;
                }
                
                /* 透明按钮样式 */
                QPushButton[transparent="true"]:hover {
                    background-color: rgba(72, 161, 182, 0.1);
                }
                QPushButton[transparent="true"]:pressed {
                    background-color: rgba(72, 161, 182, 0.2);
                }
            """) 