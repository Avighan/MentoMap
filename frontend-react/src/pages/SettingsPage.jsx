/**
 * SettingsPage - User preferences for sound, difficulty, notifications, theme.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FaArrowLeft,
  FaCog,
  FaVolumeUp,
  FaVolumeMute,
  FaBell,
  FaBellSlash,
  FaPalette,
  FaGamepad,
  FaSave,
  FaCheckCircle,
  FaUser,
  FaSignOutAlt,
} from 'react-icons/fa';
import { useAuth } from '../contexts/AuthContext';
import { getProfile, updateProfile, updateWellbeingConsent, deleteWellbeingData } from '../api/profile';
import { useTranslation } from 'react-i18next';
import { useDutyMode, setDutyMode } from '../utils/dutyMode';

const colors = {
  primary: '#FFD166',
  text: '#2D3047',
  textLight: '#6B7280',
  success: '#06D6A0',
  error: '#EF476F',
};

const DIFFICULTY_OPTIONS = [
  { value: 'easy', label: 'Easy', description: 'Relaxed pace, more hints, forgiving scoring' },
  { value: 'intermediate', label: 'Intermediate', description: 'Balanced challenge for most players' },
  { value: 'advanced', label: 'Advanced', description: 'Tougher scenarios, less time, stricter scoring' },
];

const STORAGE_KEY = 'mento_user_settings';

const LANGUAGES = [
  { code: 'en', labelKey: 'settings.language_en' },
  { code: 'hi', labelKey: 'settings.language_hi' },
  { code: 'ta', labelKey: 'settings.language_ta' },
  { code: 'te', labelKey: 'settings.language_te' },
  { code: 'mr', labelKey: 'settings.language_mr' },
  { code: 'bn', labelKey: 'settings.language_bn' },
];

const FONT_SIZES = [
  { value: 'small',  label: 'Small',  rem: '0.875rem' },
  { value: 'medium', label: 'Medium', rem: '1rem' },
  { value: 'large',  label: 'Large',  rem: '1.125rem' },
];

const defaultSettings = {
  soundEnabled: true,
  musicVolume: 70,
  sfxVolume: 80,
  notificationsEnabled: true,
  dailyReminder: true,
  preferredDifficulty: 'intermediate',
  autoAdvanceRounds: false,
  showHints: true,
  compactMode: false,
  animationsEnabled: true,
  fontSize: 'medium',
};

const SettingsPage = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { i18n, t } = useTranslation();
  const dutyMode = useDutyMode();
  const [currentLang, setCurrentLang] = useState(localStorage.getItem('mento_lang') || 'en');
  const [wellbeingConsent, setWellbeingConsent] = useState(null);
  const [wellbeingUpdating, setWellbeingUpdating] = useState(false);
  const [reflectionFreq, setReflectionFreq] = useState(
    parseInt(localStorage.getItem('reflection_frequency') || '3')
  );

  useEffect(() => {
    getProfile()
      .then(p => {
        setWellbeingConsent(p.wellbeing_consent);
        // Sync server-stored daily-dispatch preference into local settings on mount.
        const serverPref = p?.preferences?.module_daily_dispatch;
        if (typeof serverPref === 'boolean') {
          setSettings(prev => ({ ...prev, module_daily_dispatch: serverPref }));
        }
      })
      .catch(() => {});
  }, []);

  const handleWellbeingToggle = async (enabled) => {
    setWellbeingUpdating(true);
    try {
      await updateWellbeingConsent(enabled ? 'given' : 'withdrawn');
      setWellbeingConsent(enabled ? 'given' : 'withdrawn');
    } catch (e) {
      console.error('Wellbeing consent update failed', e);
    } finally {
      setWellbeingUpdating(false);
    }
  };

  const handleDeleteWellbeingData = async () => {
    if (!window.confirm('Delete all your wellbeing data? This cannot be undone.')) return;
    try {
      await deleteWellbeingData();
      setWellbeingConsent('withdrawn');
      alert('Your wellbeing data has been deleted.');
    } catch (e) {
      alert('Failed to delete wellbeing data.');
    }
  };

  const handleReflectionFreqChange = (val) => {
    setReflectionFreq(val);
    localStorage.setItem('reflection_frequency', val.toString());
  };

  const handleLanguageChange = (lang) => {
    setCurrentLang(lang);
    i18n.changeLanguage(lang);
    localStorage.setItem('mento_lang', lang);
  };
  const [settings, setSettings] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
    } catch {
      return defaultSettings;
    }
  });
  const [saved, setSaved] = useState(false);

  const updateSetting = (key, value) => {
    setSettings(prev => {
      const next = { ...prev, [key]: value };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  const handleSave = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  // Apply font size on mount and whenever it changes
  useEffect(() => {
    const size = FONT_SIZES.find(f => f.value === settings.fontSize) || FONT_SIZES[1];
    document.documentElement.style.setProperty('--fs-base', size.rem);
  }, [settings.fontSize]);

  const handleLogout = () => {
    if (window.confirm('Are you sure you want to log out?')) {
      logout();
      navigate('/login');
    }
  };

  const Toggle = ({ enabled, onChange, label, description, iconOn, iconOff }) => (
    <div className="flex items-center justify-between py-3">
      <div className="flex-1 min-w-0 pr-4">
        <p className="text-sm font-medium" style={{ color: colors.text }}>{label}</p>
        {description && <p className="text-xs text-gray-400 mt-0.5">{description}</p>}
      </div>
      <button
        onClick={() => onChange(!enabled)}
        className={`relative w-12 h-6 rounded-full transition-colors flex-shrink-0 ${
          enabled ? 'bg-green-400' : 'bg-gray-300'
        }`}
      >
        <motion.div
          className="absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-sm"
          animate={{ left: enabled ? '26px' : '2px' }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        />
      </button>
    </div>
  );

  const Slider = ({ value, onChange, label, min = 0, max = 100 }) => (
    <div className="py-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium" style={{ color: colors.text }}>{label}</p>
        <span className="text-xs font-bold text-gray-500">{value}%</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full h-2 rounded-lg appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, ${colors.primary} 0%, ${colors.primary} ${value}%, #E5E7EB ${value}%, #E5E7EB 100%)`,
        }}
      />
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-100">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center gap-3">
          <button
            onClick={() => navigate('/games')}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <FaArrowLeft className="text-gray-500 text-sm" />
          </button>
          <div className="flex-1">
            <h1 className="text-lg font-bold" style={{ color: colors.text }}>
              Settings
            </h1>
            <p className="text-xs text-gray-400">Customize your experience</p>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleSave}
            className="px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-colors"
            style={{
              backgroundColor: saved ? colors.success : colors.primary,
              color: saved ? '#fff' : colors.text,
            }}
          >
            {saved ? <FaCheckCircle /> : <FaSave />}
            {saved ? 'Saved!' : 'Save'}
          </motion.button>
        </div>
      </header>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Account Section */}
        <section className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-4">
            <FaUser className="text-blue-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: colors.textLight }}>
              Account
            </h2>
          </div>
          <div className="flex items-center gap-3 pb-3 border-b border-gray-50">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-yellow-300 to-orange-400 flex items-center justify-center text-white font-bold">
              {(user?.username || 'U')[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold truncate" style={{ color: colors.text }}>
                {user?.username || 'Player'}
              </p>
              <p className="text-xs text-gray-400">{user?.email || ''}</p>
            </div>
            <button
              onClick={() => navigate('/profile')}
              className="text-xs text-blue-500 hover:underline"
            >
              View Profile
            </button>
          </div>
          <div className="pt-3">
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-sm text-red-500 hover:text-red-600 transition-colors"
            >
              <FaSignOutAlt /> Log Out
            </button>
          </div>
        </section>

        {/* Sound Settings */}
        <section className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-2">
            {settings.soundEnabled ? (
              <FaVolumeUp className="text-green-400" />
            ) : (
              <FaVolumeMute className="text-gray-400" />
            )}
            <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: colors.textLight }}>
              Sound
            </h2>
          </div>
          <Toggle
            enabled={settings.soundEnabled}
            onChange={(v) => updateSetting('soundEnabled', v)}
            label="Sound Effects"
            description="Play sounds for actions, achievements, and transitions"
          />
          {settings.soundEnabled && (
            <>
              <Slider
                value={settings.musicVolume}
                onChange={(v) => updateSetting('musicVolume', v)}
                label="Background Music"
              />
              <Slider
                value={settings.sfxVolume}
                onChange={(v) => updateSetting('sfxVolume', v)}
                label="Sound Effects Volume"
              />
            </>
          )}
        </section>

        {/* Language */}
        <section className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">🌐</span>
            <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: colors.textLight }}>
              {t('settings.language')}
            </h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {LANGUAGES.map(lang => (
              <button
                key={lang.code}
                onClick={() => handleLanguageChange(lang.code)}
                className={`px-3 py-1.5 rounded-lg border-2 text-sm font-medium transition-all ${
                  currentLang === lang.code
                    ? 'border-purple-500 bg-purple-50 text-purple-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                {t(lang.labelKey)}
              </button>
            ))}
          </div>
        </section>

        {/* Notifications */}
        <section className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-2">
            {settings.notificationsEnabled ? (
              <FaBell className="text-yellow-400" />
            ) : (
              <FaBellSlash className="text-gray-400" />
            )}
            <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: colors.textLight }}>
              Notifications
            </h2>
          </div>
          <Toggle
            enabled={settings.notificationsEnabled}
            onChange={(v) => updateSetting('notificationsEnabled', v)}
            label="Push Notifications"
            description="Receive alerts for daily challenges and achievements"
          />
          {settings.notificationsEnabled && (
            <Toggle
              enabled={settings.dailyReminder}
              onChange={(v) => updateSetting('dailyReminder', v)}
              label="Daily Play Reminder"
              description="Get a reminder to maintain your streak"
            />
          )}
        </section>

        {/* Gameplay */}
        <section className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-2">
            <FaGamepad className="text-purple-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: colors.textLight }}>
              Gameplay
            </h2>
          </div>

          {/* Difficulty Selector */}
          <div className="py-3">
            <p className="text-sm font-medium mb-2" style={{ color: colors.text }}>Preferred Difficulty</p>
            <div className="grid grid-cols-3 gap-2">
              {DIFFICULTY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => updateSetting('preferredDifficulty', opt.value)}
                  className={`p-2.5 rounded-xl border-2 text-center transition-all ${
                    settings.preferredDifficulty === opt.value
                      ? 'border-yellow-400 bg-yellow-50'
                      : 'border-gray-100 bg-white hover:border-gray-200'
                  }`}
                >
                  <p className="text-sm font-semibold" style={{ color: colors.text }}>{opt.label}</p>
                  <p className="text-xs text-gray-400 mt-0.5 hidden sm:block">{opt.description}</p>
                </button>
              ))}
            </div>
          </div>

          <Toggle
            enabled={settings.showHints}
            onChange={(v) => updateSetting('showHints', v)}
            label="Show Hints"
            description="Display helpful tips during gameplay"
          />
          <Toggle
            enabled={settings.autoAdvanceRounds}
            onChange={(v) => updateSetting('autoAdvanceRounds', v)}
            label="Auto-Advance Rounds"
            description="Automatically move to next round after outcome"
          />

          {/* Reflection Prompts */}
          <div className="mt-4">
            <h4 className="text-sm font-semibold mb-2" style={{ color: colors.text }}>Reflection Prompts</h4>
            <div className="flex flex-col gap-2">
              {[{val: 1, label: 'Every round'}, {val: 3, label: 'Every 3 rounds (default)'}, {val: 5, label: 'Every 5 rounds'}, {val: 0, label: 'Off'}].map(opt => (
                <label key={opt.val} className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="radio"
                    name="reflection_freq"
                    value={opt.val}
                    checked={reflectionFreq === opt.val}
                    onChange={() => handleReflectionFreqChange(opt.val)}
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>
        </section>

        {/* Duty Mode (Kantian opt-out from extrinsic rewards) */}
        <section className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-indigo-500">⚖️</span>
            <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: colors.textLight }}>
              Duty Mode
            </h2>
          </div>
          <p className="text-xs text-gray-500 mb-2 leading-relaxed">
            Inspired by Kant: morality should not depend on rewards or fear.
            When on, Mento hides XP popups, achievement celebrations, skill-delta toasts,
            and streak banners during play. You still earn them — they just don't
            interrupt your reasoning. Reflection prompts in ethics lessons will also
            ask the universalization question ("if everyone did this…").
          </p>
          <Toggle
            enabled={dutyMode}
            onChange={(v) => setDutyMode(v)}
            label="Hide reward popups during play"
            description={dutyMode ? 'On — playing for the reasoning, not the points' : 'Off — gamification rewards visible'}
          />
        </section>

        {/* Display */}
        <section className="bg-white rounded-xl border border-gray-100 p-4">
          <div className="flex items-center gap-2 mb-2">
            <FaPalette className="text-pink-400" />
            <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: colors.textLight }}>
              Display
            </h2>
          </div>
          <Toggle
            enabled={settings.animationsEnabled}
            onChange={(v) => updateSetting('animationsEnabled', v)}
            label="Animations"
            description="Enable smooth transitions and motion effects"
          />
          <Toggle
            enabled={settings.compactMode}
            onChange={(v) => updateSetting('compactMode', v)}
            label="Compact Mode"
            description="Reduce spacing for more content on screen"
          />
          {/* Font Size */}
          <div className="py-3">
            <p className="text-sm font-medium mb-2" style={{ color: colors.text }}>Font Size</p>
            <div className="grid grid-cols-3 gap-2">
              {FONT_SIZES.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => updateSetting('fontSize', opt.value)}
                  className={`p-2.5 rounded-xl border-2 text-center transition-all ${
                    settings.fontSize === opt.value
                      ? 'border-pink-400 bg-pink-50'
                      : 'border-gray-100 bg-white hover:border-gray-200'
                  }`}
                >
                  <p className="font-semibold" style={{ color: colors.text, fontSize: opt.rem }}>{opt.label}</p>
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Wellbeing Monitoring (student only) */}
        {user && (user.role === 'student' || !user.role) && (
          <section className="bg-white rounded-xl border border-gray-100 p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-green-500">💚</span>
              <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: colors.textLight }}>
                Wellbeing Monitoring
              </h2>
            </div>
            <p className="text-xs text-gray-500 mb-3">
              When enabled, Mento notices in-game patterns (like stress or fatigue) and may gently notify your teacher or parent. This is not a medical assessment.
            </p>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium" style={{ color: colors.text }}>Enable Wellbeing Tracking</p>
                <p className="text-xs text-gray-400">{wellbeingConsent === 'given' ? 'Currently enabled' : 'Currently disabled'}</p>
              </div>
              <button
                onClick={() => handleWellbeingToggle(wellbeingConsent !== 'given')}
                disabled={wellbeingUpdating}
                className={`relative w-12 h-6 rounded-full transition-colors ${wellbeingConsent === 'given' ? 'bg-green-500' : 'bg-gray-200'}`}
              >
                <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${wellbeingConsent === 'given' ? 'translate-x-6' : 'translate-x-0'}`} />
              </button>
            </div>
            {wellbeingConsent === 'given' && (
              <button
                onClick={handleDeleteWellbeingData}
                className="mt-3 text-xs text-red-400 hover:text-red-600 underline"
              >
                Delete my wellbeing data (right to erasure)
              </button>
            )}
          </section>
        )}

        {/* Accessibility & Sensory */}
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <h3 className="text-sm font-bold text-gray-800 mb-1">Accessibility &amp; Sensory</h3>
          <p className="text-xs text-gray-400 mb-3">These settings help with focus, sensory sensitivity, and ADHD support.</p>
          <div className="space-y-3">
            {[
              { key: 'accessibility_focus_mode', label: 'Focus Mode', desc: 'Hides non-essential overlays (badges, streaks) during gameplay' },
              { key: 'accessibility_reduced_motion', label: 'Reduced animations', desc: 'Minimizes moving elements for motion sensitivity' },
              { key: 'accessibility_high_contrast', label: 'High contrast mode', desc: 'Increases text and UI contrast' },
              { key: 'accessibility_extended_time', label: 'Extended response time', desc: 'Removes time pressure from timed challenges' },
            ].map(setting => (
              <label key={setting.key} className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  defaultChecked={!!localStorage.getItem(setting.key)}
                  onChange={e => {
                    if (e.target.checked) localStorage.setItem(setting.key, '1');
                    else localStorage.removeItem(setting.key);
                    window.dispatchEvent(new Event('storage'));
                  }}
                  className="mt-0.5 accent-blue-600"
                />
                <div>
                  <div className="text-sm font-medium text-gray-700">{setting.label}</div>
                  <div className="text-xs text-gray-500">{setting.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Learning Notifications (Phase D — daily-dispatch opt-in) */}
        <div className="bg-white rounded-2xl shadow p-6">
          <div className="flex items-center gap-3 mb-4">
            <FaBell color={colors.primary} size={22} />
            <h2 className="text-lg font-semibold text-gray-800">Learning Notifications</h2>
          </div>
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={settings.module_daily_dispatch !== false}
              onChange={async (e) => {
                const checked = e.target.checked;
                updateSetting('module_daily_dispatch', checked);
                try {
                  await updateProfile({ preferences: { module_daily_dispatch: checked } });
                } catch (err) {
                  console.warn('Failed to persist daily dispatch preference', err);
                }
              }}
              className="mt-1 w-5 h-5 rounded"
            />
            <div>
              <div className="text-sm font-medium text-gray-700">28-day Mento Entrepreneur dispatch</div>
              <div className="text-xs text-gray-500">
                A short daily nudge (~6pm) while you’re in the 4-week workshop. Turn off any time.
              </div>
            </div>
          </label>
        </div>

        {/* App Info */}
        <div className="text-center py-4 text-xs text-gray-400 space-y-1">
          <p>Mento Arcade v2.0</p>
          <p>Built with care for curious minds</p>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
