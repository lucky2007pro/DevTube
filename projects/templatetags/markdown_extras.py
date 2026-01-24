from django import template
from django.template.defaultfilters import stringfilter
import markdown as md

register = template.Library()

@register.filter()
@stringfilter
def markdown(value):
    """
    Matnni Markdowndan HTMLga o'tkazadi.
    Fenced code blocks va jadvallarni ham qo'llab-quvvatlaydi.
    """
    return md.markdown(value, extensions=['markdown.extensions.fenced_code', 'markdown.extensions.tables'])