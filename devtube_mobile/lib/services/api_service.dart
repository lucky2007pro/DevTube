import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/project.dart';
import '../models/user_profile.dart';

class ApiService {
  static const String baseUrl = "https://devtube-s744.onrender.com";

  // --- TOKEN BILAN ISHLASH ---
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    // Token borligini va bo'sh emasligini tekshiramiz
    String? token = prefs.getString('auth_token');
    if (token != null && token.isNotEmpty) {
      return token;
    }
    return null;
  }

  // --- 1. LOYIHALARNI OLISH ---
  static Future<List<Project>> fetchProjects() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/projects/'));
      if (response.statusCode == 200) {
        List jsonResponse = json.decode(utf8.decode(response.bodyBytes));
        return jsonResponse.map((data) => Project.fromJson(data)).toList();
      }
      return [];
    } catch (e) {
      print("Fetch Error: $e");
      return [];
    }
  }

  // --- 2. MANBA KODINI YUKLASH ---
  static Future<String?> fetchSourceCode(int projectId) async {
    // Kod ochiq bo'lsa (free), token shart emas, lekin yopiq bo'lsa token kerak
    // Shuning uchun tokenni har ehtimolga qarshi qo'shamiz
    final token = await getToken();
    Map<String, String> headers = {};
    if (token != null) {
      headers['Authorization'] = 'Token $token';
    }

    try {
      final response = await http.get(
        Uri.parse('$baseUrl/live-view/$projectId/'),
        headers: headers
      );

      if (response.statusCode == 200) {
        // UTF-8 bilan qaytaramiz
        return utf8.decode(response.bodyBytes);
      }
    } catch (e) {
      print("Code Fetch Error: $e");
    }
    return null;
  }

  // --- 3. SINXRONLASH ---
  static Future<Map<String, dynamic>> toggleSync(String username) async {
    final token = await getToken();
    if (token == null) return {'error': 'Tizimga kiring'};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/sync/$username/'),
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        return {'error': 'Server xatosi: ${response.statusCode}'};
      }
    } catch (e) {
      return {'error': 'Internet yo\'q'};
    }
  }

  // --- 4. KOMMENTARIYA YOZISH ---
  static Future<Map<String, dynamic>> postComment(int projectId, String body) async {
    final token = await getToken();
    if (token == null) return {'success': false, 'error': 'Tizimga kiring'};

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/watch/$projectId/'),
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: {'body': body},
      );

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        return {'success': true, 'data': data};
      } else {
        return {'success': false, 'error': 'Xatolik: ${response.statusCode}'};
      }
    } catch (e) {
      return {'success': false, 'error': 'Internet xatosi'};
    }
  }

  // --- 5. XARID QILISH ---
  static Future<bool> buyProject(int projectId) async {
    final token = await getToken();
    if (token == null) return false;

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/buy/$projectId/'),
        headers: {
          'Authorization': 'Token $token',
          'X-Requested-With': 'XMLHttpRequest',
        },
      );
      // Django 302 (Redirect) qaytaradi, bu muvaffaqiyat belgisi
      return response.statusCode == 200 || response.statusCode == 302;
    } catch (e) {
      return false;
    }
  }

  // --- 6. AUTH VA PROFIL ---
  static Future<UserProfile?> fetchUserProfile() async {
    final token = await getToken();
    if (token == null) return null;
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/profile/'),
        headers: {'Authorization': 'Token $token'},
      );
      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        return UserProfile.fromJson(data);
      }
    } catch (e) {}
    return null;
  }

  static Future<bool> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/login/'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'username': username, 'password': password}),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final token = data['token'];
        if (token != null) {
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('auth_token', token);
          return true;
        }
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  static Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
  }

  static Future<bool> depositFunds(String amount, File receiptImage) async {
    final token = await getToken();
    if (token == null) return false;
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/wallet/deposit/'));
      request.headers['Authorization'] = 'Token $token';
      request.fields['amount'] = amount;
      request.fields['message'] = "App Deposit";
      request.files.add(await http.MultipartFile.fromPath('receipt', receiptImage.path, contentType: MediaType('image', 'jpeg')));
      var response = await request.send();
      return response.statusCode == 200 || response.statusCode == 302;
    } catch (e) {
      return false;
    }
  }
}