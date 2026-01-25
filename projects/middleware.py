# projects/middleware.py
from django.utils import timezone
from .models import Profile

class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # 1. Faqat LOGIN QILGANLARNI tekshiramiz
        if request.user.is_authenticated:
            # 2. Bazaga so'rov yuborib, vaqtni yangilaymiz
            # update() funksiyasi save() ga qaraganda tezroq va yengilroq ishlaydi
            Profile.objects.filter(user=request.user).update(last_activity=timezone.now())

        return response