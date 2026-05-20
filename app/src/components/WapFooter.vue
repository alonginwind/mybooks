<template>
  <footer class="wap-footer">
    <div class="wap-footer-links">
      <a href="https://github.com/PoxenStudio/talebook" target="_blank">Project</a>
      | <a href="/podcast">Podcast</a>
      | <a href="https://mybooks.top">Talebook</a>
    </div>
    <p v-if="version">{{ $t('appHeader.systemVersion') }}: {{ version }}</p>
  </footer>
</template>

<script>
export default {
  name: 'WapFooter',
  computed: {
    version() {
      return this.$store.state.sys.version || '';
    }
  }
};
</script>

<style scoped>
.wap-footer {
  border-top: 1px solid #ccc;
  padding: 16px;
  text-align: center;
  font-size: 14px;
}
.wap-footer a {
  color: #333;
}
</style>
