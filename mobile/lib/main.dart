import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'app/app.dart';
import 'core/network/api_providers.dart';
import 'core/services/offline_service.dart';
// offlineServiceProvider is in api_providers.dart

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Hive
  await Hive.initFlutter();

  // Initialize SharedPreferences
  final prefs = await SharedPreferences.getInstance();

  // Initialize OfflineService (opens Hive boxes, starts connectivity listener)
  final offlineService = OfflineService();
  await offlineService.init();

  runApp(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        offlineServiceProvider.overrideWithValue(offlineService),
      ],
      child: const PricknCareApp(),
    ),
  );
}
