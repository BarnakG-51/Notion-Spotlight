import 'package:flutter/material.dart';
import 'package:hotkey_manager/hotkey_manager.dart';
import 'package:tray_manager/tray_manager.dart';
import 'package:window_manager/window_manager.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io' show Platform;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize window manager
  await windowManager.ensureInitialized();
  WindowOptions windowOptions = const WindowOptions(
    size: Size(600, 60),
    center: true,
    backgroundColor: Colors.transparent,
    skipTaskbar: true,
    windowButtonVisibility: false,
    titleBarStyle: TitleBarStyle.hidden,
  );
  windowManager.waitUntilReadyToShow(windowOptions, () async {
    await windowManager.show();
    await windowManager.focus();
  });

  // Initialize tray manager
  await trayManager.setIcon('assets/tray_icon.png');
  Menu menu = Menu(
    items: [
      MenuItem(
        key: 'show_window',
        label: 'Show Notion Spotlight',
      ),
      MenuItem.separator(),
      MenuItem(
        key: 'quit',
        label: 'Quit',
      ),
    ],
  );
  await trayManager.setContextMenu(menu);

  runApp(const NotionSpotlightApp());
}

class NotionSpotlightApp extends StatelessWidget {
  const NotionSpotlightApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(),
      home: const SpotlightWindow(),
    );
  }
}

class SpotlightWindow extends StatefulWidget {
  const SpotlightWindow({super.key});

  @override
  State<SpotlightWindow> createState() => _SpotlightWindowState();
}

class _SpotlightWindowState extends State<SpotlightWindow>
    with TrayListener, WindowListener {
  final TextEditingController _controller = TextEditingController();
  String _response = '';
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    trayManager.addListener(this);
    windowManager.addListener(this);

    // Register global hotkey
    HotKey hotKey = HotKey(
      KeyCode.keyK,
      modifiers: [Platform.isMacOS ? KeyModifier.meta : KeyModifier.control],
      scope: HotKeyScope.system,
    );
    hotKeyManager.register(
      hotKey,
      keyDownHandler: (hotKey) {
        _showWindow();
      },
    );

    // Auto-hide after 2 seconds of inactivity
    _controller.addListener(_onTextChanged);
  }

  void _onTextChanged() {
    // Reset auto-hide timer when user types
    Future.delayed(const Duration(seconds: 2), () {
      if (_controller.text.isEmpty && !_isProcessing) {
        windowManager.hide();
      }
    });
  }

  void _showWindow() async {
    await windowManager.show();
    await windowManager.focus();
    _controller.clear();
    setState(() => _response = '');
  }

  Future<void> _processPrompt() async {
    if (_controller.text.isEmpty) return;

    setState(() {
      _isProcessing = true;
      _response = 'Processing...';
    });

    try {
      final response = await http.post(
        Uri.parse('http://127.0.0.1:8001/prompt'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'text': _controller.text}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() => _response = data['message']);
      } else {
        setState(() => _response = 'Error: ${response.statusCode}');
      }
    } catch (e) {
      setState(() => _response = 'Connection error: $e');
    } finally {
      setState(() => _isProcessing = false);
    }

    // Auto-hide after showing result
    Future.delayed(const Duration(seconds: 2), () {
      windowManager.hide();
    });
  }

  @override
  void onTrayIconMouseDown() {
    _showWindow();
  }

  @override
  void onTrayMenuItemClick(MenuItem menuItem) {
    switch (menuItem.key) {
      case 'show_window':
        _showWindow();
        break;
      case 'quit':
        windowManager.close();
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black.withOpacity(0.9),
      body: Container(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Input field
            TextField(
              controller: _controller,
              autofocus: true,
              style: const TextStyle(color: Colors.white, fontSize: 18),
              decoration: InputDecoration(
                hintText: 'Ask Notion...',
                hintStyle: TextStyle(color: Colors.white.withOpacity(0.5)),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(25),
                  borderSide: BorderSide.none,
                ),
                filled: true,
                fillColor: Colors.white.withOpacity(0.1),
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              ),
              onSubmitted: (_) => _processPrompt(),
            ),
            // Response
            if (_response.isNotEmpty)
              Container(
                margin: const EdgeInsets.only(top: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _response,
                  style: const TextStyle(color: Colors.white, fontSize: 14),
                ),
              ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    trayManager.removeListener(this);
    windowManager.removeListener(this);
    _controller.dispose();
    super.dispose();
  }
}
