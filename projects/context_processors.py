from .seo import build_seo


def seo_defaults(request):
    return {'seo': build_seo(request)}

