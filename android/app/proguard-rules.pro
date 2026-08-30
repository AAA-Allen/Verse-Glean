# Retrofit/Gson 模型保持
-keep class com.yhsg.app.network.** { *; }
-keepattributes Signature
-keepattributes *Annotation*

# security-crypto 依赖的 Tink 引用了编译期注解，运行时 classpath 不需要（review8）
-dontwarn com.google.errorprone.annotations.**
