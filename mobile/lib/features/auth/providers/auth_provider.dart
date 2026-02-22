import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/config/app_config.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_providers.dart';

/// Auth state
enum AuthStatus { initial, loading, authenticated, unauthenticated, otpSent, error }

class AuthState {
  final AuthStatus status;
  final String? errorMessage;
  final String? phoneNumber;
  final bool biometricAvailable;

  const AuthState({
    this.status = AuthStatus.initial,
    this.errorMessage,
    this.phoneNumber,
    this.biometricAvailable = false,
  });

  AuthState copyWith({
    AuthStatus? status,
    String? errorMessage,
    String? phoneNumber,
    bool? biometricAvailable,
  }) {
    return AuthState(
      status: status ?? this.status,
      errorMessage: errorMessage,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      biometricAvailable: biometricAvailable ?? this.biometricAvailable,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final ApiClient _apiClient;
  final SharedPreferences _prefs;
  final LocalAuthentication _localAuth;

  AuthNotifier({
    required ApiClient apiClient,
    required SharedPreferences prefs,
    LocalAuthentication? localAuth,
  })  : _apiClient = apiClient,
        _prefs = prefs,
        _localAuth = localAuth ?? LocalAuthentication(),
        super(const AuthState());

  /// Check if user is already logged in
  Future<void> checkAuthStatus() async {
    final token = _prefs.getString(AppConfig.accessTokenKey);
    if (token != null) {
      // Check biometric availability
      final biometricAvailable = await _isBiometricAvailable();
      state = state.copyWith(
        status: AuthStatus.authenticated,
        biometricAvailable: biometricAvailable,
      );
    } else {
      state = state.copyWith(status: AuthStatus.unauthenticated);
    }
  }

  /// Request OTP for phone number
  Future<void> requestOtp(String phoneNumber) async {
    state = state.copyWith(status: AuthStatus.loading, errorMessage: null);
    try {
      await _apiClient.post('/auth/otp/request', data: {
        'phone_number': '+91$phoneNumber',
      });
      state = state.copyWith(
        status: AuthStatus.otpSent,
        phoneNumber: phoneNumber,
      );
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.error,
        errorMessage: _extractError(e),
      );
    }
  }

  /// Verify OTP and store tokens
  Future<bool> verifyOtp(String phoneNumber, String otp) async {
    state = state.copyWith(status: AuthStatus.loading, errorMessage: null);
    try {
      final response = await _apiClient.post('/auth/otp/verify', data: {
        'phone_number': '+91$phoneNumber',
        'otp': otp,
      });

      final data = response.data as Map<String, dynamic>;
      final accessToken = data['access_token'] as String;
      final refreshToken = data['refresh_token'] as String?;

      await _prefs.setString(AppConfig.accessTokenKey, accessToken);
      if (refreshToken != null) {
        await _prefs.setString(AppConfig.refreshTokenKey, refreshToken);
      }
      // Store phone for biometric re-auth context
      await _prefs.setString('auth_phone', phoneNumber);
      // Mark biometric eligible
      await _prefs.setBool('biometric_eligible', true);

      state = state.copyWith(status: AuthStatus.authenticated);
      return true;
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.error,
        errorMessage: _extractError(e),
      );
      return false;
    }
  }

  /// Authenticate with biometrics
  Future<bool> authenticateWithBiometrics() async {
    try {
      final authenticated = await _localAuth.authenticate(
        localizedReason: 'Authenticate to access PricknCare',
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: true,
        ),
      );
      if (authenticated) {
        state = state.copyWith(status: AuthStatus.authenticated);
      }
      return authenticated;
    } catch (e) {
      return false;
    }
  }

  /// Check if biometrics are available
  Future<bool> _isBiometricAvailable() async {
    try {
      final canCheck = await _localAuth.canCheckBiometrics;
      final isSupported = await _localAuth.isDeviceSupported();
      return canCheck && isSupported;
    } catch (_) {
      return false;
    }
  }

  /// Check if user should see biometric screen
  Future<bool> shouldShowBiometric() async {
    final eligible = _prefs.getBool('biometric_eligible') ?? false;
    if (!eligible) return false;
    return await _isBiometricAvailable();
  }

  /// Logout
  Future<void> logout() async {
    await _prefs.remove(AppConfig.accessTokenKey);
    await _prefs.remove(AppConfig.refreshTokenKey);
    await _prefs.remove('biometric_eligible');
    await _prefs.remove('auth_phone');
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  /// Check if token exists (for router guard)
  bool get isAuthenticated =>
      _prefs.getString(AppConfig.accessTokenKey) != null;

  String _extractError(dynamic e) {
    if (e is ApiException) return e.message;
    return 'Something went wrong. Please try again.';
  }
}

/// Auth provider
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  final prefs = ref.watch(sharedPreferencesProvider);
  return AuthNotifier(apiClient: apiClient, prefs: prefs);
});
