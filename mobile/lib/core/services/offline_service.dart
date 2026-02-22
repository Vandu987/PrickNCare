import 'dart:async';
import 'dart:convert';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'sync_service.dart';

/// Represents a queued offline action to be synced when connectivity returns.
class PendingAction {
  final String id;
  final String type;
  final String endpoint;
  final String method;
  final Map<String, dynamic>? body;
  final DateTime timestamp;
  int retryCount;

  PendingAction({
    required this.id,
    required this.type,
    required this.endpoint,
    required this.method,
    this.body,
    required this.timestamp,
    this.retryCount = 0,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'type': type,
        'endpoint': endpoint,
        'method': method,
        'body': body,
        'timestamp': timestamp.toIso8601String(),
        'retryCount': retryCount,
      };

  factory PendingAction.fromJson(Map<String, dynamic> json) => PendingAction(
        id: json['id'] as String,
        type: json['type'] as String,
        endpoint: json['endpoint'] as String,
        method: json['method'] as String,
        body: json['body'] as Map<String, dynamic>?,
        timestamp: DateTime.parse(json['timestamp'] as String),
        retryCount: json['retryCount'] as int? ?? 0,
      );
}

class OfflineService {
  static const String _pendingActionsBox = 'pending_actions';
  static const String _cachedOrdersBox = 'cached_orders';

  final Connectivity _connectivity = Connectivity();
  late Box<String> _actionsBox;
  late Box<String> _ordersBox;
  SyncService? _syncService;

  bool _isOnline = true;
  bool get isOnline => _isOnline;

  StreamSubscription<List<ConnectivityResult>>? _connectivitySub;
  final _statusController = StreamController<bool>.broadcast();
  Stream<bool> get onlineStream => _statusController.stream;

  /// Initialize boxes and start listening to connectivity changes.
  Future<void> init() async {
    _actionsBox = await Hive.openBox<String>(_pendingActionsBox);
    _ordersBox = await Hive.openBox<String>(_cachedOrdersBox);

    // Check initial status
    final results = await _connectivity.checkConnectivity();
    _isOnline = !results.contains(ConnectivityResult.none);
    _statusController.add(_isOnline);

    // Listen for changes
    _connectivitySub = _connectivity.onConnectivityChanged.listen((results) {
      final online = !results.contains(ConnectivityResult.none);
      if (online != _isOnline) {
        _isOnline = online;
        _statusController.add(_isOnline);
        if (_isOnline) {
          _syncService?.processQueue();
        }
      }
    });
  }

  void attachSyncService(SyncService syncService) {
    _syncService = syncService;
  }

  /// Queue an action for later sync.
  Future<void> queueAction(PendingAction action) async {
    await _actionsBox.put(action.id, jsonEncode(action.toJson()));
  }

  /// Get all pending actions in order of timestamp.
  List<PendingAction> getPendingActions() {
    final actions = _actionsBox.values
        .map((json) => PendingAction.fromJson(
            jsonDecode(json) as Map<String, dynamic>))
        .toList();
    actions.sort((a, b) => a.timestamp.compareTo(b.timestamp));
    return actions;
  }

  /// Remove a completed action.
  Future<void> removeAction(String id) async {
    await _actionsBox.delete(id);
  }

  /// Update a pending action (e.g. increment retry count).
  Future<void> updateAction(PendingAction action) async {
    await _actionsBox.put(action.id, jsonEncode(action.toJson()));
  }

  int get pendingCount => _actionsBox.length;

  // --- Cached Orders ---

  /// Cache orders locally for offline viewing.
  Future<void> cacheOrders(List<Map<String, dynamic>> orders) async {
    await _ordersBox.clear();
    for (final order in orders) {
      final id = order['id']?.toString() ?? order.hashCode.toString();
      await _ordersBox.put(id, jsonEncode(order));
    }
  }

  /// Get cached orders.
  List<Map<String, dynamic>> getCachedOrders() {
    return _ordersBox.values
        .map((json) => jsonDecode(json) as Map<String, dynamic>)
        .toList();
  }

  Future<void> dispose() async {
    await _connectivitySub?.cancel();
    await _statusController.close();
  }
}
