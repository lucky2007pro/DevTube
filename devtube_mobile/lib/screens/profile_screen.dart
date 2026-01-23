import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../models/user_profile.dart';
import '../services/api_service.dart';
import 'login_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late Future<UserProfile?> futureProfile;

  @override
  void initState() {
    super.initState();
    futureProfile = ApiService.fetchUserProfile();
  }

  // Balans to'ldirish uchun saytga yo'naltirish
  Future<void> _depositMoney() async {
    const url = "https://devtube-s744.onrender.com/wallet/deposit/";
    if (!await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication)) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Havolani ochib bo'lmadi")));
    }
  }

  void _logout() async {
    await ApiService.logout();
    await FirebaseAuth.instance.signOut();
    if(mounted) {
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (context) => const LoginScreen()),
        (route) => false
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Mening Profilim")),
      body: FutureBuilder<UserProfile?>(
        future: futureProfile,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: Color(0xFF6366F1)));
          }
          if (!snapshot.hasData) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text("Ma'lumot topilmadi. Tizimga kiring."),
                  TextButton(onPressed: _logout, child: const Text("Kirish"))
                ],
              ),
            );
          }

          final user = snapshot.data!;

          return SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                CircleAvatar(radius: 50, backgroundImage: NetworkImage(user.avatarUrl)),
                const SizedBox(height: 15),
                Text(user.username, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white)),
                Text(user.email, style: const TextStyle(color: Colors.white54)),

                const SizedBox(height: 30),

                // HAMYON KARTASI
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [Color(0xFF10B981), Color(0xFF059669)]),
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [const BoxShadow(color: Colors.black26, blurRadius: 10, offset: Offset(0, 5))],
                  ),
                  child: Column(
                    children: [
                      const Text("Joriy Balans", style: TextStyle(color: Colors.white70)),
                      Text("\$${user.balance.toStringAsFixed(2)}", style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: Colors.white)),
                      const SizedBox(height: 15),
                      ElevatedButton.icon(
                        onPressed: _depositMoney,
                        icon: const Icon(Icons.add_circle, color: Colors.green),
                        label: const Text("Hisobni to'ldirish", style: TextStyle(color: Colors.black)),
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.white, shape: const StadiumBorder()),
                      )
                    ],
                  ),
                ),

                const SizedBox(height: 30),

                ListTile(
                  leading: const Icon(Icons.logout, color: Colors.red),
                  title: const Text("Tizimdan chiqish", style: TextStyle(color: Colors.red)),
                  onTap: _logout,
                  tileColor: const Color(0xFF1E293B),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                )
              ],
            ),
          );
        },
      ),
    );
  }
}