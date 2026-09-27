"""Safe, deliberately small Markdown renderer for chat messages."""

import html
import re

try:
    import bleach
    import markdown
except ImportError:  # safe fallback for minimal installations
    bleach = markdown = None


ALLOWED_TAGS = ["p", "br", "strong", "em", "code", "pre", "blockquote", "ul", "ol", "li", "a"]


def render_markdown(value):
    value = str(value or "")
    if bleach is None or markdown is None:
        return html.escape(value).replace("\n", "<br>")
    rendered = markdown.markdown(value, extensions=["fenced_code", "sane_lists"], output_format="html")
    rendered = bleach.clean(rendered, tags=ALLOWED_TAGS, attributes={"a": ["href", "title"]}, protocols=["http", "https"], strip=True)
    return re.sub(r"<a ([^>]*href=)", r'<a rel="nofollow noopener noreferrer" target="_blank" \1', rendered)
