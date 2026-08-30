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
import com.yhsg.app.network.LoginBody
import com.yhsg.app.service.FloatingService
import kotlinx.coroutines.launch
import retrofit2.HttpException
import androidx.compose.ui.text.input.PasswordVisualTransformation

/**
 * 主界面：权限引导 → 悬浮球开关 → 胶囊列表/详情/编辑 + 服务器设置（T2.6/T2.7 骨架）。
 */
class MainActivity : ComponentActivity() {

    private val notifPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    // T3.7：MediaProjection 授权弹窗必须由 Activity 发起；授权结果转交前台服务采集
    private val projectionLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == RESULT_OK && result.data != null) {
                startForegroundService(
                    Intent(this, com.yhsg.app.service.CaptureService::class.java).apply {
                        putExtra(com.yhsg.app.service.CaptureService.EXTRA_RESULT_CODE, result.resultCode)
                        putExtra(com.yhsg.app.service.CaptureService.EXTRA_RESULT_DATA, result.data)
                    }
                )
            }
        }

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
        var loginDialog by remember { mutableStateOf(false) }
        var confirmLogout by remember { mutableStateOf(false) }
        var loggedIn by remember { mutableStateOf(prefs.isLoggedIn) }
        val snackbar = remember { SnackbarHostState() }

        fun loadCapsules() {
            scope.launch {
                runCatching { ApiClient.service(prefs).listCapsules() }
                    .onSuccess { capsuleList = it.data.items }
                    .onFailure {
                        scope.launch { snackbar.showSnackbar("加载失败：${errText(it)}") }
                    }
            }
        }

        fun doLogin(username: String, password: String, onErr: (String) -> Unit) {
            scope.launch {
                runCatching { ApiClient.service(prefs).login(LoginBody(username, password)) }
                    .onSuccess { env ->
                        prefs.apiToken = env.data.access_token
                        prefs.refreshToken = env.data.refresh_token
                        prefs.nickname = env.data.user.nickname
                        loggedIn = true
                        loginDialog = false
                        // showSnackbar 会挂起协程，放独立协程避免拖慢列表刷新
                        scope.launch { snackbar.showSnackbar("欢迎，${env.data.user.nickname}") }
                        loadCapsules()
                    }
                    // 登录接口的 401 是密码错误/限流，展示后端的中文 detail 而非"登录已过期"
                    .onFailure { onErr(if (it is HttpException) errDetail(it) ?: errText(it) else errText(it)) }
            }
        }

        LaunchedEffect(Unit) { loadCapsules() }

        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text("影海拾光") },
                    actions = {
                        TextButton(onClick = { serverDialog = true }) { Text("设置") }
                        TextButton(onClick = { if (loggedIn) confirmLogout = true else loginDialog = true }) {
                            Text(if (loggedIn) "退出" else "登录")
                        }
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
                                    .onFailure { snackbar.showSnackbar("保存失败：${errText(it)}") }
                            }
                        },
                    )
                } ?: Column(Modifier.padding(padding).padding(16.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = {
                            startForegroundService(Intent(this@MainActivity, FloatingService::class.java))
                            scope.launch { snackbar.showSnackbar("悬浮球已启动，去视频 App 试试") }
                        }) { Text("启动悬浮球") }
                        OutlinedButton(onClick = {
                            val mpm = getSystemService(MEDIA_PROJECTION_SERVICE)
                                as android.media.projection.MediaProjectionManager
                            projectionLauncher.launch(mpm.createScreenCaptureIntent())
                        }) { Text("捕获当前声音") }
                    }
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
                                            .onFailure { snackbar.showSnackbar("详情加载失败：${errText(it)}") }
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

        if (loginDialog) {
            LoginDialog(
                onDismiss = { loginDialog = false },
                onLogin = { username, password, onErr -> doLogin(username, password, onErr) },
            )
        }

        if (confirmLogout) {
            AlertDialog(
                onDismissRequest = { confirmLogout = false },
                title = { Text("退出登录") },
                text = { Text("确定退出${prefs.nickname.ifEmpty { "当前账号" }}？") },
                confirmButton = {
                    TextButton(onClick = {
                        prefs.logout()
                        loggedIn = false
                        confirmLogout = false
                        capsuleList = emptyList()
                        loadCapsules()
                    }) { Text("退出") }
                },
                dismissButton = { TextButton(onClick = { confirmLogout = false }) { Text("取消") } },
            )
        }
    }

    /** 401 统一转登录提示（release 未登录 / token 过期）；其余保持原始信息。 */
    private fun errText(e: Throwable): String = when {
        e is HttpException && e.code() == 401 -> "未登录或登录已过期，请点右上角「登录」"
        else -> e.message ?: "网络错误"
    }

    /** 后端业务错误体 {"detail": "..."} 里的中文提示（登录接口用）。 */
    private fun errDetail(e: HttpException): String? = try {
        val body = e.response()?.errorBody()?.string()
        org.json.JSONObject(body ?: "").optString("detail").ifEmpty { null }
    } catch (_: Exception) {
        null
    }

    /** 正式版已关闭明文流量：http 地址必然连不上，提前给出解释（第六轮审查 3.1）。 */
    private fun httpHint(url: String): String? =
        if (!BuildConfig.DEBUG && url.startsWith("http://")) {
            "正式版不支持明文 http 连接（安全策略）。请联系服务提供方获取 https 地址，或改用 debug 版联调。"
        } else null

    @Composable
    private fun LoginDialog(
        onDismiss: () -> Unit,
        onLogin: (String, String, (String) -> Unit) -> Unit,
    ) {
        var username by remember { mutableStateOf("") }
        var password by remember { mutableStateOf("") }
        var err by remember { mutableStateOf<String?>(null) }
        AlertDialog(
            onDismissRequest = onDismiss,
            title = { Text("登录影海拾光") },
            text = {
                Column {
                    OutlinedTextField(
                        value = username, onValueChange = { username = it },
                        label = { Text("用户名") }, singleLine = true,
                    )
                    OutlinedTextField(
                        value = password, onValueChange = { password = it },
                        label = { Text("密码") }, singleLine = true,
                        visualTransformation = PasswordVisualTransformation(),
                    )
                    err?.let {
                        Spacer(Modifier.height(8.dp))
                        Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                    }
                }
            },
            confirmButton = { TextButton(onClick = { onLogin(username, password) { err = it } }) { Text("登录") } },
            dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } },
        )
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
                Column {
                    OutlinedTextField(
                        value = text, onValueChange = { text = it },
                        label = { Text("http://192.168.x.x:8000") },
                        singleLine = true,
                    )
                    httpHint(text)?.let {
                        Spacer(Modifier.height(8.dp))
                        Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                    }
                }
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
