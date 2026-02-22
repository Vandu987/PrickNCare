import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'api_client.dart';
import '../services/offline_service.dart';

/// SharedPreferences provider - must be overridden at app start
final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('SharedPreferences must be overridden in main');
});

/// OfflineService provider — overridden in main with initialized instance.
final offlineServiceProvider = Provider<OfflineService>((ref) {
  throw UnimplementedError('OfflineService must be overridden in main');
});

/// ApiClient provider
final apiClientProvider = Provider<ApiClient>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  final offlineService = ref.watch(offlineServiceProvider);
  return ApiClient(prefs: prefs, offlineService: offlineService);
});
