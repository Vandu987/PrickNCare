import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/app_config.dart';
import '../services/offline_service.dart';
import 'offline_interceptor.dart';

class ApiClient {
  late final Dio _dio;

  ApiClient({required SharedPreferences prefs, OfflineService? offlineService}) {
    _dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.baseUrl,
        connectTimeout: AppConfig.connectTimeout,
        receiveTimeout: AppConfig.receiveTimeout,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // Auth Interceptor
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final token = prefs.getString(AppConfig.accessTokenKey);
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401) {
            // Try refresh token
            final refreshToken = prefs.getString(AppConfig.refreshTokenKey);
            if (refreshToken != null) {
              try {
                final response = await Dio().post(
                  '${AppConfig.baseUrl}/auth/refresh',
                  data: {'refresh_token': refreshToken},
                );
                final newToken = response.data['access_token'] as String;
                await prefs.setString(AppConfig.accessTokenKey, newToken);

                // Retry original request
                error.requestOptions.headers['Authorization'] = 'Bearer $newToken';
                final retryResponse = await _dio.fetch(error.requestOptions);
                return handler.resolve(retryResponse);
              } catch (_) {
                // Refresh failed - clear tokens
                await prefs.remove(AppConfig.accessTokenKey);
                await prefs.remove(AppConfig.refreshTokenKey);
              }
            }
          }
          return handler.next(error);
        },
      ),
    );

    // Offline interceptor — queues mutating requests when offline
    if (offlineService != null) {
      _dio.interceptors.add(OfflineInterceptor(offlineService));
    }

    // Logging in debug mode
    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      logPrint: (obj) => print('[API] $obj'),
    ));
  }

  // GET
  Future<Response> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) =>
      _dio.get(path, queryParameters: queryParameters, options: options);

  // POST
  Future<Response> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    Options? options,
  }) =>
      _dio.post(path, data: data, queryParameters: queryParameters, options: options);

  // PUT
  Future<Response> put(
    String path, {
    dynamic data,
    Options? options,
  }) =>
      _dio.put(path, data: data, options: options);

  // PATCH
  Future<Response> patch(
    String path, {
    dynamic data,
    Options? options,
  }) =>
      _dio.patch(path, data: data, options: options);

  // DELETE
  Future<Response> delete(
    String path, {
    Options? options,
  }) =>
      _dio.delete(path, options: options);

  // Multipart upload
  Future<Response> upload(
    String path, {
    required FormData formData,
    void Function(int, int)? onSendProgress,
  }) =>
      _dio.post(path, data: formData, onSendProgress: onSendProgress);
}

/// ApiException for structured error handling
class ApiException implements Exception {
  final String message;
  final int? statusCode;
  final dynamic data;

  ApiException({required this.message, this.statusCode, this.data});

  factory ApiException.fromDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return ApiException(message: 'Connection timeout. Please try again.');
      case DioExceptionType.connectionError:
        return ApiException(message: 'No internet connection.');
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        final data = error.response?.data;
        String message = 'Something went wrong';
        if (data is Map && data.containsKey('detail')) {
          message = data['detail'].toString();
        }
        return ApiException(message: message, statusCode: statusCode, data: data);
      default:
        return ApiException(message: 'Unexpected error occurred.');
    }
  }

  @override
  String toString() => message;
}
