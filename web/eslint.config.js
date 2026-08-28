import pluginVue from 'eslint-plugin-vue'

export default [
  ...pluginVue.configs['flat/recommended'],
  {
    rules: {
      // App.vue 等单词组件名在骨架期允许；T3.4 收敛时再改
      'vue/multi-word-component-names': 'off',
    },
  },
]
