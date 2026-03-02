import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../data/exercise_repository.dart';

final exerciseDateProvider = StateProvider<DateTime>((ref) {
  return DateTime.now();
});

final selectedMuscleGroupProvider = StateProvider<String?>((ref) {
  return null;
});

final exerciseLogsProvider = FutureProvider.autoDispose<Map<String, dynamic>>((
  Ref ref,
) {
  final DateTime selectedDate = ref.watch(exerciseDateProvider);
  final String dateText = DateFormat('yyyy-MM-dd').format(selectedDate);
  return ref.read(exerciseRepositoryProvider).getExerciseLogs(dateText);
});

Future<void> deleteExerciseLogAndRefresh(WidgetRef ref, int logId) async {
  await ref.read(exerciseRepositoryProvider).deleteExerciseLog(logId);
  ref.invalidate(exerciseLogsProvider);
}
