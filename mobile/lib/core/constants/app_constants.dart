class AppConstants {
  // API
  static const String baseUrl = 'http://localhost:8000/api/v1';
  static const int connectTimeout = 30000;
  static const int receiveTimeout = 30000;

  // Storage keys
  static const String accessTokenKey = 'access_token';
  static const String refreshTokenKey = 'refresh_token';
  static const String userDataKey = 'user_data';

  // Order statuses
  static const String statusPending = 'pending';
  static const String statusAssigned = 'assigned';
  static const String statusInTransit = 'in_transit';
  static const String statusCollected = 'collected';
  static const String statusDelivered = 'delivered';
  static const String statusCancelled = 'cancelled';
}
