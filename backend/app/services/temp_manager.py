import os
import shutil
import tempfile
from pathlib import Path


class TempManager:
    """任务临时文件管理"""

    def __init__(self, base_dir: str = None):
        """base_dir: 临时文件根目录，默认系统临时目录"""
        if base_dir:
            self.base_dir = base_dir
        else:
            self.base_dir = os.path.join(tempfile.gettempdir(), "subtitle_generator")
        os.makedirs(self.base_dir, exist_ok=True)

    def create_task_dir(self, task_id: str) -> str:
        """为任务创建临时目录，返回路径"""
        task_dir = os.path.join(self.base_dir, task_id)
        os.makedirs(task_dir, exist_ok=True)
        return task_dir

    def cleanup_task(self, task_id: str):
        """清理任务临时文件"""
        task_dir = os.path.join(self.base_dir, task_id)
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir, ignore_errors=True)

    def get_task_dir(self, task_id: str) -> str:
        """获取任务临时目录路径"""
        return os.path.join(self.base_dir, task_id)
