import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/connectivity_provider.dart';
import '../../core/services/sync_service.dart';

/// Banner displayed at the top of the app when offline or syncing.
class OfflineBanner extends ConsumerWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isOnline = ref.watch(isOnlineProvider);
    final syncStatus = ref.watch(syncStatusProvider);

    if (isOnline) {
      // Show brief sync status if syncing
      return syncStatus.when(
        data: (status) {
          if (status == SyncStatus.syncing) {
            return _buildBanner(
              context,
              icon: Icons.sync,
              message: 'Syncing pending actions...',
              color: Colors.blue,
            );
          }
          return const SizedBox.shrink();
        },
        loading: () => const SizedBox.shrink(),
        error: (_, __) => const SizedBox.shrink(),
      );
    }

    final pendingCount = ref.watch(pendingActionsCountProvider);
    final suffix = pendingCount > 0 ? ' • $pendingCount pending' : '';

    return _buildBanner(
      context,
      icon: Icons.cloud_off,
      message: 'You are offline$suffix',
      color: Colors.orange.shade800,
    );
  }

  Widget _buildBanner(
    BuildContext context, {
    required IconData icon,
    required String message,
    required Color color,
  }) {
    return Material(
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        color: color,
        child: SafeArea(
          bottom: false,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: Colors.white, size: 16),
              const SizedBox(width: 8),
              Text(
                message,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
