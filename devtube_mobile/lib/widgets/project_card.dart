import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../models/project.dart';
import '../screens/detail_screen.dart';

class ProjectCard extends StatelessWidget {
  final Project project;

  const ProjectCard({super.key, required this.project});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => DetailScreen(project: project))),
      child: Container(
        margin: const EdgeInsets.only(bottom: 24),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [const BoxShadow(color: Colors.black26, blurRadius: 10, offset: Offset(0, 4))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Stack(
              children: [
                ClipRRect(
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                  child: CachedNetworkImage(
                    imageUrl: project.imageUrl,
                    height: 200, width: double.infinity, fit: BoxFit.cover,
                    placeholder: (context, url) => Container(color: const Color(0xFF0F172A)),
                    errorWidget: (context, url, error) => Container(height: 200, color: Colors.grey[900], child: const Icon(Icons.broken_image)),
                  ),
                ),
                Positioned(
                  bottom: 10, right: 10,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(color: Colors.black87, borderRadius: BorderRadius.circular(4)),
                    child: Text(project.isFree ? "BEPUL" : project.price, style: TextStyle(color: project.isFree ? Colors.greenAccent : Colors.amber, fontWeight: FontWeight.bold, fontSize: 10)),
                  ),
                ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(project.title, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      CircleAvatar(backgroundImage: NetworkImage(project.authorAvatar), radius: 10),
                      const SizedBox(width: 6),
                      Text(project.authorName, style: const TextStyle(color: Colors.white70, fontSize: 12)),
                      const Spacer(),
                      const Icon(Icons.visibility, size: 14, color: Colors.grey),
                      const SizedBox(width: 4),
                      Text("${project.views}", style: const TextStyle(color: Colors.grey, fontSize: 12)),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}