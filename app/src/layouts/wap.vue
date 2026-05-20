<template>
  <div class="wap-layout">
    <nuxt />
  </div>
</template>

<script>
export default {
  name: 'WapLayout',
  head() {
    return {
      title: 'Talebook WAP',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no' }
      ]
    };
  }
};
</script>

<style scoped>
.wap-layout {
  min-height: 100vh;
  background-color: #f5f5f5;
}
</style>
