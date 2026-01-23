import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:shimmer/shimmer.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../models/project.dart';
import '../services/api_service.dart';
import 'detail_screen.dart';
import 'login_screen.dart';
import 'profile_screen.dart';
import 'creator_profile_screen.dart'; // <--- MUHIM: Bu fayl import qilinishi shart

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  // Pastki menyu indeksi (0: Home, 1: Feed, 2: Upload, 3: Mini, 4: Profile)
  int _selectedIndex = 0;

  late Future<List<Project>> futureProjects;
  bool isLoggedIn = false;
  String selectedCategory = "Barchasi";

  // Qidiruv va Filtrlash uchun
  List<Project> _allProjects = []; // Barcha yuklangan loyihalar
  List<Project> _filteredProjects = []; // Qidiruv natijasi
  bool _isSearching = false;
  final TextEditingController _searchController = TextEditingController();

  final List<Map<String, dynamic>> categories = [
    {"name": "Barchasi", "icon": Icons.grid_view_rounded},
    {"name": "Web Dasturlash", "icon": Icons.language},
    {"name": "Mobil Ilovalar", "icon": Icons.phone_android},
    {"name": "Sun'iy Intellekt", "icon": Icons.psychology},
    {"name": "O'yinlar", "icon": Icons.sports_esports},
    {"name": "Kompyuter Dasturlari", "icon": Icons.computer},
  ];

  @override
  void initState() {
    super.initState();
    _loadData();
    _checkLoginStatus();
    _searchController.addListener(_onSearchChanged);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  // --- 1. MA'LUMOT YUKLASH ---
  void _loadData() {
    futureProjects = ApiService.fetchProjects();
    futureProjects.then((projects) {
      if (mounted) {
        setState(() {
          _allProjects = projects;
          _filteredProjects = projects; // Boshida hammasi ko'rinadi
        });
      }
    });
  }

  void _checkLoginStatus() async {
    final token = await ApiService.getToken();
    if (mounted) setState(() => isLoggedIn = token != null);
  }

  // --- 2. QIDIRUV MANTIQI ---
  void _onSearchChanged() {
    String query = _searchController.text.toLowerCase();
    setState(() {
      _filteredProjects = _allProjects.where((p) {
        return p.title.toLowerCase().contains(query) ||
               p.authorName.toLowerCase().contains(query) ||
               p.description.toLowerCase().contains(query);
      }).toList();
    });
  }

  // --- 3. KATEGORIYA FILTRI ---
  bool _shouldShowProject(Project project, String selectedButtonCategory) {
    if (selectedButtonCategory == "Barchasi") return true;
    final searchKey = selectedButtonCategory.toLowerCase().split(' ')[0];
    final pTitle = project.title.toLowerCase();
    final pCategory = project.category.toLowerCase();

    if (pCategory.contains(searchKey) || pTitle.contains(searchKey)) return true;

    if (selectedButtonCategory == "Web Dasturlash") {
      return pTitle.contains("html") || pTitle.contains("js") || pTitle.contains("php") || pTitle.contains("react");
    }
    return false;
  }

  // --- 4. PASTKI MENYU BOSILGANDA ---
  void _onItemTapped(int index) {
    // Agar profil (4-indeks) bosilsa va login qilinmagan bo'lsa
    if (index == 4 && !isLoggedIn) {
      Navigator.push(context, MaterialPageRoute(builder: (context) => const LoginScreen()));
      return;
    }
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    // Indeksga qarab ekranni almashtirish
    Widget bodyContent;
    switch (_selectedIndex) {
      case 0:
        bodyContent = _buildHomeTab();
        break;
      case 1:
        bodyContent = _buildPlaceholderTab("Sinxronlarim", Icons.sync, "Obuna bo'lganlaringiz loyihalari shu yerda chiqadi.");
        break;
      case 2:
        bodyContent = _buildPlaceholderTab("Loyiha Yuklash", Icons.cloud_upload, "Tez orada mobil ilovadan loyiha yuklash imkoni bo'ladi.");
        break;
      case 3:
        bodyContent = _buildPlaceholderTab("Mini Loyihalar", Icons.bolt, "Kichik kodlar va snippetlar bo'limi.");
        break;
      case 4:
        bodyContent = const ProfileScreen(); // Profil oynasi shu yerda ochiladi
        break;
      default:
        bodyContent = _buildHomeTab();
    }

    // Profil oynasi alohida Scaffoldga ega bo'lgani uchun uni to'g'ridan to'g'ri qaytarmasdan,
    // BottomNavigationBar saqlanib qolishi uchun shu yerda boshqaramiz.
    // Agar _selectedIndex 4 bo'lsa ham, biz umumiy Scaffoldni qaytaramiz, body o'zgaradi.

    return Scaffold(
      // AppBar faqat Bosh sahifada (0) ko'rinadi, chunki Search Bar shu yerda kerak.
      appBar: _selectedIndex == 0
          ? AppBar(
              title: _isSearching
                  ? TextField(
                      controller: _searchController,
                      autofocus: true,
                      style: const TextStyle(color: Colors.white),
                      decoration: const InputDecoration(
                        hintText: "Loyiha yoki muallifni qidiring...",
                        hintStyle: TextStyle(color: Colors.white54),
                        border: InputBorder.none,
                      ),
                    )
                  : Row(
                      children: [
                        const Icon(Icons.play_circle_fill, color: Color(0xFF6366F1), size: 30),
                        const SizedBox(width: 8),
                        Text("DevTube", style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 20)),
                      ],
                    ),
              actions: [
                IconButton(
                  icon: Icon(_isSearching ? Icons.close : Icons.search, color: Colors.white70),
                  onPressed: () {
                    setState(() {
                      _isSearching = !_isSearching;
                      if (!_isSearching) _searchController.clear();
                    });
                  },
                ),
                const SizedBox(width: 10),
              ],
            )
          : null, // Boshqa tablarda AppBar yo'q (Profile o'zining AppBariga ega bo'lsa, o'sha ko'rinadi)

      body: bodyContent,

      bottomNavigationBar: Theme(
        data: Theme.of(context).copyWith(
          canvasColor: const Color(0xFF0F172A), // Nav bar foni
        ),
        child: BottomNavigationBar(
          items: const [
            BottomNavigationBarItem(icon: Icon(Icons.home), label: 'Bosh sahifa'),
            BottomNavigationBarItem(icon: Icon(Icons.sync_alt), label: 'Sinxronlar'),
            BottomNavigationBarItem(icon: Icon(Icons.add_circle_outline, size: 35), label: ''), // O'rtadagi katta tugma (Label bo'sh)
            BottomNavigationBarItem(icon: Icon(Icons.bolt), label: 'Mini'),
            BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Profil'),
          ],
          currentIndex: _selectedIndex,
          selectedItemColor: const Color(0xFF6366F1),
          unselectedItemColor: Colors.grey,
          showUnselectedLabels: true,
          type: BottomNavigationBarType.fixed,
          onTap: _onItemTapped,
        ),
      ),
    );
  }

  // --- HOME TABI (ASOSIY RO'YXAT) ---
  Widget _buildHomeTab() {
    return RefreshIndicator(
      onRefresh: () async => _loadData(),
      child: Column(
        children: [
          // Qidiruv yoqilmagan bo'lsa, kategoriyalarni ko'rsatamiz
          if (!_isSearching) _buildCategorySlider(),

          Expanded(
            child: FutureBuilder<List<Project>>(
              future: futureProjects,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) return _buildSkeleton();

                // Agar xato bo'lsa
                if (snapshot.hasError) return Center(child: Text("Xatolik: ${snapshot.error}", style: const TextStyle(color: Colors.red)));

                // Agar ma'lumot hali yuklanmagan bo'lsa ham _allProjects bo'sh bo'lmasligi mumkin
                // Shuning uchun sourceList ni tanlaymiz
                List<Project> sourceList = _isSearching ? _filteredProjects : (_allProjects.isNotEmpty ? _allProjects : (snapshot.data ?? []));

                // Kategoriyaga qarab filtrlash (faqat qidiruv yo'q bo'lsa)
                List<Project> displayList = _isSearching
                    ? sourceList
                    : sourceList.where((p) => _shouldShowProject(p, selectedCategory)).toList();

                if (displayList.isEmpty) {
                  // Agar ma'lumot yuklanib bo'lgan va ro'yxat bo'sh bo'lsa
                  if (snapshot.connectionState == ConnectionState.done) {
                     return const Center(child: Text("Loyihalar topilmadi", style: TextStyle(color: Colors.grey)));
                  } else {
                     return _buildSkeleton(); // Hali yuklanayotgan bo'lsa
                  }
                }

                return ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: displayList.length,
                  itemBuilder: (context, index) => _buildCard(displayList[index]),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  // --- KATEGORIYA SLIDERI ---
  Widget _buildCategorySlider() {
    return Container(
      height: 38,
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: categories.length,
        itemBuilder: (context, index) {
          final cat = categories[index];
          final isSelected = cat['name'] == selectedCategory;
          return GestureDetector(
            onTap: () => setState(() => selectedCategory = cat['name']),
            child: Container(
              margin: const EdgeInsets.only(right: 8),
              padding: const EdgeInsets.symmetric(horizontal: 12),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: isSelected ? const Color(0xFF6366F1) : const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.white.withOpacity(0.05)),
              ),
              child: Row(
                children: [
                  Icon(cat['icon'], color: isSelected ? Colors.white : Colors.white70, size: 14),
                  const SizedBox(width: 6),
                  Text(cat['name'], style: TextStyle(color: isSelected ? Colors.white : Colors.white70, fontSize: 12)),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // --- LOYIHA KARTASI ---
  Widget _buildCard(Project project) {
    return GestureDetector(
      // DetailScreen ga o'tishda allProjects ni ham yuboramiz (XATOSIZ)
      onTap: () => Navigator.push(context, MaterialPageRoute(
        builder: (context) => DetailScreen(project: project, allProjects: _allProjects)
      )),
      child: Container(
        margin: const EdgeInsets.only(bottom: 20),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [const BoxShadow(color: Colors.black26, blurRadius: 10, offset: Offset(0, 4))],
        ),
        child: Column(
          children: [
            // Rasm qismi
            ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
              child: CachedNetworkImage(
                imageUrl: project.imageUrl,
                height: 180, width: double.infinity, fit: BoxFit.cover,
                placeholder: (context, url) => Container(color: const Color(0xFF0F172A)),
                errorWidget: (context, url, error) => const Icon(Icons.broken_image, size: 50, color: Colors.grey),
              ),
            ),

            // Ma'lumot qismi
            Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  // MUALLIF PROFILIGA O'TISH
                  GestureDetector(
                    onTap: () {
                      // CreatorProfileScreen ga o'tish (XATOSIZ)
                      Navigator.push(context, MaterialPageRoute(
                        builder: (context) => CreatorProfileScreen(
                          username: project.authorName,
                          avatarUrl: project.authorAvatar,
                          allProjects: _allProjects, // Barcha loyihalarni uzatamiz
                        )
                      ));
                    },
                    child: CircleAvatar(backgroundImage: NetworkImage(project.authorAvatar), radius: 14),
                  ),
                  const SizedBox(width: 10),

                  // Sarlavha va Muallif
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(project.title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14), maxLines: 1, overflow: TextOverflow.ellipsis),
                        Text(project.authorName, style: const TextStyle(color: Colors.white54, fontSize: 11)),
                      ],
                    ),
                  ),

                  // Narx
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.black54,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: project.isFree ? Colors.green.withOpacity(0.5) : Colors.amber.withOpacity(0.5))
                    ),
                    child: Text(
                      project.price,
                      style: TextStyle(
                        color: project.isFree ? Colors.greenAccent : Colors.amber,
                        fontWeight: FontWeight.bold,
                        fontSize: 12
                      )
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // --- BO'SH SAHIFALAR (Placeholder) ---
  Widget _buildPlaceholderTab(String title, IconData icon, String desc) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 80, color: Colors.white12),
          const SizedBox(height: 20),
          Text(title, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 10),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 40),
            child: Text(desc, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white54)),
          ),
        ],
      ),
    );
  }

  // --- SKELETON LOADING ---
  Widget _buildSkeleton() {
    return Shimmer.fromColors(
      baseColor: const Color(0xFF1E293B),
      highlightColor: const Color(0xFF334155),
      child: ListView.builder(
        itemCount: 3,
        itemBuilder: (_, __) => Container(
          height: 200,
          margin: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16))
        )
      ),
    );
  }
}