<template>
  <header class="wap-header">
    <div class="wap-header-left">
      <template v-if="isLoggedIn">
        <img :src="user.avatar" class="user-avatar" alt="avatar" />
        <button class="logout-btn" @click="handleLogout">退出</button>
      </template>
      <template v-else>
        <button class="login-btn" @click="handleLogin">登录</button>
      </template>
    </div>
    <div class="wap-header-center">
      <a href="/wap" class="site-name">Talebook</a>
    </div>
  </header>
</template>

<script>
export default {
  name: 'WapHeader',
  data() {
    return {
    };
  },
  computed: {
    isLoggedIn() {
      return this.$store.state.user && this.$store.state.user.is_login;
    },
    user() {
      return this.$store.state.user || {};
    },
  },
  methods: {
    handleLogin() {
      this.$router.push('/wap/login');
    },
    handleLogout() {
      this.$router.push('/logout');
    }
  }
};
</script>

<style scoped>
.wap-header {
  border-bottom: 1px solid #ccc;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.wap-header-left button {
  padding: 4px 8px;
}
.site-name {
  font-weight: bold;
  font-size: 18px;
  text-decoration: none;
  color: #333;
}
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  margin-right: 8px;
}
</style>
