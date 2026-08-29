package com.yhsg.app

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.yhsg.app.data.Prefs
import com.yhsg.app.network.ApiClient
import com.yhsg.app.network.CapsuleData
import com.yhsg.app.network.CapsuleSummary
import com.yhsg.app.service.FloatingService
import kotlinx.coroutines.launch

/**
 * 主界面：权限引导 → 悬浮球开关 → 胶囊列表/详情/编辑 + 服务器设置（T2.6/T2.7 骨架）。
 */
class MainActivity : ComponentActivity() {

    private val notifPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
        setContent { App() }
    }

    @OptIn(ExperimentalMaterial3Api::class)
    @Composable
    private fun App() {
        val prefs = remember { Prefs(this) }
        val scope = rememberCoroutineScope()
        var hasOverlay by remember { mutableStateOf(Settings.canDrawOverlays(this)) }
        var selected by remember { mutableStateOf<CapsuleData?>(null) }
        var capsuleList by remember { mutableStateOf<List<CapsuleSummary>>(emptyList()) }
        var serverDialog by remember { mutableStateOf(false) }
        val snackbar = remember { SnackbarHostState() }

        fun loadCapsules() {
            scope.launch {
                runCatching { ApiClient.service(prefs).listCapsules() }
                    .onSuccess { capsuleList = it.data.items }
                    .onFailure {
                        scope.launch { snackbar.showSnackbar("加载失败：${it.message}（检查设置页服务器地址）") }
                    }
            }
        }

        LaunchedEffect(Unit) { loadCapsules() }

        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text("影海拾光") },
                    actions = {
                        TextButton(onClick = { serverDialog = true }) { Text("设置") }
                        TextButton(onClick = { loadCapsules() }) { Text("刷新") }
                    }
                )
            },
            snackbarHost = { SnackbarHost(snackbar) },
        ) { padding ->
            if (!hasOverlay) {
                PermissionGuide(padding) { hasOverlay = Settings.canDrawOverlays(this) }
            } else {
                selected?.let { capsule ->
                    CapsuleDetail(
                        capsule, padding,
                        onBack = { selected = null },
                        onSave = { theme, steps, tags ->
                            scope.launch {
                                runCatching {
                                    ApiClient.service(prefs).updateCapsule(
                                        capsule.id,
                                        com.yhsg.app.network.CapsuleUpsert(
                                            theme = theme, steps = steps, tags = tags
                                        )
                                    )
                                }
                                    .onSuccess { selected = it.data; loadCapsules() }
                                    .onFailure { snackbar.showSnackbar("保存失败：${it.message}") }
                            }
                        },
                    )
                } ?: Column(Modifier.padding(padding).padding(16.dp)) {
                    Button(onClick = {
                        startForegroundService(Intent(this@MainActivity, FloatingService::class.java))
                        scope.launch { snackbar.showSnackbar("悬浮球已启动，去视频 App 试试") }
                    }) { Text("启动悬浮球") }
                    Spacer(Modifier.height(12.dp))
                    if (capsuleList.isEmpty()) {
                        Text("还没有胶囊：去抖音/B站点「分享 → 影海拾光」")
                    }
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(capsuleList, key = { it.id }) { item ->
                            Card(
                                onClick = {
                                    scope.launch {
                                        runCatching { ApiClient.service(prefs).getCapsule(item.id) }
                                            .onSuccess { selected = it.data }
                                            .onFailure { snackbar.showSnackbar("详情加载失败：${it.message}") }
                                    }
                                },
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Column(Modifier.padding(12.dp)) {
                                    Text(item.theme, style = MaterialTheme.typography.titleMedium)
                                    Spacer(Modifier.height(4.dp))
                                    Text(
                                        "${item.category} · ${item.steps_count} 步 · ${item.tags.joinToString(" ") { "#$it" }}",
                                        style = MaterialTheme.typography.bodySmall,
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        if (serverDialog) {
            ServerDialog(
                current = prefs.serverBaseUrl,
                version = BuildConfig.VERSION_NAME,
                onDismiss = { serverDialog = false },
            ) { url ->
                prefs.serverBaseUrl = url
                serverDialog = false
                loadCapsules()
            }
        }
    }

    @Composable
    private fun PermissionGuide(padding: PaddingValues, onChanged: () -> Unit) {
        Column(
            Modifier.padding(padding).padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("悬浮球需要「显示在其他应用上层」权限")
            Spacer(Modifier.height(12.dp))
            Button(onClick = {
                startActivity(
                    Intent(
                        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:$packageName"),
                    )
                )
            }) { Text("去授权") }
            Spacer(Modifier.height(8.dp))
            Button(onClick = { onChanged() }) { Text("我已授权，刷新") }
        }
    }

    @Composable
    private fun ServerDialog(
        current: String,
        version: String,
        onDismiss: () -> Unit,
        onSave: (String) -> Unit,
    ) {
        var text by remember { mutableStateOf(current) }
        AlertDialog(
            onDismissRequest = onDismiss,
            title = { Text("服务器地址（v$version）") },
            text = {
                OutlinedTextField(
                    value = text, onValueChange = { text = it },
                    label = { Text("http://192.168.x.x:8000") },
                    singleLine = true,
                )
            },
            confirmButton = { TextButton(onClick = { onSave(text) }) { Text("保存") } },
            dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
        )
    }

    @Composable
    private fun CapsuleDetail(
        capsule: CapsuleData,
        padding: PaddingValues,
        onBack: () -> Unit,
        onSave: (String, List<String>, List<String>) -> Unit,
    ) {
        var editing by remember { mutableStateOf(false) }
        var theme by remember(capsule.id) { mutableStateOf(capsule.theme) }
        var stepsText by remember(capsule.id) { mutableStateOf(capsule.steps.joinToString("\n")) }
        var tagsText by remember(capsule.id) { mutableStateOf(capsule.tags.joinToString(" ")) }

        Column(Modifier.padding(padding).padding(16.dp)) {
            TextButton(onClick = onBack) { Text("← 返回") }
            Text(capsule.theme, style = MaterialTheme.typography.titleLarge)
            Text(
                "${capsule.category} · ${capsule.video.platform} · ${capsule.video.title ?: "手动文案"}",
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(8.dp))
            Text("关键变量：${capsule.variables.joinToString("；")}")
            Spacer(Modifier.height(8.dp))
            if (editing) {
                OutlinedTextField(theme, { theme = it }, label = { Text("核心主题") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(stepsText, { stepsText = it }, label = { Text("步骤（每行一条）") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(tagsText, { tagsText = it }, label = { Text("标签（空格分隔）") }, modifier = Modifier.fillMaxWidth())
                Row {
                    Button(onClick = {
                        onSave(
                            theme,
                            stepsText.lines().filter { it.isNotBlank() },
                            tagsText.split(" ", "、", ",").filter { it.isNotBlank() },
                        )
                        editing = false
                    }) { Text("保存") }
                    TextButton(onClick = { editing = false }) { Text("取消") }
                }
            } else {
                capsule.steps.forEachIndexed { i, s -> Text("${i + 1}. $s") }
                Spacer(Modifier.height(8.dp))
                Text("标签：${capsule.tags.joinToString(" ") { "#$it" }}", style = MaterialTheme.typography.bodySmall)
                TextButton(onClick = { editing = true }) { Text("编辑") }
            }
        }
    }
}
