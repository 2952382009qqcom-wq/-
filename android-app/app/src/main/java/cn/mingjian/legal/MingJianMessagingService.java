package cn.mingjian.legal;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.os.Build;

import androidx.core.app.NotificationCompat;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

public final class MingJianMessagingService extends FirebaseMessagingService {
    private static final String CHANNEL_ID = "mingjian_messages";

    @Override
    public void onMessageReceived(RemoteMessage message) {
        String route = message.getData().getOrDefault("route", "/");
        Intent intent = new Intent(this, MainActivity.class)
                .setAction(Intent.ACTION_VIEW)
                .putExtra("notification_route", route)
                .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, route.hashCode(), intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(new NotificationChannel(CHANNEL_ID, "明鉴消息", NotificationManager.IMPORTANCE_DEFAULT));
        }
        // The server defaults to generic lock-screen text to avoid leaking legal content.
        String title = message.getNotification() == null ? "明鉴有新消息" : message.getNotification().getTitle();
        String body = message.getNotification() == null ? "打开明鉴查看详情" : message.getNotification().getBody();
        manager.notify(message.getMessageId() == null ? route.hashCode() : message.getMessageId().hashCode(),
                new NotificationCompat.Builder(this, CHANNEL_ID)
                        .setSmallIcon(R.drawable.ic_launcher_foreground)
                        .setContentTitle(title).setContentText(body).setAutoCancel(true)
                        .setContentIntent(pendingIntent).build());
    }
}
