import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/theme/app_theme.dart';
import '../providers/location_provider.dart';

/// Full-screen Google Maps navigation showing phlebotomist → patient route.
class NavigationScreen extends ConsumerStatefulWidget {
  final double patientLat;
  final double patientLng;
  final String patientName;
  final String patientAddress;

  const NavigationScreen({
    super.key,
    required this.patientLat,
    required this.patientLng,
    required this.patientName,
    required this.patientAddress,
  });

  @override
  ConsumerState<NavigationScreen> createState() => _NavigationScreenState();
}

class _NavigationScreenState extends ConsumerState<NavigationScreen> {
  final Completer<GoogleMapController> _mapCtrl = Completer();

  @override
  Widget build(BuildContext context) {
    final locAsync = ref.watch(locationProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text('Navigate to ${widget.patientName}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.navigation),
            tooltip: 'Open in Google Maps',
            onPressed: () => _launchGoogleMaps(),
          ),
        ],
      ),
      body: locAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => _LocationError(message: e.toString()),
        data: (position) => _buildMap(position),
      ),
    );
  }

  Widget _buildMap(Position position) {
    final myLatLng = LatLng(position.latitude, position.longitude);
    final patientLatLng = LatLng(widget.patientLat, widget.patientLng);

    final markers = <Marker>{
      Marker(
        markerId: const MarkerId('phlebotomist'),
        position: myLatLng,
        icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueAzure),
        infoWindow: const InfoWindow(title: 'You'),
      ),
      Marker(
        markerId: const MarkerId('patient'),
        position: patientLatLng,
        icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueRed),
        infoWindow: InfoWindow(
          title: widget.patientName,
          snippet: widget.patientAddress,
        ),
      ),
    };

    // Simple straight-line polyline (no Directions API needed)
    final polylines = <Polyline>{
      Polyline(
        polylineId: const PolylineId('route'),
        points: [myLatLng, patientLatLng],
        color: AppColors.primary,
        width: 4,
        patterns: [PatternItem.dash(20), PatternItem.gap(10)],
      ),
    };

    // Compute distance & duration estimate
    final distKm = Geolocator.distanceBetween(
          myLatLng.latitude,
          myLatLng.longitude,
          patientLatLng.latitude,
          patientLatLng.longitude,
        ) /
        1000;
    final etaMin = (distKm / 25 * 60).ceil(); // ~25 km/h city average

    // Bounds to fit both markers
    final bounds = LatLngBounds(
      southwest: LatLng(
        min(myLatLng.latitude, patientLatLng.latitude),
        min(myLatLng.longitude, patientLatLng.longitude),
      ),
      northeast: LatLng(
        max(myLatLng.latitude, patientLatLng.latitude),
        max(myLatLng.longitude, patientLatLng.longitude),
      ),
    );

    return Stack(
      children: [
        GoogleMap(
          initialCameraPosition: CameraPosition(target: myLatLng, zoom: 14),
          markers: markers,
          polylines: polylines,
          myLocationEnabled: true,
          myLocationButtonEnabled: true,
          zoomControlsEnabled: false,
          onMapCreated: (ctrl) {
            _mapCtrl.complete(ctrl);
            // Fit bounds after map renders
            Future.delayed(const Duration(milliseconds: 300), () {
              ctrl.animateCamera(
                CameraUpdate.newLatLngBounds(bounds, 80),
              );
            });
          },
        ),
        // Bottom info bar
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          child: Container(
            color: Colors.white,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: SafeArea(
              top: false,
              child: Row(
                children: [
                  // Distance
                  _InfoChip(
                    icon: Icons.straighten,
                    label: distKm < 1
                        ? '${(distKm * 1000).round()} m'
                        : '${distKm.toStringAsFixed(1)} km',
                  ),
                  const SizedBox(width: 16),
                  // ETA
                  _InfoChip(
                    icon: Icons.timer_outlined,
                    label: etaMin < 60
                        ? '$etaMin min'
                        : '${etaMin ~/ 60}h ${etaMin % 60}m',
                  ),
                  const Spacer(),
                  // Launch turn-by-turn
                  ElevatedButton.icon(
                    onPressed: _launchGoogleMaps,
                    icon: const Icon(Icons.navigation, size: 18),
                    label: const Text('Start'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 20, vertical: 12),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _launchGoogleMaps() async {
    final uri = Uri.parse(
      'google.navigation:q=${widget.patientLat},${widget.patientLng}&mode=d',
    );
    // Fallback to web
    final webUri = Uri.parse(
      'https://www.google.com/maps/dir/?api=1'
      '&destination=${widget.patientLat},${widget.patientLng}'
      '&travelmode=driving',
    );

    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else if (await canLaunchUrl(webUri)) {
      await launchUrl(webUri, mode: LaunchMode.externalApplication);
    }
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;
  const _InfoChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 18, color: AppColors.primary),
        const SizedBox(width: 4),
        Text(label,
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(fontWeight: FontWeight.w600)),
      ],
    );
  }
}

class _LocationError extends StatelessWidget {
  final String message;
  const _LocationError({required this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.location_off, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => Geolocator.openLocationSettings(),
              child: const Text('Open Location Settings'),
            ),
          ],
        ),
      ),
    );
  }
}
