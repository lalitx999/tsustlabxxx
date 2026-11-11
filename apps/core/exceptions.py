class ServiceError(Exception):
    """A business rule was broken. The message is safe to show to the user (Thai)."""

    def __init__(self, message, status=400, code='invalid'):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


class NotFoundError(ServiceError):
    def __init__(self, message='ไม่พบข้อมูล'):
        super().__init__(message, status=404, code='not_found')


class ForbiddenError(ServiceError):
    def __init__(self, message='ไม่มีสิทธิ์ทำรายการนี้'):
        super().__init__(message, status=403, code='forbidden')
