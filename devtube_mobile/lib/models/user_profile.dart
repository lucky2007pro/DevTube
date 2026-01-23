class UserProfile {
  final String username;
  final String email;
  final String avatarUrl;
  final String bio;
  final double balance;

  UserProfile({
    required this.username,
    required this.email,
    required this.avatarUrl,
    required this.bio,
    required this.balance,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    String finalAvatar = 'https://ui-avatars.com/api/?name=${json['username']}';
    if (json['avatar'] != null) {
      String img = json['avatar'].toString();
      finalAvatar = img.startsWith('http') ? img : 'https://devtube-s744.onrender.com$img';
    }

    return UserProfile(
      username: json['username'] ?? '',
      email: json['email'] ?? '',
      avatarUrl: finalAvatar,
      bio: json['bio'] ?? '',
      // Balansni string yoki number kelishiga qarab to'g'irlash
      balance: double.tryParse(json['balance'].toString()) ?? 0.0,
    );
  }
}