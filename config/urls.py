from django.contrib import admin
from django.urls import path, include  # Importlar birlashtirildi
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from projects import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- ASOSIY SAHIFALAR ---
    path('', views.home_page, name='home'),
    path('trending/', views.trending, name='trending'),
    path('liked/', views.liked_videos, name='liked_videos'),
    path('my-videos/', views.my_videos, name='my_videos'),

    # --- LOYIHA AMALLARI ---
    path('create/', views.create_project, name='create_project'),
    path('watch/<int:pk>/', views.project_detail, name='project_detail'),
    path('update/<int:pk>/', views.update_project, name='update_project'),
    path('delete/<int:pk>/', views.delete_project, name='delete_project'),
    path('like/<int:pk>/', views.like_project, name='like_project'),
    path('buy/<int:pk>/', views.buy_project, name='buy_project'),

    # --- TOOLS (YANGI) ---
    path('cpp/', views.cpp_test, name='cpp_test'),

    # --- USER PROFILI VA AUTH ---
    path('profile/', views.profile, name='profile'),
    path('register/', views.register, name='register'),
    path('signup/', views.register, name='signup'), # Yangi qo'shilgan qator
    # Login va Logout (O'zining standart views'lari ishlatildi)
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Google orqali kirish (Allauth)
    path('accounts/', include('allauth.urls')),
]

# Media fayllar (Rasm/Video) ishlashi uchun:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)