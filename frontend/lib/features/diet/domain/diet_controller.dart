import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../data/diet_repository.dart';

final selectedDietDateProvider = StateProvider<DateTime>((ref) {
  return DateTime.now();
});

final dietLogsProvider = FutureProvider.autoDispose<Map<String, dynamic>>((
  Ref ref,
) {
  final DateTime selectedDate = ref.watch(selectedDietDateProvider);
  final String dateText = DateFormat('yyyy-MM-dd').format(selectedDate);
  return ref.read(dietRepositoryProvider).getDietLogs(dateText);
});

Future<void> deleteDietLogAndRefresh(WidgetRef ref, int logId) async {
  await ref.read(dietRepositoryProvider).deleteDietLog(logId);
  ref.invalidate(dietLogsProvider);
}
