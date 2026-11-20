import React from 'react';
import { View, StyleSheet, StatusBar } from 'react-native';
import { TabNavigator } from './src/navigation/TabNavigator';
import { THEME } from './src/constants/theme';

export function App() {
  return (
    <View style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor={THEME.colors.canvas} />
      <TabNavigator studentId="24-00123" />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: THEME.colors.canvas,
  },
});

export default App;
