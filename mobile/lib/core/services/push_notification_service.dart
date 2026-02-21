import 'dart:io';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../network/api_client.dart';

/// Top-level handler for background messages (must be top-level function)
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  debugPrint('[FCM] Background message: ${message.messageId}');
  // Handle background data messages here if needed
}

/// Push notification service — singleton managing FCM lifecycle
class PushNotificationService {
  final FirebaseMessaging _messaging;
  final ApiClient _apiClient;
  final SharedPreferences _prefs;

  static const String _fcmTokenKey = 'fcm_token';
  static const String _permissionRequestedKey = 'notification_permission_requested';

  PushNotificationService({
    required ApiClient apiClient,
    required SharedPreferences prefs,
    FirebaseMessaging? messaging,
  })  : _apiClient = apiClient,
        _prefs = prefs,
        _messaging = messaging ?? FirebaseMessaging.instance;

  /// Initialize FCM: request permission, get token, set up listeners
  Future<void> initialize({
    void Function(RemoteMessage)? onMessageTap,
  }) async {
    // Register background handler
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

    // Request permission (first launch or if not yet requested)
    await _requestPermission();

    // Get and register FCM token
    await _registerToken();

    // Listen for token refresh
    _messaging.onTokenRefresh.listen((newToken) {
      _sendTokenToServer(newToken);
    });

    // Foreground message handling
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debugPrint('[FCM] Foreground message: ${message.notification?.title}');
      _handleForegroundMessage(message);
    });

    // When user taps notification (app in background)
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      debugPrint('[FCM] Notification tapped: ${message.data}');
      onMessageTap?.call(message);
    });

    // Check if app was opened from terminated state via notification
    final initialMessage = await _messaging.getInitialMessage();
    if (initialMessage != null) {
      debugPrint('[FCM] App opened from notification: ${initialMessage.data}');
      onMessageTap?.call(initialMessage);
    }
  }

  /// Request notification permission
  Future<bool> _requestPermission() async {
    final settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    await _prefs.setBool(_permissionRequestedKey, true);

    final authorized = settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional;

    debugPrint('[FCM] Permission: ${settings.authorizationStatus}');
    return authorized;
  }

  /// Whether permission has been requested before
  bool get permissionRequested =>
      _prefs.getBool(_permissionRequestedKey) ?? false;

  /// Get and register FCM token
  Future<void> _registerToken() async {
    try {
      String? token;

      if (Platform.isIOS) {
        // Get APNS token first on iOS
        final apnsToken = await _messaging.getAPNSToken();
        if (apnsToken == null) {
          debugPrint('[FCM] APNS token not available yet');
          return;
        }
      }

      token = await _messaging.getToken();

      if (token != null) {
        final storedToken = _prefs.getString(_fcmTokenKey);
        if (token != storedToken) {
          await _sendTokenToServer(token);
          await _prefs.setString(_fcmTokenKey, token);
        }
        debugPrint('[FCM] Token: ${token.substring(0, 20)}...');
      }
    } catch (e) {
      debugPrint('[FCM] Token registration error: $e');
    }
  }

  /// Send FCM token to backend
  Future<void> _sendTokenToServer(String token) async {
    try {
      await _apiClient.post('/devices/register', data: {
        'fcm_token': token,
        'platform': Platform.isIOS ? 'ios' : 'android',
      });
      await _prefs.setString(_fcmTokenKey, token);
      debugPrint('[FCM] Token registered with server');
    } catch (e) {
      debugPrint('[FCM] Failed to register token: $e');
    }
  }

  /// Handle foreground messages (show local notification or in-app banner)
  void _handleForegroundMessage(RemoteMessage message) {
    final notification = message.notification;
    if (notification == null) return;

    // For foreground, you'd typically show a local notification or snackbar.
    // The actual display is handled by the UI layer listening to a stream.
    debugPrint('[FCM] Foreground: ${notification.title} - ${notification.body}');
  }

  /// Delete token (e.g., on logout)
  Future<void> deleteToken() async {
    try {
      final token = _prefs.getString(_fcmTokenKey);
      if (token != null) {
        await _apiClient.post('/devices/unregister', data: {
          'fcm_token': token,
        });
      }
      await _messaging.deleteToken();
      await _prefs.remove(_fcmTokenKey);
      debugPrint('[FCM] Token deleted');
    } catch (e) {
      debugPrint('[FCM] Token deletion error: $e');
    }
  }

  /// Get current token (for debugging)
  Future<String?> getToken() => _messaging.getToken();
}
