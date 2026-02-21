import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prickncare_mobile/app/app.dart';
import 'package:prickncare_mobile/core/di/injection.dart';
import 'package:prickncare_mobile/presentation/screens/splash_screen.dart';

void main() {
  setUpAll(() async {
    await configureDependencies();
  });

  testWidgets('PricknCare app smoke test - renders splash screen',
      (WidgetTester tester) async {
    await tester.pumpWidget(const PricknCareApp());

    // Splash screen should be displayed initially
    expect(find.byType(SplashScreen), findsOneWidget);
    expect(find.text('PricknCare'), findsOneWidget);

    // Advance past the 2-second splash delay so no pending timers remain
    await tester.pump(const Duration(seconds: 3));
  });
}
