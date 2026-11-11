"""Lightweight TH/EN switch for the public website (the old site had the same toggle).

Strings live in apps/website/content.py. The chosen language is kept in the
`lang` cookie; LanguageMiddleware puts it on request.lang.
"""
LANGUAGES = ('th', 'en')
DEFAULT_LANG = 'en'
COOKIE_NAME = 'lang'


def resolve_lang(request) -> str:
    value = request.COOKIES.get(COOKIE_NAME, DEFAULT_LANG)
    return value if value in LANGUAGES else DEFAULT_LANG
