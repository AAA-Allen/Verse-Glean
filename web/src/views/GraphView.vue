<script setup>
// C3 3D 知识图谱骨架：3d-force-graph（TECHNICAL_DESIGN 选型：内置力导向，免手写物理引擎）
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ForceGraph from '3d-force-graph'
import http from '../api/http'

const router = useRouter()
const container = ref(null)
const loading = ref(true)
const CATEGORY_COLORS = { step: '#4f8ef7', config: '#f7a94f', theory: '#7bc86c' }

onMounted(async () => {
  const data = await http.get('/graph')
  loading.value = false

  const graph = ForceGraph()(container.value)
    .nodeLabel((n) => n.theme)
    .nodeColor((n) => CATEGORY_COLORS[n.category] || '#999')
    .nodeVal((n) => 1 + n.degree)
    .linkLabel((e) => `相似度 ${e.similarity}`)
    .backgroundColor('#000018')
  graph.graphData(data)
  // C3 下钻：点击节点打开胶囊详情（AC-07）
  graph.onNodeClick((n) => router.push(`/capsules/${n.id}`))
})
</script>

<template>
  <div>
    <van-nav-bar left-arrow title="知识星空" @click-left="$router.back()" />
    <van-loading v-if="loading" class="loading" vertical>加载图谱…</van-loading>
    <div ref="container" class="graph"></div>
  </div>
</template>

<style scoped>
.graph { width: 100vw; height: calc(100vh - 46px); }
.loading { margin-top: 40vh; }
</style>
