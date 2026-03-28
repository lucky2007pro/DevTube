from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Sum, Count, Max
from django.contrib.auth.models import User
from .models import PrivateMessage, Project, Transaction, Withdrawal, Contact, Sync
from django.utils import timezone
from datetime import timedelta
import os

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_get_conversations(request):
    user = request.user
    # Soxta bo'lmasligi uchun, yuborgan yoki qabul qilgan xabarlarini olamiz
    messages = PrivateMessage.objects.filter(sender=user) | PrivateMessage.objects.filter(receiver=user)
    messages = messages.order_by('-created_at')
    
    users_dict = {}
    for msg in messages:
        other_user = msg.receiver if msg.sender == user else msg.sender
        if other_user.username not in users_dict:
            users_dict[other_user.username] = {
                'username': other_user.username,
                'lastMessage': msg.body,
                'lastMessageTime': msg.created_at.strftime("%H:%M %d-%b"),
                'unreadCount': 0 if msg.is_read or msg.sender==user else 1,
                'isVerified': getattr(other_user, 'profile', None) and other_user.profile.is_verified,
                'isLastMsgMine': msg.sender == user,
                'avatarUrl': other_user.profile.avatar.url if getattr(other_user, 'profile', None) and other_user.profile.avatar else "https://i.pravatar.cc/150",
            }
        else:
            if not msg.is_read and msg.receiver == user:
                users_dict[other_user.username]['unreadCount'] += 1

    return Response(list(users_dict.values()))

@api_view(['GET'])
@permission_classes([AllowAny])
def api_get_announcements(request):
    # Saytda hozircha alohida model yo'q, shuning uchun statik tarzda / mock qilib qaytaramiz (yoki DB dan oladigan qilish mumkin)
    data = [
        {
            "title": "DevTube 2.0 ishga tushdi! 🚀",
            "content": "API integratsiyasi to'liq bajarildi.",
            "date": timezone.now().strftime("%d %B, %Y"),
            "isNew": True
        }
    ]
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_get_notifications(request):
    user = request.user
    notifications = user.notifications.all().order_by('-timestamp')[:20]
    data = []
    for n in notifications:
        data.append({
            'actor': getattr(n.actor, 'username', 'Tizim'),
            'verb': n.verb,
            'timestamp': n.timestamp.strftime("%Y-%m-%d %H:%M"),
            'target': str(n.target) if n.target else '',
            'type': 'buy' if 'sotib' in n.verb else ('like' if 'like' in n.verb else 'info')
        })
    return Response(data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_admin_stats(request):
    total_users = User.objects.count()
    total_projects = Project.objects.count()
    revenue_agg = Transaction.objects.filter(status='completed').aggregate(Sum('amount'))
    total_revenue = float(revenue_agg['amount__sum'] or 0)
    
    top_spenders = list(User.objects.annotate(
        spent=Sum('buyer_transactions__amount')
    ).order_by('-spent')[:3].values('username', 'spent'))
    
    top_sellers = list(User.objects.annotate(
        sales=Count('projects__transactions')
    ).order_by('-sales')[:3].values('username', 'sales'))
    for t in top_spenders:
         if t['spent'] is not None: t['spent'] = float(t['spent'])
         
    return Response({
        'totalUsers': total_users,
        'onlineUsers': 0, # WebSockets orqali sanaladi, hozircha 0
        'totalRevenue': total_revenue,
        'totalProjects': total_projects,
        'topSpenders': top_spenders,
        'topSellers': top_sellers
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_wallet_withdraw(request):
    card_number = request.data.get('card_number')
    amount = float(request.data.get('amount', 0))
    user = request.user
    if getattr(user, 'profile', None) and user.profile.balance >= amount and amount >= 5:
        Withdrawal.objects.create(user=user, card_number=card_number, amount=amount)
        # Profile balansini tushirish logikasi (agar darhol tushsa)
        user.profile.balance -= amount
        user.profile.save()
        return Response({"success": True, "message": "So'rov yuborildi."})
    return Response({"error": "Balans yetarli emas yoki summa noto'g'ri (Min 5$)"}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_raise_dispute(request):
    transaction_id = request.data.get('transaction_id')
    # Aloqa modeli orqali nizo ochamiz
    Contact.objects.create(
        user=request.user,
        subject=f"Nizo / Shikoyat: ID #{transaction_id}",
        message="Tranzaksiya bo'yicha ilova orqali nizo ochildi."
    )
    return Response({"success": True})
