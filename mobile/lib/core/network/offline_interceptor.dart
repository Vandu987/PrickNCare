import 'package:dio/dio.dart';
import '../services/offline_service.dart';

/// Dio interceptor that queues mutating requests when offline
/// instead of letting them fail.
class OfflineInterceptor extends Interceptor {
  final OfflineService _offlineService;

  /// Safe methods that should fail fast (not queued).
  static const _readOnlyMethods = {'GET', 'HEAD', 'OPTIONS'};

  OfflineInterceptor(this._offlineService);

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (_offlineService.isOnline) {
      return handler.next(options);
    }

    final method = options.method.toUpperCase();

    // Let reads fail normally so the UI can show cached data.
    if (_readOnlyMethods.contains(method)) {
      return handler.reject(
        DioException(
          requestOptions: options,
          type: DioExceptionType.connectionError,
          message: 'Device is offline',
        ),
      );
    }

    // Queue mutating requests for later sync.
    final action = PendingAction(
      id: '${DateTime.now().millisecondsSinceEpoch}_${options.path.hashCode}',
      type: options.extra['actionType'] as String? ?? 'api_call',
      endpoint: options.path,
      method: method,
      body: options.data is Map<String, dynamic>
          ? options.data as Map<String, dynamic>
          : null,
      timestamp: DateTime.now(),
    );

    _offlineService.queueAction(action);

    // Return a synthetic success so the UI can proceed optimistically.
    handler.resolve(
      Response(
        requestOptions: options,
        statusCode: 202,
        data: {'queued': true, 'action_id': action.id},
      ),
    );
  }
}
