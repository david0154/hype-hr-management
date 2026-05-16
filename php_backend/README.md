# PHP Backend — DEPRECATED

> ⚠️ **This PHP backend is no longer used.**
>
> All salary slip generation is now handled **on-device** by the Android app.
> The Python admin app handles all Firestore operations directly.
>
> ## What replaced it
> | Old PHP File | Replaced By |
> |---|---|
> | `cron_job.php` | `SalarySlipReminderWorker.kt` (WorkManager, fires on 1st of month) |
> | `salary_generator.php` | `SalarySlipActivity.kt` (on-device, no storage) |
> | `mailer.php` | Not needed — slip shared via Android Share Intent |
> | `sms_service.php` | Not needed — notification via Android NotificationManager |
> | `firebase_api.php` | Direct Firestore SDK in Python + Kotlin |
>
> ## How to remove
> Simply delete the `php_backend/` folder. No server hosting needed.
>
> _Developed by David | Nexuzy Lab | nexuzylab@gmail.com_
