import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class CollectionScreen extends ConsumerWidget {
  final String orderId;
  const CollectionScreen({super.key, required this.orderId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: Text('Collection #$orderId')),
      body: Center(
        child: Text('Collection workflow for $orderId - Coming soon'),
      ),
    );
  }
}
