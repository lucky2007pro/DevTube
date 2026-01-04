from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from projects import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- ASOSIY SAHIFALAR ---
    path('', views.home_page, name='home'),
    path('trending/', views.trending, name='trending'),
    path('syncing/', views.syncing_projects, name='syncing'),
    path('liked/', views.liked_videos, name='liked_videos'),

    # --- YANGI QO'SHILDI: SAQLANGANLAR SAHIFASI ---
    path('saved/', views.saved_projects, name='saved_projects'),

    path('my-videos/', views.my_videos, name='my_videos'),

    # --- LOYIHA AMALLARI ---
    path('create/', views.create_project, name='create_project'),
    path('watch/<int:pk>/', views.project_detail, name='project_detail'),
    path('update/<int:pk>/', views.update_project, name='update_project'),
    path('delete/<int:pk>/', views.delete_project, name='delete_project'),
    path('like/<int:pk>/', views.like_project, name='like_project'),

    # --- YANGI QO'SHILDI: SAQLASH FUNKSIYASI (AJAX) ---
    path('project/<int:pk>/save/', views.save_project, name='save_project'),

    path('buy/<int:pk>/', views.buy_project, name='buy_project'),

    # --- IT DUNYOSIGA XOS: SYNC TIZIMI ---
    path('sync/<str:username>/', views.toggle_sync, name='toggle_sync'),

    # --- TOOLS ---
    # ESKI: path('cpp/', views.cpp_test, name='cpp_test'),
    # YANGI:
    path('compiler/', views.online_compiler, name='compiler'),
    path('community-chat/', views.community_chat, name='community_chat'),
    path('cpp/', views.cpp_test, name='cpp_test'),
    # --- USER PROFILI VA AUTH ---
    # O'z profiliga kirish
    path('profile/', views.profile, name='profile'),
    # Boshqa dasturchining profilini username orqali ko'rish
    path('user/<str:username>/', views.profile, name='profile_by_username'),

    path('register/', views.register, name='register'),
    path('signup/', views.register, name='signup'),

    # Login va Logout
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Google orqali kirish (Allauth)
    path('accounts/', include('allauth.urls')),
]

# Media fayllar (Rasm/Video) ishlashi uchun:
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)