declare namespace React {
  export type ReactNode = any;
  export interface FC<P = {}> {
    (props: P): any;
  }
  export function useState<T>(initial: T | (() => T)): [T, (val: T | ((prev: T) => T)) => void];
  export function useEffect(effect: () => void | (() => void), deps?: any[]): void;
  export function useCallback<T extends (...args: any[]) => any>(fn: T, deps: any[]): T;
  export function useRef<T>(initial: T): { current: T };
}

declare module 'react' {
  export = React;
}

declare module 'react/jsx-runtime' {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: any;
}

declare module 'react-native' {
  export const View: any;
  export const Text: any;
  export const TouchableOpacity: any;
  export const TextInput: any;
  export const StyleSheet: {
    create<T extends Record<string, any>>(styles: T): T;
  };
  export const ScrollView: any;
  export const ActivityIndicator: any;
  export const Alert: any;
  export const StatusBar: any;
  export const SafeAreaView: any;
  export type ViewStyle = any;
  export type TextStyle = any;
  export type ImageStyle = any;
}

declare module 'expo-camera' {
  export const CameraView: any;
  export function useCameraPermissions(): [any, () => Promise<any>];
}

declare module 'expo-haptics' {
  export enum NotificationFeedbackType {
    Success = 'success',
    Warning = 'warning',
    Error = 'error',
  }
  export function notificationAsync(type: NotificationFeedbackType): Promise<void>;
}

declare module 'expo-sqlite' {
  export interface SQLiteDatabase {
    execAsync(sql: string): Promise<void>;
    runAsync(sql: string, ...params: any[]): Promise<any>;
    getAllAsync<T = any>(sql: string, ...params: any[]): Promise<T[]>;
  }
  export function openDatabaseSync(dbName: string): SQLiteDatabase;
}

declare module '@react-navigation/native' {
  export const NavigationContainer: any;
}

declare module '@react-navigation/bottom-tabs' {
  export function createBottomTabNavigator(): any;
}
