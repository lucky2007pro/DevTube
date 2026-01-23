import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/project.dart';
import '../services/api_service.dart';
import 'live_view.dart';
import 'creator_profile_screen.dart';

class DetailScreen extends StatefulWidget {
  final Project project;
  final List<Project> allProjects;

  const DetailScreen({
    super.key,
    required this.project,
    this.allProjects = const [],
  });

  @override
  State<DetailScreen> createState() => _DetailScreenState();
}

class _DetailScreenState extends State<DetailScreen> {
  bool isSynced = false;
  bool isActionLoading = false;
  bool hasBoughtLocally = false;

  // Kodni saqlash uchun
  String? fetchedSourceCode;
  bool isCodeLoading = false;

  final TextEditingController _commentController = TextEditingController();
  List<Comment> _comments = [];

  final Color bgDark = const Color(0xFF0D1117);
  final Color neonPrimary = const Color(0xFF6366F1);
  final Color borderColor = Colors.white.withOpacity(0.1);

  @override
  void initState() {
    super.initState();
    _comments = widget.project.comments;
    // Agar loyiha ochiq bo'lsa, kodni avtomatik yuklaymiz
    if (widget.project.isFree) {
      _loadSourceCode();
    }
  }

  // --- KODNI SERVERNIDAN YUKLASH ---
  Future<void> _loadSourceCode() async {
    setState(() => isCodeLoading = true);
    String? code = await ApiService.fetchSourceCode(widget.project.id);
    if (mounted) {
      setState(() {
        fetchedSourceCode = code;
        isCodeLoading = false;
      });
    }
  }

  // --- SINXRONLASH (OBUNA) ---
  Future<void> _handleSync() async {
    setState(() => isActionLoading = true);

    // API dan javobni olamiz
    var result = await ApiService.toggleSync(widget.project.authorName);

    setState(() => isActionLoading = false);

    // Agar xato bo'lsa
    if (result.containsKey('error')) {
       if(mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(result['error']), backgroundColor: Colors.red));
    } else {
       // Muvaffaqiyatli
       setState(() {
         isSynced = result['is_synced'] ?? false;
       });
       if(mounted) {
         ScaffoldMessenger.of(context).showSnackBar(
           SnackBar(
             content: Text(isSynced ? "Obuna bo'lindi" : "Obuna bekor qilindi"),
             backgroundColor: isSynced ? Colors.green : Colors.grey
           )
         );
       }
    }
  }

  // --- XARID QILISH ---
  Future<void> _handlePurchase() async {
    bool confirm = await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: bgDark,
        title: const Text("Xaridni tasdiqlang", style: TextStyle(color: Colors.white)),
        content: Text("Hisobingizdan ${widget.project.price} yechiladi. Davom etamizmi?", style: const TextStyle(color: Colors.white70)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("Yo'q", style: TextStyle(color: Colors.grey))),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text("Ha", style: TextStyle(color: Colors.greenAccent))),
        ],
      ),
    ) ?? false;

    if (!confirm) return;

    setState(() => isActionLoading = true);
    bool success = await ApiService.buyProject(widget.project.id);
    setState(() => isActionLoading = false);

    if (success) {
      setState(() => hasBoughtLocally = true);
      _loadSourceCode(); // Xariddan keyin kodni yuklaymiz
      if(mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Xarid muvaffaqiyatli!"), backgroundColor: Colors.green));
    } else {
      if(mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text("Mablag' yetarli emas!"),
            backgroundColor: Colors.red,
            action: SnackBarAction(
              label: "To'ldirish",
              textColor: Colors.white,
              onPressed: () => launchUrl(Uri.parse("https://devtube-s744.onrender.com/wallet/deposit/"), mode: LaunchMode.externalApplication),
            ),
          ),
        );
      }
    }
  }

  // --- IZOH QOLDIRISH ---
  Future<void> _postComment() async {
    String text = _commentController.text.trim();
    if (text.isEmpty) return;

    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Yuborilmoqda..."), duration: Duration(milliseconds: 500)));

    // API Service dagi yangilangan metodni chaqiramiz
    var result = await ApiService.postComment(widget.project.id, text);

    if (result.containsKey('success') && result['success'] == true) {
      var data = result['data']; // Yangi izoh ma'lumotlari
      setState(() {
        // Yangi izohni ro'yxat boshiga qo'shamiz
        _comments.insert(0, Comment(
          username: data['username'] ?? 'Foydalanuvchi',
          avatarUrl: data['avatar_url'] != null && data['avatar_url'].toString().isNotEmpty
              ? (data['avatar_url'].toString().startsWith('http') ? data['avatar_url'] : 'https://devtube-s744.onrender.com${data['avatar_url']}')
              : 'https://ui-avatars.com/api/?name=${data['username']}',
          body: data['body'] ?? '',
          timeAgo: "Hozirgina"
        ));
        _commentController.clear();
      });
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Izoh qoldirildi!"), backgroundColor: Colors.green));
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(result['error'] ?? "Xatolik yuz berdi"), backgroundColor: Colors.red));
    }
  }

  void _copyCode() {
    if (fetchedSourceCode != null) {
      Clipboard.setData(ClipboardData(text: fetchedSourceCode!));
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Kod nusxalandi!"), backgroundColor: Colors.green));
    } else {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Kod hali yuklanmadi"), backgroundColor: Colors.orange));
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool isFree = widget.project.isFree;
    final bool isUnlocked = isFree || hasBoughtLocally;

    return Scaffold(
      backgroundColor: bgDark,
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 100, 16, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Preview
            GestureDetector(
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => LiveViewScreen(url: "https://devtube-s744.onrender.com/live-view/${widget.project.id}/", title: widget.project.title))),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  ClipRRect(borderRadius: BorderRadius.circular(20), child: CachedNetworkImage(imageUrl: widget.project.imageUrl, height: 220, width: double.infinity, fit: BoxFit.cover)),
                  Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(color: Colors.black54, shape: BoxShape.circle, border: Border.all(color: Colors.white24)), child: const Icon(Icons.play_arrow, color: Colors.white, size: 40)),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Title & Sync
            Row(
              children: [
                Expanded(child: Text(widget.project.title, style: GoogleFonts.inter(fontSize: 22, fontWeight: FontWeight.w900, color: Colors.white))),
                const SizedBox(width: 10),
                ActionChip(
                  label: isActionLoading
                    ? const SizedBox(width: 12, height: 12, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : Text(isSynced ? "Sinxronlandi" : "Sinxronlash"),
                  backgroundColor: isSynced ? Colors.green : neonPrimary,
                  labelStyle: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                  onPressed: _handleSync,
                ),
              ],
            ),

            // Muallif Profiliga o'tish
            const SizedBox(height: 15),
            GestureDetector(
              onTap: () {
                 Navigator.push(context, MaterialPageRoute(
                   builder: (context) => CreatorProfileScreen(
                     username: widget.project.authorName,
                     avatarUrl: widget.project.authorAvatar,
                     allProjects: widget.allProjects,
                   )
                 ));
              },
              child: Row(
                children: [
                  CircleAvatar(backgroundImage: NetworkImage(widget.project.authorAvatar)),
                  const SizedBox(width: 10),
                  Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(widget.project.authorName, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    const Text("Dasturchi • PRO", style: TextStyle(color: Colors.grey, fontSize: 11)),
                  ]),
                  const Spacer(),
                  const Icon(Icons.chevron_right, color: Colors.grey),
                ],
              ),
            ),

            const SizedBox(height: 20),

            // Kod qismi
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: const Color(0xFF161B22), borderRadius: BorderRadius.circular(16), border: Border.all(color: borderColor)),
              child: Column(
                children: [
                  Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                    const Text("Manba Kodi", style: TextStyle(color: Colors.blueAccent, fontWeight: FontWeight.bold)),
                    if(isUnlocked) IconButton(icon: const Icon(Icons.copy, color: Colors.white70), onPressed: _copyCode)
                  ]),
                  Divider(color: Colors.white.withOpacity(0.1)),

                  // Agar qulflangan bo'lsa -> Qulf
                  // Agar ochiq va loading bo'lsa -> Spinner
                  // Agar ochiq va yuklangan bo'lsa -> Kod
                  !isUnlocked
                      ? const Center(child: Column(children: [Icon(Icons.lock, color: Colors.amber, size: 40), SizedBox(height: 10), Text("Kod yopiq. Xarid qiling.", style: TextStyle(color: Colors.grey))]))
                      : (isCodeLoading
                          ? const Center(child: CircularProgressIndicator(color: Colors.blueAccent))
                          : Text(fetchedSourceCode ?? "Kod yuklanmadi yoki bo'sh.", style: GoogleFonts.firaCode(color: Colors.white70, fontSize: 12))),
                ],
              ),
            ),

            const SizedBox(height: 30),

            // Komentariyalar
            Text("Fikrlar (${widget.project.commentCount})", style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),

            // Input
            Row(children: [
              Expanded(child: TextField(
                controller: _commentController,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: "Fikr qoldirish...",
                  hintStyle: const TextStyle(color: Colors.grey),
                  filled: true,
                  fillColor: Colors.white10,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(30), borderSide: BorderSide.none)
                ),
              )),
              IconButton(onPressed: _postComment, icon: const Icon(Icons.send, color: Colors.blueAccent))
            ]),

            const SizedBox(height: 15),

            // List (Bo'sh bo'lsa xabar chiqaramiz)
            _comments.isEmpty
              ? const Text("Hozircha fikrlar yo'q", style: TextStyle(color: Colors.white54, fontStyle: FontStyle.italic))
              : ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: _comments.length,
                  itemBuilder: (ctx, i) {
                    final com = _comments[i];
                    return ListTile(
                      leading: CircleAvatar(backgroundImage: NetworkImage(com.avatarUrl)),
                      title: Text(com.username, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                      subtitle: Text(com.body, style: const TextStyle(color: Colors.white70)),
                      trailing: Text(com.timeAgo, style: const TextStyle(color: Colors.grey, fontSize: 10)),
                    );
                  }
                )
          ],
        ),
      ),
      bottomNavigationBar: Padding(
        padding: const EdgeInsets.all(20),
        child: ElevatedButton(
          onPressed: isActionLoading
            ? null
            : (isUnlocked ? _copyCode : _handlePurchase),
          style: ElevatedButton.styleFrom(
            backgroundColor: isUnlocked ? Colors.green : neonPrimary,
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))
          ),
          child: isActionLoading
             ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
             : Text(isUnlocked ? "KODNI NUSXALASH" : "XARID QILISH (${widget.project.price})", style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
        ),
      ),
    );
  }
}