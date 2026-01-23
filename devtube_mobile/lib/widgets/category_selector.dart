import 'package:flutter/material.dart';

class CategorySelector extends StatelessWidget {
  final List<Map<String, dynamic>> categories;
  final String selectedCategory;
  final Function(String) onSelect;

  const CategorySelector({
    super.key,
    required this.categories,
    required this.selectedCategory,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
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
            onTap: () => onSelect(cat['name']),
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
}