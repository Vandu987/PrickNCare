class UserEntity {
  final String id;
  final String name;
  final String phone;
  final String role;
  final bool isActive;

  const UserEntity({
    required this.id,
    required this.name,
    required this.phone,
    required this.role,
    required this.isActive,
  });
}
