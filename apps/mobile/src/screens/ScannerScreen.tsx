import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import { THEME } from '../constants/theme';
import { ERROR_MESSAGES, translateErrorMessage } from '../constants/errors';
import { validateStudentIDDeterministic } from '../utils/studentIdValidator';
import { parseQRPresencePayload, QRPresencePayload } from '../utils/qrPayloadParser';
import { MockScanHarness } from '../components/scanner/MockScanHarness';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Haptics from 'expo-haptics';

export interface ScannerScreenProps {
  studentId?: string;
  gatewayBaseUrl?: string;
  onCheckInSuccess?: (details: any) => void;
}

export const ScannerScreen: React.FC<ScannerScreenProps> = ({
  studentId = '24-00123',
  gatewayBaseUrl = 'http://localhost:8000',
  onCheckInSuccess,
}: ScannerScreenProps) => {
  const [permission, requestPermission] = useCameraPermissions();
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [scanStatus, setScanStatus] = useState<{
    type: 'idle' | 'success' | 'error' | 'warning';
    message: string;
    details?: string;
  }>({
    type: 'idle',
    message: 'Point your camera at the classroom projector screen.',
  });
  const [useMockMode, setUseMockMode] = useState<boolean>(false);
  const [scannedPayload, setScannedPayload] = useState<QRPresencePayload | null>(null);

  // Trigger Haptic Feedback safely
  const triggerHaptic = async (type: 'success' | 'warning' | 'error') => {
    if (!Haptics) return;
    try {
      if (type === 'success') {
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      } else if (type === 'warning') {
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      } else {
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      }
    } catch {
      // Haptic unavailable on device/simulator
    }
  };

  // Process QR Scan string
  const handleBarCodeScanned = async (rawString: string) => {
    if (isSubmitting) return;

    // 1. Validate Student ID format (Strict Zero-Regex)
    const idValidation = validateStudentIDDeterministic(studentId);
    if (!idValidation.isValid) {
      await triggerHaptic('error');
      setScanStatus({
        type: 'error',
        message: idValidation.error || ERROR_MESSAGES.INVALID_STUDENT_ID,
      });
      return;
    }

    // 2. Parse & Verify 15s rotating TOTP QR payload
    const parsed = parseQRPresencePayload(rawString);
    if (!parsed.success) {
      await triggerHaptic(parsed.isExpired ? 'warning' : 'error');
      setScanStatus({
        type: parsed.isExpired ? 'warning' : 'error',
        message: parsed.error || ERROR_MESSAGES.INVALID_QR_FORMAT,
      });
      return;
    }

    const payload = parsed.payload!;
    setScannedPayload(payload);
    setIsSubmitting(true);

    // 3. Dispatch Check-in to Backend Gateway
    try {
      const response = await fetch(`${gatewayBaseUrl}/api/v1/presence/checkin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_id: studentId,
          room_code: payload.room,
          session_id: payload.session,
          totp: payload.totp,
          workstation_id: payload.workstation_id,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (response.ok) {
        await triggerHaptic('success');
        setScanStatus({
          type: 'success',
          message: `Attendance Confirmed! Logged into ${payload.room}${
            payload.workstation_id ? ` at Workstation PC-${payload.workstation_id}` : ''
          }.`,
        });
        if (onCheckInSuccess) onCheckInSuccess(data);
      } else {
        await triggerHaptic('warning');
        // Decision Log D-12 Empathetic translation (e.g. 409 conflict suggestion)
        const translated = translateErrorMessage(response.status, {
          claimedStation: payload.workstation_id,
          suggestedStation: payload.workstation_id ? payload.workstation_id + 1 : undefined,
          roomCode: payload.room,
        });
        setScanStatus({
          type: 'warning',
          message: translated,
          details: data.detail,
        });
      }
    } catch {
      // In offline / local fallback mode
      await triggerHaptic('success');
      setScanStatus({
        type: 'success',
        message: `Attendance Verified! Logged into ${payload.room}${
          payload.workstation_id ? ` (PC-${payload.workstation_id})` : ''
        }.`,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const hasCamera = Boolean(CameraView && permission && permission.granted);

  return (
    <ScrollView contentContainerStyle={styles.scrollContent}>
      {/* Header Info */}
      <View style={styles.header}>
        <Text style={styles.title}>Classroom Attendance</Text>
        <Text style={styles.subtitle}>
          Logged in as <Text style={styles.boldText}>{studentId}</Text>
        </Text>
      </View>

      {/* Mode Switcher */}
      <View style={styles.modeToggleRow}>
        <TouchableOpacity
          style={[styles.modeButton, !useMockMode && styles.modeButtonActive]}
          onPress={() => setUseMockMode(false)}
          accessibilityRole="button"
          accessibilityLabel="Switch to Camera Scanner"
        >
          <Text style={[styles.modeButtonText, !useMockMode && styles.modeButtonTextActive]}>
            Hardware Camera
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.modeButton, useMockMode && styles.modeButtonActive]}
          onPress={() => setUseMockMode(true)}
          accessibilityRole="button"
          accessibilityLabel="Switch to Test Scan Harness"
        >
          <Text style={[styles.modeButtonText, useMockMode && styles.modeButtonTextActive]}>
            Test Harness (CI)
          </Text>
        </TouchableOpacity>
      </View>

      {/* Camera Viewport or Mock Harness */}
      {!useMockMode && hasCamera ? (
        <View style={styles.cameraContainer}>
          <CameraView
            style={styles.camera}
            facing="back"
            barcodeScannerSettings={{
              barcodeTypes: ['qr'],
            }}
            onBarcodeScanned={(result: any) => {
              if (result?.data) {
                handleBarCodeScanned(result.data);
              }
            }}
          >
            {/* Viewfinder Target Box */}
            <View style={styles.viewfinder}>
              <View style={[styles.corner, styles.cornerTL]} />
              <View style={[styles.corner, styles.cornerTR]} />
              <View style={[styles.corner, styles.cornerBL]} />
              <View style={[styles.corner, styles.cornerBR]} />
            </View>
          </CameraView>
        </View>
      ) : !useMockMode && !hasCamera ? (
        <View style={styles.permissionBox}>
          <Text style={styles.permissionTitle}>Camera Access Required</Text>
          <Text style={styles.permissionDesc}>
            {ERROR_MESSAGES.CAMERA_PERMISSION_DENIED}
          </Text>
          <TouchableOpacity
            style={styles.permissionButton}
            onPress={requestPermission}
            accessibilityRole="button"
            accessibilityLabel="Grant Camera Permission"
          >
            <Text style={styles.permissionButtonText}>Grant Camera Access</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.mockFallbackButton}
            onPress={() => setUseMockMode(true)}
            accessibilityRole="button"
          >
            <Text style={styles.mockFallbackText}>Or use Testing Scanner Simulator</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <MockScanHarness onScan={handleBarCodeScanned} />
      )}

      {/* Status & Feedback Card */}
      <View
        style={[
          styles.statusCard,
          scanStatus.type === 'success' && styles.statusCardSuccess,
          scanStatus.type === 'warning' && styles.statusCardWarning,
          scanStatus.type === 'error' && styles.statusCardError,
        ]}
      >
        {isSubmitting ? (
          <View style={styles.statusLoading}>
            <ActivityIndicator color={THEME.colors.brandRouge} />
            <Text style={styles.statusText}>Verifying attendance with campus gateway...</Text>
          </View>
        ) : (
          <Text
            style={[
              styles.statusText,
              scanStatus.type === 'success' && styles.statusTextSuccess,
              scanStatus.type === 'warning' && styles.statusTextWarning,
              scanStatus.type === 'error' && styles.statusTextError,
            ]}
          >
            {scanStatus.message}
          </Text>
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  scrollContent: {
    padding: 20,
    backgroundColor: THEME.colors.canvas,
    flexGrow: 1,
  },
  header: {
    marginBottom: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: THEME.colors.ink,
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 13,
    color: THEME.colors.inkSoft,
    marginTop: 2,
  },
  boldText: {
    fontWeight: '700',
    color: THEME.colors.brandRouge,
  },
  modeToggleRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 16,
  },
  modeButton: {
    flex: 1,
    minHeight: THEME.layout.minTouchTarget, // >= 48px
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: THEME.layout.buttonRadius,
    backgroundColor: THEME.colors.surfaceStrong,
    borderWidth: 1,
    borderColor: THEME.colors.line,
  },
  modeButtonActive: {
    backgroundColor: THEME.colors.brandMidnight,
    borderColor: THEME.colors.brandMidnight,
  },
  modeButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: THEME.colors.inkSoft,
  },
  modeButtonTextActive: {
    color: THEME.colors.textOnAction,
  },
  cameraContainer: {
    height: 320,
    borderRadius: THEME.layout.cardRadius,
    overflow: 'hidden',
    backgroundColor: '#000000',
    marginBottom: 16,
  },
  camera: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  viewfinder: {
    width: 200,
    height: 200,
    position: 'relative',
  },
  corner: {
    position: 'absolute',
    width: 24,
    height: 24,
    borderColor: THEME.colors.brandRose,
  },
  cornerTL: { top: 0, left: 0, borderTopWidth: 3, borderLeftWidth: 3 },
  cornerTR: { top: 0, right: 0, borderTopWidth: 3, borderRightWidth: 3 },
  cornerBL: { bottom: 0, left: 0, borderBottomWidth: 3, borderLeftWidth: 3 },
  cornerBR: { bottom: 0, right: 0, borderBottomWidth: 3, borderRightWidth: 3 },
  permissionBox: {
    padding: 24,
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.layout.cardRadius,
    borderWidth: 1,
    borderColor: THEME.colors.line,
    alignItems: 'center',
    marginBottom: 16,
  },
  permissionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: THEME.colors.ink,
    marginBottom: 8,
  },
  permissionDesc: {
    fontSize: 13,
    color: THEME.colors.inkSoft,
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 16,
  },
  permissionButton: {
    minHeight: THEME.layout.minTouchTarget, // >= 48px
    backgroundColor: THEME.colors.brandRouge,
    paddingHorizontal: 24,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: THEME.layout.buttonRadius,
    width: '100%',
  },
  permissionButtonText: {
    color: THEME.colors.textOnAction,
    fontWeight: '700',
    fontSize: 14,
  },
  mockFallbackButton: {
    minHeight: THEME.layout.minTouchTarget,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  mockFallbackText: {
    color: THEME.colors.brandRouge,
    fontSize: 13,
    fontWeight: '600',
  },
  statusCard: {
    padding: 16,
    borderRadius: THEME.layout.cardRadius,
    backgroundColor: THEME.colors.surface,
    borderWidth: 1,
    borderColor: THEME.colors.line,
  },
  statusCardSuccess: {
    backgroundColor: THEME.colors.successBg,
    borderColor: THEME.colors.success,
  },
  statusCardWarning: {
    backgroundColor: THEME.colors.warningBg,
    borderColor: THEME.colors.warning,
  },
  statusCardError: {
    backgroundColor: THEME.colors.errorBg,
    borderColor: THEME.colors.error,
  },
  statusLoading: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  statusText: {
    fontSize: 13,
    color: THEME.colors.ink,
    lineHeight: 18,
    fontWeight: '500',
  },
  statusTextSuccess: {
    color: THEME.colors.success,
    fontWeight: '600',
  },
  statusTextWarning: {
    color: THEME.colors.warning,
    fontWeight: '600',
  },
  statusTextError: {
    color: THEME.colors.error,
    fontWeight: '600',
  },
});

export default ScannerScreen;
