// eslint-disable-next-line no-undef
importScripts("https://www.gstatic.com/firebasejs/8.10.0/firebase-app.js");
// eslint-disable-next-line no-undef
importScripts(
    "https://www.gstatic.com/firebasejs/8.10.0/firebase-messaging.js"
);

const firebaseConfig = {
    apiKey: "BDDnshDPlAqZy2OH1t9_7smH3Xkmxu6gYkjrflzNRq5GKpZqxOM93KxTdUSSalhHH_eXz8T5anWQVSGjIUCAmOo",
    authDomain: "push--notification-6906d.firebaseapp.com",
    projectId: "push--notification-6906d",
    storageBucket: "push--notification-6906d.appspot.com",
    messagingSenderId: "793596879023",
    appId: "1:793596879023:web:58734d828f3a0b1438b45a"
};


// eslint-disable-next-line no-undef
firebase.initializeApp(firebaseConfig);
// eslint-disable-next-line no-undef
const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
    console.log(
        "[firebase-messaging-sw.js] Received background message ",
        payload
    );
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: payload.notification.image,
    };

    // eslint-disable-next-line no-restricted-globals
    self.registration.showNotification(notificationTitle, notificationOptions);
});