# Proguard Rules untuk Google Mobile Ads
-keep public class com.google.android.gms.ads.** {
  public *;
}

-keep public class com.google.ads.** {
  public *;
}

-keepattributes *Annotation*
-keepattributes Signature
-keep class * extends java.util.ListResourceBundle {
    protected Object[][] getContents();
}

-keep public class com.dragonarrowescape.game.** {
  public *;
}