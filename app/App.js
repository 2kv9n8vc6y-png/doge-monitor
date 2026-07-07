import React, { useEffect, useState, useCallback } from "react";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabsNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import { Platform, Alert } from "react-native";

import ReportScreen from "./src/screens/ReportScreen";
import SettingsScreen from "./src/screens/SettingsScreen";

const Tab = createBottomTabsNavigator();

// Configure notification behavior when app is in foreground
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

// Register for push notifications and return the Expo push token
async function registerForPushNotifications() {
  if (!Device.isDevice) {
    console.log("Push notifications require a physical device");
    return null;
  }

  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("doge-reports", {
      name: "DOGE 报告",
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#f5a623",
    });
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    Alert.alert("权限被拒绝", "无法发送推送通知，请在系统设置中开启通知权限。");
    return null;
  }

  const tokenData = await Notifications.getExpoPushTokenAsync({
    projectId: null, // will be set by EAS or expo go
  });

  return tokenData.data;
}

export default function App() {
  const [pushToken, setPushToken] = useState(null);
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    // Register for push on app start
    registerForPushNotifications().then((token) => {
      if (token) {
        setPushToken(token);
        console.log("Expo Push Token:", token);
      }
    });

    // Listen for incoming notifications
    const receivedSub = Notifications.addNotificationReceivedListener((n) => {
      setNotification(n);
    });

    const responseSub = Notifications.addNotificationResponseReceivedListener(
      (_response) => {
        // Handle notification tap — could navigate to report tab
      }
    );

    return () => {
      receivedSub.remove();
      responseSub.remove();
    };
  }, []);

  const clearNotification = useCallback(() => {
    setNotification(null);
  }, []);

  return (
    <NavigationContainer>
      <StatusBar style="light" />
      <Tab.Navigator
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: "#f5a623",
          tabBarInactiveTintColor: "#666",
          tabBarStyle: {
            backgroundColor: "#1a1a2e",
            borderTopColor: "#2a2a4a",
            borderTopWidth: 1,
            paddingBottom: 8,
            paddingTop: 8,
            height: 60,
          },
          tabBarLabelStyle: {
            fontSize: 12,
            fontWeight: "600",
          },
        }}
      >
        <Tab.Screen
          name="Report"
          options={{
            tabBarLabel: "报告",
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="analytics" size={size} color={color} />
            ),
          }}
        >
          {(props) => (
            <ReportScreen
              {...props}
              notification={notification}
              onClearNotification={clearNotification}
            />
          )}
        </Tab.Screen>
        <Tab.Screen
          name="Settings"
          options={{
            tabBarLabel: "设置",
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="settings-outline" size={size} color={color} />
            ),
          }}
        >
          {(props) => (
            <SettingsScreen {...props} pushToken={pushToken} />
          )}
        </Tab.Screen>
      </Tab.Navigator>
    </NavigationContainer>
  );
}
