import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/constants/app_constants.dart';
import '../features/auth/presentation/screens/login_screen.dart';
import '../features/auth/presentation/screens/otp_screen.dart';
import '../features/dashboard/presentation/screens/dashboard_screen.dart';
import '../features/orders/presentation/screens/orders_screen.dart';
import '../features/orders/presentation/screens/order_detail_screen.dart';
import '../features/collection/presentation/screens/collection_screen.dart';
import '../features/splash/presentation/screens/splash_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: AppConstants.splashRoute,
    routes: [
      GoRoute(
        path: AppConstants.splashRoute,
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: AppConstants.loginRoute,
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: AppConstants.otpRoute,
        builder: (context, state) {
          final phone = state.extra as String? ?? '';
          return OtpScreen(phoneNumber: phone);
        },
      ),
      GoRoute(
        path: AppConstants.dashboardRoute,
        builder: (context, state) => const DashboardScreen(),
      ),
      GoRoute(
        path: AppConstants.ordersRoute,
        builder: (context, state) => const OrdersScreen(),
      ),
      GoRoute(
        path: AppConstants.orderDetailRoute,
        builder: (context, state) {
          final id = state.pathParameters['id']!;
          return OrderDetailScreen(orderId: id);
        },
      ),
      GoRoute(
        path: AppConstants.collectionRoute,
        builder: (context, state) {
          final id = state.pathParameters['id']!;
          return CollectionScreen(orderId: id);
        },
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(child: Text('Page not found: ${state.uri}')),
    ),
  );
});
