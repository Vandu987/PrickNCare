import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_providers.dart';

// ── Models ──────────────────────────────────────────────────────────

class VialEntry {
  final String type;
  int quantity;

  VialEntry({required this.type, this.quantity = 1});

  Map<String, dynamic> toJson() => {'type': type, 'quantity': quantity};
}

enum PaymentMode { cash, upi, card }

class PaymentInfo {
  final double amount;
  final PaymentMode mode;
  final String? transactionId;

  PaymentInfo({required this.amount, required this.mode, this.transactionId});

  Map<String, dynamic> toJson() => {
        'amount': amount,
        'mode': mode.name,
        if (transactionId != null) 'transaction_id': transactionId,
      };
}

// ── State ───────────────────────────────────────────────────────────

class CollectionState {
  final int currentStep;
  final bool patientVerified;
  final File? samplePhoto;
  final String? photoUrl;
  final List<VialEntry> vials;
  final Uint8List? signatureBytes;
  final String? signatureUrl;
  final PaymentInfo? payment;
  final bool isSubmitting;
  final bool isComplete;
  final String? error;

  const CollectionState({
    this.currentStep = 0,
    this.patientVerified = false,
    this.samplePhoto,
    this.photoUrl,
    this.vials = const [],
    this.signatureBytes,
    this.signatureUrl,
    this.payment,
    this.isSubmitting = false,
    this.isComplete = false,
    this.error,
  });

  CollectionState copyWith({
    int? currentStep,
    bool? patientVerified,
    File? samplePhoto,
    String? photoUrl,
    List<VialEntry>? vials,
    Uint8List? signatureBytes,
    String? signatureUrl,
    PaymentInfo? payment,
    bool? isSubmitting,
    bool? isComplete,
    String? error,
  }) {
    return CollectionState(
      currentStep: currentStep ?? this.currentStep,
      patientVerified: patientVerified ?? this.patientVerified,
      samplePhoto: samplePhoto ?? this.samplePhoto,
      photoUrl: photoUrl ?? this.photoUrl,
      vials: vials ?? this.vials,
      signatureBytes: signatureBytes ?? this.signatureBytes,
      signatureUrl: signatureUrl ?? this.signatureUrl,
      payment: payment ?? this.payment,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      isComplete: isComplete ?? this.isComplete,
      error: error,
    );
  }

  bool get canProceed {
    switch (currentStep) {
      case 0:
        return patientVerified;
      case 1:
        return samplePhoto != null;
      case 2:
        return vials.isNotEmpty && vials.every((v) => v.quantity > 0);
      case 3:
        return signatureBytes != null;
      case 4:
        return payment != null;
      case 5:
        return true;
      default:
        return false;
    }
  }
}

// ── Notifier ────────────────────────────────────────────────────────

class CollectionNotifier extends StateNotifier<CollectionState> {
  final ApiClient _api;
  final String orderId;

  CollectionNotifier(this._api, this.orderId) : super(const CollectionState());

  void verifyPatient(bool verified) {
    state = state.copyWith(patientVerified: verified);
  }

  void setSamplePhoto(File photo) {
    state = state.copyWith(samplePhoto: photo);
  }

  void addVial(String type) {
    final vials = List<VialEntry>.from(state.vials);
    final existing = vials.indexWhere((v) => v.type == type);
    if (existing >= 0) {
      vials[existing].quantity++;
    } else {
      vials.add(VialEntry(type: type));
    }
    state = state.copyWith(vials: vials);
  }

  void removeVial(int index) {
    final vials = List<VialEntry>.from(state.vials);
    vials.removeAt(index);
    state = state.copyWith(vials: vials);
  }

  void updateVialQuantity(int index, int qty) {
    final vials = List<VialEntry>.from(state.vials);
    if (index < vials.length) {
      vials[index].quantity = qty;
      state = state.copyWith(vials: vials);
    }
  }

  void setSignature(Uint8List bytes) {
    state = state.copyWith(signatureBytes: bytes);
  }

  void setPayment(PaymentInfo payment) {
    state = state.copyWith(payment: payment);
  }

  void nextStep() {
    if (state.currentStep < 5) {
      state = state.copyWith(currentStep: state.currentStep + 1);
    }
  }

  void previousStep() {
    if (state.currentStep > 0) {
      state = state.copyWith(currentStep: state.currentStep - 1);
    }
  }

  void goToStep(int step) {
    if (step >= 0 && step <= 5) {
      state = state.copyWith(currentStep: step);
    }
  }

  /// Upload photo to /files/upload, returns the URL
  Future<String?> _uploadFile(File file, String fieldName) async {
    try {
      final formData = FormData.fromMap({
        fieldName: await MultipartFile.fromFile(
          file.path,
          filename: file.path.split('/').last,
        ),
      });
      final response = await _api.upload('/files/upload', formData: formData);
      return response.data['url'] as String?;
    } catch (e) {
      return null;
    }
  }

  /// Upload signature bytes as a PNG
  Future<String?> _uploadSignature(Uint8List bytes) async {
    try {
      final formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(
          bytes,
          filename: 'signature_$orderId.png',
          contentType: DioMediaType.parse('image/png'),
        ),
      });
      final response = await _api.upload('/files/upload', formData: formData);
      return response.data['url'] as String?;
    } catch (e) {
      return null;
    }
  }

  /// Submit the entire collection workflow
  Future<bool> submit() async {
    state = state.copyWith(isSubmitting: true, error: null);
    try {
      // 1. Upload sample photo
      String? photoUrl;
      if (state.samplePhoto != null) {
        photoUrl = await _uploadFile(state.samplePhoto!, 'file');
        if (photoUrl == null) {
          state = state.copyWith(
              isSubmitting: false, error: 'Failed to upload sample photo');
          return false;
        }
      }

      // 2. Upload signature
      String? signatureUrl;
      if (state.signatureBytes != null) {
        signatureUrl = await _uploadSignature(state.signatureBytes!);
        if (signatureUrl == null) {
          state = state.copyWith(
              isSubmitting: false, error: 'Failed to upload signature');
          return false;
        }
      }

      // 3. Submit payment
      if (state.payment != null) {
        await _api.post(
          '/orders/$orderId/payment',
          data: state.payment!.toJson(),
        );
      }

      // 4. Submit collection data
      await _api.post(
        '/orders/$orderId/collection',
        data: {
          'sample_photo_url': photoUrl,
          'signature_url': signatureUrl,
          'vials': state.vials.map((v) => v.toJson()).toList(),
        },
      );

      // 5. Update order status to COLLECTED
      await _api.put(
        '/orders/$orderId/status',
        data: {'status': 'collected'},
      );

      state = state.copyWith(
        isSubmitting: false,
        isComplete: true,
        photoUrl: photoUrl,
        signatureUrl: signatureUrl,
      );
      return true;
    } on DioException catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        error: ApiException.fromDioError(e).message,
      );
      return false;
    } catch (e) {
      state = state.copyWith(isSubmitting: false, error: e.toString());
      return false;
    }
  }
}

// ── Providers ───────────────────────────────────────────────────────

final collectionProvider = StateNotifierProvider.family<CollectionNotifier,
    CollectionState, String>((ref, orderId) {
  final api = ref.watch(apiClientProvider);
  return CollectionNotifier(api, orderId);
});
