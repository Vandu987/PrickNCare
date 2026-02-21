import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_providers.dart';

// ── Models ──────────────────────────────────────────────────────────

class Order {
  final String id;
  final String bookingId;
  final String patientName;
  final String patientPhone;
  final String address;
  final double? latitude;
  final double? longitude;
  final String status;
  final String priority;
  final DateTime scheduledAt;
  final List<OrderPackage> packages;
  final String? notes;

  Order({
    required this.id,
    required this.bookingId,
    required this.patientName,
    required this.patientPhone,
    required this.address,
    this.latitude,
    this.longitude,
    required this.status,
    required this.priority,
    required this.scheduledAt,
    required this.packages,
    this.notes,
  });

  factory Order.fromJson(Map<String, dynamic> json) {
    return Order(
      id: json['id']?.toString() ?? '',
      bookingId: json['booking_id']?.toString() ?? '',
      patientName: json['patient_name'] ?? '',
      patientPhone: json['patient_phone'] ?? '',
      address: json['address'] ?? '',
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      status: json['status'] ?? 'pending',
      priority: json['priority'] ?? 'normal',
      scheduledAt: DateTime.tryParse(json['scheduled_at'] ?? '') ?? DateTime.now(),
      packages: (json['packages'] as List<dynamic>?)
              ?.map((p) => OrderPackage.fromJson(p as Map<String, dynamic>))
              .toList() ??
          [],
      notes: json['notes'],
    );
  }
}

class OrderPackage {
  final String name;
  final int testCount;

  OrderPackage({required this.name, required this.testCount});

  factory OrderPackage.fromJson(Map<String, dynamic> json) {
    return OrderPackage(
      name: json['name'] ?? '',
      testCount: json['test_count'] ?? 0,
    );
  }
}

// ── State ───────────────────────────────────────────────────────────

class OrdersState {
  final List<Order> orders;
  final bool isLoading;
  final String? error;

  const OrdersState({this.orders = const [], this.isLoading = false, this.error});

  OrdersState copyWith({List<Order>? orders, bool? isLoading, String? error}) {
    return OrdersState(
      orders: orders ?? this.orders,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }
}

// ── Notifier ────────────────────────────────────────────────────────

class OrdersNotifier extends StateNotifier<OrdersState> {
  final ApiClient _api;

  OrdersNotifier(this._api) : super(const OrdersState()) {
    fetchOrders();
  }

  Future<void> fetchOrders() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final response = await _api.get('/orders/assigned');
      final data = response.data as List<dynamic>? ?? [];
      final orders = data.map((e) => Order.fromJson(e as Map<String, dynamic>)).toList();
      state = state.copyWith(orders: orders, isLoading: false);
    } on DioException catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: ApiException.fromDioError(e).message,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<bool> updateOrderStatus(String orderId, String status, {String? reason}) async {
    try {
      await _api.put(
        '/orders/$orderId/status',
        data: {
          'status': status,
          if (reason != null) 'reason': reason,
        },
      );
      // Update local state
      state = state.copyWith(
        orders: state.orders.map((o) {
          if (o.id == orderId) {
            return Order(
              id: o.id,
              bookingId: o.bookingId,
              patientName: o.patientName,
              patientPhone: o.patientPhone,
              address: o.address,
              latitude: o.latitude,
              longitude: o.longitude,
              status: status,
              priority: o.priority,
              scheduledAt: o.scheduledAt,
              packages: o.packages,
              notes: o.notes,
            );
          }
          return o;
        }).toList(),
      );
      return true;
    } catch (_) {
      return false;
    }
  }
}

// ── Providers ───────────────────────────────────────────────────────

final ordersProvider = StateNotifierProvider<OrdersNotifier, OrdersState>((ref) {
  final api = ref.watch(apiClientProvider);
  return OrdersNotifier(api);
});

final orderDetailProvider = FutureProvider.family<Order, String>((ref, orderId) async {
  final api = ref.watch(apiClientProvider);
  final response = await api.get('/orders/$orderId');
  return Order.fromJson(response.data as Map<String, dynamic>);
});
