// lib/screens/login_screen.dart

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../services/api_service.dart';
// MUHIM: HomeScreen boshqa faylda bo'lsa, uni import qilish shart
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool isLoading = false;

  // --- 1. NAVIGATSIYA MANTIQI (STACK TOZALASH) ---
  void _navigateToHome() {
    // Navigator.pushAndRemoveUntil orqali orqaga qaytish tugmasini yo'qotamiz
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (context) => const HomeScreen()),
      (Route<dynamic> route) => false,
    );
  }

  // --- 2. ODDIY LOGIN ---
  void _handleLogin() async {
    final username = _usernameController.text.trim();
    final password = _passwordController.text.trim();

    if (username.isEmpty || password.isEmpty) {
      _showError("Iltimos, barcha qatorlarni to'ldiring");
      return;
    }

    setState(() => isLoading = true);
    final success = await ApiService.login(username, password);

    if (mounted) setState(() => isLoading = false);

    if (success) {
      _navigateToHome();
    } else {
      _showError("Login yoki parol xato!");
    }
  }

  // --- 3. GOOGLE LOGIN ---
  Future<void> _handleGoogleLogin() async {
    setState(() => isLoading = true);
    try {
      final GoogleSignInAccount? googleUser = await GoogleSignIn().signIn();
      if (googleUser == null) {
        setState(() => isLoading = false);
        return;
      }

      final GoogleSignInAuthentication googleAuth = await googleUser.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      await FirebaseAuth.instance.signInWithCredential(credential);
      _navigateToHome();
    } catch (e) {
      _showError("Google xatosi: $e");
    } finally {
      if (mounted) setState(() => isLoading = false);
    }
  }

  // --- 4. GITHUB LOGIN ---
  Future<void> _handleGithubLogin() async {
    setState(() => isLoading = true);
    try {
      GithubAuthProvider githubProvider = GithubAuthProvider();
      await FirebaseAuth.instance.signInWithProvider(githubProvider);
      _navigateToHome();
    } catch (e) {
      _showError("GitHub xatosi: $e");
    } finally {
      if (mounted) setState(() => isLoading = false);
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.redAccent),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF020617), // base.html dagi qorong'u fon
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 30),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildLogo(),
              const SizedBox(height: 24),
              Text(
                "DevTube Premium",
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 40),
              _buildInput(_usernameController, "Login", Icons.person_outline),
              const SizedBox(height: 16),
              _buildInput(_passwordController, "Parol", Icons.lock_outline, isPassword: true),
              const SizedBox(height: 24),
              _buildLoginButton(),
              _buildDivider(),
              _buildSocialRow(),
            ],
          ),
        ),
      ),
    );
  }

  // --- QOSHIMCHA WIDGETLAR (KODNI QISQARTIRISH UCHUN) ---

  Widget _buildLogo() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: const Color(0xFF6366F1).withOpacity(0.1),
      ),
      child: const Icon(Icons.play_circle_fill, size: 80, color: Color(0xFF6366F1)),
    );
  }

  Widget _buildLoginButton() {
    return ElevatedButton(
      onPressed: isLoading ? null : _handleLogin,
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFF6366F1),
        padding: const EdgeInsets.symmetric(vertical: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        elevation: 0,
      ),
      child: isLoading
          ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
          : const Text("KIRISH", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
    );
  }

  Widget _buildDivider() {
    return const Column(
      children: [
        SizedBox(height: 32),
        Row(
          children: [
            Expanded(child: Divider(color: Colors.white10)),
            Padding(
              padding: EdgeInsets.symmetric(horizontal: 16),
              child: Text("Yoki ijtimoiy tarmoqlar", style: TextStyle(color: Colors.white24, fontSize: 12)),
            ),
            Expanded(child: Divider(color: Colors.white10)),
          ],
        ),
        SizedBox(height: 24),
      ],
    );
  }

  Widget _buildSocialRow() {
    return Row(
      children: [
        _socialButton(label: "Google", color: Colors.white, textColor: const Color(0xFF0F172A), icon: Icons.g_mobiledata, onTap: _handleGoogleLogin),
        const SizedBox(width: 16),
        _socialButton(label: "GitHub", color: const Color(0xFF1E293B), textColor: Colors.white, icon: Icons.code, onTap: _handleGithubLogin),
      ],
    );
  }

  Widget _buildInput(TextEditingController controller, String label, IconData icon, {bool isPassword = false}) {
    return TextField(
      controller: controller,
      obscureText: isPassword,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(color: Colors.white38),
        prefixIcon: Icon(icon, color: Colors.white38, size: 20),
        filled: true,
        fillColor: const Color(0xFF1E293B).withOpacity(0.5),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: Colors.white12)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: Color(0xFF6366F1))),
      ),
    );
  }

  Widget _socialButton({required String label, required Color color, required Color textColor, required IconData icon, required VoidCallback onTap}) {
    return Expanded(
      child: Material(
        color: color,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: isLoading ? null : onTap,
          borderRadius: BorderRadius.circular(16),
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: 14),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, color: textColor, size: 24),
                const SizedBox(width: 8),
                Text(label, style: TextStyle(color: textColor, fontWeight: FontWeight.bold, fontSize: 14)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}