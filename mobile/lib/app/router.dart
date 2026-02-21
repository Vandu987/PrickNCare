import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/constants/app_constants.dart';
import '../features/auth/presentation/screens/biometric_screen.dart';
import '../features/auth/presentation/screens/login_screen.dart';
import '../features/auth/presentation/screens/otp_screen.dart';
import '../features/auth/providers/auth_provider.dart';
import '../features/dashboard/presentation/screens/dashboard_screen.dart';
import '../features/orders/presentation/screens/orders_screen.dart';
import '../features/orders/presentation/screens/order_detail_screen.dart';
import '../features/collection/presentation/screens/collection_screen.dart';
import '../features/splash/presentation/screens/splash_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authNotifier = ref.watch(authProvider.notifier);

  return GoRouter(
    initialLocation: AppConstants.splashRoute,
    redirect: (context, state) {
      final path = state.uri.path;

      // Allow splash, login, otp, biometric without auth
      const publicRoutes = [
        AppConstants.splashRoute,
        AppConstants.loginRoute,
        AppConstants.otpRoute,
        AppConstants.biometricRoute,
      ];
      if (publicRoutes.contains(path)) return null;

      // Guard: redirect to login if not authenticated
      if (!authNotifier.isAuthenticated) {
        return AppConstants.loginRoute;
      }

      return null;
    },
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
        path: AppConstants.biometricRoute,
        builder: (context, state) => const BiometricScreen(),
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
