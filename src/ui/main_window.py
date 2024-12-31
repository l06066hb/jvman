import os
from loguru import logger
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTabWidget, QSystemTrayIcon,
    QMenu, QMessageBox, QFileDialog, QProgressBar,
    QApplication, QCheckBox
)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QIcon, QAction, QFont, QCursor

from src.ui.tabs.download_tab import DownloadTab
from src.ui.tabs.local_tab import LocalTab
from src.ui.tabs.settings_tab import SettingsTab
from src.ui.tabs.help_tab import HelpTab
from src.ui.tabs.docs_tab import DocsTab
from src.utils.system_utils import create_symlink, set_environment_variable, update_path_variable
from src.utils.theme_manager import ThemeManager
from src.utils.platform_manager import platform_manager
from utils.version_manager import version_manager

import sys

def get_icon_path(icon_name):
    """获取图标路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的环境
        base_path = sys._MEIPASS
    else:
        # 如果是开发环境
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    icon_path = os.path.join(base_path, 'resources', 'icons', icon_name)
    if not os.path.exists(icon_path):
        logger.warning(f"Icon not found at: {icon_path}")
        return None
    return icon_path

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
        # 设置窗口标题和大小
        self.setWindowTitle(f"{version_manager.app_name} v{version_manager.version}")
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
        self.help_tab = HelpTab()
        self.docs_tab = DocsTab()
        
        tab_widget.addTab(self.download_tab, '在线下载')
        tab_widget.addTab(self.local_tab, '本地管理')
        tab_widget.addTab(self.settings_tab, '设置')
        tab_widget.addTab(self.help_tab, '使用说明')
        tab_widget.addTab(self.docs_tab, '文档')
        
        layout.addWidget(tab_widget)
        
        # 连接信号
        self.download_tab.jdk_downloaded.connect(self.on_jdk_downloaded)
        self.local_tab.jdk_mapped.connect(self.on_jdk_mapped)
        self.settings_tab.settings_changed.connect(self.on_settings_changed)

    def setup_tray(self):
        """设置系统托盘"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # 设置图标（使用绝对路径）
        icon_path = get_icon_path('app.ico')
        if icon_path:
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
                min-width: 140px;
                max-width: 160px;
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

        # 添加当前版本显示（禁用状态用于显示信息）
        version_text = self.get_formatted_version_text()
        self.current_version_action = QAction(version_text, self)
        self.current_version_action.setIcon(QIcon(get_icon_path('java-version.png')))
        self.current_version_action.setEnabled(False)
        tray_menu.addAction(self.current_version_action)
        
        # 添加分隔符
        tray_menu.addSeparator()
        
        # 添加JDK切换子菜单
        self.jdk_menu = QMenu('切换版本')
        self.jdk_menu.setIcon(QIcon(get_icon_path('java.png')))
        self.jdk_menu.setStyleSheet(tray_menu.styleSheet())
        self.update_jdk_menu()
        tray_menu.addMenu(self.jdk_menu)
        
        # 添加分隔符
        tray_menu.addSeparator()
        
        # 添加显示/隐藏动作
        show_action = QAction('显示窗口', self)
        show_action.setIcon(QIcon(get_icon_path('window.png')))
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        # 添加分隔符
        tray_menu.addSeparator()
        
        # 添加退出动作（在最后）
        quit_action = QAction('退出程序', self)
        quit_action.setIcon(QIcon(get_icon_path('exit.png')))
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        # 设置托盘菜单
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # 连接托盘图标的点击事件
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # 更新当前版本显示
        self.update_current_version_display()

    def get_formatted_version_text(self):
        """获取格式化的版本文本"""
        current_version = self.get_current_version()
        return f"当前 JDK: {current_version}" if current_version else "未设置 JDK 版本"

    def update_current_version_display(self):
        """更新当前版本显示"""
        version_text = self.get_formatted_version_text()
        self.current_version_action.setText(version_text)
        self.tray_icon.setToolTip(f"{version_manager.app_name} v{version_manager.version}\n{version_text}")

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
                action.setIcon(QIcon(get_icon_path('java-version.png')))
                action.setCheckable(True)
                action.setChecked(True)
            else:
                action.setIcon(QIcon(get_icon_path('type_java.png')))
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
            
            # 检查权限
            if not platform_manager.check_admin_rights():
                error_msg = platform_manager.get_error_message('admin_rights')
                QMessageBox.warning(self, '权限不足', error_msg)
                return
            
            # 创建软链接
            if create_symlink(jdk['path'], junction_path):
                # 更新托盘菜单
                self.update_jdk_menu()
                # 更新本地标签页显示
                self.local_tab.refresh_jdk_list()
                self.local_tab.update_current_version()
                # 更新当前版本显示
                self.update_current_version_display()
                
                # 根据平台显示不同的成功消息
                if not platform_manager.is_windows:
                    reload_cmd = platform_manager.get_shell_reload_command()
                    self.tray_icon.showMessage(
                        'JDK切换成功',
                        f"已切换到 JDK {jdk['version']}\n请运行命令使环境变量生效：{reload_cmd}",
                        QSystemTrayIcon.MessageIcon.Information,
                        3000
                    )
                else:
                    self.tray_icon.showMessage(
                        'JDK切换成功',
                        f"已切换到 JDK {jdk['version']}",
                        QSystemTrayIcon.MessageIcon.Information,
                        2000
                    )
            else:
                error_msg = platform_manager.get_error_message('symlink_failed')
                self.tray_icon.showMessage(
                    '切换失败',
                    error_msg,
                    QSystemTrayIcon.MessageIcon.Warning,
                    3000
                )

    def on_tray_activated(self, reason):
        """处理托盘图标激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            # 获取鼠标当前位置
            cursor_pos = QCursor.pos()
            # 将菜单显示在鼠标位置上方20像素处
            menu = self.tray_icon.contextMenu()
            menu.popup(QPoint(cursor_pos.x(), cursor_pos.y() - menu.sizeHint().height() - 20))

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
        """设置变更处理"""
        try:
            # 更新主题
            ThemeManager.apply_theme(self.config.get('theme', 'light'))
            
            # 更新托盘图标提示
            if hasattr(self, 'tray_icon'):
                current_version = self.get_current_version()
                tooltip = f"{version_manager.app_name} v{version_manager.version}\n"
                tooltip += f"当前 JDK: {current_version}" if current_version else "未设置 JDK 版本"
                self.tray_icon.setToolTip(tooltip)
                
            # 更新当前版本显示
            if hasattr(self, 'current_version_action'):
                version_text = self.get_formatted_version_text()
                self.current_version_action.setText(version_text)
                
        except Exception as e:
            logger.error(f"更新设置失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"更新设置失败: {str(e)}")

    def get_current_version(self):
        """获取当前JDK版本"""
        try:
            junction_path = self.config.get('junction_path')
            if os.path.exists(junction_path):
                current_path = os.path.realpath(junction_path)
                for jdk in self.config.get_all_jdks():
                    if os.path.samefile(jdk['path'], current_path):
                        return jdk['version']
        except Exception as e:
            logger.error(f"获取当前版本失败: {str(e)}")
        return None

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        if self.tray_icon.isVisible():
            # 获取关闭行为配置
            close_action = self.config.get('close_action', None)
            
            if close_action is None:
                # 创建消息框
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle('关闭选项')
                msg_box.setText('您希望如何处理程序？')
                msg_box.setIcon(QMessageBox.Icon.Question)
                
                # 添加按钮
                minimize_btn = msg_box.addButton('最小化到托盘', QMessageBox.ButtonRole.AcceptRole)
                exit_btn = msg_box.addButton('退出程序', QMessageBox.ButtonRole.RejectRole)
                msg_box.setDefaultButton(minimize_btn)
                
                # 添加"不再提示"复选框
                checkbox = QCheckBox("记住我的选择，不再提示", msg_box)
                msg_box.setCheckBox(checkbox)
                
                # 显示对话框
                msg_box.exec()
                
                # 处理用户选择
                clicked_button = msg_box.clickedButton()
                remember_choice = checkbox.isChecked()
                
                if clicked_button == minimize_btn:
                    if remember_choice:
                        self.config.set('close_action', 'minimize')
                        self.config.save()
                    self.hide()
                    event.ignore()
                else:  # exit_btn
                    if remember_choice:
                        self.config.set('close_action', 'exit')
                        self.config.save()
                    self.quit_application()
            else:
                # 使用保存的选择
                if close_action == 'minimize':
                    self.hide()
                    event.ignore()
                else:  # 'exit'
                    self.quit_application()
        else:
            self.quit_application()

    def quit_application(self):
        """完全退出应用程序"""
        # 保存配置
        self.config.save()
        # 移除托盘图标
        self.tray_icon.setVisible(False)
        # 退出应用
        QApplication.quit() 