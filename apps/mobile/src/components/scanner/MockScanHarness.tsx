import React, { useState } from 'react';
import { View, Text, TouchableOpacity, TextInput, StyleSheet } from 'react-native';
import { THEME } from '../../constants/theme';

export interface MockScanHarnessProps {
  onScan: (mockData: string) => void;
  roomCode?: string;
  sessionId?: string;
}

/**
 * Headless & Automated Testing Mock Scan Harness.
 * Emulates physical QR code scanning in CI/CD, unit tests, and hardware simulators.
 */
export const MockScanHarness: React.FC<MockScanHarnessProps> = ({
  onScan,
  roomCode = 'PRRC 301',
  sessionId = 'session-ipt2-001',
}: MockScanHarnessProps) => {
  const [customTOTP, setCustomTOTP] = useState<string>('482910');
  const [customStation, setCustomStation] = useState<string>('12');

  const triggerValidScan = () => {
    const payload = JSON.stringify({
      room: roomCode,
      session: sessionId,
      totp: customTOTP || '482910',
      ts: Date.now(),
      workstation_id: customStation ? Number(customStation) : undefined,
    });
    onScan(payload);
  };

  const triggerExpiredScan = () => {
    const payload = JSON.stringify({
      room: roomCode,
      session: sessionId,
      totp: '112233',
      ts: Date.now() - 60000, // 60s ago (exceeds 30s threshold)
      workstation_id: 15,
    });
    onScan(payload);
  };

  const triggerInvalidScan = () => {
    onScan('https://external-site.com/invalid-qr-code');
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>CI / Testing Harness</Text>
        </View>
        <Text style={styles.roomSubtitle}>{roomCode} Simulation</Text>
      </View>

      <Text style={styles.description}>
        Simulate classroom camera scan events without physical projector hardware.
      </Text>

      <View style={styles.inputRow}>
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>TOTP Code (6 digits)</Text>
          <TextInput
            style={styles.textInput}
            value={customTOTP}
            onChangeText={setCustomTOTP}
            placeholder="482910"
            keyboardType="numeric"
            maxLength={6}
          />
        </View>
        <View style={styles.inputGroup}>
          <Text style={styles.inputLabel}>Workstation #</Text>
          <TextInput
            style={styles.textInput}
            value={customStation}
            onChangeText={setCustomStation}
            placeholder="12"
            keyboardType="numeric"
            maxLength={2}
          />
        </View>
      </View>

      <View style={styles.buttonStack}>
        <TouchableOpacity
          style={[styles.button, styles.primaryButton]}
          onPress={triggerValidScan}
          accessibilityLabel="Simulate Valid Attendance QR Scan"
          accessibilityRole="button"
        >
          <Text style={styles.primaryButtonText}>Simulate Valid QR Scan</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.secondaryButton]}
          onPress={triggerExpiredScan}
          accessibilityLabel="Simulate Expired QR Scan"
          accessibilityRole="button"
        >
          <Text style={styles.secondaryButtonText}>Simulate Expired QR (Refresh Test)</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.button, styles.outlineButton]}
          onPress={triggerInvalidScan}
          accessibilityLabel="Simulate Malformed QR Scan"
          accessibilityRole="button"
        >
          <Text style={styles.outlineButtonText}>Simulate Invalid QR</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.layout.cardRadius,
    padding: 16,
    borderWidth: 1,
    borderColor: THEME.colors.line,
    marginVertical: 12,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  badge: {
    backgroundColor: THEME.colors.brandRose,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  badgeText: {
    color: THEME.colors.brandRouge,
    fontSize: 11,
    fontWeight: '700',
  },
  roomSubtitle: {
    fontSize: 12,
    color: THEME.colors.inkSoft,
    fontWeight: '600',
  },
  description: {
    fontSize: 13,
    color: THEME.colors.inkSoft,
    marginBottom: 12,
    lineHeight: 18,
  },
  inputRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 12,
  },
  inputGroup: {
    flex: 1,
  },
  inputLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: THEME.colors.ink,
    marginBottom: 4,
  },
  textInput: {
    height: THEME.layout.minTouchTarget, // >= 48px
    borderWidth: 1,
    borderColor: THEME.colors.controlBorder,
    borderRadius: THEME.layout.controlRadius,
    paddingHorizontal: 12,
    fontSize: 14,
    color: THEME.colors.ink,
    backgroundColor: THEME.colors.canvas,
  },
  buttonStack: {
    gap: 8,
  },
  button: {
    minHeight: THEME.layout.minTouchTarget, // strictly >= 48px
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: THEME.layout.buttonRadius,
    paddingHorizontal: 16,
  },
  primaryButton: {
    backgroundColor: THEME.colors.brandRouge,
  },
  primaryButtonText: {
    color: THEME.colors.textOnAction,
    fontWeight: '700',
    fontSize: 14,
  },
  secondaryButton: {
    backgroundColor: THEME.colors.surfaceStrong,
    borderWidth: 1,
    borderColor: THEME.colors.line,
  },
  secondaryButtonText: {
    color: THEME.colors.ink,
    fontWeight: '600',
    fontSize: 13,
  },
  outlineButton: {
    borderWidth: 1,
    borderColor: THEME.colors.line,
    backgroundColor: 'transparent',
  },
  outlineButtonText: {
    color: THEME.colors.inkSoft,
    fontWeight: '500',
    fontSize: 13,
  },
});

export default MockScanHarness;
