import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/services/sync_service.dart';
import '../../core/network/api_providers.dart';

/// Re-export offlineServiceProvider from api_providers for convenience.
export '../../core/network/api_providers.dart' show offlineServiceProvider;

/// SyncService provider.
final syncServiceProvider = Provider<SyncService>((ref) {
  final offlineService = ref.watch(offlineServiceProvider);
  final apiClient = ref.watch(apiClientProvider);
  final syncService = SyncService(
    offlineService: offlineService,
    apiClient: apiClient,
  );
  ref.onDispose(() => syncService.dispose());
  return syncService;
});

/// Stream provider for online/offline status.
final connectivityStreamProvider = StreamProvider<bool>((ref) {
  final offlineService = ref.watch(offlineServiceProvider);
  return offlineService.onlineStream;
});

/// Current connectivity status (synchronous read).
final isOnlineProvider = Provider<bool>((ref) {
  final asyncValue = ref.watch(connectivityStreamProvider);
  return asyncValue.when(
    data: (online) => online,
    loading: () => true, // assume online until we know
    error: (_, __) => true,
  );
});

/// Sync status stream.
final syncStatusProvider = StreamProvider<SyncStatus>((ref) {
  final syncService = ref.watch(syncServiceProvider);
  return syncService.statusStream;
});

/// Pending actions count.
final pendingActionsCountProvider = Provider<int>((ref) {
  final offlineService = ref.watch(offlineServiceProvider);
  return offlineService.pendingCount;
});
