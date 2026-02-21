import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import 'routes.dart';

class PricknCareApp extends StatelessWidget {
  const PricknCareApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'PricknCare',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      routerConfig: AppRoutes.router,
    );
  }
}
