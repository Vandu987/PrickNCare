import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:signature/signature.dart';

import '../../../../core/theme/app_theme.dart';
import '../../providers/collection_provider.dart';
import '../../../orders/providers/order_provider.dart';

class CollectionScreen extends ConsumerStatefulWidget {
  final String orderId;
  const CollectionScreen({super.key, required this.orderId});

  @override
  ConsumerState<CollectionScreen> createState() => _CollectionScreenState();
}

class _CollectionScreenState extends ConsumerState<CollectionScreen> {
  late final SignatureController _signatureController;
  final _paymentAmountController = TextEditingController();
  final _transactionIdController = TextEditingController();
  PaymentMode _selectedPaymentMode = PaymentMode.cash;

  static const _vialTypes = [
    'EDTA (Purple)',
    'Serum (Red)',
    'Citrate (Blue)',
    'Fluoride (Grey)',
    'Heparin (Green)',
    'Plain',
  ];

  static const _stepTitles = [
    'Verify Patient',
    'Sample Photo',
    'Vial Details',
    'Signature',
    'Payment',
    'Confirm & Submit',
  ];

  @override
  void initState() {
    super.initState();
    _signatureController = SignatureController(
      penStrokeWidth: 3,
      penColor: Colors.black,
      exportBackgroundColor: Colors.white,
    );
  }

  @override
  void dispose() {
    _signatureController.dispose();
    _paymentAmountController.dispose();
    _transactionIdController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(collectionProvider(widget.orderId));
    final notifier = ref.read(collectionProvider(widget.orderId).notifier);
    final orderAsync = ref.watch(orderDetailProvider(widget.orderId));

    if (state.isComplete) {
      return _buildSuccessScreen(state);
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Collection'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(60),
          child: _buildStepIndicator(state.currentStep),
        ),
      ),
      body: orderAsync.when(
        data: (order) => Column(
          children: [
            // Patient info bar
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              color: AppColors.primary.withOpacity(0.05),
              child: Text(
                '${order.patientName} • ${order.patientPhone}',
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
            // Step content
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: _buildStepContent(state, notifier, order),
              ),
            ),
            // Error banner
            if (state.error != null)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                color: AppColors.error.withOpacity(0.1),
                child: Text(
                  state.error!,
                  style: const TextStyle(color: AppColors.error),
                  textAlign: TextAlign.center,
                ),
              ),
            // Navigation buttons
            _buildBottomBar(state, notifier),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error loading order: $e')),
      ),
    );
  }

  Widget _buildStepIndicator(int currentStep) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: List.generate(_stepTitles.length, (i) {
          final isActive = i == currentStep;
          final isDone = i < currentStep;
          return Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircleAvatar(
                  radius: 14,
                  backgroundColor: isDone
                      ? AppColors.success
                      : isActive
                          ? Colors.white
                          : Colors.white.withOpacity(0.3),
                  child: isDone
                      ? const Icon(Icons.check, size: 16, color: Colors.white)
                      : Text(
                          '${i + 1}',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: isActive
                                ? AppColors.primary
                                : AppColors.textLight,
                          ),
                        ),
                ),
                const SizedBox(height: 2),
                Text(
                  _stepTitles[i],
                  style: TextStyle(
                    fontSize: 9,
                    color: isActive ? Colors.white : Colors.white70,
                  ),
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          );
        }),
      ),
    );
  }

  Widget _buildStepContent(
      CollectionState state, CollectionNotifier notifier, Order order) {
    switch (state.currentStep) {
      case 0:
        return _buildVerifyStep(state, notifier, order);
      case 1:
        return _buildPhotoStep(state, notifier);
      case 2:
        return _buildVialStep(state, notifier);
      case 3:
        return _buildSignatureStep(state, notifier);
      case 4:
        return _buildPaymentStep(state, notifier);
      case 5:
        return _buildConfirmStep(state, order);
      default:
        return const SizedBox.shrink();
    }
  }

  // ── Step 1: Verify Patient ──────────────────────────────────────

  Widget _buildVerifyStep(
      CollectionState state, CollectionNotifier notifier, Order order) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Verify Patient Identity',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 24),
        _infoCard('Patient Name', order.patientName, Icons.person),
        const SizedBox(height: 12),
        _infoCard('Phone', order.patientPhone, Icons.phone),
        const SizedBox(height: 12),
        _infoCard('Address', order.address, Icons.location_on),
        if (order.packages.isNotEmpty) ...[
          const SizedBox(height: 12),
          _infoCard(
            'Packages',
            order.packages.map((p) => p.name).join(', '),
            Icons.medical_services,
          ),
        ],
        const SizedBox(height: 24),
        CheckboxListTile(
          value: state.patientVerified,
          onChanged: (v) => notifier.verifyPatient(v ?? false),
          title: const Text(
            'I confirm the patient identity matches the order details',
            style: TextStyle(fontWeight: FontWeight.w500),
          ),
          controlAffinity: ListTileControlAffinity.leading,
          activeColor: AppColors.primary,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: AppColors.primary.withOpacity(0.3)),
          ),
        ),
      ],
    );
  }

  Widget _infoCard(String label, String value, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Row(
        children: [
          Icon(icon, color: AppColors.primary, size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label,
                    style: const TextStyle(
                        fontSize: 12, color: AppColors.textSecondary)),
                const SizedBox(height: 2),
                Text(value,
                    style: const TextStyle(
                        fontSize: 15, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ── Step 2: Sample Photo ────────────────────────────────────────

  Widget _buildPhotoStep(CollectionState state, CollectionNotifier notifier) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Capture Sample Photo',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        const Text(
          'Take a clear photo of the collected sample tubes.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 24),
        if (state.samplePhoto != null) ...[
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.file(
              state.samplePhoto!,
              height: 300,
              width: double.infinity,
              fit: BoxFit.cover,
            ),
          ),
          const SizedBox(height: 16),
        ],
        Row(
          children: [
            Expanded(
              child: _actionButton(
                icon: Icons.camera_alt,
                label: 'Camera',
                onTap: () => _pickImage(ImageSource.camera, notifier),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _actionButton(
                icon: Icons.photo_library,
                label: 'Gallery',
                onTap: () => _pickImage(ImageSource.gallery, notifier),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _pickImage(ImageSource source, CollectionNotifier notifier) async {
    final picker = ImagePicker();
    final image = await picker.pickImage(
      source: source,
      maxWidth: 1200,
      maxHeight: 1200,
      imageQuality: 85,
    );
    if (image != null) {
      notifier.setSamplePhoto(File(image.path));
    }
  }

  Widget _actionButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 24),
        decoration: BoxDecoration(
          border: Border.all(color: AppColors.primary.withOpacity(0.3)),
          borderRadius: BorderRadius.circular(12),
          color: AppColors.primary.withOpacity(0.03),
        ),
        child: Column(
          children: [
            Icon(icon, size: 36, color: AppColors.primary),
            const SizedBox(height: 8),
            Text(label,
                style: const TextStyle(
                    fontWeight: FontWeight.w600, color: AppColors.primary)),
          ],
        ),
      ),
    );
  }

  // ── Step 3: Vial Details ────────────────────────────────────────

  Widget _buildVialStep(CollectionState state, CollectionNotifier notifier) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Record Vial Details',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        const Text(
          'Select vial types and quantities collected.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: _vialTypes.map((type) {
            final exists = state.vials.any((v) => v.type == type);
            return FilterChip(
              label: Text(type),
              selected: exists,
              onSelected: (_) {
                if (!exists) notifier.addVial(type);
              },
              selectedColor: AppColors.primary.withOpacity(0.15),
              checkmarkColor: AppColors.primary,
            );
          }).toList(),
        ),
        const SizedBox(height: 20),
        if (state.vials.isNotEmpty)
          ...state.vials.asMap().entries.map((entry) {
            final i = entry.key;
            final vial = entry.value;
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                title: Text(vial.type,
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.remove_circle_outline),
                      onPressed: vial.quantity > 1
                          ? () => notifier.updateVialQuantity(i, vial.quantity - 1)
                          : null,
                      color: AppColors.error,
                    ),
                    Text('${vial.quantity}',
                        style: const TextStyle(
                            fontSize: 18, fontWeight: FontWeight.bold)),
                    IconButton(
                      icon: const Icon(Icons.add_circle_outline),
                      onPressed: () =>
                          notifier.updateVialQuantity(i, vial.quantity + 1),
                      color: AppColors.primary,
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline),
                      onPressed: () => notifier.removeVial(i),
                      color: AppColors.error,
                    ),
                  ],
                ),
              ),
            );
          }),
      ],
    );
  }

  // ── Step 4: Signature ───────────────────────────────────────────

  Widget _buildSignatureStep(
      CollectionState state, CollectionNotifier notifier) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Patient Signature',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        const Text(
          'Ask the patient to sign below to confirm sample collection.',
          style: TextStyle(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 16),
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.primary.withOpacity(0.3), width: 2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: Signature(
              controller: _signatureController,
              height: 250,
              backgroundColor: Colors.white,
            ),
          ),
        ),
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextButton.icon(
              onPressed: () {
                _signatureController.clear();
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Clear'),
            ),
            const SizedBox(width: 16),
            ElevatedButton.icon(
              onPressed: () async {
                if (_signatureController.isNotEmpty) {
                  final bytes = await _signatureController.toPngBytes();
                  if (bytes != null) {
                    notifier.setSignature(bytes);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Signature captured'),
                          backgroundColor: AppColors.success,
                          duration: Duration(seconds: 1),
                        ),
                      );
                    }
                  }
                }
              },
              icon: const Icon(Icons.check),
              label: const Text('Confirm Signature'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.primary,
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
        if (state.signatureBytes != null) ...[
          const SizedBox(height: 16),
          const Center(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.check_circle, color: AppColors.success, size: 20),
                SizedBox(width: 6),
                Text('Signature captured',
                    style: TextStyle(
                        color: AppColors.success, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
        ],
      ],
    );
  }

  // ── Step 5: Payment ─────────────────────────────────────────────

  Widget _buildPaymentStep(
      CollectionState state, CollectionNotifier notifier) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Record Payment',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _paymentAmountController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(
            labelText: 'Amount (₹)',
            prefixIcon: const Icon(Icons.currency_rupee),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
          ),
        ),
        const SizedBox(height: 20),
        const Text('Payment Mode',
            style: TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
        const SizedBox(height: 8),
        ...PaymentMode.values.map((mode) {
          final icons = {
            PaymentMode.cash: Icons.money,
            PaymentMode.upi: Icons.qr_code,
            PaymentMode.card: Icons.credit_card,
          };
          return RadioListTile<PaymentMode>(
            value: mode,
            groupValue: _selectedPaymentMode,
            onChanged: (v) => setState(() => _selectedPaymentMode = v!),
            title: Text(mode.name.toUpperCase()),
            secondary: Icon(icons[mode], color: AppColors.primary),
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8)),
          );
        }),
        if (_selectedPaymentMode != PaymentMode.cash) ...[
          const SizedBox(height: 12),
          TextField(
            controller: _transactionIdController,
            decoration: InputDecoration(
              labelText: 'Transaction ID (optional)',
              prefixIcon: const Icon(Icons.receipt_long),
              border:
                  OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ],
        const SizedBox(height: 20),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: () {
              final amount =
                  double.tryParse(_paymentAmountController.text.trim());
              if (amount == null || amount <= 0) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Enter a valid amount'),
                    backgroundColor: AppColors.error,
                  ),
                );
                return;
              }
              notifier.setPayment(PaymentInfo(
                amount: amount,
                mode: _selectedPaymentMode,
                transactionId: _transactionIdController.text.trim().isNotEmpty
                    ? _transactionIdController.text.trim()
                    : null,
              ));
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Payment recorded'),
                  backgroundColor: AppColors.success,
                  duration: Duration(seconds: 1),
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.primary,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
            ),
            child: const Text('Save Payment', style: TextStyle(fontSize: 16)),
          ),
        ),
        if (state.payment != null) ...[
          const SizedBox(height: 12),
          const Center(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.check_circle, color: AppColors.success, size: 20),
                SizedBox(width: 6),
                Text('Payment saved',
                    style: TextStyle(
                        color: AppColors.success, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
        ],
      ],
    );
  }

  // ── Step 6: Confirm & Submit ────────────────────────────────────

  Widget _buildConfirmStep(CollectionState state, Order order) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Review & Confirm',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 16),
        _summaryTile(Icons.person, 'Patient', order.patientName),
        _summaryTile(Icons.verified, 'Identity Verified',
            state.patientVerified ? 'Yes' : 'No'),
        _summaryTile(Icons.camera_alt, 'Sample Photo',
            state.samplePhoto != null ? 'Captured' : 'Missing'),
        _summaryTile(
          Icons.science,
          'Vials',
          state.vials.map((v) => '${v.type} ×${v.quantity}').join(', '),
        ),
        _summaryTile(Icons.draw, 'Signature',
            state.signatureBytes != null ? 'Captured' : 'Missing'),
        if (state.payment != null) ...[
          _summaryTile(Icons.payment, 'Payment',
              '₹${state.payment!.amount.toStringAsFixed(2)} (${state.payment!.mode.name.toUpperCase()})'),
          if (state.payment!.transactionId != null)
            _summaryTile(
                Icons.receipt, 'Txn ID', state.payment!.transactionId!),
        ],
        const SizedBox(height: 8),
        if (state.samplePhoto != null)
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.file(state.samplePhoto!, height: 150, fit: BoxFit.cover),
          ),
      ],
    );
  }

  Widget _summaryTile(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Icon(icon, size: 20, color: AppColors.primary),
          const SizedBox(width: 10),
          Text('$label: ',
              style: const TextStyle(
                  fontWeight: FontWeight.w600, color: AppColors.textSecondary)),
          Expanded(
            child: Text(value,
                style: const TextStyle(fontWeight: FontWeight.w500)),
          ),
        ],
      ),
    );
  }

  // ── Bottom Navigation ───────────────────────────────────────────

  Widget _buildBottomBar(CollectionState state, CollectionNotifier notifier) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          if (state.currentStep > 0)
            Expanded(
              child: OutlinedButton(
                onPressed: notifier.previousStep,
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('Back'),
              ),
            ),
          if (state.currentStep > 0) const SizedBox(width: 12),
          Expanded(
            flex: 2,
            child: ElevatedButton(
              onPressed: state.isSubmitting
                  ? null
                  : !state.canProceed
                      ? null
                      : state.currentStep == 5
                          ? () => _submitCollection(notifier)
                          : notifier.nextStep,
              style: ElevatedButton.styleFrom(
                backgroundColor:
                    state.currentStep == 5 ? AppColors.success : AppColors.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
              ),
              child: state.isSubmitting
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : Text(
                      state.currentStep == 5 ? 'Submit Collection' : 'Next',
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w600),
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submitCollection(CollectionNotifier notifier) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm Submission'),
        content: const Text(
            'Are you sure you want to submit this collection? This action cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.success),
            child:
                const Text('Submit', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await notifier.submit();
    }
  }

  // ── Success Screen ──────────────────────────────────────────────

  Widget _buildSuccessScreen(CollectionState state) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: AppColors.success.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.check_circle,
                      size: 80, color: AppColors.success),
                ),
                const SizedBox(height: 24),
                const Text(
                  'Collection Complete!',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                Text(
                  'Order #${widget.orderId} has been collected successfully.',
                  style: const TextStyle(
                      color: AppColors.textSecondary, fontSize: 15),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 32),
                // Summary card
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.grey.shade200),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Summary',
                          style: TextStyle(
                              fontWeight: FontWeight.bold, fontSize: 16)),
                      const Divider(),
                      _summaryRow('Vials',
                          '${state.vials.fold<int>(0, (sum, v) => sum + v.quantity)} tubes'),
                      _summaryRow('Photo', state.photoUrl != null ? '✓ Uploaded' : '—'),
                      _summaryRow(
                          'Signature', state.signatureUrl != null ? '✓ Uploaded' : '—'),
                      if (state.payment != null) ...[
                        _summaryRow('Amount',
                            '₹${state.payment!.amount.toStringAsFixed(2)}'),
                        _summaryRow(
                            'Mode', state.payment!.mode.name.toUpperCase()),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 32),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () => context.go('/orders'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12)),
                    ),
                    child: const Text('Back to Orders',
                        style: TextStyle(fontSize: 16)),
                  ),
                ),
              ],
            ),
          ),
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
}
