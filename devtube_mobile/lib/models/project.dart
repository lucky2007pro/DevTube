class Comment {
  final String username;
  final String avatarUrl;
  final String body;
  final String timeAgo;

  Comment({
    required this.username,
    required this.avatarUrl,
    required this.body,
    required this.timeAgo,
  });

  factory Comment.fromJson(Map<String, dynamic> json) {
    return Comment(
      username: json['username'] ?? 'Foydalanuvchi',
      avatarUrl: json['avatar_url'] ?? 'https://ui-avatars.com/api/?name=${json['username']}',
      body: json['body'] ?? '',
      timeAgo: "Hozirgina",
    );
  }
}

class Project {
  final int id;
  final String title;
  final String description;
  final String imageUrl;
  final String price;
  final String authorName;
  final String authorAvatar;
  final String category;
  final int commentCount;
  final String? sourceCode;
  final int views;
  final List<Comment> comments;

  Project({
    required this.id,
    required this.title,
    required this.description,
    required this.imageUrl,
    required this.price,
    required this.authorName,
    required this.authorAvatar,
    required this.category,
    this.commentCount = 0,
    this.sourceCode,
    this.views = 0,
    this.comments = const [],
  });

  bool get isFree {
    final cleanPrice = price.replaceAll('\$', '').trim().toLowerCase();
    return cleanPrice == '0' || cleanPrice == '0.0' || cleanPrice == '0.00' || cleanPrice == 'bepul' || price.isEmpty;
  }

  factory Project.fromJson(Map<String, dynamic> json) {
    String formattedPrice;
    var rawPrice = json['price'];

    if (rawPrice == null || rawPrice.toString() == '0' || rawPrice.toString() == '0.0' || rawPrice.toString() == '0.00') {
      formattedPrice = "BEPUL";
    } else {
      String p = rawPrice.toString();
      formattedPrice = p.contains('\$') ? p : "\$$p";
    }

    String finalImageUrl = 'https://via.placeholder.com/300';
    if (json['image'] != null) {
      String img = json['image'].toString();
      finalImageUrl = img.startsWith('http') ? img : 'https://devtube-s744.onrender.com$img';
    }

    // Izohlar API da alohida field bo'lmasa, bo'sh ro'yxat qaytaramiz
    List<Comment> commentsList = [];
    if (json['comments'] != null) {
      commentsList = (json['comments'] as List).map((i) => Comment.fromJson(i)).toList();
    }

    return Project(
      id: json['id'] ?? 0,
      title: json['title'] ?? 'Nomsiz',
      description: json['description'] ?? '',
      imageUrl: finalImageUrl,
      price: formattedPrice,
      authorName: json['author_name'] ?? 'Noma\'lum',
      authorAvatar: json['author_avatar'] != null && json['author_avatar'].toString().isNotEmpty
          ? (json['author_avatar'].toString().startsWith('http')
              ? json['author_avatar']
              : 'https://devtube-s744.onrender.com${json['author_avatar']}')
          : 'https://ui-avatars.com/api/?name=User',
      category: json['category'] ?? "Barchasi",
      commentCount: json['comment_count'] ?? commentsList.length,
      // AGAR SERVER KODNI BERMASA, NULL BO'LADI
      sourceCode: json['source_code']?.toString(),
      views: json['views'] ?? 0,
      comments: commentsList,
    );
  }
}