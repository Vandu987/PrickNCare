import '../entities/user_entity.dart';
import '../repositories/auth_repository.dart';

class VerifyOtpUseCase {
  final AuthRepository _repository;

  VerifyOtpUseCase(this._repository);

  Future<UserEntity> call(String phone, String otp) =>
      _repository.verifyOtp(phone, otp);
}
