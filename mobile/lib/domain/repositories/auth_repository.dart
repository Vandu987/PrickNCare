import '../entities/user_entity.dart';

abstract class AuthRepository {
  Future<void> requestOtp(String phone);
  Future<UserEntity> verifyOtp(String phone, String otp);
  Future<void> logout();
  Future<UserEntity?> getCurrentUser();
}
