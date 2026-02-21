import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

/// Current device position, updated in real-time.
final locationProvider =
    StateNotifierProvider<LocationNotifier, AsyncValue<Position>>((ref) {
  final notifier = LocationNotifier();
  ref.onDispose(() => notifier.dispose());
  return notifier;
});

class LocationNotifier extends StateNotifier<AsyncValue<Position>> {
  StreamSubscription<Position>? _sub;

  LocationNotifier() : super(const AsyncValue.loading()) {
    _init();
  }

  Future<void> _init() async {
    try {
      // Check & request permissions
      LocationPermission perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied ||
          perm == LocationPermission.deniedForever) {
        state = AsyncValue.error(
          'Location permission denied. Please enable location access in Settings.',
          StackTrace.current,
        );
        return;
      }

      if (!await Geolocator.isLocationServiceEnabled()) {
        state = AsyncValue.error(
          'Location services are disabled. Please enable GPS.',
          StackTrace.current,
        );
        return;
      }

      // Get initial position
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
      state = AsyncValue.data(pos);

      // Stream updates
      _sub = Geolocator.getPositionStream(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          distanceFilter: 10, // metres
        ),
      ).listen(
        (p) => state = AsyncValue.data(p),
        onError: (e) => state = AsyncValue.error(e, StackTrace.current),
      );
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
