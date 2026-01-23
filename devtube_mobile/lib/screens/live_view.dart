// lib/screens/live_view.dart

import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

class LiveViewScreen extends StatefulWidget {
  final String url;
  final String title;

  const LiveViewScreen({super.key, required this.url, required this.title});

  @override
  State<LiveViewScreen> createState() => _LiveViewScreenState();
}

class _LiveViewScreenState extends State<LiveViewScreen> {
  late final WebViewController controller;
  bool isLoading = true;
  String? errorMessage; // Xatolik matni

  @override
  void initState() {
    super.initState();
    controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.white) // Qora ekran bo'lmasligi uchun oq fon
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (url) {
            setState(() {
              isLoading = true;
              errorMessage = null;
            });
          },
          onPageFinished: (url) {
            setState(() {
              isLoading = false;
            });
          },
          onWebResourceError: (WebResourceError error) {
            // Agar internet yoki server xatosi bo'lsa
            setState(() {
              errorMessage = "Xatolik: ${error.description}";
              isLoading = false;
            });
          },
        ),
      )
      ..loadRequest(Uri.parse(widget.url));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black, // Tashqi fon
      appBar: AppBar(
        title: Text(widget.title, style: const TextStyle(fontSize: 16)),
        backgroundColor: const Color(0xFF0F172A),
        actions: [
          // Qayta yuklash tugmasi 🔄
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              controller.reload();
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          if (errorMessage != null)
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline, color: Colors.red, size: 50),
                  const SizedBox(height: 10),
                  Text(
                    errorMessage!,
                    style: const TextStyle(color: Colors.white),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: () => controller.reload(),
                    child: const Text("Qayta urinish"),
                  )
                ],
              ),
            )
          else
            WebViewWidget(controller: controller),

          if (isLoading)
            const Center(child: CircularProgressIndicator(color: Color(0xFF6366F1))),
        ],
      ),
    );
  }
}