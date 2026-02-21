import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_providers.dart';

/// Dashboard data model
class DashboardData {
  final int totalAssignments;
  final int completed;
  final int pending;
  final double todayEarnings;
  final double weeklyEarnings;
  final List<UpcomingAssignment> upcomingAssignments;

  const DashboardData({
    this.totalAssignments = 0,
    this.completed = 0,
    this.pending = 0,
    this.todayEarnings = 0,
    this.weeklyEarnings = 0,
    this.upcomingAssignments = const [],
  });

  factory DashboardData.fromJson(Map<String, dynamic> json) {
    final summary = json['summary'] as Map<String, dynamic>? ?? {};
    final earnings = json['earnings'] as Map<String, dynamic>? ?? {};
    final upcoming = json['upcoming_assignments'] as List<dynamic>? ?? [];

    return DashboardData(
      totalAssignments: (summary['total'] as num?)?.toInt() ?? 0,
      completed: (summary['completed'] as num?)?.toInt() ?? 0,
      pending: (summary['pending'] as num?)?.toInt() ?? 0,
      todayEarnings: (earnings['today'] as num?)?.toDouble() ?? 0,
      weeklyEarnings: (earnings['weekly'] as num?)?.toDouble() ?? 0,
      upcomingAssignments:
          upcoming.map((e) => UpcomingAssignment.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }
}

class UpcomingAssignment {
  final String id;
  final String patientName;
  final String scheduledTime;
  final String address;
  final String status;

  const UpcomingAssignment({
    required this.id,
    required this.patientName,
    required this.scheduledTime,
    required this.address,
    this.status = 'pending',
  });

  factory UpcomingAssignment.fromJson(Map<String, dynamic> json) {
    return UpcomingAssignment(
      id: (json['id'] ?? json['order_id'] ?? '').toString(),
      patientName: json['patient_name'] as String? ?? 'Unknown',
      scheduledTime: json['scheduled_time'] as String? ?? '',
      address: json['address'] as String? ?? '',
      status: json['status'] as String? ?? 'pending',
    );
  }
}

/// Fetches dashboard data from API
final dashboardProvider = FutureProvider.autoDispose<DashboardData>((ref) async {
  final apiClient = ref.watch(apiClientProvider);

  try {
    final response = await apiClient.get('/reports/dashboard');
    return DashboardData.fromJson(response.data as Map<String, dynamic>);
  } on ApiException {
    rethrow;
  } catch (e) {
    // Fallback: try fetching orders and build summary
    try {
      final ordersResponse = await apiClient.get('/orders', queryParameters: {
        'today': true,
        'limit': 50,
      });
      final responseData = ordersResponse.data as Map<String, dynamic>;
      final orders = responseData['results'] as List<dynamic>? ??
          responseData['orders'] as List<dynamic>? ??
          <dynamic>[];

      final int total = orders.length;
      int completed = 0;
      int pending = 0;
      double earnings = 0;
      final upcoming = <UpcomingAssignment>[];

      for (final order in orders) {
        final o = order as Map<String, dynamic>;
        final status = o['status'] as String? ?? '';
        if (status == 'completed') {
          completed++;
          earnings += (o['amount'] as num?)?.toDouble() ?? 0;
        } else if (status != 'cancelled') {
          pending++;
          if (upcoming.length < 5) {
            upcoming.add(UpcomingAssignment.fromJson(o));
          }
        }
      }

      return DashboardData(
        totalAssignments: total,
        completed: completed,
        pending: pending,
        todayEarnings: earnings,
        weeklyEarnings: 0,
        upcomingAssignments: upcoming,
      );
    } catch (_) {
      return const DashboardData();
    }
  }
});
