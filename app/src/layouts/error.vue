<template>
  <v-app dark>
    <h1 v-if="error.statusCode === 404">
      {{ pageNotFound }}
    </h1>
    <h1 v-else>
      {{ otherError }}
    </h1>
    <NuxtLink to="/"> Home page </NuxtLink>
  </v-app>
</template>

<script>
export default {
  name: "EmptyLayout",
  layout: "empty",

  props: {
    error: {
      type: Object,
      default: null,
    },
  },
  created() {
    //this.$store.commit("puremode", true);
  },

  computed: {
    pageNotFound() {
      return this.$t ? this.$t("error_page_not_found") : "404: 页面已走失，请回首页";
    },
    otherError() {
      return this.$t ? this.$t("error_server_starting") : "[MyBooks] 服务正在启动中，稍后重试";
    },
  },
  head() {
    const title = this.error && this.error.statusCode === 404 ? this.pageNotFound : this.otherError;
    return {
      title,
    };
  },
};
</script>

<style scoped>
h1 {
  font-size: 20px;
}
.msg {
  text-align: center;
}
</style>

