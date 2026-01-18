<template>
  <div class="webdav-page">
    <h1>{{ $t('webdav.introduction') }}</h1>
    <section>
      <h2>{{ $t('webdav.link') }}</h2>
      <p>{{ $t('webdav.linkDescription') }}<code>{{ opdsUrl }}</code></p>
    </section>
    <section>
      <h2>客户端访问</h2>
      <p>可以在任何支持WebDAV访问的阅读器、应用程序或者电子书上直接访问书库内容，如Koodo Reader，以及文石、汉王等设备。</p>
      <br/>
      <p>参考文章：<a href="https://mp.weixin.qq.com/s/82zFUwv46CLFzHnIf57IyQ" target="_blank" rel="noopener noreferrer">支持以WebDAV直接访问书库</a><br/>
        不支持匿名访问，需要输入书库中的用户名和密码。
      </p>
      <br/>
    </section>
  </div>
</template>

<script>
export default {
  data() {
    return {
      opdsUrl: process.client ? window.location.origin + '/books/' : ''
    }
  }
}
</script>

<style scoped>
.webdav-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
}

section {
  margin-bottom: 30px;
}

h2 {
  margin-bottom: 15px;
}

ul, ol {
  padding-left: 20px;
}

code {
  background: #f5f5f5;
  padding: 2px 5px;
  border-radius: 3px;
}
</style>
