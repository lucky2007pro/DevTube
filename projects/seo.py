from django.templatetags.static import static


DEFAULT_SEO = {
    'title': 'DevTube | Premium Code Platform',
    'description': "DevTube - dasturlash loyihalarini topish, sotish va xavfsiz tekshirish platformasi.",
    'robots': 'index, follow',
}

ROUTE_SEO = {
    'home': {
        'title': 'DevTube | Dasturlash loyihalari bozori',
        'description': "Eng yaxshi dasturlash loyihalarini qidiring, ko'ring va sotib oling.",
    },
    'global_search': {
        'title': 'Qidiruv natijalari | DevTube',
        'description': "DevTube bo'yicha global qidiruv natijalari.",
    },
    'trending': {
        'title': 'Trend loyihalar | DevTube',
        'description': 'Eng ko`p ko`rilgan va mashhur loyihalar ro`yxati.',
    },
    'announcements': {
        'title': 'Yangiliklar va e`lonlar | DevTube',
        'description': "Platformadagi so'nggi yangiliklar va e'lonlar.",
    },
    'help': {
        'title': 'Yordam markazi | DevTube',
        'description': 'Platformadan foydalanish bo`yicha qo`llanma va savol-javoblar.',
    },
    'contact': {
        'title': 'Bog`lanish | DevTube',
        'description': 'Savol va takliflaringiz uchun aloqa sahifasi.',
    },
    'community_chat': {
        'title': 'Community chat | DevTube',
        'description': 'Dasturchilar hamjamiyati bilan real vaqt chat.',
        'robots': 'noindex, nofollow',
    },
    'inbox': {
        'title': 'Xabarlar | DevTube',
        'description': 'Shaxsiy xabarlaringiz sahifasi.',
        'robots': 'noindex, nofollow',
    },
    'direct_chat': {
        'title': 'To`g`ridan-to`g`ri chat | DevTube',
        'description': 'Foydalanuvchi bilan shaxsiy chat.',
        'robots': 'noindex, nofollow',
    },
    'my_notifications': {
        'title': 'Bildirishnomalar | DevTube',
        'description': 'Shaxsiy bildirishnomalar sahifasi.',
        'robots': 'noindex, nofollow',
    },
    'profile': {
        'title': 'Profil | DevTube',
        'description': 'Foydalanuvchi profili va faoliyati.',
    },
    'public_profile': {
        'title': 'Muallif profili | DevTube',
        'description': 'Muallifning ommaviy profili va loyihalari.',
    },
    'create_project': {
        'title': 'Yangi loyiha yuklash | DevTube',
        'description': 'Yangi dasturlash loyihasini platformaga joylang.',
        'robots': 'noindex, nofollow',
    },
    'update_project': {
        'title': 'Loyihani tahrirlash | DevTube',
        'description': 'Mavjud loyihani yangilash sahifasi.',
        'robots': 'noindex, nofollow',
    },
    'delete_project': {
        'title': 'Loyihani o`chirish | DevTube',
        'description': 'Loyiha o`chirish tasdiqlash sahifasi.',
        'robots': 'noindex, nofollow',
    },
}


def build_seo(request):
    url_name = ''
    if getattr(request, 'resolver_match', None):
        url_name = request.resolver_match.url_name or ''

    seo = {**DEFAULT_SEO, **ROUTE_SEO.get(url_name, {})}

    absolute_uri = request.build_absolute_uri()
    seo['canonical_url'] = absolute_uri
    seo['og_url'] = absolute_uri
    seo['og_title'] = seo['title']
    seo['og_description'] = seo['description']
    seo['og_image'] = request.build_absolute_uri(static('img/devtube-banner.png'))
    seo['twitter_url'] = absolute_uri
    seo['twitter_title'] = seo['title']
    seo['twitter_description'] = seo['description']
    seo['twitter_image'] = seo['og_image']
    seo['keywords'] = 'devtube, dasturlash, loyiha, code marketplace, python, web, ai'

    return seo

