/**
 * Firebase Web SDK (modular) — app, Analytics, Firestore.
 * Enable Firestore in the Firebase console and set security rules before production use.
 * https://console.firebase.google.com/project/face-recognization-syste-14265/firestore
 */
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js";
import { getAnalytics, isSupported } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-analytics.js";
import { getFirestore } from "https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyBmgvf_9C02Atv4XJ9njXX6bz03X2FmfM8",
  authDomain: "face-recognization-syste-14265.firebaseapp.com",
  projectId: "face-recognization-syste-14265",
  storageBucket: "face-recognization-syste-14265.firebasestorage.app",
  messagingSenderId: "716699352769",
  appId: "1:716699352769:web:2b22cbb9ed6625d9e9de40",
  measurementId: "G-LWX771B40L",
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

let analytics = null;
isSupported()
  .then((ok) => {
    if (ok) {
      analytics = getAnalytics(app);
    }
  })
  .catch(() => {});

/** For non-module scripts or DevTools: `window.faceAttendanceFirebase` */
window.faceAttendanceFirebase = { app, db, get analytics() {
  return analytics;
} };

window.dispatchEvent(
  new CustomEvent("face-attendance-firebase-ready", {
    detail: { app, db },
  }),
);

console.info("[FaceAttendance] Firebase initialized (Firestore + App).");
