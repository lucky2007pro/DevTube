from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from rest_framework.authtoken.views import obtain_auth_token

# 1. ASOSIY VIEWS IMPORTI (Shu yetarli)
from projects import views

# 2. API VIEWS IMPORTI
from projects.views import (
    ProjectListAPI, ProjectDetailAPI,
    RegisterAPI, ProjectCreateAPI, ProjectUpdateDeleteAPI, ProfileAPI
)

import notifications.urls

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- FLUTTER API 📱 ---
    path('api/auth/login/', obtain_auth_token, name='api_token_auth'),
    path('api/auth/register/', RegisterAPI.as_view(), name='api_register'),
    path('api/profile/', ProfileAPI.as_view(), name='api_profile'),

    path('api/projects/', ProjectListAPI.as_view(), name='api_project_list'),
    path('api/projects/create/', ProjectCreateAPI.as_view(), name='api_project_create'),
    path('api/projects/<int:pk>/', ProjectDetailAPI.as_view(), name='api_project_detail'),
    path('api/projects/<int:pk>/manage/', ProjectUpdateDeleteAPI.as_view(), name='api_project_manage'),

    # --- JONLI NATIJA ---
    path('live-view/<slug:slug>/', views.live_project_view, name='live_project_view'),

    # --- ASOSIY SAHIFALAR ---
    path('', views.home_page, name='home'),
    path('trending/', views.trending, name='trending'),
    path('feed/', views.syncing_projects, name='syncing'),
    path('liked/', views.liked_videos, name='liked_videos'),
    path('saved/', views.saved_projects, name='saved_projects'),
    path('my-videos/', views.my_videos, name='my_videos'),

    # --- LOYIHA AMALLARI ---
    path('create/', views.create_project, name='create_project'),
    path('watch/<slug:slug>/', views.project_detail, name='project_detail'),
    path('update/<int:pk>/', views.update_project, name='update_project'),
    path('delete/<int:pk>/', views.delete_project, name='delete_project'),

    # --- INTERAKTIV ---
    path('like/<int:pk>/', views.like_project, name='like_project'),
    path('save/<int:pk>/', views.save_project, name='save_project'),
    path('report/<int:pk>/', views.report_project, name='report_project'),
    path('sync/<str:username>/', views.toggle_sync, name='toggle_sync'),

    # --- MOLIYA ---
    path('buy/<int:pk>/', views.buy_project, name='buy_project'),
    path('wallet/deposit/', views.add_funds, name='add_funds'),
    path('wallet/withdraw/', views.withdraw_money, name='withdraw_money'),

    # --- TOOLS ---
    path('compiler/', views.online_compiler, name='compiler'),
    path('tools/cpp-test/', views.cpp_test, name='cpp_test'),
    path('chat/', views.community_chat, name='community_chat'),
    # --- TELEGRAM WEBHOOK (TUZATILDI) ---
    # views.telegram_webhook deb chaqiramiz, chunki tepadagi import shuni bildiradi
    path('telegram-webhook/', views.telegram_webhook, name='telegram_webhook'),

    # --- BOSHQA ---
    path('inbox/notifications/', include(notifications.urls, namespace='notifications')),
    path('notifications/', views.my_notifications, name='my_notifications'),
    path('profile/', views.profile, name='profile'),
    path('@<str:username>/', views.profile, name='profile_by_username'),

    # --- AUTH WEB ---
    path('accounts/', include('allauth.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('signup/', views.register, name='register'),

    path('news/', views.announcements, name='announcements'),
    path('help/', views.help_page, name='help'),
    path('contact/', views.contact_page, name='contact'),
    path('portfolio/', views.portfolio_page, name='portfolio'),
    path('fix-my-db-slugs-secret-123/', views.fix_database_slugs),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)