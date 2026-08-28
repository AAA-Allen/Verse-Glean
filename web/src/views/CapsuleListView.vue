<script setup>
// C2 胶囊流骨架：分页列表 + 标签筛选（对应 TC-C02）
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'

const router = useRouter()
const items = ref([])
const total = ref(0)
const page = ref(1)
const tag = ref('')

async function load() {
  // TODO(T3.4): 下拉刷新/触底加载/关键词搜索框
  const data = await http.get('/capsules', { params: { page: page.value, tag: tag.value || undefined } })
  items.value = data.items
  total.value = data.total
}

onMounted(load)
</script>

<template>
  <div>
    <van-nav-bar title="知识胶囊" right-text="图谱" @click-right="router.push('/graph')" />
    <van-search v-model="tag" placeholder="按标签筛选" @search="load" />
    <van-cell-group inset>
      <van-cell
        v-for="item in items"
        :key="item.id"
        :title="item.theme"
        :label="item.tags.join(' · ')"
        is-link
        @click="router.push(`/capsules/${item.id}`)"
      />
    </van-cell-group>
    <van-empty v-if="!items.length" description="还没有胶囊，去 App 分享一条视频吧" />
  </div>
</template>
