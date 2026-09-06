/**
 * WorksheetRenderer — generic form renderer for 'worksheet'/'reflection'
 * lessons in ModuleDetailPage.jsx. Called as:
 *   <WorksheetRenderer schema={effectiveSchema} value={answers} onChange={handleAnswersChange} />
 * where `value`/`onChange` carry the whole per-lesson answers object
 * (ModuleDetailPage debounce-saves it via api/modules.js `saveLesson`).
 *
 * Two schema shapes are produced by ModuleDetailPage before this ever runs:
 *   { type: 'reflection', prompts: [string, ...], min_chars }
 *   { fields: [{ id, type, label, options? }, ...] }   (generic worksheet)
 *
 * Judgment call (no further schema spec exists in the repo): support a
 * reasonable field-type set (text, textarea, select, checklist, number) with
 * textarea as the fallback for anything unrecognized, so unknown module
 * content still renders something editable rather than crashing.
 */
import React from 'react';

const fieldStyle = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid #E5E7EB',
  fontSize: '0.95rem',
  fontFamily: 'inherit',
};

const labelStyle = {
  display: 'block',
  fontWeight: 600,
  fontSize: '0.85rem',
  marginBottom: 6,
  color: '#2D3047',
};

function ReflectionSchema({ schema, value, onChange }) {
  const prompts = schema.prompts || [];
  const minChars = schema.min_chars || 0;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {prompts.map((prompt, idx) => {
        const key = `prompt_${idx}`;
        const text = value?.[key] || '';
        return (
          <div key={key}>
            <label style={labelStyle}>{prompt}</label>
            <textarea
              style={{ ...fieldStyle, minHeight: 100, resize: 'vertical' }}
              value={text}
              onChange={(e) => onChange({ ...value, [key]: e.target.value })}
              placeholder="Write your thoughts here..."
            />
            {minChars > 0 && (
              <div style={{ fontSize: '0.75rem', color: text.length >= minChars ? '#06D6A0' : '#9CA3AF', marginTop: 4 }}>
                {text.length}/{minChars} characters
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function GenericField({ field, value, onChange }) {
  const common = {
    value: value ?? '',
    onChange: (e) => onChange(e.target.value),
  };
  switch (field.type) {
    case 'select':
      return (
        <select style={fieldStyle} {...common}>
          <option value="" disabled>Choose one…</option>
          {(field.options || []).map((opt) => {
            const optValue = typeof opt === 'object' ? opt.value : opt;
            const optLabel = typeof opt === 'object' ? opt.label : opt;
            return <option key={optValue} value={optValue}>{optLabel}</option>;
          })}
        </select>
      );
    case 'checklist': {
      const selected = Array.isArray(value) ? value : [];
      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {(field.options || []).map((opt) => {
            const optValue = typeof opt === 'object' ? opt.value : opt;
            const optLabel = typeof opt === 'object' ? opt.label : opt;
            const checked = selected.includes(optValue);
            return (
              <label key={optValue} style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.9rem' }}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => {
                    const next = checked ? selected.filter((v) => v !== optValue) : [...selected, optValue];
                    onChange(next);
                  }}
                />
                {optLabel}
              </label>
            );
          })}
        </div>
      );
    }
    case 'number':
      return <input type="number" style={fieldStyle} {...common} />;
    case 'text':
      return <input type="text" style={fieldStyle} {...common} />;
    case 'textarea':
    default:
      return <textarea style={{ ...fieldStyle, minHeight: 90, resize: 'vertical' }} {...common} />;
  }
}

function GenericSchema({ schema, value, onChange }) {
  const fields = schema?.fields || [];
  if (!fields.length) {
    return (
      <p style={{ color: '#9CA3AF', fontSize: '0.9rem' }}>
        This worksheet has no fields configured yet.
      </p>
    );
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {fields.map((field) => (
        <div key={field.id}>
          <label style={labelStyle}>{field.label || field.question || field.id}</label>
          <GenericField
            field={field}
            value={value?.[field.id]}
            onChange={(v) => onChange({ ...value, [field.id]: v })}
          />
        </div>
      ))}
    </div>
  );
}

export default function WorksheetRenderer({ schema, value = {}, onChange }) {
  if (!schema) {
    return <p style={{ color: '#9CA3AF', fontSize: '0.9rem' }}>Nothing to fill in for this lesson.</p>;
  }
  if (schema.type === 'reflection' && Array.isArray(schema.prompts)) {
    return <ReflectionSchema schema={schema} value={value} onChange={onChange} />;
  }
  return <GenericSchema schema={schema} value={value} onChange={onChange} />;
}
