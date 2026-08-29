<script setup>
// C2 胶囊详情/编辑/删除（T3.4，对应 TC-C03、AC-06）
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog } from 'vant'
import http from '../api/http'

const route = useRoute()
const router = useRouter()
const capsule = ref(null)
const editing = ref(false)
const theme = ref('')
const stepsText = ref('')
const tagsText = ref('')

onMounted(load)

async function load() {
  capsule.value = await http.get(`/capsules/${route.params.id}`)
}

function startEdit() {
  theme.value = capsule.value.theme
  stepsText.value = capsule.value.steps.join('\n')
  tagsText.value = capsule.value.tags.join(' ')
  editing.value = true
}

async function save() {
  capsule.value = await http.patch(`/capsules/${capsule.value.id}`, {
    theme: theme.value,
    steps: stepsText.value.split('\n').map((s) => s.trim()).filter(Boolean),
    tags: tagsText.value.split(/[\s,，、]+/).filter(Boolean),
  })
  editing.value = false
}

async function remove() {
  try {
    await showConfirmDialog({ title: '删除胶囊', message: '删除后不可恢复，确定删除吗？' })
  } catch {
    return // 用户取消
  }
  await http.delete(`/capsules/${capsule.value.id}`)
  router.replace('/')
}
</script>

<template>
  <div v-if="capsule">
    <van-nav-bar left-arrow title="胶囊详情" @click-left="router.back()">
      <template #right>
        <span style="margin-right: 12px" @click="startEdit">编辑</span>
        <span @click="remove">删除</span>
      </template>
    </van-nav-bar>

    <template v-if="!editing">
      <van-cell-group inset>
        <van-cell title="核心主题" :value="capsule.theme" />
        <van-cell title="垂类" :value="capsule.category" />
        <van-cell title="关键变量" :label="capsule.variables.join('；') || '—'" />
      </van-cell-group>
      <van-cell-group inset title="步骤清单">
        <van-cell v-for="(s, i) in capsule.steps" :key="i" :title="`${i + 1}. ${s}`" />
      </van-cell-group>
      <van-cell-group inset>
        <van-cell title="标签" :value="capsule.tags.join('、')" />
        <van-cell
          title="原文"
          :value="capsule.video.title || capsule.video.source_url || '—'"
          is-link
          :url="capsule.video.source_url || undefined"
        />
      </van-cell-group>
    </template>

    <van-cell-group v-else inset>
      <van-field v-model="theme" label="核心主题" />
      <van-field
        v-model="stepsText"
        label="步骤"
        type="textarea"
        rows="6"
        placeholder="每行一条"
      />
      <van-field v-model="tagsText" label="标签" placeholder="空格/逗号分隔" />
      <div style="display: flex; gap: 12px; padding: 12px 16px">
        <van-button type="primary" size="small" @click="save">保存</van-button>
        <van-button size="small" @click="editing = false">取消</van-button>
      </div>
    </van-cell-group>
  </div>
</template>
