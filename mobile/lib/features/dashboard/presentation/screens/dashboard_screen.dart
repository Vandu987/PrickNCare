import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_theme.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('PricknCare'),
        actions: [
          IconButton(
            icon: const Icon(Icons.person),
            onPressed: () => context.push(AppConstants.profileRoute),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Welcome back!', style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 24),
            Row(
              children: [
                _StatCard(title: 'Today\'s Orders', value: '0', icon: Icons.assignment, color: AppColors.primary),
                const SizedBox(width: 12),
                _StatCard(title: 'Completed', value: '0', icon: Icons.check_circle, color: AppColors.success),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                _StatCard(title: 'Pending', value: '0', icon: Icons.pending_actions, color: AppColors.warning),
                const SizedBox(width: 12),
                _StatCard(title: 'In Transit', value: '0', icon: Icons.directions_car, color: AppColors.info),
              ],
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => context.push(AppConstants.ordersRoute),
              icon: const Icon(Icons.list),
              label: const Text('View All Orders'),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;

  const _StatCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Icon(icon, size: 32, color: color),
              const SizedBox(height: 8),
              Text(value, style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: color)),
              const SizedBox(height: 4),
              Text(title, style: Theme.of(context).textTheme.bodyMedium, textAlign: TextAlign.center),
            ],
          ),
        ),
      ),
    );
  }
}
