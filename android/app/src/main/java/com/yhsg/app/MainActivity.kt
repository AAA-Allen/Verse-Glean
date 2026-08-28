package com.yhsg.app

import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/**
 * 主界面骨架：权限引导 + 胶囊列表占位。
 * TODO(T2.6): Compose 列表/详情/编辑页；TODO(T2.1): 接 Retrofit 真实数据。
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                var hasOverlay by remember { mutableStateOf(Settings.canDrawOverlays(this)) }
                Scaffold(
                    topBar = { TopAppBar(title = { Text("影海拾光") }) },
                ) { padding ->
                    Column(
                        Modifier.padding(padding).padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        if (!hasOverlay) {
                            Text("悬浮球需要「显示在其他应用上层」权限")
                            Button(onClick = {
                                startActivity(
                                    Intent(
                                        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                        android.net.Uri.parse("package:$packageName"),
                                    )
                                )
                                hasOverlay = Settings.canDrawOverlays(this@MainActivity)
                            }) { Text("去授权") }
                        } else {
                            Text("胶囊列表（T2.6 实现）")
                        }
                    }
                }
            }
        }
    }
}
