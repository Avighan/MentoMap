import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../../../i18n';
import MentorCheckIn from './MentorCheckIn';

const wrap = (ui) => <I18nextProvider i18n={i18n}>{ui}</I18nextProvider>;

describe('MentorCheckIn', () => {
  it('renders prompt + 3 reply chips when concentrated', () => {
    const state = { positions: { TECHV: 50, INFOS: 30 }, stocks_by_sector: { TECHV: 'IT', INFOS: 'IT' } };
    render(wrap(<MentorCheckIn state={state} onReply={() => {}} />));
    expect(screen.getAllByTestId(/mentor-reply-/).length).toBe(3);
  });

  it('reply calls onReply with choice id', () => {
    const onReply = vi.fn();
    const state = { positions: {}, stocks_by_sector: {} };
    render(wrap(<MentorCheckIn state={state} onReply={onReply} />));
    fireEvent.click(screen.getByTestId('mentor-reply-diversify'));
    expect(onReply).toHaveBeenCalledWith('diversify', expect.any(Object));
  });
});
