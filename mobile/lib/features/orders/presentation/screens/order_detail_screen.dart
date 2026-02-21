import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../../shared/widgets/loading_widget.dart';
import '../../../../shared/widgets/error_widget.dart';
import '../../providers/order_provider.dart';

class OrderDetailScreen extends ConsumerWidget {
  final String orderId;
  const OrderDetailScreen({super.key, required this.orderId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(orderDetailProvider(orderId));

    return Scaffold(
      appBar: AppBar(title: Text('Order #$orderId')),
      body: detail.when(
        loading: () => const LoadingWidget(message: 'Loading order…'),
        error: (e, _) => AppErrorWidget(
          message: e.toString(),
          onRetry: () => ref.invalidate(orderDetailProvider(orderId)),
        ),
        data: (order) => _OrderDetailBody(order: order),
      ),
    );
  }
}

class _OrderDetailBody extends ConsumerWidget {
  final Order order;
  const _OrderDetailBody({required this.order});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final timeStr = DateFormat('dd MMM yyyy, hh:mm a').format(order.scheduledAt);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Status & Priority header
          Row(
            children: [
              _buildStatusChip(order.status),
              const SizedBox(width: 8),
              if (order.priority == 'urgent')
                Chip(
                  label: const Text('URGENT', style: TextStyle(color: Colors.white, fontSize: 11)),
                  backgroundColor: AppColors.error,
                  padding: EdgeInsets.zero,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              const Spacer(),
              Text('#${order.bookingId}',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(color: AppColors.primary)),
            ],
          ),
          const SizedBox(height: 20),

          // Patient Info
          _SectionCard(
            title: 'Patient Information',
            icon: Icons.person,
            children: [
              _InfoRow(label: 'Name', value: order.patientName),
              _InfoRow(label: 'Phone', value: order.patientPhone),
              _InfoRow(label: 'Scheduled', value: timeStr),
            ],
          ),
          const SizedBox(height: 12),

          // Address
          _SectionCard(
            title: 'Address',
            icon: Icons.location_on,
            children: [
              Text(order.address, style: Theme.of(context).textTheme.bodyLarge),
              if (order.latitude != null && order.longitude != null) ...[
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _openMap(order.latitude!, order.longitude!),
                        icon: const Icon(Icons.map),
                        label: const Text('Open in Maps'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () => context.push(
                          AppConstants.navigationRoute,
                          extra: {
                            'lat': order.latitude!,
                            'lng': order.longitude!,
                            'name': order.patientName,
                            'address': order.address,
                          },
                        ),
                        icon: const Icon(Icons.navigation, size: 18),
                        label: const Text('Navigate'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          foregroundColor: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
          const SizedBox(height: 12),

          // Packages
          _SectionCard(
            title: 'Packages (${order.packages.length})',
            icon: Icons.science_outlined,
            children: [
              for (final pkg in order.packages)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    children: [
                      const Icon(Icons.check_circle_outline, size: 18, color: AppColors.success),
                      const SizedBox(width: 8),
                      Expanded(child: Text(pkg.name)),
                      Text('${pkg.testCount} tests',
                          style: Theme.of(context).textTheme.bodyMedium),
                    ],
                  ),
                ),
            ],
          ),

          // Notes
          if (order.notes != null && order.notes!.isNotEmpty) ...[
            const SizedBox(height: 12),
            _SectionCard(
              title: 'Notes',
              icon: Icons.note_outlined,
              children: [Text(order.notes!)],
            ),
          ],

          const SizedBox(height: 20),

          // Actions for pending orders
          if (order.status == 'pending') ...[
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _rejectOrder(context, ref),
                    icon: const Icon(Icons.close),
                    label: const Text('Reject'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.error,
                      side: const BorderSide(color: AppColors.error),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _acceptOrder(context, ref),
                    icon: const Icon(Icons.check),
                    label: const Text('Accept'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.success,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildStatusChip(String status) {
    final (Color bg, Color fg) = switch (status) {
      'pending' => (AppColors.warning, Colors.black87),
      'accepted' => (AppColors.info, Colors.white),
      'completed' => (AppColors.success, Colors.white),
      'rejected' => (AppColors.error, Colors.white),
      _ => (AppColors.secondary, Colors.white),
    };
    return Chip(
      label: Text(status[0].toUpperCase() + status.substring(1),
          style: TextStyle(color: fg, fontWeight: FontWeight.w600, fontSize: 12)),
      backgroundColor: bg,
      padding: EdgeInsets.zero,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
    );
  }

  Future<void> _openMap(double lat, double lng) async {
    final uri = Uri.parse('https://www.google.com/maps/search/?api=1&query=$lat,$lng');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  void _acceptOrder(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Accept Order'),
        content: Text('Accept order #${order.bookingId}?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.success),
            onPressed: () async {
              Navigator.pop(ctx);
              final ok = await ref.read(ordersProvider.notifier).updateOrderStatus(order.id, 'accepted');
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(ok ? 'Order accepted' : 'Failed to accept')),
                );
                if (ok) ref.invalidate(orderDetailProvider(order.id));
              }
            },
            child: const Text('Accept'),
          ),
        ],
      ),
    );
  }

  void _rejectOrder(BuildContext context, WidgetRef ref) {
    final reasonCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Reject Order'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Reject order #${order.bookingId}?'),
            const SizedBox(height: 12),
            TextField(
              controller: reasonCtrl,
              maxLines: 3,
              decoration: const InputDecoration(
                hintText: 'Reason for rejection (required)',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
            onPressed: () async {
              final reason = reasonCtrl.text.trim();
              if (reason.isEmpty) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Please enter a reason')),
                );
                return;
              }
              Navigator.pop(ctx);
              final ok = await ref
                  .read(ordersProvider.notifier)
                  .updateOrderStatus(order.id, 'rejected', reason: reason);
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(ok ? 'Order rejected' : 'Failed to reject')),
                );
                if (ok) ref.invalidate(orderDetailProvider(order.id));
              }
            },
            child: const Text('Reject'),
          ),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<Widget> children;
  const _SectionCard({required this.title, required this.icon, required this.children});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 20, color: AppColors.primary),
                const SizedBox(width: 8),
                Text(title, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontSize: 15)),
              ],
            ),
            const Divider(height: 20),
            ...children,
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 90,
            child: Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ),
          Expanded(child: Text(value, style: Theme.of(context).textTheme.bodyLarge)),
        ],
      ),
    );
  }
}
