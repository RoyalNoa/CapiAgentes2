import React from 'react';

interface SuggestedQuestionsProps {
  onSend: (question: string) => void;
}

const questions = [
  '¿Cuántas sucursales hay?',
  '¿Cuáles son las anomalías detectadas?',
  '¿Cuál es el total de ingresos?',
  '¿Qué cajero tiene más movimientos?',
  '¿Cuál es el balance neto?',
  '¿Hay sucursales con movimientos inusuales?'
];

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({ onSend }) => (
  <div style={{ marginTop: 16, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
    {questions.map((q) => (
      <button
        key={q}
        onClick={() => onSend(q)}
        style={{
          padding: '6px 12px',
          borderRadius: 8,
          border: '1px solid #ccc',
          background: '#f5f5f5',
          cursor: 'pointer',
        }}
      >
        {q}
      </button>
    ))}
  </div>
);

export default SuggestedQuestions;
