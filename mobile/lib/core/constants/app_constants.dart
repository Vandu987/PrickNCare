class AppConstants {
  // Routes
  static const String splashRoute = '/';
  static const String loginRoute = '/login';
  static const String otpRoute = '/otp';
  static const String dashboardRoute = '/dashboard';
  static const String ordersRoute = '/orders';
  static const String orderDetailRoute = '/orders/:id';
  static const String collectionRoute = '/collection/:id';
  static const String biometricRoute = '/biometric';
  static const String profileRoute = '/profile';
  static const String attendanceRoute = '/attendance';

  // Collection Status
  static const String statusPending = 'pending';
  static const String statusAccepted = 'accepted';
  static const String statusInTransit = 'in_transit';
  static const String statusArrived = 'arrived';
  static const String statusCollecting = 'collecting';
  static const String statusCompleted = 'completed';
  static const String statusCancelled = 'cancelled';

  // Hive Boxes
  static const String userBox = 'user_box';
  static const String settingsBox = 'settings_box';
  static const String cacheBox = 'cache_box';
}
