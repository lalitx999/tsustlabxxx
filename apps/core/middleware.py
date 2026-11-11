from .i18n import resolve_lang


class LanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.lang = resolve_lang(request)
        return self.get_response(request)
