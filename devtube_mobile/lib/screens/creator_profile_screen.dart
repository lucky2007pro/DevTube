import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../models/project.dart';
import 'detail_screen.dart'; // DetailScreen ga o'tish uchun

class CreatorProfileScreen extends StatelessWidget {
  final String username;
  final String avatarUrl;
  final List<Project> allProjects; // Barcha loyihalar

  const CreatorProfileScreen({
    super.key,
    required this.username,
    required this.avatarUrl,
    required this.allProjects,
  });

  @override
  Widget build(BuildContext context) {
    // --- TUZATISH: Ismlarni tozalab solishtiramiz ---
    final myProjects = allProjects.where((p) {
      final String author = p.authorName.toString().toLowerCase().trim();
      final String target = username.toString().toLowerCase().trim();
      return author == target;
    }).toList();

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: Text(username),
        backgroundColor: const Color(0xFF0F172A),
        elevation: 0,
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            // AVATAR
            Center(
              child: Column(
                children: [
                  Container(
                    padding: const EdgeInsets.all(3),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: const Color(0xFF6366F1), width: 2),
                    ),
                    child: CircleAvatar(
                      radius: 50,
                      backgroundImage: NetworkImage(avatarUrl),
                      backgroundColor: Colors.grey[800],
                      onBackgroundImageError: (_, __) => const Icon(Icons.person),
                    ),
                  ),
                  const SizedBox(height: 15),
                  Text(
                    username,
                    style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)
                  ),
                  const Text("DevTube Dasturchisi", style: TextStyle(color: Colors.grey)),
                ],
              ),
            ),

            const SizedBox(height: 30),

            // STATISTIKA (Sinxronlar API da yo'qligi uchun 'Hidden' qo'ydim)
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _buildStatItem("Loyihalar", "${myProjects.length}"),
                const SizedBox(width: 40),
                _buildStatItem("Sinxronlar", "Hidden"),
              ],
            ),

            const SizedBox(height: 30),
            const Divider(color: Colors.white10),
            const SizedBox(height: 10),

            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                "Muallif Loyihalari (${myProjects.length})",
                style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)
              ),
            ),
            const SizedBox(height: 15),

            // RO'YXAT
            myProjects.isEmpty
                ? Container(
                    padding: const EdgeInsets.only(top: 50),
                    alignment: Alignment.center,
                    child: Column(
                      children: [
                        const Icon(Icons.folder_open, size: 50, color: Colors.white24),
                        const SizedBox(height: 10),
                        Text("Loyihalar topilmadi: $username", style: const TextStyle(color: Colors.white54)),
                      ],
                    ),
                  )
                : ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: myProjects.length,
                    itemBuilder: (ctx, index) => _buildMiniCard(context, myProjects[index]),
                  ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(String label, String value) {
    return Column(
      children: [
        Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white)),
        const SizedBox(height: 5),
        Text(label, style: const TextStyle(color: Colors.white54)),
      ],
    );
  }

  Widget _buildMiniCard(BuildContext context, Project project) {
    return GestureDetector(
      onTap: () => Navigator.push(context, MaterialPageRoute(
        // Zanjirni uzmaslik uchun allProjects ni yana uzatamiz
        builder: (context) => DetailScreen(project: project, allProjects: allProjects)
      )),
      child: Container(
        margin: const EdgeInsets.only(bottom: 15),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.05)),
        ),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: CachedNetworkImage(
                imageUrl: project.imageUrl,
                width: 80, height: 60, fit: BoxFit.cover,
                placeholder: (context, url) => Container(color: Colors.black26),
                errorWidget: (context, url, error) => const Icon(Icons.error),
              ),
            ),
            const SizedBox(width: 15),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(project.title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16), maxLines: 1, overflow: TextOverflow.ellipsis),
                  const SizedBox(height: 4),
                  Text(project.price, style: TextStyle(color: project.isFree ? Colors.greenAccent : Colors.amber, fontWeight: FontWeight.bold, fontSize: 12)),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios, color: Colors.white24, size: 16),
          ],
        ),
      ),
    );
  }
}