import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_providers.dart';

/// Attendance status enum
enum AttendanceStatus {
  idle,
  loading,
  checkedIn,
  checkedOut,
  error,
}

/// Attendance state model
class AttendanceState {
  final AttendanceStatus status;
  final DateTime? checkInTime;
  final DateTime? checkOutTime;
  final double? latitude;
  final double? longitude;
  final String? errorMessage;
  final String? locationName;

  const AttendanceState({
    this.status = AttendanceStatus.idle,
    this.checkInTime,
    this.checkOutTime,
    this.latitude,
    this.longitude,
    this.errorMessage,
    this.locationName,
  });

  AttendanceState copyWith({
    AttendanceStatus? status,
    DateTime? checkInTime,
    DateTime? checkOutTime,
    double? latitude,
    double? longitude,
    String? errorMessage,
    String? locationName,
  }) {
    return AttendanceState(
      status: status ?? this.status,
      checkInTime: checkInTime ?? this.checkInTime,
      checkOutTime: checkOutTime ?? this.checkOutTime,
      latitude: latitude ?? this.latitude,
      longitude: longitude ?? this.longitude,
      errorMessage: errorMessage,
      locationName: locationName ?? this.locationName,
    );
  }

  /// Duration worked today
  Duration? get workedDuration {
    if (checkInTime == null) return null;
    final end = checkOutTime ?? DateTime.now();
    return end.difference(checkInTime!);
  }

  String get workedDurationFormatted {
    final d = workedDuration;
    if (d == null) return '--:--';
    final hours = d.inHours.toString().padLeft(2, '0');
    final minutes = (d.inMinutes % 60).toString().padLeft(2, '0');
    return '$hours:$minutes';
  }
}

class AttendanceNotifier extends StateNotifier<AttendanceState> {
  final ApiClient _apiClient;

  AttendanceNotifier({required ApiClient apiClient})
      : _apiClient = apiClient,
        super(const AttendanceState());

  /// Fetch today's attendance status from backend
  Future<void> fetchTodayStatus() async {
    state = state.copyWith(status: AttendanceStatus.loading);
    try {
      final response = await _apiClient.get('/attendance/today');
      final data = response.data as Map<String, dynamic>;

      final checkIn = data['check_in_time'] as String?;
      final checkOut = data['check_out_time'] as String?;

      state = AttendanceState(
        status: checkOut != null
            ? AttendanceStatus.checkedOut
            : checkIn != null
                ? AttendanceStatus.checkedIn
                : AttendanceStatus.idle,
        checkInTime: checkIn != null ? DateTime.parse(checkIn) : null,
        checkOutTime: checkOut != null ? DateTime.parse(checkOut) : null,
        latitude: (data['latitude'] as num?)?.toDouble(),
        longitude: (data['longitude'] as num?)?.toDouble(),
        locationName: data['location_name'] as String?,
      );
    } on ApiException catch (e) {
      // 404 means no attendance record today — that's fine
      if (e.statusCode == 404) {
        state = const AttendanceState(status: AttendanceStatus.idle);
      } else {
        state = state.copyWith(
          status: AttendanceStatus.error,
          errorMessage: e.message,
        );
      }
    } catch (e) {
      state = const AttendanceState(status: AttendanceStatus.idle);
    }
  }

  /// Verify GPS and perform check-in
  Future<void> checkIn() async {
    state = state.copyWith(status: AttendanceStatus.loading, errorMessage: null);
    try {
      final position = await _getCurrentPosition();

      final response = await _apiClient.post('/attendance/check-in', data: {
        'latitude': position.latitude,
        'longitude': position.longitude,
        'timestamp': DateTime.now().toIso8601String(),
      });

      final data = response.data as Map<String, dynamic>;

      state = AttendanceState(
        status: AttendanceStatus.checkedIn,
        checkInTime: DateTime.now(),
        latitude: position.latitude,
        longitude: position.longitude,
        locationName: data['location_name'] as String? ?? 'Verified Location',
      );
    } catch (e) {
      state = state.copyWith(
        status: AttendanceStatus.error,
        errorMessage: _extractError(e),
      );
    }
  }

  /// Verify GPS and perform check-out
  Future<void> checkOut() async {
    state = state.copyWith(status: AttendanceStatus.loading, errorMessage: null);
    try {
      final position = await _getCurrentPosition();

      await _apiClient.post('/attendance/check-out', data: {
        'latitude': position.latitude,
        'longitude': position.longitude,
        'timestamp': DateTime.now().toIso8601String(),
      });

      state = state.copyWith(
        status: AttendanceStatus.checkedOut,
        checkOutTime: DateTime.now(),
      );
    } catch (e) {
      state = state.copyWith(
        status: AttendanceStatus.error,
        errorMessage: _extractError(e),
      );
    }
  }

  /// Get current GPS position with permission handling
  Future<Position> _getCurrentPosition() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      throw Exception('Location services are disabled. Please enable GPS.');
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        throw Exception('Location permission denied.');
      }
    }
    if (permission == LocationPermission.deniedForever) {
      throw Exception(
        'Location permission permanently denied. Please enable it in Settings.',
      );
    }

    return await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 15),
      ),
    );
  }

  String _extractError(dynamic e) {
    if (e is ApiException) return e.message;
    if (e is Exception) return e.toString().replaceFirst('Exception: ', '');
    return 'Something went wrong. Please try again.';
  }
}

/// Attendance provider
final attendanceProvider =
    StateNotifierProvider<AttendanceNotifier, AttendanceState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AttendanceNotifier(apiClient: apiClient);
});
