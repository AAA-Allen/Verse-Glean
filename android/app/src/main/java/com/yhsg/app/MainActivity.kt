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

    // 可观察状态放 Activity 字段，onResume 重新评估（从系统设置页授权返回后自动刷新）
    private var hasOverlay by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        hasOverlay = Settings.canDrawOverlays(this)
        setContent {
            MaterialTheme {
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
                            }) { Text("去授权") }
                        } else {
                            Text("胶囊列表（T2.6 实现）")
                        }
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        hasOverlay = Settings.canDrawOverlays(this)
    }
}
