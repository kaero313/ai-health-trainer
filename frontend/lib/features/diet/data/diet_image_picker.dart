import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

abstract interface class DietImagePicker {
  Future<XFile?> pickImage(ImageSource source);
}

class DeviceDietImagePicker implements DietImagePicker {
  final ImagePicker _picker;

  DeviceDietImagePicker({ImagePicker? picker})
    : _picker = picker ?? ImagePicker();

  @override
  Future<XFile?> pickImage(ImageSource source) {
    return _picker.pickImage(source: source);
  }
}

final dietImagePickerProvider = Provider<DietImagePicker>((Ref ref) {
  return DeviceDietImagePicker();
});
