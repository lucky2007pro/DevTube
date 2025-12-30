from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from projects import views  # Faqat bir marta import qildik
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Asosiy sahifalar
    path('', views.home_page, name='home'),
    path('create/', views.create_project, name='create_project'),
    path('profile/', views.profile, name='profile'),

    # Autentifikatsiya (Kirish/Chiqish)
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    # Logout funksiyasini biroz soddalashtirdik (settings.py ga LOGOUT_REDIRECT_URL qo'shish tavsiya etiladi)
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Loyiha amallari
    path('delete/<int:pk>/', views.delete_project, name='delete_project'),
    path('update/<int:pk>/', views.update_project, name='update_project'),
    path('watch/<int:pk>/', views.project_detail, name='project_detail'),
    path('like/<int:pk>/', views.like_project, name='like_project'),
    path('buy/<int:pk>/', views.buy_project, name='buy_project'),

    # YANGI YO'LLAR (Views faylida bu funksiyalar bo'lishi SHART)
    path('trending/', views.trending, name='trending'),
    path('liked/', views.liked_videos, name='liked_videos'),
    path('my-videos/', views.my_videos, name='my_videos'),
    path('cpp/', views.cpp_test, name='cpp_test'),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)