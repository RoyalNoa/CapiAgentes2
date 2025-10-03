import { describe, expect, it, vi } from 'vitest';

import { processVoiceStreamMessage } from './useVoiceStream';

describe('processVoiceStreamMessage', () => {
  it('propaga transcripciones parciales y finales', async () => {
    const onTranscript = vi.fn();

    await processVoiceStreamMessage({ type: 'transcript', text: 'hola', is_final: false }, {
      onTranscript,
    });

    expect(onTranscript).toHaveBeenCalledWith({ text: 'hola', isFinal: false });

    onTranscript.mockClear();

    await processVoiceStreamMessage({ type: 'transcript', text: 'mundo', is_final: true }, {
      onTranscript,
    });

    expect(onTranscript).toHaveBeenCalledWith({ text: 'mundo', isFinal: true });
  });

  it('propaga la respuesta completa al contexto', async () => {
    const onResponse = vi.fn();
    const payload = {
      type: 'response',
      transcript: 'hola',
      response_text: 'respuesta',
      audio: { base64: 'YWJj', mime_type: 'audio/mpeg', url: 'https://audio' },
    };

    await processVoiceStreamMessage(payload, { onResponse });

    expect(onResponse).toHaveBeenCalledWith(payload);
  });

  it('propaga advertencias y espera su resolucion', async () => {
    const onWarning = vi.fn().mockResolvedValue(undefined);

    await processVoiceStreamMessage({ type: 'warning', message: 'limite' }, { onWarning });

    expect(onWarning).toHaveBeenCalledWith('limite');
  });

  it('propaga errores y cierre de turno', async () => {
    const onError = vi.fn();
    const onTurnComplete = vi.fn();

    await processVoiceStreamMessage({ type: 'error', message: 'fallo' }, { onError });
    expect(onError).toHaveBeenCalledWith('fallo');

    await processVoiceStreamMessage({ type: 'turn_complete' }, { onTurnComplete });
    expect(onTurnComplete).toHaveBeenCalled();
  });
});
