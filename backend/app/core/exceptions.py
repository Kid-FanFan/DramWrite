"""
自定义异常模块
"""


class ScriptMasterException(Exception):
    """应用基础异常"""

    def __init__(self, message: str = "系统错误", code: int = 5000):
        self.message = message
        self.code = code
        super().__init__(self.message)


class RequirementError(ScriptMasterException):
    """需求相关错误"""

    def __init__(self, message: str = "需求不完整"):
        super().__init__(message, code=4001)


class ProjectError(ScriptMasterException):
    """项目相关错误"""

    def __init__(self, message: str = "项目操作失败"):
        super().__init__(message, code=4002)


class GenerationError(ScriptMasterException):
    """内容生成错误"""

    def __init__(self, message: str = "内容生成失败"):
        super().__init__(message, code=4003)


class QualityCheckError(ScriptMasterException):
    """质量检查错误"""

    def __init__(self, message: str = "质检不通过"):
        super().__init__(message, code=4004)


class ExportError(ScriptMasterException):
    """导出错误"""

    def __init__(self, message: str = "文件导出失败"):
        super().__init__(message, code=4005)


class LLMError(ScriptMasterException):
    """LLM 调用错误"""

    def __init__(self, message: str = "模型调用失败"):
        super().__init__(message, code=5001)


class ValidationError(ScriptMasterException):
    """数据验证错误"""

    def __init__(self, message: str = "数据验证失败"):
        super().__init__(message, code=4006)


class ComplianceError(ScriptMasterException):
    """内容合规错误"""

    def __init__(self, message: str = "内容不符合规范"):
        super().__init__(message, code=4007)
