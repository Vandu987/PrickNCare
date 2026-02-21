class AppConfig {
  static const String appName = 'PricknCare';
  static const String baseUrl = 'http://localhost:8000/api/v1';
  static const String wsUrl = 'ws://localhost:8000/ws';

  // Google Maps
  static const String googleMapsApiKey = 'YOUR_GOOGLE_MAPS_API_KEY';

  // Timeouts
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);

  // Storage Keys
  static const String accessTokenKey = 'access_token';
  static const String refreshTokenKey = 'refresh_token';
  static const String userKey = 'user_data';
}
