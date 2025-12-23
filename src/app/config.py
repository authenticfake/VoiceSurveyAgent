*** BEGIN FILE: src/app/config.py
@@
 class Settings(BaseSettings):
@@
     # CORS
     cors_origins: str = Field(
         default="http://localhost:3000",
         description="Comma-separated list of allowed CORS origins",
     )
+
+    # Scheduler (REQ-008 runtime wiring)
+    scheduler_enabled: bool = Field(
+        default=False,
+        description="Enable background call scheduler loop at app startup.",
+    )
+    scheduler_interval_seconds: int = Field(
+        default=60,
+        ge=5,
+        le=3600,
+        description="Scheduler tick interval in seconds.",
+    )
+    scheduler_lock_key: str = Field(
+        default="voicesurveyagent_scheduler_v1",
+        description="Stable key used to derive the Postgres advisory lock id.",
+    )
*** END FILE