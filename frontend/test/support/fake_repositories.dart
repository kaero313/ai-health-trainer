import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:frontend/features/chat/data/chat_repository.dart';
import 'package:frontend/features/diet/data/diet_image_picker.dart';
import 'package:frontend/features/diet/data/diet_repository.dart';
import 'package:frontend/features/exercise/data/exercise_repository.dart';
import 'package:frontend/features/profile/data/profile_repository.dart';
import 'package:image_picker/image_picker.dart';

class FakeDietRepository extends DietRepository {
  Map<String, dynamic> logs = <String, dynamic>{};
  Map<String, dynamic> recommendation = <String, dynamic>{};
  Map<String, dynamic> analysis = <String, dynamic>{};
  Object? logsError;
  Object? recommendationError;
  Object? analysisError;
  final List<Map<String, dynamic>> createdPayloads = <Map<String, dynamic>>[];
  final List<int> deletedLogIds = <int>[];
  Uint8List? uploadedBytes;
  String? uploadedFilename;
  String? uploadedContentType;

  FakeDietRepository() : super(dio: Dio());

  @override
  Future<Map<String, dynamic>> analyzeImage({
    required Uint8List bytes,
    required String filename,
    required String contentType,
  }) async {
    uploadedBytes = bytes;
    uploadedFilename = filename;
    uploadedContentType = contentType;
    if (analysisError case final Object error) {
      throw error;
    }
    return analysis;
  }

  @override
  Future<Map<String, dynamic>> createDietLog(
    Map<String, dynamic> payload,
  ) async {
    createdPayloads.add(payload);
    return <String, dynamic>{'id': 1};
  }

  @override
  Future<void> deleteDietLog(int logId) async {
    deletedLogIds.add(logId);
  }

  @override
  Future<Map<String, dynamic>> getDietLogs(String date) async {
    if (logsError case final Object error) {
      throw error;
    }
    return logs;
  }

  @override
  Future<Map<String, dynamic>> getRecommendation({String? date}) async {
    if (recommendationError case final Object error) {
      throw error;
    }
    return recommendation;
  }

  @override
  Future<List<Map<String, dynamic>>> searchFoods(
    String query, {
    int limit = 10,
  }) async {
    return <Map<String, dynamic>>[];
  }
}

class FakeExerciseRepository extends ExerciseRepository {
  Map<String, dynamic> logs = <String, dynamic>{};
  Map<String, dynamic> recommendation = <String, dynamic>{};
  Object? logsError;
  Object? recommendationError;
  final List<Map<String, dynamic>> createdPayloads = <Map<String, dynamic>>[];
  final List<int> deletedLogIds = <int>[];

  FakeExerciseRepository() : super(dio: Dio());

  @override
  Future<Map<String, dynamic>> createExerciseLog(
    Map<String, dynamic> payload,
  ) async {
    createdPayloads.add(payload);
    return <String, dynamic>{'id': 1};
  }

  @override
  Future<void> deleteExerciseLog(int logId) async {
    deletedLogIds.add(logId);
  }

  @override
  Future<Map<String, dynamic>> getExerciseLogs(String date) async {
    if (logsError case final Object error) {
      throw error;
    }
    return logs;
  }

  @override
  Future<Map<String, dynamic>> getRecommendation({String? muscleGroup}) async {
    if (recommendationError case final Object error) {
      throw error;
    }
    return recommendation;
  }
}

class FakeChatRepository extends ChatRepository {
  Map<String, dynamic> response = <String, dynamic>{};
  Object? error;
  String? lastMessage;
  String? lastContextType;

  FakeChatRepository() : super(dio: Dio());

  @override
  Future<Map<String, dynamic>> sendMessage(
    String message,
    String contextType,
  ) async {
    lastMessage = message;
    lastContextType = contextType;
    if (error case final Object requestError) {
      throw requestError;
    }
    return response;
  }
}

class FakeProfileRepository extends ProfileRepository {
  Map<String, dynamic> profile = <String, dynamic>{};
  Object? error;

  FakeProfileRepository() : super(dio: Dio());

  @override
  Future<bool> checkProfile() async => error == null;

  @override
  Future<Map<String, dynamic>> getProfile() async {
    if (error case final Object requestError) {
      throw requestError;
    }
    return profile;
  }

  @override
  Future<Map<String, dynamic>> updateProfile(
    Map<String, dynamic> payload,
  ) async {
    profile = payload;
    return profile;
  }
}

class FakeDietImagePicker implements DietImagePicker {
  XFile? image;
  Object? error;
  ImageSource? lastSource;

  @override
  Future<XFile?> pickImage(ImageSource source) async {
    lastSource = source;
    if (error case final Object pickerError) {
      throw pickerError;
    }
    return image;
  }
}
