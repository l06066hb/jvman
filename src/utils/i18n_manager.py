import os
import json
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal
import sys
from .version_manager import version_manager

class I18nManager(QObject):
    """国际化管理器"""
    
    # 语言切换信号
    language_changed = pyqtSignal(str)
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            # 创建实例并初始化QObject
            cls._instance = super().__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance
    
    def __init__(self):
        # 避免重复初始化
        if not I18nManager._initialized:
            I18nManager._initialized = True
            
            # 初始化其他属性
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 获取src目录
            self.i18n_dir = os.path.join(current_dir, 'i18n')  # i18n目录在src下
            
            # 如果是打包后的环境，使用不同的路径
            if getattr(sys, 'frozen', False):
                base_dir = sys._MEIPASS
                self.i18n_dir = os.path.join(base_dir, 'i18n')
            
            # 从 version_manager 获取默认语言
            self.current_lang = version_manager.get_default_language()
            self.translations = {}
            self._text_cache = {}  # 添加文本缓存
            
            # 加载所有翻译文件
            self._load_all_translations()
            logger.debug(f"I18n manager initialized. Directory: {self.i18n_dir}")
    
    def _load_all_translations(self):
        """一次性加载所有语言文件"""
        try:
            for lang in ['en_US', 'zh_CN']:
                translations = {}
                
                # 加载翻译文件
                file_path = os.path.join(self.i18n_dir, f'{lang}.json')
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            try:
                                translations = json.loads(content)
                                logger.debug(f"Successfully loaded translations for {lang}")
                            except json.JSONDecodeError as je:
                                # 提供更详细的 JSON 解析错误信息
                                error_line = content.splitlines()[je.lineno-1]
                                logger.error(f"JSON parse error in {lang}.json at line {je.lineno}, column {je.colno}:")
                                logger.error(f"Line content: {error_line}")
                                logger.error(f"Error message: {str(je)}")
                                # 使用空字典作为该语言的翻译
                                translations = {}
                    except Exception as e:
                        logger.error(f"Failed to read translation file {file_path}: {str(e)}")
                        translations = {}
                else:
                    logger.warning(f"Translation file not found: {file_path}")
                    translations = {}
                
                # 确保至少有一个空字典作为翻译
                if not translations:
                    logger.warning(f"No translations loaded for {lang}, using empty dictionary")
                    translations = {}
                
                self.translations[lang] = translations
                
        except Exception as e:
            logger.error(f"Failed to load translations: {str(e)}")
            # 确保有基本的翻译字典
            self.translations = {'zh_CN': {}, 'en_US': {}}
    
    def _get_cached_text(self, key, lang):
        """从缓存获取翻译文本"""
        cache_key = f"{lang}:{key}"
        return self._text_cache.get(cache_key)
    
    def _set_cached_text(self, key, lang, value):
        """设置翻译文本缓存"""
        cache_key = f"{lang}:{key}"
        self._text_cache[cache_key] = value
    
    def set_language(self, lang):
        """设置当前语言"""
        if lang in self.translations:
            if lang != self.current_lang:
                self.current_lang = lang
                self._text_cache.clear()  # 切换语言时清除缓存
                self.language_changed.emit(lang)
                logger.debug(f"Language changed to: {lang}")
            return True
        logger.warning(f"Language {lang} not available")
        return False
    
    def get_text(self, key, default=None):
        """获取翻译文本"""
        try:
            # 首先检查缓存
            cached_text = self._get_cached_text(key, self.current_lang)
            if cached_text is not None:
                return cached_text
            
            # 支持使用点号访问嵌套键
            keys = key.split('.')
            value = self.translations.get(self.current_lang, {})
            
            # 遍历键路径
            for k in keys:
                if not isinstance(value, dict):
                    result = value if value else (default or key)
                    self._set_cached_text(key, self.current_lang, result)
                    return result
                value = value.get(k)
                if value is None:
                    result = default or key
                    self._set_cached_text(key, self.current_lang, result)
                    return result
            
            # 如果最终值是字典，返回键名
            if isinstance(value, dict):
                result = default or key
                self._set_cached_text(key, self.current_lang, result)
                return result
            
            # 返回翻译值或默认值
            result = value if value else (default or key)
            self._set_cached_text(key, self.current_lang, result)
            return result
            
        except Exception as e:
            logger.error(f"Failed to get translation for key {key}: {str(e)}")
            return default or key
    
    def get_available_languages(self):
        """获取可用的语言列表"""
        return list(self.translations.keys())
    
    def get_current_language(self):
        """获取当前语言"""
        return self.current_lang
    
    def format_text(self, key, **kwargs):
        """获取带格式化参数的翻译文本"""
        text = self.get_text(key)
        try:
            return text.format(**kwargs)
        except Exception as e:
            logger.error(f"Failed to format text for key {key}: {str(e)}")
            return text
    
    def switch_language(self, lang):
        """切换语言（set_language的别名）"""
        return self.set_language(lang)

# 创建全局实例
i18n_manager = I18nManager() 