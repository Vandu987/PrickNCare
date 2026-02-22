import 'dart:async';
import 'dart:math';
import 'package:dio/dio.dart';
import 'offline_service.dart';
import '../network/api_client.dart';

enum SyncStatus { idle, syncing, error, complete }

class SyncService {
  final OfflineService _offlineService;
  final ApiClient _apiClient;

  bool _isSyncing = false;
  final _statusController = StreamController<SyncStatus>.broadcast();
  Stream<SyncStatus> get statusStream => _statusController.stream;

  static const int _maxRetries = 5;

  SyncService({
    required OfflineService offlineService,
    required ApiClient apiClient,
  })  : _offlineService = offlineService,
        _apiClient = apiClient {
    _offlineService.attachSyncService(this);
  }

  /// Process all queued actions in order.
  Future<void> processQueue() async {
    if (_isSyncing || !_offlineService.isOnline) return;
    _isSyncing = true;
    _statusController.add(SyncStatus.syncing);

    final actions = _offlineService.getPendingActions();
    bool hadErrors = false;

    for (final action in actions) {
      if (!_offlineService.isOnline) {
        hadErrors = true;
        break;
      }

      try {
        await _executeAction(action);
        await _offlineService.removeAction(action.id);
      } catch (e) {
        action.retryCount++;
        if (action.retryCount >= _maxRetries) {
          // Drop after max retries
          await _offlineService.removeAction(action.id);
        } else {
          await _offlineService.updateAction(action);
          // Exponential backoff before next attempt
          final delay = Duration(
            milliseconds: min(1000 * pow(2, action.retryCount).toInt(), 30000),
          );
          await Future.delayed(delay);
        }
        hadErrors = true;
      }
    }

    _isSyncing = false;
    _statusController.add(hadErrors ? SyncStatus.error : SyncStatus.complete);

    // Reset to idle after a brief display period
    Future.delayed(const Duration(seconds: 3), () {
      if (!_isSyncing) _statusController.add(SyncStatus.idle);
    });
  }

  Future<Response> _executeAction(PendingAction action) async {
    switch (action.method.toUpperCase()) {
      case 'POST':
        return _apiClient.post(action.endpoint, data: action.body);
      case 'PUT':
        return _apiClient.put(action.endpoint, data: action.body);
      case 'PATCH':
        return _apiClient.patch(action.endpoint, data: action.body);
      case 'DELETE':
        return _apiClient.delete(action.endpoint);
      default:
        return _apiClient.get(action.endpoint);
    }
  }

  void dispose() {
    _statusController.close();
  }
}
