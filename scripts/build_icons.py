"""Build static/icons/sprite.svg from the lucide icon set (ISC license).

The old Next.js site used lucide-react, so we reuse the same icons to keep the
theme. Run once whenever ICONS changes:

    python scripts/build_icons.py /path/to/node_modules/lucide-react

The output is a single self-hosted SVG sprite (no CDN). Templates use it via
{% icon "name" %} from apps.core.templatetags.ui.
"""
import json
import re
import sys
from pathlib import Path

ICONS = [
    # navigation / layout
    'menu', 'x', 'chevron-left', 'chevron-right', 'chevron-down', 'arrow-right', 'arrow-left',
    'external-link', 'log-out', 'log-in', 'user', 'user-plus', 'users', 'user-check', 'settings',
    'layout-dashboard', 'calendar', 'calendar-check', 'list-todo', 'hourglass', 'truck', 'activity',
    'circle-check', 'circle-x', 'circle-alert', 'award', 'qr-code', 'credit-card', 'file-text',
    'chart-column', 'badge-dollar-sign', 'tag', 'bell', 'shield-check', 'loader-circle', 'info',
    'triangle-alert', 'mail', 'phone', 'map-pin', 'search', 'plus', 'pencil', 'trash-2', 'eye',
    'download', 'upload', 'camera', 'image', 'printer', 'refresh-cw', 'check', 'clock', 'wallet',
    'receipt', 'store', 'package', 'scan-line', 'microscope', 'clipboard-check', 'badge-check',
    'zap', 'globe', 'lock', 'copy', 'send', 'building-2', 'handshake', 'house',
    'message-circle', 'funnel', 'ban', 'rotate-ccw', 'banknote', 'percent',
    'cookie', 'star', 'chevron-up', 'circle-check-big', 'shield', 'chart-line', 'monitor',
    'database', 'image-off', 'link-2', 'zoom-in', 'zoom-out', 'rotate-cw',
]


def parse_icon_node(source: str):
    """Extract the __iconNode array literal from a lucide .mjs module."""
    match = re.search(r'const __iconNode = (\[.*?\]);\s*const', source, re.S)
    if not match:
        raise ValueError('icon node not found')
    literal = match.group(1)
    # Convert the JS literal into JSON: quote bare keys, drop trailing commas.
    literal = re.sub(r'(\{|,)\s*([a-zA-Z_][\w-]*)\s*:', r'\1"\2":', literal)
    literal = re.sub(r',\s*([\]}])', r'\1', literal)
    return json.loads(literal)


def to_svg_children(nodes):
    parts = []
    for tag, attrs in nodes:
        attr_text = ' '.join(f'{k}="{v}"' for k, v in attrs.items() if k != 'key')
        parts.append(f'<{tag} {attr_text}/>')
    return ''.join(parts)


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: build_icons.py <node_modules/lucide-react>')
    icon_dir = Path(sys.argv[1]) / 'dist' / 'esm' / 'icons'
    out = Path(__file__).resolve().parent.parent / 'static' / 'icons' / 'sprite.svg'
    symbols = []
    for name in ICONS:
        path = icon_dir / f'{name}.mjs'
        if not path.exists():
            print(f'skip (not found): {name}')
            continue
        try:
            nodes = parse_icon_node(path.read_text())
        except ValueError as exc:
            print(f'skip ({exc}): {name}')
            continue
        symbols.append(f'<symbol id="{name}" viewBox="0 0 24 24">{to_svg_children(nodes)}</symbol>')
    import importlib.util
    spec = importlib.util.spec_from_file_location('custom_icons', Path(__file__).with_name('custom_icons.py'))
    custom = importlib.util.module_from_spec(spec); spec.loader.exec_module(custom)
    for name, inner in custom.CUSTOM_ICONS.items():
        symbols.append(f'<symbol id="{name}" viewBox="0 0 24 24">{inner}</symbol>')
    out.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">'
        '<!-- Icons from Lucide (https://lucide.dev, ISC) and Heroicons v1 (https://heroicons.com, MIT) -->'
        + ''.join(symbols) + '</svg>\n'
    )
    print(f'wrote {len(symbols)} icons to {out}')


if __name__ == '__main__':
    main()
