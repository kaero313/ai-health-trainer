import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../shared/widgets/neo_widgets.dart';
import '../data/chat_repository.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen>
    with SingleTickerProviderStateMixin {
  final List<Map<String, Object?>> _messages = <Map<String, Object?>>[];
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  late final AnimationController _typingController;
  bool _isLoading = false;
  String _contextType = 'general';

  static const List<String> _contextOrder = <String>[
    'general',
    'diet',
    'exercise',
  ];

  static const Map<String, String> _contextLabels = <String, String>{
    'general': '전체',
    'diet': '식단',
    'exercise': '운동',
  };

  @override
  void initState() {
    super.initState();
    _typingController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    _messages.add(
      _buildMessage(role: 'assistant', text: '안녕하세요. 오늘 무엇을 조정할까요?'),
    );
  }

  @override
  void dispose() {
    _typingController.dispose();
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  bool get _canSend => _textController.text.trim().isNotEmpty && !_isLoading;

  Map<String, Object?> _buildMessage({
    required String role,
    required String text,
    List<String>? sources,
  }) {
    return <String, Object?>{
      'role': role,
      'text': text,
      'sources': sources,
      'timestamp': DateTime.now(),
    };
  }

  Future<void> _sendMessage() async {
    final String userText = _textController.text.trim();
    if (userText.isEmpty || _isLoading) {
      return;
    }

    setState(() {
      _messages.add(_buildMessage(role: 'user', text: userText));
      _textController.clear();
      _isLoading = true;
    });
    _typingController.repeat();
    _scrollToBottom();

    try {
      final Map<String, dynamic> data = await ref
          .read(chatRepositoryProvider)
          .sendMessage(userText, _contextType);
      final String answer = (data['answer']?.toString() ?? '').trim();
      final List<String> sources =
          (data['sources'] as List<dynamic>? ?? <dynamic>[])
              .map((dynamic item) => item.toString())
              .where((String item) => item.isNotEmpty)
              .toList();

      setState(() {
        _messages.add(
          _buildMessage(
            role: 'assistant',
            text: answer.isEmpty ? '응답을 생성하지 못했습니다.' : answer,
            sources: sources.isEmpty ? null : sources,
          ),
        );
      });
    } catch (error) {
      setState(() {
        _messages.add(
          _buildMessage(
            role: 'assistant',
            text: '요청 처리 중 문제가 발생했습니다. ${_extractErrorMessage(error)}',
          ),
        );
      });
    } finally {
      if (mounted) {
        _typingController
          ..stop()
          ..reset();
        setState(() {
          _isLoading = false;
        });
        _scrollToBottom();
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) {
        return;
      }
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOutCubic,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 16, 20, 10),
              child: NeoTopBar(title: 'AI 코치', showBack: true),
            ),
            _ContextTypeChips(
              selectedContext: _contextType,
              contextOrder: _contextOrder,
              contextLabels: _contextLabels,
              onSelected: (String contextType) {
                setState(() {
                  _contextType = contextType;
                });
              },
            ),
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
                itemCount: _messages.length + (_isLoading ? 1 : 0),
                itemBuilder: (BuildContext context, int index) {
                  if (_isLoading && index == _messages.length) {
                    return _TypingMessage(animation: _typingController);
                  }
                  return _ChatMessageItem(message: _messages[index]);
                },
              ),
            ),
            _ChatInput(
              controller: _textController,
              canSend: _canSend,
              onChanged: () => setState(() {}),
              onSend: _sendMessage,
            ),
          ],
        ),
      ),
    );
  }
}

class _ContextTypeChips extends StatelessWidget {
  final String selectedContext;
  final List<String> contextOrder;
  final Map<String, String> contextLabels;
  final ValueChanged<String> onSelected;

  const _ContextTypeChips({
    required this.selectedContext,
    required this.contextOrder,
    required this.contextLabels,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.pageHorizontal,
      ),
      child: Container(
        height: 42,
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: AppColors.surfaceHigh.withValues(alpha: 0.62),
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Row(
          children: [
            for (final String contextType in contextOrder)
              Expanded(
                child: InkWell(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  onTap: () => onSelected(contextType),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 180),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color:
                          selectedContext == contextType
                              ? AppColors.primary
                              : Colors.transparent,
                      borderRadius: BorderRadius.circular(AppRadius.md),
                    ),
                    child: Text(
                      contextLabels[contextType] ?? contextType,
                      style: AppTypography.label.copyWith(
                        color:
                            selectedContext == contextType
                                ? AppColors.background
                                : AppColors.textSecondary,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ChatMessageItem extends StatelessWidget {
  final Map<String, Object?> message;

  const _ChatMessageItem({required this.message});

  @override
  Widget build(BuildContext context) {
    final bool isUser = message['role'] == 'user';
    final String text = message['text']?.toString() ?? '';
    final List<String> sources =
        (message['sources'] as List<String>?) ?? <String>[];

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.82,
        ),
        margin: const EdgeInsets.only(bottom: AppSpacing.md),
        child: NeoGlassCard(
          highlighted: !isUser,
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isUser
                        ? Icons.person_outline
                        : Icons.psychology_alt_outlined,
                    color: isUser ? AppColors.secondary : AppColors.primary,
                    size: 18,
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  Text(
                    isUser ? '나' : 'AI 코치',
                    style: AppTypography.caption.copyWith(
                      color: isUser ? AppColors.secondary : AppColors.primary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(text, style: AppTypography.body2),
              if (sources.isNotEmpty) ...[
                const SizedBox(height: AppSpacing.sm),
                Wrap(
                  spacing: AppSpacing.xs,
                  runSpacing: AppSpacing.xs,
                  children: [
                    for (final String source in sources.take(3))
                      NeoInfoChip(label: source, color: AppColors.primary),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _TypingMessage extends StatelessWidget {
  final Animation<double> animation;

  const _TypingMessage({required this.animation});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: NeoGlassCard(
        highlighted: true,
        child: AnimatedBuilder(
          animation: animation,
          builder: (BuildContext context, Widget? child) {
            return Text(
              'AI 코치가 근거를 검색하고 있습니다${List<String>.filled((animation.value * 3).floor() + 1, '.').join()}',
              style: AppTypography.body2.copyWith(color: AppColors.primary),
            );
          },
        ),
      ),
    );
  }
}

class _ChatInput extends StatelessWidget {
  final TextEditingController controller;
  final bool canSend;
  final VoidCallback onChanged;
  final VoidCallback onSend;

  const _ChatInput({
    required this.controller,
    required this.canSend,
    required this.onChanged,
    required this.onSend,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 18),
      decoration: BoxDecoration(
        color: AppColors.surface.withValues(alpha: 0.96),
        border: Border(
          top: BorderSide(color: Colors.white.withValues(alpha: 0.06)),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              minLines: 1,
              maxLines: 4,
              style: AppTypography.body1,
              decoration: const InputDecoration(hintText: 'AI 코치에게 질문하세요'),
              onChanged: (_) => onChanged(),
              onSubmitted: (_) => onSend(),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          CircleAvatar(
            radius: 24,
            backgroundColor: canSend ? AppColors.primary : AppColors.divider,
            child: IconButton(
              icon: const Icon(
                Icons.send,
                color: AppColors.background,
                size: 19,
              ),
              onPressed: canSend ? onSend : null,
            ),
          ),
        ],
      ),
    );
  }
}

String _extractErrorMessage(Object error) {
  if (error is ChatRepositoryException) {
    return error.message;
  }
  return error.toString();
}
