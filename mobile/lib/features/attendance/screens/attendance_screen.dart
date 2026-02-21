import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/attendance_provider.dart';

class AttendanceScreen extends ConsumerStatefulWidget {
  const AttendanceScreen({super.key});

  @override
  ConsumerState<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends ConsumerState<AttendanceScreen> {
  @override
  void initState() {
    super.initState();
    // Fetch today's attendance on screen load
    Future.microtask(() {
      ref.read(attendanceProvider.notifier).fetchTodayStatus();
    });
  }

  @override
  Widget build(BuildContext context) {
    final attendance = ref.watch(attendanceProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Attendance'),
        centerTitle: true,
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(attendanceProvider.notifier).fetchTodayStatus(),
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // Status card
            _buildStatusCard(attendance),
            const SizedBox(height: 24),

            // Time info
            if (attendance.checkInTime != null) ...[
              _buildTimeRow(
                icon: Icons.login_rounded,
                label: 'Check-in',
                time: attendance.checkInTime!,
                color: AppColors.success,
              ),
              const SizedBox(height: 12),
            ],
            if (attendance.checkOutTime != null) ...[
              _buildTimeRow(
                icon: Icons.logout_rounded,
                label: 'Check-out',
                time: attendance.checkOutTime!,
                color: AppColors.error,
              ),
              const SizedBox(height: 12),
            ],

            // Duration
            if (attendance.checkInTime != null) ...[
              const SizedBox(height: 8),
              _buildDurationCard(attendance),
              const SizedBox(height: 24),
            ],

            // Location info
            if (attendance.locationName != null) ...[
              _buildInfoTile(
                Icons.location_on_rounded,
                'Location',
                attendance.locationName!,
              ),
              const SizedBox(height: 24),
            ],

            // Error message
            if (attendance.errorMessage != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.error.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: AppColors.error, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        attendance.errorMessage!,
                        style: const TextStyle(color: AppColors.error, fontSize: 14),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
            ],

            // Action button
            _buildActionButton(attendance),

            // End-of-day summary
            if (attendance.status == AttendanceStatus.checkedOut) ...[
              const SizedBox(height: 32),
              _buildSummaryCard(attendance),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildStatusCard(AttendanceState attendance) {
    final (icon, label, color) = switch (attendance.status) {
      AttendanceStatus.idle => (Icons.circle_outlined, 'Not Checked In', AppColors.secondary),
      AttendanceStatus.loading => (Icons.sync_rounded, 'Processing...', AppColors.info),
      AttendanceStatus.checkedIn => (Icons.check_circle, 'Checked In', AppColors.success),
      AttendanceStatus.checkedOut => (Icons.task_alt_rounded, 'Day Complete', AppColors.primary),
      AttendanceStatus.error => (Icons.error_outline, 'Error', AppColors.error),
    };

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      color: color.withValues(alpha: 0.1),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 24),
        child: Column(
          children: [
            Icon(icon, size: 64, color: color),
            const SizedBox(height: 16),
            Text(
              label,
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _formattedDate(DateTime.now()),
              style: const TextStyle(color: AppColors.textSecondary, fontSize: 14),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimeRow({
    required IconData icon,
    required String label,
    required DateTime time,
    required Color color,
  }) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, color: color, size: 22),
        ),
        const SizedBox(width: 14),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
            Text(
              _formattedTime(time),
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildDurationCard(AttendanceState attendance) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(Icons.timer_outlined, color: AppColors.primary),
            const SizedBox(width: 12),
            const Text('Hours Worked', style: TextStyle(fontSize: 15)),
            const Spacer(),
            Text(
              attendance.workedDurationFormatted,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: AppColors.primary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoTile(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(icon, color: AppColors.primary, size: 20),
        const SizedBox(width: 8),
        Text('$label: ', style: const TextStyle(color: AppColors.textSecondary)),
        Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w500))),
      ],
    );
  }

  Widget _buildActionButton(AttendanceState attendance) {
    if (attendance.status == AttendanceStatus.checkedOut) {
      return const SizedBox.shrink();
    }

    final isCheckIn = attendance.status != AttendanceStatus.checkedIn;
    final isLoading = attendance.status == AttendanceStatus.loading;

    return SizedBox(
      width: double.infinity,
      height: 54,
      child: ElevatedButton.icon(
        onPressed: isLoading
            ? null
            : () {
                if (isCheckIn) {
                  ref.read(attendanceProvider.notifier).checkIn();
                } else {
                  _showCheckOutConfirmation();
                }
              },
        icon: isLoading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
              )
            : Icon(isCheckIn ? Icons.login_rounded : Icons.logout_rounded),
        label: Text(
          isLoading
              ? 'Verifying Location...'
              : isCheckIn
                  ? 'Check In'
                  : 'Check Out',
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor: isCheckIn ? AppColors.success : AppColors.error,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        ),
      ),
    );
  }

  Widget _buildSummaryCard(AttendanceState attendance) {
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      color: AppColors.primary.withValues(alpha: 0.05),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.summarize_rounded, color: AppColors.primary),
                SizedBox(width: 8),
                Text(
                  'End of Day Summary',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                    color: AppColors.primary,
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            _summaryRow('Check-in', _formattedTime(attendance.checkInTime!)),
            _summaryRow('Check-out', _formattedTime(attendance.checkOutTime!)),
            _summaryRow('Total Hours', attendance.workedDurationFormatted),
            if (attendance.locationName != null)
              _summaryRow('Location', attendance.locationName!),
          ],
        ),
      ),
    );
  }

  Widget _summaryRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: AppColors.textSecondary)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  void _showCheckOutConfirmation() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Check Out'),
        content: const Text('Are you sure you want to check out for today?'),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              ref.read(attendanceProvider.notifier).checkOut();
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.error),
            child: const Text('Check Out', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  String _formattedTime(DateTime dt) {
    final hour = dt.hour > 12 ? dt.hour - 12 : dt.hour == 0 ? 12 : dt.hour;
    final period = dt.hour >= 12 ? 'PM' : 'AM';
    return '${hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')} $period';
  }

  String _formattedDate(DateTime dt) {
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ];
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return '${days[dt.weekday - 1]}, ${dt.day} ${months[dt.month - 1]} ${dt.year}';
  }
}
