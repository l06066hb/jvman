import os
from loguru import logger
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTabWidget, QSystemTrayIcon,
    QMenu, QMessageBox, QFileDialog, QProgressBar,
    QApplication, QCheckBox
)
from PyQt6.QtCore import Qt, QSize, QPoint, QTimer
from PyQt6.QtGui import QIcon, QAction, QFont, QCursor

from ui.tabs.download_tab import DownloadTab
from ui.tabs.local_tab import LocalTab
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.help_tab import HelpTab
from ui.tabs.docs_tab import DocsTab
from utils.system_utils import create_symlink, set_environment_variable, update_path_variable
from utils.theme_manager import ThemeManager
from utils.platform_manager import platform_manager
from utils.version_manager import version_manager
from utils.config_manager import ConfigManager
from utils.update_manager import UpdateManager
from utils.i18n_manager import i18n_manager
from ui.dialogs.update_dialog import UpdateNotificationDialog

import sys

def get_icon_path(icon_name):
    """获取图标路径"""
    try:
        if getattr(sys, 'frozen', False):
            # 如果是打包后的环境，图标在根目录的resources/icons下
            base_path = os.path.dirname(sys._MEIPASS)
        else:
            # 如果是开发环境
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 尝试在根目录的resources/icons下查找
        icon_path = os.path.join(base_path, 'resources', 'icons', icon_name)
        if os.path.exists(icon_path):
            return icon_path
            
        # 如果找不到，尝试在开发环境的目录结构中查找
        if not getattr(sys, 'frozen', False):
            icon_path = os.path.join(base_path, 'resources', 'icons', icon_name)
            if os.path.exists(icon_path):
                return icon_path
        
        logger.warning(f"Icon not found at: {icon_path}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to get icon path: {str(e)}")
        return None

# 初始化翻译函数
_ = i18n_manager.get_text

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self, config):
        """初始化主窗口"""
        super().__init__()
        
        # 保存配置对象
        self.config = config
        
        # 初始化更新管理器
        self.update_manager = UpdateManager()
        self.update_manager.update_available.connect(self.show_update_notification)
        self.update_manager.check_update_complete.connect(self.show_check_result)
        
        # 设置窗口标题和大小
        self.setWindowTitle(f"JDK Version Manager v{version_manager.get_version()}")
        self.setMinimumSize(800, 600)
        
        # 初始化UI
        self.setup_ui()
        
        # 设置托盘图标
        self.setup_tray()
        
        # 连接语言变更信号
        i18n_manager.language_changed.connect(self.on_language_changed)
        
        # 延迟检查更新
        QTimer.singleShot(1000, self.delayed_update_check)
        
    def setup_ui(self):
        """初始化界面"""
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.download_tab = DownloadTab(self.config)
        self.local_tab = LocalTab(self.config)
        self.settings_tab = SettingsTab(self.config, self)  # 传入配置对象和父组件
        self.help_tab = HelpTab()
        self.docs_tab = DocsTab()
        
        self.tab_widget.addTab(self.local_tab, _("tabs.local"))
        self.tab_widget.addTab(self.download_tab, _("tabs.download"))
        self.tab_widget.addTab(self.help_tab, _("tabs.help"))
        self.tab_widget.addTab(self.docs_tab, _("tabs.docs"))
        self.tab_widget.addTab(self.settings_tab, _("tabs.settings"))
        
        layout.addWidget(self.tab_widget)
        
        # 设置标签页样式
        self.tab_widget.setStyleSheet("""
            QTabWidget {
                background: transparent;
            }
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                padding: 8px 20px;
                margin: 0;
                border: none;
                background: transparent;
                color: #666666;
                font-size: 13px;
                font-weight: normal;
            }
            QTabBar::tab:hover {
                color: #1a73e8;
                background-color: rgba(26, 115, 232, 0.08);
                border-radius: 6px;
            }
            QTabBar::tab:selected {
                color: #1a73e8;
                font-weight: bold;
                background-color: rgba(26, 115, 232, 0.12);
                border-radius: 6px;
            }
            QTabBar::tab:disabled {
                color: #999999;
                background: transparent;
            }
        """)
        
        # 连接信号
        self.download_tab.jdk_downloaded.connect(self.on_jdk_downloaded)
        self.local_tab.jdk_mapped.connect(self.on_jdk_mapped)
        self.settings_tab.settings_changed.connect(self.on_settings_changed)
        # 连接本地标签页的版本变更信号
        self.local_tab.version_changed.connect(self.on_local_tab_changed)

    def change_theme(self, theme):
        """切换主题"""
        ThemeManager.apply_theme(theme)
        # 保存主题设置到配置文件
        self.config.set('theme', theme)
        self.config.save()

    def quit_application(self):
        """完全退出应用程序"""
        # 保存配置
        self.config.save()
        # 移除托盘图标
        self.tray_icon.setVisible(False)
        # 退出应用
        QApplication.quit()
            
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
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 4px 2px;
            }
            QMenu::item {
                padding: 6px 8px 6px 6px;
                border-radius: 4px;
                margin: 2px 4px;
                font-size: 9pt;
            }
            QMenu::item:selected {
                background-color: #F0F0F0;
                color: #1a73e8;
            }
            QMenu::separator {
                height: 1px;
                background: #E0E0E0;
                margin: 4px 8px;
            }
            QMenu::item:disabled {
                color: #999999;
                background-color: transparent;
            }
            QMenu::indicator {
                width: 16px;
                height: 16px;
                left: 6px;
            }
            QMenu::icon {
                padding-right: 6px;
            }
            QMenu::item:checked {
                background-color: #E8F0FE;
                color: #1a73e8;
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
        self.jdk_menu = QMenu(_("tray.switch_version"))
        self.jdk_menu.setIcon(QIcon(get_icon_path('java.png')))
        self.jdk_menu.setStyleSheet(tray_menu.styleSheet())
        self.update_jdk_menu()
        tray_menu.addMenu(self.jdk_menu)
        
        # 添加分隔符
        tray_menu.addSeparator()
        
        # 添加显示/隐藏动作
        show_action = QAction(_("tray.show_window"), self)
        show_action.setIcon(QIcon(get_icon_path('window.png')))
        show_action.triggered.connect(self.toggle_window)
        tray_menu.addAction(show_action)
        
        # 添加分隔符
        tray_menu.addSeparator()
        
        # 添加退出动作
        quit_action = QAction(_("tray.exit"), self)
        quit_action.setIcon(QIcon(get_icon_path('exit.png')))
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        # 连接语言变化信号，更新托盘菜单文本
        i18n_manager.language_changed.connect(lambda lang: self._update_tray_menu_text(show_action, quit_action))
        
        # 设置托盘菜单
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # 连接托盘图标的点击事件
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # 更新当前版本显示
        self.update_current_version_display()
        
    def get_detailed_version(self, java_path):
        """获取详细的JDK版本信息"""
        try:
            import subprocess
            result = subprocess.run([java_path, '-version'], 
                                  capture_output=True,
                                  encoding='utf-8')
            if result.returncode == 0:
                output = result.stderr
                import re
                
                # 提取版本信息和发行商信息
                version_info = {}
                
                # 匹配发行商和版本信息
                vendor_patterns = {
                    r'openjdk': 'OpenJDK',
                    r'java\s+version': 'Oracle',  # Oracle JDK
                    r'microsoft': 'Microsoft',
                    r'temurin': 'Eclipse Temurin',
                    r'corretto': 'Amazon Corretto',
                    r'zulu': 'Azul Zulu'
                }
                
                # 获取发行商
                output_lower = output.lower()
                vendor = _("version.vendor.unknown")
                for pattern, vendor_name in vendor_patterns.items():
                    if re.search(pattern, output_lower):
                        vendor = vendor_name
                        break
                
                # 获取版本号
                version_match = re.search(r'version "([^"]+)"', output)
                if version_match:
                    version = version_match.group(1)
                else:
                    version_match = re.search(r'version ([^"\s]+)', output)
                    if version_match:
                        version = version_match.group(1)
                    else:
                        version = None
                
                # 获取架构信息
                arch_match = re.search(r'(64-Bit|32-Bit)', output, re.IGNORECASE)
                arch = arch_match.group(1) if arch_match else None
                
                return {
                    'version': version,
                    'vendor': vendor,
                    'arch': arch
                }
            return None
        except Exception as e:
            logger.error(f"获取JDK版本信息失败: {str(e)}")
            return None
            
    def get_formatted_version_text(self):
        """获取格式化的版本文本"""
        current_jdk = self.config.get_current_jdk()
        if current_jdk:
            try:
                # 获取完整的版本信息
                java_executable = platform_manager.get_java_executable()
                java_path = os.path.join(current_jdk['path'], 'bin', java_executable)
                if os.path.exists(java_path):
                    version_info = self.get_detailed_version(java_path)
                    if version_info:
                        version = version_info['version']
                        vendor = version_info['vendor']
                        arch = version_info['arch']
                    else:
                        version = current_jdk.get('version', '')
                        vendor = current_jdk.get('vendor', _("version.vendor.unknown"))
                        arch = current_jdk.get('arch', '')
                else:
                    version = current_jdk.get('version', '')
                    vendor = current_jdk.get('vendor', _("version.vendor.unknown"))
                    arch = current_jdk.get('arch', '')
                
                # 构建显示文本（完整版本）
                text = _("version.format").format(vendor=vendor, version=version)
                if arch:
                    text += f" ({arch})"
                return text
            except Exception as e:
                logger.error(_("version.format_error").format(error=str(e)))
                return _("version.format_simple").format(version=current_jdk.get('version', ''))
        return _("version.not_set")
        
    def get_current_version(self):
        """获取当前JDK版本"""
        current_jdk = self.config.get_current_jdk()
        if current_jdk:
            version = current_jdk.get('version', '')
            return f"JDK {version}"
        return None
        
    def update_current_version_display(self):
        """更新当前版本显示"""
        version_text = self.get_formatted_version_text()
        if hasattr(self, 'current_version_action'):
            self.current_version_action.setText(_("tray.current_version").format(version=version_text))
            
            # 设置详细的工具提示
            current_jdk = self.config.get_current_jdk()
            if current_jdk:
                java_executable = platform_manager.get_java_executable()
                java_path = os.path.join(current_jdk['path'], 'bin', java_executable)
                if os.path.exists(java_path):
                    version_info = self.get_detailed_version(java_path)
                    if version_info:
                        version = version_info['version']
                        vendor = version_info['vendor']
                        arch = version_info['arch']
                    else:
                        version = current_jdk.get('version', '')
                        vendor = current_jdk.get('vendor', _("version.vendor.unknown"))
                        arch = current_jdk.get('arch', '')
                else:
                    version = current_jdk.get('version', '')
                    vendor = current_jdk.get('vendor', _("version.vendor.unknown"))
                    arch = current_jdk.get('arch', '')
                
                path = current_jdk.get('path', '')
                tooltip = _("tray.tooltip.current").format(vendor=vendor, version=version)
                if arch:
                    tooltip += f" ({arch})"
                tooltip += f"\n{_('tray.tooltip.path')}: {path}"
                self.current_version_action.setToolTip(tooltip)
            
        if hasattr(self, 'tray_icon'):
            # 托盘图标的工具提示显示详细信息
            current_jdk = self.config.get_current_jdk()
            if current_jdk:
                java_executable = platform_manager.get_java_executable()
                java_path = os.path.join(current_jdk['path'], 'bin', java_executable)
                if os.path.exists(java_path):
                    version_info = self.get_detailed_version(java_path)
                    if version_info:
                        version = version_info['version']
                        vendor = version_info['vendor']
                        arch = version_info['arch']
                    else:
                        version = current_jdk.get('version', '')
                        vendor = current_jdk.get('vendor', _("version.vendor.unknown"))
                        arch = current_jdk.get('arch', '')
                else:
                    version = current_jdk.get('version', '')
                    vendor = current_jdk.get('vendor', _("version.vendor.unknown"))
                    arch = current_jdk.get('arch', '')
                
                path = current_jdk.get('path', '')
                tooltip = _("tray.tooltip.app_info").format(
                    app_name=version_manager.app_name,
                    version=version_manager.version
                )
                tooltip += _("tray.tooltip.current").format(vendor=vendor, version=version)
                if arch:
                    tooltip += f" ({arch})"
                tooltip += _("tray.tooltip.path").format(path=path)
                self.tray_icon.setToolTip(tooltip)
            else:
                self.tray_icon.setToolTip(
                    _("tray.tooltip.no_version").format(
                        app_name=version_manager.app_name,
                        version=version_manager.version
                    )
                )
        
    def update_jdk_menu(self):
        """更新JDK切换菜单"""
        if not hasattr(self, 'jdk_menu'):
            return
        
        self.jdk_menu.clear()
        jdks = self.config.get_all_jdks()
        
        # 获取当前JDK
        current_jdk = self.config.get_current_jdk()
        
        # 添加所有有效的JDK版本到菜单
        valid_jdks = []
        for jdk in jdks:
            # 检查JDK路径是否有效
            jdk_path = jdk.get('path', '')
            if not os.path.exists(jdk_path):
                continue
            
            java_executable = platform_manager.get_java_executable()
            java_path = os.path.join(jdk_path, 'bin', java_executable)
            if not os.path.exists(java_path):
                continue
            
            valid_jdks.append(jdk)
        
        # 添加有效的JDK到菜单
        for jdk in valid_jdks:
            # 获取详细版本信息
            java_executable = platform_manager.get_java_executable()
            java_path = os.path.join(jdk['path'], 'bin', java_executable)
            if os.path.exists(java_path):
                version_info = self.get_detailed_version(java_path)
                if version_info:
                    version = version_info['version']
                    vendor = version_info['vendor']
                    arch = version_info['arch']
                else:
                    version = jdk.get('version', '')
                    vendor = jdk.get('vendor', _("version.vendor.unknown"))
                    arch = jdk.get('arch', '')
            else:
                version = jdk.get('version', '')
                vendor = jdk.get('vendor', _("version.vendor.unknown"))
                arch = jdk.get('arch', '')
            
            path = jdk.get('path', '')
            
            # 构建菜单项文本
            action_text = _("version.format").format(vendor=vendor, version=version)
            if arch:
                action_text += f" ({arch})"
            
            # 构建详细的工具提示
            tooltip = _("tray.tooltip.version").format(vendor=vendor, version=version)
            if arch:
                tooltip += f" ({arch})"
            tooltip += _("tray.tooltip.path").format(path=path)
            
            action = QAction(action_text, self)
            action.setToolTip(tooltip)  # 设置工具提示
            
            # 根据是否是当前版本设置不同的图标和样式
            if current_jdk and jdk['path'] == current_jdk['path']:
                action.setIcon(QIcon(get_icon_path('java-version.png')))
                action.setCheckable(True)
                action.setChecked(True)
            else:
                action.setIcon(QIcon(get_icon_path('type_java.png')))
            action.setData(jdk)
            action.triggered.connect(self.on_tray_jdk_switch)
            self.jdk_menu.addAction(action)
        
        # 如果没有有效的JDK，添加提示信息
        if not valid_jdks:
            empty_action = QAction(_("tray.no_jdk"), self)
            empty_action.setEnabled(False)
            self.jdk_menu.addAction(empty_action)
        
        # 更新当前版本显示
        self.update_current_version_display()
        
    def on_tray_jdk_switch(self):
        """处理托盘菜单中的JDK切换"""
        action = self.sender()
        if action:
            jdk = action.data()
            junction_path = self.config.get('junction_path')
            
            # 检查权限
            if not platform_manager.check_admin_rights():
                error_msg = platform_manager.get_error_message('admin_rights')
                QMessageBox.warning(self, _("dialog.error.title"), error_msg)
                return
            
            # 创建软链接
            if create_symlink(jdk['path'], junction_path):
                # 获取基本版本信息
                version = jdk.get('version', '')
                vendor = jdk.get('vendor', _("version.vendor.unknown"))
                arch = ''

                try:
                    # 尝试获取详细版本信息
                    java_executable = platform_manager.get_java_executable()
                    java_path = os.path.join(jdk['path'], 'bin', java_executable)
                    if os.path.exists(java_path):
                        version_info = self.get_detailed_version(java_path)
                        if version_info:
                            if 'version' in version_info:
                                version = version_info['version']
                            if 'vendor' in version_info:
                                vendor = version_info['vendor']
                            if 'arch' in version_info:
                                arch = version_info['arch']
                except Exception as e:
                    logger.error(f"获取版本详细信息失败: {str(e)}")

                try:
                    # 更新界面
                    self.update_jdk_menu()
                    self.local_tab.refresh_jdk_list()
                    self.local_tab.update_current_version()
                    self.update_current_version_display()
                except Exception as e:
                    logger.error(f"更新界面失败: {str(e)}")

                try:
                    # 构建显示文本
                    try:
                        version_text = f"{vendor} JDK {version}"
                        if arch:
                            version_text += f" ({arch})"
                    except Exception as e:
                        logger.error(f"格式化版本文本失败: {str(e)}")
                        version_text = f"JDK {version}"

                    # 显示通知
                    if not platform_manager.is_windows:
                        reload_cmd = platform_manager.get_shell_reload_command()
                        self.tray_icon.showMessage(
                            _("tray.switch_success"),
                            _("tray.switch_success_unix").format(version_text=version_text, reload_cmd=reload_cmd),
                            QSystemTrayIcon.MessageIcon.Information,
                            3000
                        )
                    else:
                        self.tray_icon.showMessage(
                            _("tray.switch_success"),
                            _("tray.switch_success_windows").format(version_text=version_text),
                            QSystemTrayIcon.MessageIcon.Information,
                            2000
                        )
                except Exception as e:
                    logger.error(f"显示通知失败: {str(e)}")
                    # 如果显示通知失败，使用最简单的版本
                    self.tray_icon.showMessage(
                        _("tray.switch_success"),
                        _("tray.switch_success_windows").format(version_text=f"JDK {version}"),
                        QSystemTrayIcon.MessageIcon.Information,
                        2000
                    )

                try:
                    # 发送版本变更信号
                    self.local_tab.version_changed.emit()
                except Exception as e:
                    logger.error(f"发送版本变更信号失败: {str(e)}")
            else:
                error_msg = platform_manager.get_error_message('symlink_failed')
                self.tray_icon.showMessage(
                    _("tray.switch_failed"),
                    error_msg,
                    QSystemTrayIcon.MessageIcon.Warning,
                    3000
                )
                
    def on_tray_activated(self, reason):
        """处理托盘图标激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            # 获取鼠标当前位置
            cursor_pos = QCursor.pos()
            # 将菜单显示在鼠标位置上方20像素处
            menu = self.tray_icon.contextMenu()
            menu.popup(QPoint(cursor_pos.x(), cursor_pos.y() - menu.sizeHint().height() - 20))
            
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        if self.tray_icon.isVisible():
            # 获取关闭行为配置
            close_action = self.config.get('close_action', None)
            
            if close_action is None:
                # 创建消息框
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle(_("dialog.close.title"))
                msg_box.setText(_("dialog.close.message"))
                msg_box.setIcon(QMessageBox.Icon.Question)
                
                # 添加按钮
                minimize_btn = msg_box.addButton(_("dialog.close.minimize"), QMessageBox.ButtonRole.AcceptRole)
                exit_btn = msg_box.addButton(_("dialog.close.exit"), QMessageBox.ButtonRole.RejectRole)
                msg_box.setDefaultButton(minimize_btn)
                
                # 添加"不再提示"复选框
                checkbox = QCheckBox(_("dialog.close.remember"), msg_box)
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

    def on_jdk_downloaded(self, version, path):
        """处理JDK下载完成事件"""
        self.config.add_downloaded_jdk({
            'version': version,
            'path': path,
            'type': 'downloaded'
        })
        self.local_tab.refresh_jdk_list()
        self.update_jdk_menu()  # 更新托盘菜单
        self.update_current_version_display()  # 更新当前版本显示

    def on_jdk_mapped(self, version, path):
        """处理JDK映射事件"""
        self.config.add_mapped_jdk({
            'version': version,
            'path': path,
            'type': 'mapped'
        })
        self.local_tab.refresh_jdk_list()
        self.update_jdk_menu()  # 更新托盘菜单
        self.update_current_version_display()  # 更新当前版本显示

    def on_settings_changed(self):
        """设置变更处理"""
        try:
            # 更新主题
            ThemeManager.apply_theme(self.config.get('theme', 'light'))
            # 更新托盘显示
            self.update_current_version_display()
            # 更新托盘菜单
            self.update_jdk_menu()
        except Exception as e:
            logger.error(f"更新设置失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"更新设置失败: {str(e)}")
            
    def on_local_tab_changed(self):
        """本地标签页变更处理"""
        self.update_jdk_menu()  # 更新托盘菜单
        self.update_current_version_display()  # 更新当前版本显示

    def show_update_notification(self, update_info):
        """显示更新通知"""
        dialog = UpdateNotificationDialog(update_info, self)
        dialog.exec()
        
    def show_check_result(self, success, message):
        """显示检查结果"""
        if success and not message.startswith(_("update.new_version.found")):
            QMessageBox.information(self, _("update.check.title"), message)
        elif not success:
            QMessageBox.warning(self, _("update.check.title"), message)
            
    def manual_check_update(self):
        """手动检查更新"""
        self.update_manager.manual_check_update()
        
    def start_update(self, update_info):
        """开始更新"""
        try:
            # 获取下载URL和保存路径
            download_url = update_info['download_url']
            save_dir = self.update_manager.get_update_save_path()
            save_path = os.path.join(save_dir, f"update_v{update_info['version']}.zip")
            
            # 开始下载
            self.update_manager.download_update(download_url, save_path)
        except Exception as e:
            QMessageBox.warning(self, "更新错误", f"开始更新时发生错误：{str(e)}")
            
    def toggle_window(self):
        """切换窗口显示状态"""
        if self.isHidden():
            self.show()
            self.activateWindow()  # 激活窗口（置顶）
        else:
            self.hide() 

    def on_language_changed(self):
        """当语言改变时更新界面文本"""
        try:
            # 更新标签页文本
            self.tab_widget.setTabText(0, _("tabs.local"))
            self.tab_widget.setTabText(1, _("tabs.download"))
            self.tab_widget.setTabText(2, _("tabs.help"))
            self.tab_widget.setTabText(3, _("tabs.docs"))
            self.tab_widget.setTabText(4, _("tabs.settings"))
            
            # 更新托盘菜单
            if hasattr(self, 'jdk_menu'):
                self.jdk_menu.setTitle(_("tray.switch_version"))
            if hasattr(self, 'show_action'):
                self.show_action.setText(_("tray.show_window"))
            if hasattr(self, 'quit_action'):
                self.quit_action.setText(_("tray.exit"))
            
            # 更新托盘菜单和版本显示
            self.update_jdk_menu()
            self.update_current_version_display()
            
            # 通知各个标签页更新文本
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if hasattr(tab, '_update_texts'):
                    tab._update_texts()
                    
        except Exception as e:
            logger.error(f"更新界面文本失败: {e}") 

    def _update_tray_menu_text(self, show_action, quit_action):
        """更新托盘菜单文本"""
        show_action.setText(_("tray.show_window"))
        quit_action.setText(_("tray.exit")) 

    def delayed_update_check(self):
        """延迟检查更新"""
        if self.update_manager.should_check_updates():
            self.update_manager.check_for_updates() 