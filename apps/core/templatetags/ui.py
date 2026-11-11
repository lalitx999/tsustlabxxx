"""Template helpers: {% icon %}, {% t %} and money formatting."""
from decimal import Decimal, InvalidOperation

from django import template
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def icon(name, css_class='', size=None, label=None):
    """Render an icon from the self-hosted lucide sprite (static/icons/sprite.svg)."""
    size_attr = format_html(' width="{0}" height="{0}"', size) if size else ''
    aria = format_html(' role="img" aria-label="{}"', label) if label else mark_safe(' aria-hidden="true"')
    return format_html(
        '<svg class="tl-icon {}"{}{}><use href="{}#{}"></use></svg>',
        css_class, size_attr, aria, static('icons/sprite.svg'), name,
    )


@register.simple_tag(takes_context=True)
def t(context, key):
    """Translate a key from the page's `copy` dict (falls back to the key)."""
    copy = context.get('copy') or {}
    return copy.get(key, key)


@register.filter
def baht(value):
    try:
        return f'{Decimal(str(value)):,.2f}'
    except (InvalidOperation, ValueError, TypeError):
        return '0.00'


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None
