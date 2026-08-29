<script setup>
// C3 3D 知识图谱：3d-force-graph（TECHNICAL_DESIGN 选型：内置力导向，免手写物理引擎）
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ForceGraph from '3d-force-graph'
import http from '../api/http'

const router = useRouter()
const container = ref(null)
const loading = ref(true)
const empty = ref(false)
const CATEGORY_COLORS = { step: '#4f8ef7', config: '#f7a94f', theory: '#7bc86c' }
const CATEGORY_NAMES = { step: '步骤教程', config: '配置清单', theory: '理论概念' }

onMounted(async () => {
  const data = await http.get('/graph')
  loading.value = false
  empty.value = data.nodes.length === 0
  if (empty.value) return

  // 关键：loading 消失后容器 div 在下一个 tick 才挂载，直接取 ref 是 null（实测踩坑）
  await nextTick()

  const graph = ForceGraph()(container.value)
    .nodeLabel((n) => `${n.theme}\n[${CATEGORY_NAMES[n.category] || n.category}]`)
    .nodeColor((n) => CATEGORY_COLORS[n.category] || '#999')
    .nodeVal((n) => 1 + n.degree)
    .linkLabel((e) => `相似度 ${e.similarity}`)
    .linkOpacity(0.35)
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
    <van-empty
      v-else-if="empty"
      description="还没有胶囊，去 App 分享几条视频，让星空亮起来"
    />
    <template v-else>
      <div ref="container" class="graph"></div>
      <div class="legend">
        <span v-for="(name, key) in CATEGORY_NAMES" :key="key">
          <i :style="{ background: CATEGORY_COLORS[key] }"></i>{{ name }}
        </span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.graph { width: 100vw; height: calc(100vh - 46px); }
.loading { margin-top: 40vh; }
.legend {
  position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 16px; color: #ccc; font-size: 12px;
  background: rgba(0, 0, 24, 0.7); padding: 6px 14px; border-radius: 10px;
}
.legend i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
</style>
