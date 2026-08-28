<script setup>
// C2 胶囊详情/编辑骨架（对应 TC-C03）
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '../api/http'

const route = useRoute()
const router = useRouter()
const capsule = ref(null)

onMounted(async () => {
  capsule.value = await http.get(`/capsules/${route.params.id}`)
})
</script>

<template>
  <div v-if="capsule">
    <van-nav-bar left-arrow title="胶囊详情" @click-left="router.back()" />
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
  </div>
</template>
