import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTabWidget, QSystemTrayIcon,
    QMenu, QMessageBox, QFileDialog, QProgressBar,
    QApplication
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QAction, QFont

from .tabs.download_tab import DownloadTab
from .tabs.local_tab import LocalTab
from .tabs.settings_tab import SettingsTab
from utils.system_utils import create_junction, set_environment_variable, update_path_variable
from utils.theme_manager import ThemeManager

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()
        self.setup_tray()
        # 应用主题
        ThemeManager.apply_theme(self.config.get('theme', 'light'))

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle('JDK 管理工具')
        self.setMinimumSize(800, 600)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        tab_widget = QTabWidget()
        self.download_tab = DownloadTab(self.config)
        self.local_tab = LocalTab(self.config)
        self.settings_tab = SettingsTab(self.config)
        
        tab_widget.addTab(self.download_tab, '在线下载')
        tab_widget.addTab(self.local_tab, '本地管理')
        tab_widget.addTab(self.settings_tab, '设置')
        
        layout.addWidget(tab_widget)
        
        # 连接信号
        self.download_tab.jdk_downloaded.connect(self.on_jdk_downloaded)
        self.local_tab.jdk_mapped.connect(self.on_jdk_mapped)
        self.settings_tab.settings_changed.connect(self.on_settings_changed)

    def setup_tray(self):
        """设置系统托盘"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # 设置图标（使用绝对路径）
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'icon', 'app.png')
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.tray_icon.setIcon(icon)
            self.setWindowIcon(icon)
        
        # 创建托盘菜单
        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 2px;
                min-width: 160px;
                max-width: 180px;
            }
            QMenu::item {
                padding: 4px 20px 4px 28px;
                border-radius: 3px;
                margin: 2px 3px;
                font-size: 9pt;
            }
            QMenu::item:selected {
                background-color: #F5F5F5;
                color: #000000;
            }
            QMenu::separator {
                height: 1px;
                background: #E0E0E0;
                margin: 3px 6px;
            }
            QMenu::item:disabled {
                color: #666666;
                background-color: transparent;
                padding: 4px 20px 4px 28px;
            }
            QMenu::indicator {
                width: 16px;
                height: 16px;
                margin-left: 5px;
            }
            QMenu::icon {
                margin-left: 5px;
            }
        """)

        # 添加退出动作（放在最上面）
        quit_action = QAction('退出程序', self)
        quit_action.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'icon', 'exit.png')))
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        # 添加分隔符
        tray_menu.addSeparator()
        
        # 添加当前版本显示（禁用状态用于显示信息）
        version_text = self.get_formatted_version_text()
        self.current_version_action = QAction(version_text, self)
        self.current_version_action.setEnabled(False)
        tray_menu.addAction(self.current_version_action)
        
        # 添加分隔符
        tray_menu.addSeparator()
        
        # 添加JDK切换子菜单
        self.jdk_menu = QMenu('切换版本')
        self.jdk_menu.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'icon', 'java.png')))
        self.jdk_menu.setStyleSheet(tray_menu.styleSheet())
        self.update_jdk_menu()
        tray_menu.addMenu(self.jdk_menu)
        
        # 添加分隔符
        tray_menu.addSeparator()
        
        # 添加显示/隐藏动作
        show_action = QAction('显示窗口', self)
        show_action.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'icon', 'window.png')))
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        # 设置托盘菜单
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # 连接托盘图标的点击事件
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # 更新当前版本显示
        self.update_current_version_display()

    def get_formatted_version_text(self):
        """获取格式化的版本文本"""
        junction_path = self.config.get('junction_path')
        if not os.path.exists(junction_path):
            return "未设置 JDK"
            
        java_path = os.path.join(junction_path, 'bin', 'java.exe')
        if not os.path.exists(java_path):
            return "未设置 JDK"
            
        try:
            import subprocess
            result = subprocess.run(
                [java_path, '-version'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            version_info = result.stderr.split('\n')[0].strip()
            # 简化版本信息显示
            if 'java version' in version_info.lower():
                version_info = version_info.split('"')[1]
            return f"当前: {version_info}"
        except:
            return "未知版本"

    def update_current_version_display(self):
        """更新当前版本显示"""
        version_text = self.get_formatted_version_text()
        self.current_version_action.setText(version_text)
        self.tray_icon.setToolTip(f'JDK管理工具\n{version_text}')

    def update_jdk_menu(self):
        """更新JDK切换菜单"""
        self.jdk_menu.clear()
        jdks = self.config.get_all_jdks()
        
        # 获取当前JDK版本
        current_junction = self.config.get('junction_path')
        current_version = None
        if os.path.exists(current_junction):
            for jdk in jdks:
                if os.path.samefile(jdk['path'], os.path.realpath(current_junction)):
                    current_version = jdk['version']
                    break
        
        # 添加所有JDK版本到菜单
        for jdk in jdks:
            action = QAction(f"JDK {jdk['version']}", self)
            # 根据是否是当前版本设置不同的图标
            if jdk['version'] == current_version:
                action.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'icon', 'java-version.png')))
                action.setCheckable(True)
                action.setChecked(True)
            else:
                action.setIcon(QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'icon', 'type_java.png')))
            action.setData(jdk)
            action.triggered.connect(self.on_tray_jdk_switch)
            self.jdk_menu.addAction(action)

        # 如果没有JDK，添加提示信息
        if not jdks:
            empty_action = QAction('未添加JDK', self)
            empty_action.setEnabled(False)
            self.jdk_menu.addAction(empty_action)

    def on_tray_jdk_switch(self):
        """处理托盘菜单中的JDK切换"""
        action = self.sender()
        if action:
            jdk = action.data()
            junction_path = self.config.get('junction_path')
            
            # 创建软链接
            if create_junction(jdk['path'], junction_path):
                # 更新托盘菜单
                self.update_jdk_menu()
                # 更新本地标签页显示
                self.local_tab.update_current_version()
                # 更新当前版本显示
                self.update_current_version_display()
                # 显示通知
                self.tray_icon.showMessage(
                    'JDK切换成功',
                    f"已切换到 JDK {jdk['version']}",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000  # 显示2秒
                )
            else:
                self.tray_icon.showMessage(
                    '切换失败',
                    '无法切换JDK版本',
                    QSystemTrayIcon.MessageIcon.Warning,
                    2000
                )

    def on_tray_activated(self, reason):
        """处理托盘图标激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def on_jdk_downloaded(self, version, path):
        """处理JDK下载完成事件"""
        self.config.add_downloaded_jdk({
            'version': version,
            'path': path,
            'type': 'downloaded'
        })
        self.local_tab.refresh_jdk_list()
        self.update_jdk_menu()  # 更新托盘菜单

    def on_jdk_mapped(self, version, path):
        """处理JDK映射事件"""
        self.config.add_mapped_jdk({
            'version': version,
            'path': path,
            'type': 'mapped'
        })
        self.local_tab.refresh_jdk_list()
        self.update_jdk_menu()  # 更新托盘菜单

    def on_settings_changed(self):
        """处���设置变更事件"""
        self.download_tab.update_settings()
        self.local_tab.update_settings()
        # 应用新主题
        ThemeManager.apply_theme(self.config.get('theme', 'light'))

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        if self.tray_icon.isVisible():
            QMessageBox.information(
                self, '提示',
                '程序将继续在系统托盘运行。要完全退出程序，请右键点击托盘图标并选择"退出程序"。'
            )
            self.hide()
            event.ignore()
        else:
            self.quit_application() 

    def quit_application(self):
        """完全退出应用程序"""
        # 保存配置
        self.config.save_config()
        # 移除托盘图标
        self.tray_icon.setVisible(False)
        # 退出应用
        QApplication.quit() 