import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView } from 'react-native';
import { THEME } from '../constants/theme';
import { ScannerScreen } from '../screens/ScannerScreen';

export type ActiveTab = 'Home' | 'Schedule' | 'Scan' | 'Profile';

export interface TabNavigatorProps {
  studentId?: string;
}

/**
 * 4-Tab Bottom Navigation Container.
 * Tabs: Home, Schedule, Scan, Profile.
 * Strictly adheres to:
 * - 72px navigation track height
 * - WCAG 2.2 touch targets >= 48px
 * - Prominent center thumb-zone presence scanner
 */
export const TabNavigator: React.FC<TabNavigatorProps> = ({ studentId = '24-00123' }) => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('Scan');

  const renderScreen = () => {
    switch (activeTab) {
      case 'Scan':
        return <ScannerScreen studentId={studentId} />;

      case 'Home':
        return (
          <View style={styles.placeholderContainer}>
            <View style={styles.card}>
              <Text style={styles.cardBadge}>Active Semester 2026–2027</Text>
              <Text style={styles.cardTitle}>Welcome back, Student!</Text>
              <Text style={styles.cardBody}>
                Your next class is <Text style={styles.bold}>CC-IPT2</Text> in room{' '}
                <Text style={styles.bold}>PRRC 301</Text> at 08:00 AM.
              </Text>
            </View>
          </View>
        );

      case 'Schedule':
        return (
          <View style={styles.placeholderContainer}>
            <View style={styles.card}>
              <Text style={styles.cardBadge}>Miller's Law Chunked Timetable</Text>
              <Text style={styles.cardTitle}>My Weekly Schedule</Text>
              <Text style={styles.cardBody}>
                Mon–Sat 07:00–19:00 continuous 30-min slots. Offline cached via SQLite.
              </Text>
            </View>
          </View>
        );

      case 'Profile':
        return (
          <View style={styles.placeholderContainer}>
            <View style={styles.card}>
              <Text style={styles.cardBadge}>Pamantasan ng Montalban</Text>
              <Text style={styles.cardTitle}>Student Profile</Text>
              <Text style={styles.cardBody}>
                Student ID: <Text style={styles.bold}>{studentId}</Text>
                {'\n'}Status: Enrolled (BSIT 3rd Year)
              </Text>
            </View>
          </View>
        );
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Active Screen Body */}
      <View style={styles.screenContainer}>{renderScreen()}</View>

      {/* 72px Bottom Navigation Bar */}
      <View style={styles.tabBar}>
        {/* Home Tab */}
        <TouchableOpacity
          style={styles.tabItem}
          onPress={() => setActiveTab('Home')}
          accessibilityRole="button"
          accessibilityLabel="Navigate to Home Tab"
        >
          <View style={[styles.tabContent, activeTab === 'Home' && styles.tabContentActive]}>
            <Text style={[styles.tabLabel, activeTab === 'Home' && styles.tabLabelActive]}>
              Home
            </Text>
          </View>
        </TouchableOpacity>

        {/* Schedule Tab */}
        <TouchableOpacity
          style={styles.tabItem}
          onPress={() => setActiveTab('Schedule')}
          accessibilityRole="button"
          accessibilityLabel="Navigate to Schedule Tab"
        >
          <View style={[styles.tabContent, activeTab === 'Schedule' && styles.tabContentActive]}>
            <Text style={[styles.tabLabel, activeTab === 'Schedule' && styles.tabLabelActive]}>
              Schedule
            </Text>
          </View>
        </TouchableOpacity>

        {/* Scan Tab (Thumb-Zone Centerpiece) */}
        <TouchableOpacity
          style={styles.centerScanItem}
          onPress={() => setActiveTab('Scan')}
          accessibilityRole="button"
          accessibilityLabel="Scan Attendance QR"
        >
          <View style={[styles.scanCircle, activeTab === 'Scan' && styles.scanCircleActive]}>
            <Text style={styles.scanCircleText}>SCAN</Text>
          </View>
        </TouchableOpacity>

        {/* Profile Tab */}
        <TouchableOpacity
          style={styles.tabItem}
          onPress={() => setActiveTab('Profile')}
          accessibilityRole="button"
          accessibilityLabel="Navigate to Profile Tab"
        >
          <View style={[styles.tabContent, activeTab === 'Profile' && styles.tabContentActive]}>
            <Text style={[styles.tabLabel, activeTab === 'Profile' && styles.tabLabelActive]}>
              Profile
            </Text>
          </View>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.canvas,
  },
  screenContainer: {
    flex: 1,
  },
  tabBar: {
    height: THEME.layout.bottomNavHeight, // strictly 72px
    flexDirection: 'row',
    backgroundColor: THEME.colors.surface,
    borderTopWidth: 1,
    borderTopColor: THEME.colors.line,
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: 8,
  },
  tabItem: {
    flex: 1,
    height: THEME.layout.bottomNavHeight,
    minHeight: THEME.layout.minTouchTarget, // >= 48px
    justifyContent: 'center',
    alignItems: 'center',
  },
  tabContent: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    minHeight: THEME.layout.minTouchTarget,
    justifyContent: 'center',
    alignItems: 'center',
  },
  tabContentActive: {
    backgroundColor: THEME.colors.brandRose,
  },
  tabLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: THEME.colors.inkSoft,
  },
  tabLabelActive: {
    color: THEME.colors.brandRouge,
    fontWeight: '700',
  },
  centerScanItem: {
    width: 68,
    height: THEME.layout.bottomNavHeight,
    minHeight: THEME.layout.minTouchTarget,
    justifyContent: 'center',
    alignItems: 'center',
  },
  scanCircle: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: THEME.colors.brandMidnight,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: THEME.colors.brandMidnight,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  scanCircleActive: {
    backgroundColor: THEME.colors.brandRouge,
  },
  scanCircleText: {
    color: THEME.colors.textOnAction,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  placeholderContainer: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  card: {
    backgroundColor: THEME.colors.surface,
    padding: 24,
    borderRadius: THEME.layout.cardRadius,
    borderWidth: 1,
    borderColor: THEME.colors.line,
  },
  cardBadge: {
    fontSize: 11,
    fontWeight: '700',
    color: THEME.colors.brandRouge,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 6,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: THEME.colors.ink,
    marginBottom: 8,
  },
  cardBody: {
    fontSize: 14,
    color: THEME.colors.inkSoft,
    lineHeight: 20,
  },
  bold: {
    fontWeight: '700',
    color: THEME.colors.ink,
  },
});

export default TabNavigator;
